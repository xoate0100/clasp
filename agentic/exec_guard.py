"""
exec_guard.py — run a subprocess under hard resource caps.

Purpose: let an agent (or a human) execute tests and scripts without risking the
dev machine. Guards the classic "blow up the box" failure modes:
  - runaway / infinite loops            -> wall_timeout_s
  - memory leaks / blowups              -> max_memory_mb (tree RSS)
  - output floods (log/context blowups) -> max_output_bytes
  - fork bombs / unbounded spawn        -> max_subprocesses (tree child count)
  - CPU pegging                         -> max_cpu_seconds
  - hangs / undrained pipes             -> timeout + always-drained stdio

Cross-platform (Windows + POSIX). Stdlib alone enforces timeout, output cap, and
whole-tree kill; memory / cpu / subprocess-count caps use psutil when available
and become best-effort warnings when it is not installed.

Every run appends a JSON line to 6_ai_runtime_context/EXEC_GUARD_LOG.jsonl.

Programmatic:
    from agentic.exec_guard import run_guarded, Limits
    r = run_guarded([sys.executable, "script.py"], cwd=root,
                    limits=Limits(wall_timeout_s=120, max_memory_mb=1024))
    if r.killed: ...
    sys.exit(r.returncode)

CLI:
    python -m agentic.exec_guard --timeout 60 --max-memory-mb 1024 -- pytest -q
"""

from __future__ import annotations

import json
import os
import pathlib
import signal
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

try:
    import psutil  # optional: enables memory / cpu / subprocess-count caps
except Exception:  # pragma: no cover - psutil is optional
    psutil = None

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_LOG = REPO_ROOT / "6_ai_runtime_context" / "EXEC_GUARD_LOG.jsonl"
IS_WINDOWS = os.name == "nt"


@dataclass
class Limits:
    """Resource caps for a guarded run. 0 disables the CPU cap; others always apply."""

    wall_timeout_s: float = 300.0        # kill whole tree after this many seconds
    max_memory_mb: int = 2048            # kill if tree RSS exceeds this (needs psutil)
    max_output_bytes: int = 10_000_000   # kill after this much combined stdout+stderr
    max_subprocesses: int = 64           # kill if tree spawns more children (needs psutil)
    max_cpu_seconds: float = 0.0         # 0 = disabled; else kill on cumulative CPU (psutil)
    poll_interval_s: float = 0.25        # how often the monitor samples


@dataclass
class GuardResult:
    returncode: int
    killed: bool
    reason: str                # "" when clean; otherwise why the tree was killed
    duration_s: float
    peak_memory_mb: float
    max_children: int
    output_bytes: int
    truncated: bool
    stdout: str
    stderr: str
    cmd: list

    def ok(self) -> bool:
        return self.returncode == 0 and not self.killed


class _Reader(threading.Thread):
    """Drain a pipe on its own thread (avoids deadlock) and cap what we retain."""

    def __init__(self, stream, cap: int):
        super().__init__(daemon=True)
        self.stream = stream
        self.cap = cap
        self.buf = bytearray()
        self.count = 0
        self.truncated = False

    def run(self):
        try:
            for chunk in iter(lambda: self.stream.read(65536), b""):
                self.count += len(chunk)
                if len(self.buf) < self.cap:
                    self.buf.extend(chunk[: self.cap - len(self.buf)])
                else:
                    self.truncated = True
        except Exception:
            pass


def _popen_kwargs() -> dict:
    if IS_WINDOWS:
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"preexec_fn": os.setsid}  # new session -> killpg reaches the whole tree


def _kill_tree(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    if psutil is not None:
        try:
            parent = psutil.Process(proc.pid)
            procs = parent.children(recursive=True) + [parent]
            for p in procs:
                try:
                    p.terminate()
                except Exception:
                    pass
            _, alive = psutil.wait_procs(procs, timeout=2)
            for p in alive:
                try:
                    p.kill()
                except Exception:
                    pass
            return
        except Exception:
            pass
    # stdlib fallback
    try:
        if IS_WINDOWS:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def run_guarded(cmd, *, cwd=None, env=None, limits: Limits | None = None,
                log_path=None, label: str = "") -> GuardResult:
    """Run `cmd` under `limits`. Never raises for child failures; returns a GuardResult."""
    limits = limits or Limits()
    log_path = pathlib.Path(log_path) if log_path else DEFAULT_LOG
    cmd = [str(c) for c in cmd]
    start = time.monotonic()
    started_at = datetime.now(timezone.utc).isoformat()

    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **_popen_kwargs(),
    )
    out = _Reader(proc.stdout, limits.max_output_bytes)
    err = _Reader(proc.stderr, limits.max_output_bytes)
    out.start()
    err.start()

    reason = ""
    peak_mem = 0.0
    max_children = 0
    ps_proc = None
    if psutil is not None:
        try:
            ps_proc = psutil.Process(proc.pid)
        except Exception:
            ps_proc = None

    while proc.poll() is None:
        if time.monotonic() - start > limits.wall_timeout_s:
            reason = f"wall-timeout > {limits.wall_timeout_s}s"
            break
        if out.count + err.count > limits.max_output_bytes:
            reason = f"output-flood > {limits.max_output_bytes} bytes"
            break
        if ps_proc is not None:
            try:
                kids = ps_proc.children(recursive=True)
                max_children = max(max_children, len(kids))
                if len(kids) > limits.max_subprocesses:
                    reason = f"subprocess-explosion > {limits.max_subprocesses} children"
                    break
                rss = ps_proc.memory_info().rss
                for k in kids:
                    try:
                        rss += k.memory_info().rss
                    except Exception:
                        pass
                mb = rss / (1024 * 1024)
                peak_mem = max(peak_mem, mb)
                if mb > limits.max_memory_mb:
                    reason = f"memory > {limits.max_memory_mb} MB"
                    break
                if limits.max_cpu_seconds > 0:
                    ct = ps_proc.cpu_times()
                    if (ct.user + ct.system) > limits.max_cpu_seconds:
                        reason = f"cpu > {limits.max_cpu_seconds}s"
                        break
            except psutil.NoSuchProcess:
                break
            except Exception:
                pass
        time.sleep(limits.poll_interval_s)

    killed = bool(reason)
    if killed:
        _kill_tree(proc)

    try:
        proc.wait(timeout=5)
    except Exception:
        _kill_tree(proc)
        try:
            proc.wait(timeout=5)
        except Exception:
            pass

    out.join(timeout=2)
    err.join(timeout=2)

    returncode = proc.returncode if proc.returncode is not None else -1
    if killed and returncode == 0:
        returncode = 137  # conventional "process killed"

    result = GuardResult(
        returncode=returncode,
        killed=killed,
        reason=reason,
        duration_s=round(time.monotonic() - start, 3),
        peak_memory_mb=round(peak_mem, 1),
        max_children=max_children,
        output_bytes=out.count + err.count,
        truncated=out.truncated or err.truncated,
        stdout=out.buf.decode("utf-8", "replace"),
        stderr=err.buf.decode("utf-8", "replace"),
        cmd=cmd,
    )
    _log_event(log_path, result, started_at, label, limits)
    return result


def _log_event(log_path: pathlib.Path, result: GuardResult, started_at: str,
               label: str, limits: Limits) -> None:
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "ts": started_at,
            "label": label,
            "cmd": result.cmd,
            "returncode": result.returncode,
            "killed": result.killed,
            "reason": result.reason,
            "duration_s": result.duration_s,
            "peak_memory_mb": result.peak_memory_mb,
            "max_children": result.max_children,
            "output_bytes": result.output_bytes,
            "truncated": result.truncated,
            "psutil": psutil is not None,
            "limits": asdict(limits),
        }
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(event) + "\n")
    except Exception:
        pass  # logging must never crash a run


# ---- CLI --------------------------------------------------------------------
def _parse_cli(argv):
    import argparse

    p = argparse.ArgumentParser(prog="exec_guard", description="Run a command under resource caps.")
    p.add_argument("--timeout", type=float, default=Limits.wall_timeout_s, help="wall-clock seconds")
    p.add_argument("--max-memory-mb", type=int, default=Limits.max_memory_mb)
    p.add_argument("--max-output-bytes", type=int, default=Limits.max_output_bytes)
    p.add_argument("--max-subprocesses", type=int, default=Limits.max_subprocesses)
    p.add_argument("--max-cpu-seconds", type=float, default=Limits.max_cpu_seconds)
    p.add_argument("--label", default="")
    p.add_argument("--quiet", action="store_true", help="don't echo child output at end")
    p.add_argument("command", nargs=argparse.REMAINDER, help="-- then the command to run")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_cli(argv if argv is not None else sys.argv[1:])
    cmd = args.command
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        print("exec_guard: no command. Usage: python -m agentic.exec_guard [opts] -- <cmd...>", file=sys.stderr)
        return 2
    if psutil is None:
        print("[exec_guard] note: psutil not installed - memory/cpu/subprocess caps are best-effort "
              "(timeout + output cap still enforced).", file=sys.stderr)
    limits = Limits(
        wall_timeout_s=args.timeout,
        max_memory_mb=args.max_memory_mb,
        max_output_bytes=args.max_output_bytes,
        max_subprocesses=args.max_subprocesses,
        max_cpu_seconds=args.max_cpu_seconds,
    )
    result = run_guarded(cmd, limits=limits, label=args.label)
    if not args.quiet:
        if result.stdout:
            sys.stdout.write(result.stdout)
        if result.stderr:
            sys.stderr.write(result.stderr)
    if result.killed:
        print(f"\n[exec_guard] KILLED: {result.reason} (after {result.duration_s}s, "
              f"peak {result.peak_memory_mb}MB, {result.max_children} child procs)", file=sys.stderr)
    else:
        print(f"\n[exec_guard] done rc={result.returncode} in {result.duration_s}s "
              f"(peak {result.peak_memory_mb}MB)", file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
