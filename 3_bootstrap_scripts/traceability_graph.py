#!/usr/bin/env python3
import json, subprocess, re, pathlib
out = {"nodes": [], "edges": []}
logs = subprocess.check_output(["git","log","--pretty=%H%x09%s"], text=True, errors="ignore")
for line in logs.splitlines():
    h, s = (line.split("\t")+["",""])[:2]
    m = re.search(r"plan:([^\s]+)\s+component:([^\s]+)\s+task:([^\s]+)", s or "")
    if m:
        out["nodes"].append({"commit": h, "plan": m.group(1), "component": m.group(2), "task": m.group(3)})
pathlib.Path("ai_reports").mkdir(exist_ok=True)
pathlib.Path("ai_reports/traceability.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print("[traceability] generated ai_reports/traceability.json")

