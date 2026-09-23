#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Environment Detection System
Detects development environment (Windows/WSL/Linux/macOS) and available tools.
"""

import platform
import shutil
import subprocess
import pathlib
from typing import Dict, Optional, Tuple
from enum import Enum


class Environment(Enum):
    """Development environment types."""
    WINDOWS_CMD = "windows_cmd"
    WINDOWS_POWERSHELL = "windows_powershell"
    WSL = "wsl"
    LINUX = "linux"
    MACOS = "macos"
    UNKNOWN = "unknown"


class EnvironmentDetector:
    """Detect development environment and tools."""

    def __init__(self):
        """Initialize environment detector."""
        self.system = platform.system()
        self.detected_env = self._detect_environment()
        self.tools = self._detect_tools()

    def _detect_environment(self) -> Environment:
        """Detect the development environment."""
        system = platform.system().lower()

        if system == "windows":
            # Check if running in WSL
            if self._is_wsl():
                return Environment.WSL

            # Check PowerShell
            try:
                subprocess.run(
                    ["pwsh", "--version"],
                    capture_output=True,
                    check=True,
                    timeout=5
                )
                return Environment.WINDOWS_POWERSHELL
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                return Environment.WINDOWS_CMD

        elif system == "linux":
            # Check if WSL
            if self._is_wsl():
                return Environment.WSL
            return Environment.LINUX

        elif system == "darwin":
            return Environment.MACOS

        return Environment.UNKNOWN

    def _is_wsl(self) -> bool:
        """Check if running in WSL."""
        try:
            with open("/proc/version", "r", encoding="utf-8") as f:
                content = f.read().lower()
                return "microsoft" in content or "wsl" in content
        except (FileNotFoundError, PermissionError):
            # Not Linux or can't read /proc/version
            return False

    def _detect_tools(self) -> Dict[str, Optional[str]]:
        """Detect available tools and their paths."""
        tools = {
            "python": None,
            "python3": None,
            "git": None,
            "pre_commit": None,
            "bash": None,
            "shell": None,
        }

        # Detect Python
        for py_cmd in ["python3", "python", "py"]:
            py_path = shutil.which(py_cmd)
            if py_path:
                tools[py_cmd] = py_path
                if not tools["python"]:  # Prefer python3
                    tools["python"] = py_path

        # Detect Git
        git_path = shutil.which("git")
        if git_path:
            tools["git"] = git_path

        # Detect pre-commit
        precommit_path = shutil.which("pre-commit")
        if precommit_path:
            tools["pre_commit"] = precommit_path

        # Detect shell
        if self.detected_env in [Environment.WSL, Environment.LINUX, Environment.MACOS]:
            bash_path = shutil.which("bash")
            if bash_path:
                tools["bash"] = bash_path
                tools["shell"] = bash_path
        elif self.detected_env == Environment.WINDOWS_POWERSHELL:
            pwsh_path = shutil.which("pwsh")
            if pwsh_path:
                tools["shell"] = pwsh_path
        elif self.detected_env == Environment.WINDOWS_CMD:
            tools["shell"] = "cmd.exe"

        return tools

    def get_python_command(self) -> str:
        """Get the correct Python command for this environment."""
        # Prefer python3, fallback to python
        return self.tools.get("python3") or self.tools.get("python") or "python3"

    def get_shell_command(self) -> str:
        """Get the correct shell command for this environment."""
        return self.tools.get("shell") or "bash"

    def get_path_separator(self) -> str:
        """Get the correct path separator for this environment."""
        if self.detected_env in [Environment.WINDOWS_CMD, Environment.WINDOWS_POWERSHELL]:
            return "\\"
        return "/"

    def normalize_path(self, path: str) -> str:
        """Normalize path for this environment."""
        if self.detected_env in [Environment.WINDOWS_CMD, Environment.WINDOWS_POWERSHELL]:
            return path.replace("/", "\\")
        return path.replace("\\", "/")

    def verify_environment(self) -> Tuple[bool, list[str]]:
        """Verify environment is ready for hooks."""
        errors = []

        if not self.tools.get("python"):
            errors.append("Python not found (required)")

        if not self.tools.get("git"):
            errors.append("Git not found (required)")

        if not self.tools.get("pre_commit"):
            errors.append("pre-commit not found (recommended)")

        return len(errors) == 0, errors


def main():
    """Main entry point for testing."""
    detector = EnvironmentDetector()

    print(f"Detected Environment: {detector.detected_env.value}")
    print(f"Python Command: {detector.get_python_command()}")
    print(f"Shell Command: {detector.get_shell_command()}")
    print(f"Path Separator: {detector.get_path_separator()}")

    is_ready, errors = detector.verify_environment()
    if is_ready:
        print("Environment verification: OK")
    else:
        print("Environment verification: FAILED")
        for error in errors:
            print(f"  - {error}")

    return 0 if is_ready else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
