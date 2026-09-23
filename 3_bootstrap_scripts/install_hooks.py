#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cross-Platform Hook Installer
Installs pre-commit hooks with environment-specific setup.
"""

import subprocess
import pathlib
import sys
from typing import Tuple, Optional

# Import environment detection and config generation
from detect_environment import EnvironmentDetector
from generate_hook_config import HookConfigGenerator


class HookInstaller:
    """Install hooks with environment-specific setup."""
    
    def __init__(self, project_root: Optional[pathlib.Path] = None):
        """
        Initialize hook installer.
        
        Args:
            project_root: Root directory of the project. Defaults to current directory.
        """
        if project_root is None:
            project_root = pathlib.Path(".").resolve()
        else:
            project_root = pathlib.Path(project_root).resolve()
        
        self.project_root = project_root
        self.detector = EnvironmentDetector()
        self.config_generator = HookConfigGenerator(self.detector)
    
    def install_hooks(self, force: bool = False) -> Tuple[bool, str]:
        """
        Install hooks with environment detection.
        
        Args:
            force: If True, use --overwrite flag to force reinstallation.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Verify environment
        is_ready, errors = self.detector.verify_environment()
        if not is_ready:
            return False, f"Environment not ready: {', '.join(errors)}"
        
        # Generate adapted config (optional - pre-commit will use existing .pre-commit-config.yaml)
        # We can generate it for reference, but pre-commit install uses the existing file
        try:
            config = self.config_generator.generate_precommit_config()
            if not self.config_generator.validate_config_structure(config):
                return False, "Failed to generate valid hook configuration"
        except Exception as e:
            # Non-fatal - pre-commit will use existing config
            pass
        
        # Install pre-commit hooks
        try:
            precommit_cmd = self.detector.tools.get("pre_commit") or "pre-commit"
            cmd = [precommit_cmd, "install"]
            
            if force:
                cmd.append("--overwrite")
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
                timeout=60
            )
            
            return True, "Hooks installed successfully"
        
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            return False, f"Failed to install hooks: {error_msg}"
        except FileNotFoundError:
            return False, "pre-commit not found. Install with: pip install pre-commit"
        except subprocess.TimeoutExpired:
            return False, "Hook installation timed out"
        except Exception as e:
            return False, f"Unexpected error during installation: {str(e)}"
    
    def verify_installation(self) -> bool:
        """
        Verify that hooks are actually installed.
        
        Returns:
            True if hooks are installed, False otherwise.
        """
        hooks_dir = self.project_root / ".git" / "hooks"
        precommit_hook = hooks_dir / "pre-commit"
        
        if not hooks_dir.exists():
            return False
        
        if not precommit_hook.exists():
            return False
        
        # Check if it's a valid pre-commit hook (should be a symlink or script)
        try:
            # Check if file is executable or is a symlink
            if precommit_hook.is_symlink() or precommit_hook.stat().st_mode & 0o111:
                return True
        except (OSError, AttributeError):
            pass
        
        return False
    
    def _run_precommit_install(self, force: bool = False) -> Tuple[bool, str]:
        """
        Internal method to run pre-commit install command.
        
        Args:
            force: If True, use --overwrite flag.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        return self.install_hooks(force=force)


def main():
    """Main entry point for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Install pre-commit hooks with cross-platform support"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reinstallation of hooks (--overwrite)"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify hooks are installed"
    )
    parser.add_argument(
        "--project-root",
        type=pathlib.Path,
        default=None,
        help="Project root directory (default: current directory)"
    )
    
    args = parser.parse_args()
    
    installer = HookInstaller(project_root=args.project_root)
    
    if args.verify:
        is_installed = installer.verify_installation()
        if is_installed:
            print("✅ Hooks are installed")
            return 0
        else:
            print("❌ Hooks are not installed")
            return 1
    
    print("Installing pre-commit hooks...")
    print(f"Environment: {installer.detector.detected_env.value}")
    print(f"Python: {installer.detector.get_python_command()}")
    
    success, message = installer.install_hooks(force=args.force)
    
    if success:
        print(f"✅ {message}")
        
        # Verify installation
        if installer.verify_installation():
            print("✅ Installation verified")
        else:
            print("⚠️  Installation completed but verification failed")
        
        return 0
    else:
        print(f"❌ {message}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
