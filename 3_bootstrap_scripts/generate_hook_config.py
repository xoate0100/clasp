#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hook Configuration Generator
Generates environment-specific pre-commit hook configurations.
"""

import yaml
import pathlib
from typing import Dict, List, Optional, Any
from detect_environment import EnvironmentDetector, Environment


class HookConfigGenerator:
    """Generate environment-specific hook configurations."""
    
    def __init__(self, detector: Optional[EnvironmentDetector] = None):
        """Initialize hook config generator."""
        self.detector = detector or EnvironmentDetector()
        self.env = self.detector.detected_env
    
    def generate_precommit_config(self) -> Dict[str, Any]:
        """Generate pre-commit configuration for current environment."""
        base_config = {
            "repos": [],
            "default_language_version": {
                "python": "3.10"
            }
        }
        
        # Add environment-specific repos
        repos = self._get_base_repos()
        
        # Adapt repos for current environment
        adapted_repos = []
        for repo in repos:
            adapted = self._adapt_repo_for_environment(repo)
            if adapted:
                adapted_repos.append(adapted)
        
        base_config["repos"] = adapted_repos
        
        return base_config
    
    def _get_base_repos(self) -> List[Dict[str, Any]]:
        """Get base repository configurations."""
        return [
            {
                "repo": "https://github.com/pre-commit/pre-commit-hooks",
                "hooks": [
                    {"id": "trailing-whitespace"},
                    {"id": "end-of-file-fixer"},
                    {"id": "check-yaml"},
                    {"id": "check-json"},
                    {"id": "check-added-large-files"},
                    {"id": "check-merge-conflict"},
                ]
            },
            {
                "repo": "local",
                "hooks": self._get_local_hooks()
            }
        ]
    
    def _get_local_hooks(self) -> List[Dict[str, Any]]:
        """Get local hook configurations adapted for environment."""
        python_cmd = self.detector.get_python_command()
        shell_cmd = self.detector.get_shell_command()
        
        hooks = [
            {
                "id": "syntax-checks",
                "name": "Syntax & Structural Validation",
                "entry": f"{python_cmd} -m py_compile",
                "language": "system",
                "types": ["python"],
                "pass_filenames": True
            },
            {
                "id": "format-style",
                "name": "Style Enforcement",
                "entry": f"{python_cmd} -m black --check",
                "language": "system",
                "types": ["python"],
                "pass_filenames": True
            },
            {
                "id": "static-analysis",
                "name": "Type & Static Analysis",
                "entry": f"{python_cmd} -m pylint",
                "language": "system",
                "types": ["python"],
                "pass_filenames": True
            },
            {
                "id": "security-scan",
                "name": "Security & Secrets",
                "entry": f"{python_cmd} -m bandit -r .",
                "language": "system",
                "types": ["python"],
                "pass_filenames": False
            },
            {
                "id": "architecture-check",
                "name": "Architecture & SOLID Enforcement",
                "entry": f"{python_cmd} 3_bootstrap_scripts/architecture_check.py",
                "language": "system",
                "pass_filenames": True
            },
            {
                "id": "ai-behavior-validation",
                "name": "AI Behavior Containment",
                "entry": f"{python_cmd} 3_bootstrap_scripts/ai_behavior_validation.py",
                "language": "system",
                "pass_filenames": True
            },
            {
                "id": "check-context-staleness",
                "name": "AI Context Staleness Check",
                "entry": f"{python_cmd} 3_bootstrap_scripts/check_context_staleness.py",
                "language": "system",
                "pass_filenames": False
            },
            {
                "id": "check-governance-install",
                "name": "Governance Installation Check",
                "entry": f"{python_cmd} 3_bootstrap_scripts/check_governance_install.py",
                "language": "system",
                "pass_filenames": False
            },
            {
                "id": "task-completion-gate",
                "name": "Task Completion Gate",
                "entry": f"{python_cmd} 3_bootstrap_scripts/task_completion_gate.py",
                "language": "system",
                "pass_filenames": False
            },
            {
                "id": "check-state-transition",
                "name": "State Transition Validation",
                "entry": f"{python_cmd} 3_bootstrap_scripts/check_state_transition.py",
                "language": "system",
                "pass_filenames": False
            },
            {
                "id": "guardrail-enforcement",
                "name": "Guardrail Enforcement",
                "entry": f"{python_cmd} 3_bootstrap_scripts/guardrail_enforcement.py",
                "language": "system",
                "pass_filenames": True
            },
            {
                "id": "tests-and-coverage",
                "name": "Tests & Coverage",
                "entry": f"{python_cmd} -m pytest --cov --cov-report=term-missing",
                "language": "system",
                "types": ["python"],
                "pass_filenames": False
            }
        ]
        
        # Adapt hooks for environment
        adapted_hooks = []
        for hook in hooks:
            adapted = self.adapt_hook_entry(hook)
            adapted_hooks.append(adapted)
        
        return adapted_hooks
    
    def adapt_hook_entry(self, hook_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt hook entry for current environment."""
        adapted = hook_entry.copy()
        entry = adapted.get("entry", "")
        
        # Adapt entry command for environment
        if self.env in [Environment.WINDOWS_CMD, Environment.WINDOWS_POWERSHELL]:
            # Windows: Replace bash with appropriate shell
            if "bash" in entry.lower():
                shell_cmd = self.detector.get_shell_command()
                # Replace first occurrence of bash with shell command
                entry = entry.replace("bash", shell_cmd, 1)
        # Unix-like systems (WSL, Linux, macOS) can use bash as-is
        
        # Normalize paths in entry
        adapted["entry"] = self.detector.normalize_path(entry)
        
        return adapted
    
    def normalize_hook_paths(self, hook_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize paths in hook entry for current environment."""
        adapted = hook_entry.copy()
        entry = adapted.get("entry", "")
        
        # Normalize paths using detector
        normalized_entry = self.detector.normalize_path(entry)
        adapted["entry"] = normalized_entry
        
        return adapted
    
    def _adapt_repo_for_environment(self, repo: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Adapt repository configuration for environment."""
        if repo.get("repo") == "local":
            # Local hooks are already adapted
            return repo
        
        # Standard repos work across environments
        return repo
    
    def validate_config_structure(self, config: Dict[str, Any]) -> bool:
        """Validate pre-commit config structure."""
        if not isinstance(config, dict):
            return False
        
        if "repos" not in config:
            return False
        
        if not isinstance(config["repos"], list):
            return False
        
        # Validate each repo entry
        for repo in config["repos"]:
            if not isinstance(repo, dict):
                return False
            if "repo" not in repo:
                return False
        
        return True
    
    def read_existing_config(self, config_path: str) -> Optional[Dict[str, Any]]:
        """Read existing pre-commit config file."""
        path = pathlib.Path(config_path)
        if not path.exists():
            return None
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                return config if self.validate_config_structure(config) else None
        except Exception:
            return None
    
    def write_config_file(self, config: Dict[str, Any], output_path: str) -> bool:
        """Write pre-commit config to file."""
        if not self.validate_config_structure(config):
            return False
        
        try:
            path = pathlib.Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            return True
        except Exception:
            return False
    
    def merge_with_existing(self, new_config: Dict[str, Any], 
                           existing_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge new config with existing config."""
        merged = existing_config.copy()
        
        # Merge repos
        existing_repos = {r.get("repo"): r for r in merged.get("repos", [])}
        new_repos = {r.get("repo"): r for r in new_config.get("repos", [])}
        
        # Update or add repos
        for repo_url, repo_config in new_repos.items():
            existing_repos[repo_url] = repo_config
        
        merged["repos"] = list(existing_repos.values())
        
        return merged


def main():
    """Main entry point for testing."""
    generator = HookConfigGenerator()
    
    print(f"Generating hook config for: {generator.env.value}")
    
    config = generator.generate_precommit_config()
    
    if generator.validate_config_structure(config):
        print("✅ Config structure valid")
        print(f"Repos: {len(config.get('repos', []))}")
        local_repos = [r for r in config.get('repos', []) if r.get('repo') == 'local']
        local_hooks_count = len(local_repos[0].get('hooks', [])) if local_repos else 0
        print(f"Local hooks: {local_hooks_count}")
    else:
        print("❌ Config structure invalid")
        return 1
    
    # Test write
    test_path = ".pre-commit-config.generated.yaml"
    if generator.write_config_file(config, test_path):
        print(f"✅ Config written to {test_path}")
        pathlib.Path(test_path).unlink()  # Clean up
    else:
        print("❌ Failed to write config")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
