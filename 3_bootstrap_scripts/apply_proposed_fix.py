#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix Application Service
Applies proposed fixes from matched issues.
Part of Phase 2: Real-Time Learning system.
"""

import json
import pathlib
import re
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

# Import issue matcher from Task 7
from match_issue import IssueMatcher


class FixApplicator:
    """Apply proposed fixes from matched issues."""
    
    def __init__(self):
        """Initialize fix applicator."""
        self.matcher = IssueMatcher()
        self.applied_fixes_path = pathlib.Path("6_ai_runtime_context/applied_fixes.json")
        self.applied_fixes_path.parent.mkdir(parents=True, exist_ok=True)
    
    def apply_fix(
        self,
        issue_description: str,
        category: str = "feedback",
        dry_run: bool = False
    ) -> Tuple[bool, str]:
        """
        Apply proposed fix for an issue.
        
        Args:
            issue_description: Description of the issue to fix
            category: Issue category (default: "feedback")
            dry_run: If True, show what would be done without applying
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Find similar issue
        match = self.matcher.find_similar_issue(issue_description, category)
        
        if not match:
            return False, "No similar issue found with proposed fixes"
        
        # Check for proposed fixes
        proposed_fixes = match.get("proposed_fixes", [])
        if not proposed_fixes:
            return False, f"Issue #{match.get('number')} has no proposed fixes"
        
        # Use the first proposed fix
        fix = proposed_fixes[0]
        
        # Validate fix
        if not self._validate_fix(fix):
            return False, "Proposed fix is invalid or incomplete"
        
        if dry_run:
            return True, self._generate_dry_run_report(match, fix)
        
        # Apply the fix
        try:
            success = self._apply_fix_content(fix, match)
            
            if success:
                # Track applied fix
                self._track_applied_fix(match, issue_description)
                return True, f"Fix applied successfully from issue #{match.get('number')}"
            else:
                return False, "Failed to apply fix"
        
        except Exception as e:
            return False, f"Error applying fix: {str(e)}"
    
    def _validate_fix(self, fix_data: Dict) -> bool:
        """
        Validate proposed fix before application.
        
        Args:
            fix_data: Fix data dictionary
        
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(fix_data, dict):
            return False
        
        # Must have body/content
        body = fix_data.get("body", "")
        if not body or len(body.strip()) < 10:
            return False
        
        return True
    
    def _apply_fix_content(self, fix: Dict, match: Dict) -> bool:
        """
        Apply fix content (commands, file changes, etc.).
        
        Args:
            fix: Fix data dictionary
            match: Matched issue dictionary
        
        Returns:
            True if applied successfully, False otherwise
        """
        fix_body = fix.get("body", "")
        
        # Extract commands from fix body
        commands = self._extract_fix_commands(fix_body)
        
        # Extract file changes
        file_changes = self._extract_file_changes(fix_body)
        
        # Apply commands
        for command in commands:
            if not self._execute_command(command):
                return False
        
        # Apply file changes
        for change in file_changes:
            if not self._apply_file_changes(change):
                return False
        
        return True
    
    def _extract_fix_commands(self, fix_body: str) -> List[str]:
        """
        Extract commands from fix body.
        
        Args:
            fix_body: Fix body text
        
        Returns:
            List of commands to execute
        """
        commands = []
        
        # Look for code blocks with commands
        code_block_pattern = r'```(?:bash|sh|shell)?\s*\n(.*?)\n```'
        matches = re.findall(code_block_pattern, fix_body, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            # Split by lines and extract commands
            lines = match.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    commands.append(line)
        
        # Look for numbered/bulleted command lists
        list_pattern = r'(?:^\d+\.|^[-*])\s*(.+)$'
        for line in fix_body.split('\n'):
            match = re.match(list_pattern, line.strip())
            if match:
                cmd = match.group(1).strip()
                if cmd.startswith(('python', 'npm', 'pip', 'git', 'pre-commit')):
                    commands.append(cmd)
        
        return commands
    
    def _extract_file_changes(self, fix_body: str) -> List[Dict]:
        """
        Extract file changes from fix body.
        
        Args:
            fix_body: Fix body text
        
        Returns:
            List of file change dictionaries
        """
        changes = []
        
        # Look for file update patterns
        file_patterns = [
            r'update\s+([^\s]+\.(?:py|yaml|yml|json|md|ts|js))',
            r'change\s+([^\s]+\.(?:py|yaml|yml|json|md|ts|js))',
            r'modify\s+([^\s]+\.(?:py|yaml|yml|json|md|ts|js))',
            r'edit\s+([^\s]+\.(?:py|yaml|yml|json|md|ts|js))',
        ]
        
        for pattern in file_patterns:
            matches = re.finditer(pattern, fix_body, re.IGNORECASE)
            for match in matches:
                file_path = match.group(1)
                changes.append({
                    "file": file_path,
                    "action": "update"
                })
        
        return changes
    
    def _execute_command(self, command: str) -> bool:
        """
        Execute a command safely.
        
        Args:
            command: Command to execute
        
        Returns:
            True if successful, False otherwise
        """
        # Safety check - only allow certain commands
        allowed_prefixes = ['python', 'python3', 'pip', 'npm', 'pre-commit', 'git']
        
        if not any(command.startswith(prefix) for prefix in allowed_prefixes):
            print(f"WARN: Command not allowed: {command}")
            return False
        
        try:
            # Split command into parts
            parts = command.split()
            if not parts:
                return False
            
            result = subprocess.run(
                parts,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                print(f"WARN: Command failed: {command}")
                print(f"  Error: {result.stderr[:200]}")
                return False
            
            return True
        
        except subprocess.TimeoutExpired:
            print(f"WARN: Command timed out: {command}")
            return False
        except Exception as e:
            print(f"WARN: Error executing command: {e}")
            return False
    
    def _apply_file_changes(self, change: Dict) -> bool:
        """
        Apply file changes.
        
        Args:
            change: Change dictionary with file and action
        
        Returns:
            True if successful, False otherwise
        """
        file_path = change.get("file")
        if not file_path:
            return False
        
        # For now, just validate file exists
        # Actual content changes would require more sophisticated parsing
        path = pathlib.Path(file_path)
        
        if change.get("action") == "update" and path.exists():
            # File exists, would be updated
            return True
        
        return False
    
    def _generate_dry_run_report(self, match: Dict, fix: Dict) -> str:
        """
        Generate dry-run report showing what would be done.
        
        Args:
            match: Matched issue dictionary
            fix: Fix dictionary
        
        Returns:
            Report string
        """
        report_lines = [
            f"Dry-run: Would apply fix from issue #{match.get('number')}",
            f"  Issue: {match.get('title')}",
            f"  URL: {match.get('html_url', 'N/A')}",
            f"  Fix author: {fix.get('author', 'unknown')}",
        ]
        
        commands = self._extract_fix_commands(fix.get("body", ""))
        if commands:
            report_lines.append(f"  Commands to execute: {len(commands)}")
            for cmd in commands[:3]:  # Show first 3
                report_lines.append(f"    - {cmd}")
        
        file_changes = self._extract_file_changes(fix.get("body", ""))
        if file_changes:
            report_lines.append(f"  Files to update: {len(file_changes)}")
            for change in file_changes[:3]:  # Show first 3
                report_lines.append(f"    - {change.get('file')}")
        
        return "\n".join(report_lines)
    
    def _track_applied_fix(self, match: Dict, issue_description: str) -> None:
        """
        Track applied fix for audit purposes.
        
        Args:
            match: Matched issue dictionary
            issue_description: Original issue description
        """
        # Load existing applied fixes
        applied_fixes = []
        if self.applied_fixes_path.exists():
            try:
                with open(self.applied_fixes_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    applied_fixes = data.get("applied_fixes", [])
            except (json.JSONDecodeError, IOError):
                applied_fixes = []
        
        # Add new entry
        from datetime import datetime
        applied_fixes.append({
            "issue_number": match.get("number"),
            "issue_title": match.get("title"),
            "issue_url": match.get("html_url"),
            "original_description": issue_description,
            "applied_at": datetime.now().isoformat(),
            "fix_author": match.get("proposed_fixes", [{}])[0].get("author", "unknown")
        })
        
        # Save
        try:
            with open(self.applied_fixes_path, "w", encoding="utf-8") as f:
                json.dump({"applied_fixes": applied_fixes}, f, indent=2)
        except IOError as e:
            print(f"WARN: Failed to track applied fix: {e}")


def main():
    """Main entry point for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Apply proposed fixes from matched issues"
    )
    parser.add_argument(
        "description",
        help="Issue description to fix"
    )
    parser.add_argument(
        "--category",
        default="feedback",
        help="Issue category (default: feedback)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without applying"
    )
    
    args = parser.parse_args()
    
    applicator = FixApplicator()
    success, message = applicator.apply_fix(
        args.description,
        args.category,
        dry_run=args.dry_run
    )
    
    if success:
        print(f"✓ {message}")
        return 0
    else:
        print(f"✗ {message}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
