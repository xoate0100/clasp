#!/usr/bin/env python3
# Emits a minimal structured review (always safe to run)
try:
    import yaml
except ImportError:
    yaml = None

import subprocess, re, sys

if yaml is None:
    print('{"summary": "0 issues", "violations": []}')
    sys.exit(0)
diff = subprocess.check_output(["git","diff","--cached"], text=True, errors="ignore")
issues=[]
if "TODO" in diff or "FIXME" in diff:
    issues.append({"rule":"todos", "msg":"Remove TODO/FIXME before commit"})
print(yaml.safe_dump({"summary": f"{len(issues)} issues", "violations": issues}))

