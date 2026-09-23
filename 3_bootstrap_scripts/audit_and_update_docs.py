#!/usr/bin/env python3
"""
Documentation Audit and Update Script
Audits documentation structure, updates indexes, and ensures cross-references.
"""

import json
import pathlib
import re
from datetime import datetime
from typing import Dict, List, Set, Tuple

PROJECT_ROOT = pathlib.Path(__file__).parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
DOCS_INDEX_DIR = PROJECT_ROOT / "4_docs_index"


def find_all_docs() -> List[pathlib.Path]:
    """Find all markdown documentation files."""
    docs = []
    for md_file in DOCS_DIR.rglob("*.md"):
        if md_file.name.startswith("."):
            continue
        docs.append(md_file.relative_to(DOCS_DIR))
    return sorted(docs)


def extract_title(content: str) -> str:
    """Extract title from markdown file (first # heading)."""
    lines = content.split("\n")
    for line in lines[:20]:  # Check first 20 lines
        if line.startswith("# "):
            return line[2:].strip()
        if line.startswith("## "):
            return line[3:].strip()
    return "Untitled"


def categorize_doc(doc_path: pathlib.Path) -> str:
    """Categorize documentation by path and content."""
    path_str = str(doc_path).lower()
    
    # Core framework docs
    if "meta_framework" in path_str or "overview" in path_str:
        return "Core Framework"
    if "architecture" in path_str or "technical" in path_str:
        return "Architecture"
    
    # Hub-and-spoke model
    if "hub" in path_str or "spoke" in path_str:
        return "Hub-and-Spoke Model"
    
    # Versioning and updates
    if "version" in path_str or "upgrade" in path_str or "update" in path_str or "migration" in path_str:
        return "Versioning & Updates"
    
    # Feedback system
    if "feedback" in path_str:
        return "Feedback System"
    
    # Legacy upgrade
    if "legacy" in path_str:
        return "Legacy Upgrade"
    
    # Integration guides
    if "integration" in path_str or "guide" in path_str:
        return "Integration Guides"
    
    # Implementation summaries
    if "implementation" in path_str or "summary" in path_str:
        return "Implementation Summaries"
    
    # Analysis documents
    if "analysis" in path_str or "evaluation" in path_str:
        return "Analysis & Evaluation"
    
    # Execution and workflows
    if "execution" in path_str or "checklist" in path_str or "workflow" in path_str or "strategy" in path_str:
        return "Execution & Workflows"
    
    # Standards and templates
    if "template" in path_str or "standard" in path_str:
        return "Templates & Standards"
    
    return "Other"


def find_cross_references(content: str) -> List[str]:
    """Find markdown links in content."""
    # Pattern: [text](path) or [text](path#anchor)
    pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    matches = re.findall(pattern, content)
    return [path for _, path in matches if path.endswith('.md')]


def build_comprehensive_index() -> Dict:
    """Build comprehensive documentation index."""
    docs = find_all_docs()
    index = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_documents": len(docs),
        "categories": {},
        "documents": []
    }
    
    # Group by category
    for doc_path in docs:
        category = categorize_doc(doc_path)
        if category not in index["categories"]:
            index["categories"][category] = []
        
        try:
            full_path = DOCS_DIR / doc_path
            content = full_path.read_text(encoding="utf-8")
            title = extract_title(content)
            cross_refs = find_cross_references(content)
            
            doc_entry = {
                "path": str(doc_path).replace("\\", "/"),
                "title": title,
                "category": category,
                "cross_references": cross_refs,
                "size_bytes": full_path.stat().st_size,
                "modified": datetime.fromtimestamp(full_path.stat().st_mtime).isoformat() + "Z"
            }
            
            index["categories"][category].append(doc_entry)
            index["documents"].append(doc_entry)
        except Exception as e:
            print(f"WARN: Could not process {doc_path}: {e}")
    
    return index


def generate_markdown_index(index: Dict) -> str:
    """Generate markdown documentation index."""
    lines = [
        "# Documentation Index",
        "",
        f"*Last updated: {index['generated_at']}*",
        f"*Total documents: {index['total_documents']}*",
        "",
        "## Table of Contents",
        ""
    ]
    
    # Add category links
    for category in sorted(index["categories"].keys()):
        anchor = category.lower().replace(" ", "-").replace("&", "")
        lines.append(f"- [{category}](#{anchor})")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Add categorized sections
    for category in sorted(index["categories"].keys()):
        lines.append(f"## {category}")
        lines.append("")
        
        docs_in_category = sorted(
            index["categories"][category],
            key=lambda x: x["title"]
        )
        
        for doc in docs_in_category:
            lines.append(f"- [{doc['title']}]({doc['path']})")
            if doc["cross_references"]:
                refs_str = ", ".join([f"[{r}]({r})" for r in doc["cross_references"][:3]])
                if len(doc["cross_references"]) > 3:
                    refs_str += f" (+{len(doc['cross_references']) - 3} more)"
                lines.append(f"  - *References: {refs_str}*")
        
        lines.append("")
    
    # Add cross-reference map
    lines.append("---")
    lines.append("")
    lines.append("## Cross-Reference Map")
    lines.append("")
    lines.append("### Documents by Topic")
    lines.append("")
    
    # Group by topic keywords
    topics = {
        "Hub-and-Spoke": ["hub", "spoke", "template", "update", "version"],
        "Feedback": ["feedback", "issue", "report"],
        "Governance": ["governance", "constitution", "sandbox", "rules"],
        "State Management": ["state", "plan", "task", "pointer", "intent"],
        "Testing": ["test", "tdd", "coverage"],
        "Architecture": ["architecture", "solid", "layer", "component"],
    }
    
    for topic, keywords in topics.items():
        lines.append(f"#### {topic}")
        matching_docs = []
        for doc in index["documents"]:
            path_lower = doc["path"].lower()
            title_lower = doc["title"].lower()
            if any(kw in path_lower or kw in title_lower for kw in keywords):
                matching_docs.append(doc)
        
        for doc in sorted(matching_docs, key=lambda x: x["title"]):
            lines.append(f"- [{doc['title']}]({doc['path']})")
        lines.append("")
    
    return "\n".join(lines)


def update_json_index(index: Dict) -> None:
    """Update JSON index file."""
    output_path = DOCS_DIR / "index.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, sort_keys=True)
    print(f"OK: Updated {output_path}")


def update_markdown_index(index: Dict) -> None:
    """Update markdown index file."""
    output_path = DOCS_DIR / "DOCUMENTATION_INDEX.md"
    content = generate_markdown_index(index)
    
    # Preserve any custom content before/after auto-generated section
    if output_path.exists():
        existing = output_path.read_text(encoding="utf-8")
        # Look for custom sections
        if "<!-- AUTO-GENERATED START -->" in existing:
            parts = existing.split("<!-- AUTO-GENERATED START -->")
            if len(parts) == 2:
                custom_header = parts[0]
                if "<!-- AUTO-GENERATED END -->" in parts[1]:
                    custom_footer = parts[1].split("<!-- AUTO-GENERATED END -->")[1]
                    content = f"{custom_header}<!-- AUTO-GENERATED START -->\n\n{content}\n\n<!-- AUTO-GENERATED END -->{custom_footer}"
    
    output_path.write_text(content, encoding="utf-8")
    print(f"OK: Updated {output_path}")


def check_orphaned_docs(index: Dict) -> List[str]:
    """Check for documents with no cross-references."""
    orphaned = []
    for doc in index["documents"]:
        # Count how many other docs reference this one
        references = 0
        for other_doc in index["documents"]:
            if doc["path"] in other_doc["cross_references"]:
                references += 1
        
        if references == 0 and doc["category"] != "Other":
            orphaned.append(doc["path"])
    
    return orphaned


def check_broken_links(index: Dict) -> List[Tuple[str, str]]:
    """Check for broken cross-references."""
    broken = []
    all_paths = {doc["path"] for doc in index["documents"]}
    
    # Also check for files outside docs/ directory
    project_root = PROJECT_ROOT
    docs_dir = DOCS_DIR
    
    for doc in index["documents"]:
        for ref in doc["cross_references"]:
            # Normalize path
            ref_normalized = ref.split("#")[0]  # Remove anchor
            
            # Skip example/placeholder links
            if "path/to/" in ref_normalized or "example" in ref_normalized.lower():
                continue
            
            # Check if it's in docs/
            if ref_normalized not in all_paths:
                # Check if it's outside docs/ (relative path)
                if ref_normalized.startswith("../"):
                    # Try to resolve relative path
                    ref_path = (docs_dir / doc["path"]).parent / ref_normalized
                    if not ref_path.exists():
                        broken.append((doc["path"], ref))
                else:
                    broken.append((doc["path"], ref))
    
    return broken


def main():
    """Main execution."""
    import sys
    import io
    
    # Fix Windows encoding issues
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    print("Auditing documentation...")
    
    # Build index
    index = build_comprehensive_index()
    
    # Update indexes
    update_json_index(index)
    update_markdown_index(index)
    
    # Check for issues
    orphaned = check_orphaned_docs(index)
    broken = check_broken_links(index)
    
    # Report
    print(f"\nDocumentation Statistics:")
    print(f"   Total documents: {index['total_documents']}")
    print(f"   Categories: {len(index['categories'])}")
    
    for category, docs in sorted(index["categories"].items()):
        print(f"   - {category}: {len(docs)} documents")
    
    if orphaned:
        print(f"\nWARN: Orphaned documents (no cross-references): {len(orphaned)}")
        for doc in orphaned[:5]:
            print(f"   - {doc}")
        if len(orphaned) > 5:
            print(f"   ... and {len(orphaned) - 5} more")
    
    if broken:
        print(f"\nERROR: Broken links: {len(broken)}")
        for doc, ref in broken[:5]:
            print(f"   - {doc} -> {ref}")
        if len(broken) > 5:
            print(f"   ... and {len(broken) - 5} more")
    
    if not orphaned and not broken:
        print("\nOK: All documentation is properly cross-referenced!")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
