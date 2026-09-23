#!/usr/bin/env python3
"""Documentation sync — ensure index exists and refresh optional doc lifecycle artifacts."""

import pathlib
import sys

REPO_ROOT = pathlib.Path(".").resolve()
sys.path.insert(0, str(REPO_ROOT))

idx = REPO_ROOT / "4_docs_index" / "DOCUMENTATION_INDEX.md"
if not idx.exists():
    idx.parent.mkdir(parents=True, exist_ok=True)
    idx.write_text(
        "# Documentation Index\n\n"
        "<!-- AUTO-GENERATED ACTIVE DOCS START -->\n"
        "| Doc | Status |\n|-----|--------|\n| *(pending sync)* | active |\n"
        "<!-- AUTO-GENERATED ACTIVE DOCS END -->\n\n"
        "<!-- AUTO-GENERATED ARCHIVE TABLE START -->\n"
        "| Archived doc | Date | Superseded by |\n|-------------|------|----------------|\n"
        "| *(none yet)* | — | — |\n"
        "<!-- AUTO-GENERATED ARCHIVE TABLE END -->\n",
        encoding="utf-8",
    )

try:
    from agentic.optional_tools import is_tool_enabled

    if is_tool_enabled("doc_lifecycle", REPO_ROOT):
        from agentic.doc_governance import sync_archive_readme, sync_documentation_index
        from agentic.docs_lifecycle import refresh_human_docs

        refresh_human_docs(REPO_ROOT)
        sync_documentation_index(REPO_ROOT)
        sync_archive_readme(REPO_ROOT)
except ImportError:
    pass

print("[docs] sync complete")
