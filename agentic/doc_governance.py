"""Documentation governance — index sync, archive validation, deprecation enforcement."""

from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

MANIFEST_PATH = REPO_ROOT / "docs" / "DOC_MANIFEST.yaml"
DOCS_INDEX_PATH = REPO_ROOT / "4_docs_index" / "DOCUMENTATION_INDEX.md"
ARCHIVE_README = REPO_ROOT / "docs" / "archive" / "README.md"
MASTER_INDEX = REPO_ROOT / "docs" / "MASTER_INDEX.md"

ACTIVE_DOCS_START = "<!-- AUTO-GENERATED ACTIVE DOCS START -->"
ACTIVE_DOCS_END = "<!-- AUTO-GENERATED ACTIVE DOCS END -->"
ARCHIVE_TABLE_START = "<!-- AUTO-GENERATED ARCHIVE TABLE START -->"
ARCHIVE_TABLE_END = "<!-- AUTO-GENERATED ARCHIVE TABLE END -->"


@dataclass(frozen=True)
class DocMeta:
    path: str
    status: str
    superseded_by: str | None = None
    archived_date: str | None = None


DEPRECATED_RE = re.compile(
    r">\s*\*\*Deprecated\.\*\*\s*Superseded by\s*\[[^\]]+\]\(([^)]+)\)",
    re.IGNORECASE,
)
ARCHIVED_RE = re.compile(
    r">\s*\*\*Archived on\*\*\s*(\d{4}-\d{2}-\d{2})\.\s*Superseded by\s*\[[^\]]+\]\(([^)]+)\)",
    re.IGNORECASE,
)
LINK_RE = re.compile(r"\]\(([^)#]+)")


def _load_manifest() -> dict:
    if yaml is None or not MANIFEST_PATH.exists():
        return {}
    with open(MANIFEST_PATH, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


def parse_doc_meta(path: pathlib.Path, root: pathlib.Path | None = None) -> DocMeta:
    root = root or REPO_ROOT
    rel = str(path.relative_to(root)).replace("\\", "/")
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    head = "\n".join(text.splitlines()[:8])

    if rel.startswith("docs/archive/") and path.name != "README.md":
        match = ARCHIVED_RE.search(head)
        if match:
            return DocMeta(
                path=rel,
                status="archived",
                archived_date=match.group(1),
                superseded_by=match.group(2),
            )
        return DocMeta(path=rel, status="archived")

    match = DEPRECATED_RE.search(head)
    if match:
        return DocMeta(path=rel, status="deprecated", superseded_by=match.group(1))

    return DocMeta(path=rel, status="active")


def collect_docs(root: pathlib.Path | None = None) -> list[pathlib.Path]:
    root = root or REPO_ROOT
    docs_dir = root / "docs"
    paths: list[pathlib.Path] = []
    if not docs_dir.exists():
        return paths
    for path in sorted(docs_dir.rglob("*.md")):
        if path.name == "README.md" and path.parent.name == "archive":
            continue
        paths.append(path)
    return paths


def collect_archived_docs(root: pathlib.Path | None = None) -> list[pathlib.Path]:
    root = root or REPO_ROOT
    archive = root / "docs" / "archive"
    if not archive.exists():
        return []
    return sorted(p for p in archive.glob("*.md") if p.name != "README.md")


def _replace_block(content: str, start: str, end: str, body: str) -> str:
    if start not in content or end not in content:
        raise ValueError(f"Missing markers {start} / {end}")
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    replacement = f"{start}\n{body}\n{end}"
    new_content, count = pattern.subn(replacement, content, count=1)
    if count != 1:
        raise ValueError("Failed to replace auto-generated block")
    return new_content


def render_active_docs_table(active: list[DocMeta]) -> str:
    lines = ["| Doc | Status |", "|-----|--------|"]
    for meta in sorted(active, key=lambda m: m.path):
        if meta.path.startswith("docs/archive/"):
            continue
        lines.append(f"| `{meta.path}` | {meta.status} |")
    return "\n".join(lines)


def render_archive_table(archived: list[DocMeta]) -> str:
    lines = ["| Archived doc | Date | Superseded by |", "|-------------|------|----------------|"]
    rows = [m for m in archived if m.status == "archived" and not m.path.endswith("README.md")]
    if not rows:
        lines.append("| *(none yet)* | — | — |")
    else:
        for meta in sorted(rows, key=lambda m: m.path):
            lines.append(
                f"| `{meta.path}` | {meta.archived_date or '—'} | `{meta.superseded_by or '—'}` |"
            )
    return "\n".join(lines)


def sync_documentation_index(root: pathlib.Path | None = None) -> bool:
    root = root or REPO_ROOT
    if not DOCS_INDEX_PATH.exists():
        return False
    if ACTIVE_DOCS_START not in DOCS_INDEX_PATH.read_text(encoding="utf-8"):
        return False

    metas = [parse_doc_meta(p, root) for p in collect_docs(root)]
    active = [m for m in metas if m.status in ("active", "deprecated")]
    archived = [parse_doc_meta(p, root) for p in collect_archived_docs(root)]

    content = DOCS_INDEX_PATH.read_text(encoding="utf-8")
    new_content = _replace_block(
        content,
        ACTIVE_DOCS_START,
        ACTIVE_DOCS_END,
        render_active_docs_table(active),
    )
    new_content = _replace_block(
        new_content,
        ARCHIVE_TABLE_START,
        ARCHIVE_TABLE_END,
        render_archive_table(archived),
    )
    if new_content != content:
        DOCS_INDEX_PATH.write_text(new_content, encoding="utf-8")
        return True
    return False


def sync_archive_readme(root: pathlib.Path | None = None) -> bool:
    root = root or REPO_ROOT
    if not ARCHIVE_README.exists():
        return False
    archived = [parse_doc_meta(p, root) for p in collect_archived_docs(root)]
    content = ARCHIVE_README.read_text(encoding="utf-8")
    if ARCHIVE_TABLE_START not in content:
        return False
    new_content = _replace_block(
        content,
        ARCHIVE_TABLE_START,
        ARCHIVE_TABLE_END,
        render_archive_table(archived),
    )
    if new_content != content:
        ARCHIVE_README.write_text(new_content, encoding="utf-8")
        return True
    return False


def validate_doc_governance(root: pathlib.Path | None = None) -> list[str]:
    root = root or REPO_ROOT
    errors: list[str] = []
    manifest = _load_manifest()
    exempt = set(manifest.get("generated_or_exempt") or [])

    for path in collect_docs(root):
        rel = str(path.relative_to(root)).replace("\\", "/")
        if rel.startswith("docs/archive/"):
            continue
        meta = parse_doc_meta(path, root)
        if meta.status == "deprecated":
            errors.append(
                f"{rel}: deprecated — run `python 3_bootstrap_scripts/docs_archive.py archive {rel}`"
            )

    for path in collect_archived_docs(root):
        rel = str(path.relative_to(root)).replace("\\", "/")
        meta = parse_doc_meta(path, root)
        if not meta.archived_date:
            errors.append(f"{rel}: missing archive header (Archived on YYYY-MM-DD)")
        if meta.superseded_by:
            target = (root / meta.superseded_by).resolve()
            if not target.exists():
                errors.append(f"{rel}: superseded_by target missing -> {meta.superseded_by}")

    for path in collect_docs(root):
        rel = str(path.relative_to(root)).replace("\\", "/")
        if rel.startswith("docs/archive/"):
            continue
        if rel in exempt:
            continue
        text = path.read_text(encoding="utf-8")
        base = path.parent
        for match in LINK_RE.finditer(text):
            target = match.group(1).strip()
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            if target in ("path", "doc", "new-doc", "path/to/file.md", "../relative/path.md"):
                continue
            if "FILE.md" in target or "FILE.json" in target:
                continue
            resolved = (base / target).resolve()
            if not resolved.exists():
                planned = set(manifest.get("planned_doc_paths") or [])
                try:
                    rel_target = str(resolved.relative_to(root)).replace("\\", "/")
                except ValueError:
                    rel_target = target
                if rel_target in planned or target in planned:
                    continue
                errors.append(f"{rel}: broken link -> {target}")

    if MASTER_INDEX.exists():
        master_text = MASTER_INDEX.read_text(encoding="utf-8")
        for rel in manifest.get("onboarding_chain") or []:
            if rel.endswith("MASTER_INDEX.md"):
                continue
            if rel not in master_text and pathlib.Path(rel).name not in master_text:
                errors.append(f"{rel}: missing from docs/MASTER_INDEX.md (onboarding chain)")

    return errors


def archive_document(source_rel: str, superseded_by: str, root: pathlib.Path | None = None) -> pathlib.Path:
    root = root or REPO_ROOT
    source = root / source_rel
    if not source.exists():
        raise FileNotFoundError(source_rel)

    archive_dir = root / "docs" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    dest = archive_dir / source.name
    if dest.exists():
        raise FileExistsError(f"already archived: {dest.relative_to(root)}")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    original = source.read_text(encoding="utf-8")
    header = f"> **Archived on** {today}. Superseded by [successor]({superseded_by}).\n\n"
    dest.write_text(header + original, encoding="utf-8")
    source.unlink()

    sync_documentation_index(root)
    sync_archive_readme(root)
    return dest


def deprecate_document(source_rel: str, superseded_by: str, root: pathlib.Path | None = None) -> None:
    root = root or REPO_ROOT
    source = root / source_rel
    if not source.exists():
        raise FileNotFoundError(source_rel)
    text = source.read_text(encoding="utf-8")
    if DEPRECATED_RE.search("\n".join(text.splitlines()[:8])):
        return
    header = f"> **Deprecated.** Superseded by [successor]({superseded_by}).\n\n"
    source.write_text(header + text, encoding="utf-8")
