#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Issue Matching Service
Matches new issues against knowledge base to find similar issues and proposed fixes.
Part of Phase 2: Real-Time Learning system.
"""

import json
import pathlib
import sys
from typing import Dict, List, Optional

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install pyyaml")
    sys.exit(1)

# Import issue knowledge base from Task 6
from query_issue_knowledge import IssueKnowledgeBase


class IssueMatcher:
    """Match issues against knowledge base to find similar issues and fixes."""
    
    def __init__(self):
        """Initialize issue matcher."""
        self.local_db_path = pathlib.Path("6_ai_runtime_context/issue_matches.json")
        self.local_db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def find_similar_issue(
        self,
        issue_description: str,
        category: str = "feedback",
        threshold: float = 0.7
    ) -> Optional[Dict]:
        """
        Find similar issue in local database or query knowledge base.
        
        Args:
            issue_description: Description of the issue to match
            category: Issue category (default: "feedback")
            threshold: Minimum similarity score (default: 0.7)
        
        Returns:
            Best match if similarity >= threshold, None otherwise
        """
        # Check local database first
        local_match = self._check_local_issues(issue_description, category, threshold)
        if local_match:
            return local_match
        
        # Query knowledge base
        manifest = self._load_version_manifest()
        template_repo = manifest.get("template_repo", "")
        
        if not template_repo:
            return None
        
        # Convert full URL to owner/repo format if needed
        template_repo = self._normalize_repo_url(template_repo)
        
        try:
            kb = IssueKnowledgeBase(template_repo)
            similar_issues = kb.query_similar_issues(issue_description, category)
            
            if similar_issues and similar_issues[0].get("similarity_score", 0.0) >= threshold:
                best_match = similar_issues[0]
                
                # Store in local database
                self._store_local_issue(issue_description, best_match, category)
                
                return best_match
        
        except Exception as e:
            print(f"WARN: Failed to query knowledge base: {e}")
        
        return None
    
    def _check_local_issues(
        self,
        description: str,
        category: str,
        threshold: float
    ) -> Optional[Dict]:
        """
        Check local issue database for matches.
        
        Args:
            description: Issue description
            category: Issue category
            threshold: Minimum similarity score
        
        Returns:
            Match if found and above threshold, None otherwise
        """
        if not self.local_db_path.exists():
            return None
        
        try:
            with open(self.local_db_path, "r", encoding="utf-8") as f:
                db_data = json.load(f)
            
            issues = db_data.get("issues", [])
            
            # Find matching issue
            for entry in issues:
                if (entry.get("description") == description and 
                    entry.get("category") == category):
                    match = entry.get("match", {})
                    similarity = match.get("similarity_score", 0.0)
                    
                    if similarity >= threshold:
                        return match
            
            return None
        
        except (json.JSONDecodeError, IOError, KeyError):
            return None
    
    def _store_local_issue(
        self,
        description: str,
        match: Dict,
        category: str
    ) -> None:
        """
        Store issue match in local database.
        
        Args:
            description: Issue description
            match: Match dictionary with issue details
            category: Issue category
        """
        # Load existing database
        db_data = {"issues": []}
        if self.local_db_path.exists():
            try:
                with open(self.local_db_path, "r", encoding="utf-8") as f:
                    db_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                db_data = {"issues": []}
        
        # Check if entry already exists
        issues = db_data.get("issues", [])
        for entry in issues:
            if (entry.get("description") == description and 
                entry.get("category") == category):
                # Update existing entry
                entry["match"] = match
                entry["updated_at"] = self._get_timestamp()
                break
        else:
            # Add new entry
            issues.append({
                "description": description,
                "category": category,
                "match": match,
                "created_at": self._get_timestamp(),
                "updated_at": self._get_timestamp()
            })
        
        db_data["issues"] = issues
        
        # Save database
        try:
            with open(self.local_db_path, "w", encoding="utf-8") as f:
                json.dump(db_data, f, indent=2)
        except IOError as e:
            print(f"WARN: Failed to save local issue database: {e}")
    
    def _load_version_manifest(self) -> Dict:
        """
        Load version manifest to get template repository.
        
        Returns:
            Version manifest dictionary
        """
        manifest_path = pathlib.Path("0_phase0_bootstrap/META_FRAMEWORK_VERSION.yaml")
        
        if not manifest_path.exists():
            return {}
        
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = yaml.safe_load(f)
                return manifest or {}
        except (yaml.YAMLError, IOError):
            return {}
    
    def _get_timestamp(self) -> str:
        """Get current timestamp as ISO string."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _normalize_repo_url(self, repo_string: str) -> str:
        """
        Normalize repository URL to owner/repo format.
        
        Args:
            repo_string: Repository URL or owner/repo string
        
        Returns:
            Normalized owner/repo format
        """
        import re
        
        # If already in owner/repo format, return as-is
        if "/" in repo_string and not repo_string.startswith("http"):
            return repo_string
        
        # Extract owner/repo from URL
        match = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$", repo_string)
        if match:
            return f"{match.group(1)}/{match.group(2)}"
        
        # Return as-is if can't parse
        return repo_string


def main():
    """Main entry point for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Match issues against knowledge base"
    )
    parser.add_argument(
        "description",
        help="Issue description to match"
    )
    parser.add_argument(
        "--category",
        default="feedback",
        help="Issue category (default: feedback)"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.7,
        help="Similarity threshold (default: 0.7)"
    )
    
    args = parser.parse_args()
    
    matcher = IssueMatcher()
    match = matcher.find_similar_issue(
        args.description,
        args.category,
        args.threshold
    )
    
    if match:
        print(f"Found similar issue:")
        print(f"  Issue #{match.get('number')}: {match.get('title')}")
        print(f"  Similarity: {match.get('similarity_score', 0):.2%}")
        print(f"  URL: {match.get('html_url', 'N/A')}")
        if match.get('proposed_fixes'):
            print(f"  Proposed fixes: {len(match['proposed_fixes'])}")
        return 0
    else:
        print("No similar issue found above threshold.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
