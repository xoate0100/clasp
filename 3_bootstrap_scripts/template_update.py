#!/usr/bin/env python3
"""
Template Update System
Pulls updates from the template repository and merges them safely into existing projects.
Supports AI-assisted migration for pre-versioned projects.
"""

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import yaml

# Import standardized feedback for error reporting
try:
    from standardized_feedback import report_update_issue
except ImportError:
    # Fallback if standardized_feedback not available
    def report_update_issue(*args, **kwargs):
        pass


VERSION_FILE = pathlib.Path("0_phase0_bootstrap/META_FRAMEWORK_VERSION.yaml")
VERSION_SCHEMA = pathlib.Path("7_schemas/meta_framework_version.schema.json")


# Custom exception classes for enhanced error handling
class TemplateUpdateError(Exception):
    """Base exception for template update errors."""
    
    def __init__(self, message: str, **context):
        super().__init__(message)
        self.message = message
        self.context = context
    
    def __str__(self) -> str:
        msg = self.message
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items() if v)
            if context_str:
                msg += f" ({context_str})"
        return msg


class MigrationError(TemplateUpdateError):
    """Migration-specific error."""
    
    def __init__(self, message: str, version: str = "", details: str = "", suggestion: str = ""):
        super().__init__(message, version=version, details=details, suggestion=suggestion)
        self.version = version
        self.details = details
        self.suggestion = suggestion


class FileCopyError(TemplateUpdateError):
    """File copy error."""
    
    def __init__(self, message: str, file_path: str = "", source: str = "", destination: str = ""):
        super().__init__(message, file_path=file_path, source=source, destination=destination)
        self.file_path = file_path
        self.source = source
        self.destination = destination


class CloneError(TemplateUpdateError):
    """Template repository clone error."""
    
    def __init__(self, message: str, repo: str = "", version: str = "", suggestion: str = ""):
        super().__init__(message, repo=repo, version=version, suggestion=suggestion)
        self.repo = repo
        self.version = version
        self.suggestion = suggestion


class ValidationError(TemplateUpdateError):
    """Schema validation error."""
    
    def __init__(self, message: str, errors: List[str] = None, file_path: str = ""):
        super().__init__(message, errors=errors or [], file_path=file_path)
        self.errors = errors or []
        self.file_path = file_path


def calculate_file_checksum(file_path: pathlib.Path) -> str:
    """
    Calculate SHA256 checksum of a file.
    
    Args:
        file_path: Path to the file
    
    Returns:
        SHA256 checksum as hexadecimal string
    """
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            # Read in chunks to handle large files efficiently
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        raise FileCopyError(
            f"Failed to calculate checksum: {e}",
            file_path=str(file_path)
        ) from e


def verify_file_integrity(source_path: pathlib.Path, dest_path: pathlib.Path) -> bool:
    """
    Verify that source and destination files have matching checksums.
    
    Args:
        source_path: Path to source file
        dest_path: Path to destination file
    
    Returns:
        True if files match, False otherwise
    """
    if not source_path.exists():
        return False
    if not dest_path.exists():
        return False
    
    try:
        source_checksum = calculate_file_checksum(source_path)
        dest_checksum = calculate_file_checksum(dest_path)
        return source_checksum == dest_checksum
    except Exception:
        return False


def verify_copied_files(
    template_dir: pathlib.Path,
    target_dir: pathlib.Path,
    updated_files: List[str]
) -> Tuple[bool, List[str]]:
    """
    Verify integrity of all copied files.
    
    Args:
        template_dir: Template directory (source)
        target_dir: Target directory (destination)
        updated_files: List of relative file paths that were copied
    
    Returns:
        Tuple of (all_match: bool, mismatches: List[str])
    """
    mismatches = []
    
    for rel_path in updated_files:
        source_file = template_dir / rel_path
        dest_file = target_dir / rel_path
        
        if not verify_file_integrity(source_file, dest_file):
            mismatches.append(rel_path)
    
    return len(mismatches) == 0, mismatches


def copy_to_staging_directory(
    template_dir: pathlib.Path,
    staging_dir: pathlib.Path,
    files: List[str]
) -> bool:
    """
    Copy files to staging directory for atomic update.
    
    Args:
        template_dir: Template directory (source)
        staging_dir: Staging directory (temporary)
        files: List of relative file paths to copy
    
    Returns:
        True if all files copied successfully, False otherwise
    """
    try:
        staging_dir.mkdir(parents=True, exist_ok=True)
        
        for rel_path in files:
            source_file = template_dir / rel_path
            staging_file = staging_dir / rel_path
            
            if not source_file.exists():
                continue
            
            # Create parent directories
            staging_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            shutil.copy2(source_file, staging_file)
        
        return True
    except Exception as e:
        raise FileCopyError(
            f"Failed to copy files to staging: {e}",
            file_path=", ".join(files[:3])
        ) from e


def verify_staging_directory(
    staging_dir: pathlib.Path,
    template_dir: pathlib.Path,
    files: List[str]
) -> Tuple[bool, List[str]]:
    """
    Verify all files in staging directory match template.
    
    Args:
        staging_dir: Staging directory
        template_dir: Template directory (source)
        files: List of relative file paths to verify
    
    Returns:
        Tuple of (all_valid: bool, invalid_files: List[str])
    """
    invalid = []
    
    for rel_path in files:
        staging_file = staging_dir / rel_path
        template_file = template_dir / rel_path
        
        if not verify_file_integrity(template_file, staging_file):
            invalid.append(rel_path)
    
    return len(invalid) == 0, invalid


def apply_staging_to_target(
    staging_dir: pathlib.Path,
    target_dir: pathlib.Path,
    files: List[str]
) -> bool:
    """
    Apply staging files to target directory atomically.
    
    Args:
        staging_dir: Staging directory
        target_dir: Target directory
        files: List of relative file paths to apply
    
    Returns:
        True if all files applied successfully, False otherwise
    """
    try:
        for rel_path in files:
            staging_file = staging_dir / rel_path
            target_file = target_dir / rel_path
            
            if not staging_file.exists():
                continue
            
            # Create parent directories
            target_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Move file from staging to target (atomic on most systems)
            if target_file.exists():
                target_file.unlink()  # Remove existing file first
            shutil.move(str(staging_file), str(target_file))
        
        return True
    except Exception as e:
        raise FileCopyError(
            f"Failed to apply staging files: {e}",
            file_path=", ".join(files[:3])
        ) from e


def rollback_staging(staging_dir: pathlib.Path) -> bool:
    """
    Rollback staging directory by removing it.
    
    Args:
        staging_dir: Staging directory to remove
    
    Returns:
        True if rollback successful, False otherwise
    """
    try:
        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)
        return True
    except Exception as e:
        # Log but don't fail - staging cleanup is best effort
        print(f"WARN: Failed to clean up staging directory: {e}")
        return False


def create_backup(target_dir: pathlib.Path, files: List[str]) -> pathlib.Path:
    """
    Create backup of files before update.
    
    Args:
        target_dir: Target directory containing files to backup
        files: List of relative file paths to backup
    
    Returns:
        Path to backup directory
    """
    backup_dir = pathlib.Path(tempfile.mkdtemp(prefix="template_backup_"))
    
    try:
        for rel_path in files:
            source_file = target_dir / rel_path
            
            if not source_file.exists():
                continue
            
            backup_file = backup_dir / rel_path
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file to backup
            shutil.copy2(source_file, backup_file)
        
        return backup_dir
    except Exception as e:
        # Cleanup on failure
        shutil.rmtree(backup_dir, ignore_errors=True)
        raise FileCopyError(
            f"Failed to create backup: {e}",
            file_path=", ".join(files[:3])
        ) from e


def restore_from_backup(
    backup_dir: pathlib.Path,
    target_dir: pathlib.Path,
    files: List[str]
) -> bool:
    """
    Restore files from backup.
    
    Args:
        backup_dir: Backup directory
        target_dir: Target directory to restore to
        files: List of relative file paths to restore
    
    Returns:
        True if restore successful, False otherwise
    """
    try:
        for rel_path in files:
            backup_file = backup_dir / rel_path
            target_file = target_dir / rel_path
            
            if not backup_file.exists():
                continue
            
            # Create parent directories
            target_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Restore file from backup
            if target_file.exists():
                target_file.unlink()  # Remove existing file first
            shutil.copy2(backup_file, target_file)
        
        return True
    except Exception as e:
        raise FileCopyError(
            f"Failed to restore from backup: {e}",
            file_path=", ".join(files[:3])
        ) from e


def cleanup_backup(backup_dir: pathlib.Path) -> bool:
    """
    Cleanup backup directory.
    
    Args:
        backup_dir: Backup directory to remove
    
    Returns:
        True if cleanup successful, False otherwise
    """
    try:
        if backup_dir.exists():
            shutil.rmtree(backup_dir, ignore_errors=True)
        return True
    except Exception as e:
        # Log but don't fail - backup cleanup is best effort
        print(f"WARN: Failed to clean up backup directory: {e}")
        return False


def rollback_update(
    backup_dir: pathlib.Path,
    target_dir: pathlib.Path,
    files: List[str]
) -> bool:
    """
    Rollback update by restoring from backup and cleaning up.
    
    Args:
        backup_dir: Backup directory
        target_dir: Target directory to restore to
        files: List of relative file paths to restore
    
    Returns:
        True if rollback successful, False otherwise
    """
    try:
        # Restore files
        restore_success = restore_from_backup(backup_dir, target_dir, files)
        if not restore_success:
            return False
        
        # Cleanup backup
        cleanup_backup(backup_dir)
        return True
    except Exception as e:
        # Try to cleanup even if restore failed
        cleanup_backup(backup_dir)
        raise FileCopyError(
            f"Failed to rollback update: {e}",
            file_path=", ".join(files[:3])
        ) from e


def handle_update_error(error: Exception, from_version: str, to_version: str) -> None:
    """
    Handle update errors by reporting to feedback system.
    
    Args:
        error: The exception that occurred
        from_version: Source version
        to_version: Target version
    """
    error_type = type(error).__name__
    error_msg = str(error)
    
    # Extract details and suggestions from error context if available
    details = error_msg
    suggestion = ""
    
    if isinstance(error, TemplateUpdateError):
        details = error.message
        if hasattr(error, 'details') and error.details:
            details += f": {error.details}"
        if hasattr(error, 'suggestion') and error.suggestion:
            suggestion = error.suggestion
    
    # Report to feedback system
    report_update_issue(
        issue_type=error_type,
        from_version=from_version,
        to_version=to_version,
        migration_applied=False,
        details=details,
        error=error_msg,
        resolution=suggestion or "Review error details and retry update"
    )


def validate_version_manifest(manifest: Dict[str, Any], project_root: pathlib.Path = None) -> Tuple[bool, List[str]]:
    """
    Validate version manifest against schema.
    
    Args:
        manifest: Version manifest dictionary to validate
        project_root: Root directory of the project (default: current directory)
    
    Returns:
        Tuple of (is_valid: bool, errors: List[str])
    """
    if project_root is None:
        project_root = pathlib.Path(".")
    
    schema_path = project_root / VERSION_SCHEMA
    
    # If schema doesn't exist, skip validation (graceful degradation)
    if not schema_path.exists():
        return True, []
    
    try:
        import jsonschema
    except ImportError:
        # jsonschema not available, skip validation
        return True, []
    
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        
        # Validate manifest against schema
        jsonschema.validate(instance=manifest, schema=schema)
        return True, []
    except jsonschema.ValidationError as e:
        error_msg = f"Schema validation error: {e.message}"
        if e.path:
            error_msg += f" (path: {'/'.join(str(p) for p in e.path)})"
        return False, [error_msg]
    except json.JSONDecodeError as e:
        return False, [f"Schema file is invalid JSON: {e}"]
    except Exception as e:
        return False, [f"Validation error: {e}"]


def validate_before_update(manifest: Dict[str, Any], project_root: pathlib.Path = None) -> bool:
    """
    Validate version manifest before update operations.
    
    Args:
        manifest: Version manifest to validate
        project_root: Root directory of the project
    
    Returns:
        True if valid, False otherwise (prints errors)
    """
    is_valid, errors = validate_version_manifest(manifest, project_root)
    
    if not is_valid:
        print("ERROR: Version manifest validation failed before update:")
        for error in errors:
            print(f"  - {error}")
        print("  Update aborted to prevent corruption.")
    
    return is_valid


def validate_after_update(manifest: Dict[str, Any], project_root: pathlib.Path = None) -> bool:
    """
    Validate version manifest after update operations.
    
    Args:
        manifest: Version manifest to validate
        project_root: Root directory of the project
    
    Returns:
        True if valid, False otherwise (prints errors)
    """
    is_valid, errors = validate_version_manifest(manifest, project_root)
    
    if not is_valid:
        print("ERROR: Version manifest validation failed after update:")
        for error in errors:
            print(f"  - {error}")
        print("  WARN: Manifest may be corrupted. Review manually.")
    
    return is_valid


def load_version_manifest() -> Optional[Dict[str, Any]]:
    """Load the version manifest if it exists."""
    if not VERSION_FILE.exists():
        return None
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"ERROR: Failed to load version manifest: {e}")
        return None


def save_version_manifest(manifest: Dict[str, Any], validate: bool = True, project_root: pathlib.Path = None) -> bool:
    """
    Save the version manifest with optional validation.
    
    Args:
        manifest: Version manifest to save
        validate: Whether to validate before saving (default: True)
        project_root: Root directory of the project
    
    Returns:
        True if saved successfully, False otherwise
    """
    # Validate before saving if requested
    if validate:
        is_valid, errors = validate_version_manifest(manifest, project_root)
        if not is_valid:
            print("ERROR: Cannot save invalid version manifest:")
            for error in errors:
                print(f"  - {error}")
            return False
    
    try:
        VERSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(VERSION_FILE, "w", encoding="utf-8") as f:
            yaml.dump(manifest, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        return True
    except Exception as e:
        print(f"ERROR: Failed to save version manifest: {e}")
        return False


def detect_pre_versioned_project() -> bool:
    """Detect if this is a pre-versioned project (no META_FRAMEWORK_VERSION.yaml)."""
    return not VERSION_FILE.exists()


def initialize_version_manifest(template_repo: str, version: str = "1.0.0") -> Dict[str, Any]:
    """Create initial version manifest for pre-versioned projects."""
    return {
        "template_version": version,
        "template_repo": template_repo,
        "installed_at": datetime.utcnow().isoformat() + "Z",
        "last_updated_at": None,
        "update_history": [],
        "features": {
            "dynamic_layout_adaptation": pathlib.Path("3_bootstrap_scripts/layout_adaptor.py").exists(),
            "guided_initialization": pathlib.Path("3_bootstrap_scripts/init_wizard.py").exists(),
            "dynamic_ai_context": pathlib.Path("3_bootstrap_scripts/generate_ai_context.py").exists(),
            "template_versioning": False,  # Being added now
            "drift_detection": pathlib.Path("scripts/meta_framework_drift_check.py").exists(),
        },
        "template_directories": [
            "0_phase0_bootstrap/",
            "1_global_standards/",
            "2_framework_templates/",
            "3_bootstrap_scripts/",
            "5_reference_architectures/",
            "7_schemas/",
            "8_ci/",
        ],
        "protected_files": [
            "0_phase0_bootstrap/MVP_SPECIFICATION.yaml",
            "0_phase0_bootstrap/feature_flags.yml",
        ],
        "project_directories": [
            "4_docs_index/",
            "6_ai_runtime_context/",
            "frontend/",
            "backend/",
            "shared/",
            "apps/",
            "packages/",
            "docs/",
        ],
    }


def get_latest_template_version(template_repo: str) -> Optional[str]:
    """Get the latest version from the template repository.
    
    Tries multiple methods:
    1. GitHub API (read from META_FRAMEWORK_VERSION.yaml) - PRIMARY
    2. Git tags - FALLBACK
    """
    # Method 1: Try GitHub API (read from version manifest file)
    try:
        import requests
        import re
        import base64
        
        # Extract owner/repo from URL
        match = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$", template_repo)
        if match:
            owner, repo = match.groups()
            api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/0_phase0_bootstrap/META_FRAMEWORK_VERSION.yaml"
            
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                content = base64.b64decode(response.json()["content"]).decode("utf-8")
                import yaml
                manifest = yaml.safe_load(content)
                version = manifest.get("template_version")
                if version:
                    return version
    except ImportError:
        # requests not available, skip API method
        pass
    except Exception:
        # API failed, continue to fallback
        pass
    
    # Method 2: Fallback to git tags
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--tags", template_repo],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None

        # Parse tags to find latest version
        tags = []
        for line in result.stdout.splitlines():
            if "refs/tags/" in line:
                tag = line.split("refs/tags/")[-1].split()[0]
                # Remove 'v' prefix if present for comparison
                clean_tag = tag[1:] if tag.startswith("v") else tag
                if any(c.isdigit() for c in clean_tag):
                    tags.append(clean_tag)

        if tags:
            # Sort versions properly (semver)
            try:
                sorted_tags = sorted(tags, key=lambda v: tuple(map(int, v.split("."))))
                return sorted_tags[-1]
            except (ValueError, AttributeError):
                # Fallback: return last tag
                return tags[-1]

        return None
    except Exception as e:
        print(f"WARN: Could not fetch latest version from template repo: {e}")
        return None


def clone_template_to_temp(template_repo: str, version: Optional[str] = None) -> Optional[pathlib.Path]:
    """
    Clone template repository to a temporary directory.
    
    Raises:
        CloneError: If cloning fails
    """
    temp_dir = tempfile.mkdtemp(prefix="template_update_")
    try:
        cmd = ["git", "clone", "--depth", "1", template_repo, temp_dir]
        if version:
            cmd.extend(["--branch", version])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            shutil.rmtree(temp_dir, ignore_errors=True)
            suggestion = "Check repository URL and network connectivity. Ensure git is installed."
            raise CloneError(
                f"Failed to clone template repository: {result.stderr or 'Unknown error'}",
                repo=template_repo,
                version=version or "latest",
                suggestion=suggestion
            )
        return pathlib.Path(temp_dir)
    except CloneError:
        raise  # Re-raise CloneError
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise CloneError(
            f"Unexpected error cloning template: {e}",
            repo=template_repo,
            version=version or "latest",
            suggestion="Check git installation and repository access"
        ) from e


def get_template_directories(manifest: Dict[str, Any]) -> List[str]:
    """Get list of template directories from manifest."""
    return manifest.get("template_directories", [])


def get_protected_files(manifest: Dict[str, Any]) -> List[str]:
    """Get list of protected files that should not be overwritten."""
    return manifest.get("protected_files", [])


def should_update_file(file_path: str, protected_files: List[str]) -> bool:
    """Check if a file should be updated (not protected)."""
    for protected in protected_files:
        if file_path == protected or file_path.startswith(protected):
            return False
    return True


def copy_template_files(
    template_dir: pathlib.Path,
    target_dir: pathlib.Path,
    template_dirs: List[str],
    protected_files: List[str],
    dry_run: bool = False,
) -> Tuple[List[str], List[str]]:
    """Copy template files to target, respecting protected files."""
    updated_files = []
    skipped_files = []

    for template_dir_name in template_dirs:
        src_dir = template_dir / template_dir_name.rstrip("/")
        if not src_dir.exists():
            continue

        target_base = target_dir / template_dir_name.rstrip("/")
        target_base.parent.mkdir(parents=True, exist_ok=True)

        # Walk through template directory
        for src_file in src_dir.rglob("*"):
            if src_file.is_dir():
                continue

            # Get relative path from template root
            rel_path = src_file.relative_to(template_dir)
            rel_str = str(rel_path).replace("\\", "/")

            # Check if protected
            if not should_update_file(rel_str, protected_files):
                skipped_files.append(rel_str)
                continue

            target_file = target_dir / rel_path
            target_file.parent.mkdir(parents=True, exist_ok=True)

            if not dry_run:
                try:
                    shutil.copy2(src_file, target_file)
                    
                    # Verify file integrity after copy
                    if not verify_file_integrity(src_file, target_file):
                        raise FileCopyError(
                            f"File integrity verification failed after copy",
                            file_path=rel_str,
                            source=str(src_file),
                            destination=str(target_file)
                        )
                except FileCopyError:
                    raise  # Re-raise FileCopyError
                except Exception as e:
                    raise FileCopyError(
                        f"Failed to copy file: {e}",
                        file_path=rel_str,
                        source=str(src_file),
                        destination=str(target_file)
                    ) from e
            updated_files.append(rel_str)

    return updated_files, skipped_files


def update_version_manifest(
    manifest: Dict[str, Any],
    new_version: str,
    migration_applied: bool = False,
    notes: str = "",
) -> Dict[str, Any]:
    """Update version manifest with new version and history."""
    old_version = manifest.get("template_version", "unknown")

    manifest["template_version"] = new_version
    manifest["last_updated_at"] = datetime.utcnow().isoformat() + "Z"

    # Add to update history
    update_entry = {
        "from_version": old_version,
        "to_version": new_version,
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "migration_applied": migration_applied,
        "notes": notes,
    }
    manifest.setdefault("update_history", []).append(update_entry)

    return manifest


def get_required_files_for_version(version: str) -> List[str]:
    """
    Get list of required files for a specific version migration.
    
    Args:
        version: Target version string (e.g., "1.0.0")
    
    Returns:
        List of file paths relative to project root
    """
    required = []
    
    # Base requirements for all versions
    required.append("0_phase0_bootstrap/META_FRAMEWORK_VERSION.yaml")
    
    # Version comparison helper
    def version_tuple(v: str) -> Tuple[int, int, int]:
        parts = v.split("-")[0].split(".")
        return (int(parts[0]), int(parts[1]) if len(parts) > 1 else 0, int(parts[2]) if len(parts) > 2 else 0)
    
    target_v = version_tuple(version)
    
    # Version-specific requirements
    if target_v >= (1, 6, 0):
        required.append("1_global_standards/AI_OPERATING_CONSTITUTION.md")
        required.append("7_schemas/intent_declaration.schema.json")
    
    if target_v >= (1, 7, 0):
        required.append("3_bootstrap_scripts/auto_advance_state.py")

    if target_v >= (2, 1, 0):
        required.append("5_reference_architectures/DECISION_REGISTRY.yaml")
        required.append("5_reference_architectures/AGENT_REGISTRY.yaml")
        required.append("agentic/registry.py")
        required.append("3_bootstrap_scripts/resurrection_scan.py")

    if target_v >= (2, 2, 0):
        required.append("5_reference_architectures/OPTIONAL_AGENTIC_TOOLS.yaml")
        required.append("5_reference_architectures/KNOWLEDGE_SOURCES.yaml")
        required.append("3_bootstrap_scripts/agentic_tools.py")
        required.append("agentic/optional_tools.py")

    return required


def verify_migration_dependencies(
    project_root: pathlib.Path,
    target_version: str
) -> Tuple[bool, List[str]]:
    """
    Verify all required files exist before running migrations.
    
    Args:
        project_root: Root directory of the project
        target_version: Target version for migration
    
    Returns:
        Tuple of (all_present: bool, missing_files: List[str])
    """
    missing = []
    required_files = get_required_files_for_version(target_version)
    
    for file_path in required_files:
        full_path = project_root / file_path
        if not full_path.exists():
            missing.append(file_path)
    
    return len(missing) == 0, missing


def check_migration_prerequisites(
    migration_func,
    project_root: pathlib.Path,
    target_version: str
) -> Tuple[bool, List[str]]:
    """
    Check prerequisites for a specific migration function.
    
    Args:
        migration_func: Migration function to check
        project_root: Root directory of the project
        target_version: Target version
    
    Returns:
        Tuple of (all_present: bool, missing_files: List[str])
    """
    # First check general dependencies
    all_present, missing = verify_migration_dependencies(project_root, target_version)
    
    # Migration-specific checks could be added here
    # For now, we rely on the general dependency check
    
    return all_present, missing


def apply_migrations(from_version: str, to_version: str, project_root: pathlib.Path = None) -> Tuple[bool, str]:
    """Apply migrations between versions. Returns (success, notes)."""
    if project_root is None:
        project_root = pathlib.Path(".")

    # Handle "latest" version - skip migrations if version is "latest"
    if to_version == "latest" or from_version == "latest":
        return False, "Skipped (latest version - migrations not applicable)"

    # Version comparison (simple semver-like)
    def version_tuple(v: str) -> Tuple[int, int, int]:
        # Skip if "latest" (shouldn't happen here, but defensive)
        if v == "latest":
            return (999, 999, 999)  # High version number
        parts = v.split("-")[0].split(".")
        return (int(parts[0]), int(parts[1]) if len(parts) > 1 else 0, int(parts[2]) if len(parts) > 2 else 0)

    from_v = version_tuple(from_version)
    to_v = version_tuple(to_version)

    notes = []
    migration_needed = False

    # Try to load migration modules
    try:
        import sys
        migrations_path = pathlib.Path(__file__).parent / "migrations"
        if migrations_path.exists():
            sys.path.insert(0, str(pathlib.Path(__file__).parent))
            from migrations import get_migration, list_available_migrations

            # Apply migrations in order
            available = list_available_migrations()
            for target_version in available:
                target_v = version_tuple(target_version)
                if from_v < target_v <= to_v:
                    # Verify dependencies before running migration
                    all_present, missing = verify_migration_dependencies(project_root, target_version)
                    if not all_present:
                        raise MigrationError(
                            f"Migration dependencies missing for version {target_version}",
                            version=target_version,
                            details=f"Missing files: {', '.join(missing)}",
                            suggestion="Ensure all required template files are copied before running migrations"
                        )
                    
                    migration_func = get_migration(target_version)
                    if migration_func:
                        # Additional prerequisite check
                        prereq_ok, missing_prereq = check_migration_prerequisites(
                            migration_func, project_root, target_version
                        )
                        if not prereq_ok:
                            raise MigrationError(
                                f"Migration prerequisites not met for version {target_version}",
                                version=target_version,
                                details=f"Missing prerequisites: {', '.join(missing_prereq)}",
                                suggestion="Ensure all migration prerequisites are satisfied"
                            )
                        
                        success, migration_notes = migration_func(project_root)
                        if success:
                            notes.append(f"{target_version}: {migration_notes}")
                            migration_needed = True
                        else:
                            raise MigrationError(
                                f"Migration failed for version {target_version}",
                                version=target_version,
                                details=migration_notes or "Migration returned failure",
                                suggestion="Review migration logs and fix issues before retrying"
                            )
    except ImportError:
        # Fallback to simple migrations if module system not available
        if from_v < (1, 0, 0) and to_v >= (1, 0, 0):
            # Verify dependencies even for fallback
            all_present, missing = verify_migration_dependencies(project_root, "1.0.0")
            if not all_present:
                raise MigrationError(
                    "Migration dependencies missing for version 1.0.0",
                    version="1.0.0",
                    details=f"Missing files: {', '.join(missing)}",
                    suggestion="Ensure all required template files are copied before running migrations"
                )
            notes.append("Initialized template versioning system")
            migration_needed = True

    return migration_needed, "; ".join(notes) if notes else "No migrations required"


def check_for_updates(template_repo: str, current_version: Optional[str] = None) -> Optional[str]:
    """Check if updates are available."""
    latest = get_latest_template_version(template_repo)
    if not latest:
        return None
    if current_version and latest == current_version:
        return None
    return latest


def check_cli_support() -> Tuple[bool, str]:
    """Check if cli.py has update-template command. Returns (has_command, error_message)."""
    cli_path = pathlib.Path("3_bootstrap_scripts/cli.py")
    if not cli_path.exists():
        return False, "cli.py not found"
    try:
        content = cli_path.read_text(encoding="utf-8")
        if "update-template" in content:
            return True, ""
        return False, "cli.py missing update-template command"
    except Exception as e:
        return False, f"Failed to read cli.py: {e}"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="template_update.py",
        description="Update template files from the template repository",
    )
    parser.add_argument(
        "--template-repo",
        default="",
        help="Template repository URL (default: from version manifest or detect)",
    )
    parser.add_argument(
        "--version",
        default="",
        help="Specific version to update to (default: latest)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes",
    )
    parser.add_argument(
        "--init-versioning",
        action="store_true",
        help="Initialize versioning for pre-versioned projects (AI-assisted)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force update even if versions match",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip backup creation (not recommended)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify file integrity without updating",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current template version and status",
    )

    args = parser.parse_args(argv)

    # Load or initialize version manifest
    manifest = load_version_manifest()
    is_pre_versioned = detect_pre_versioned_project()
    
    # Validate existing manifest before proceeding
    if manifest and not validate_before_update(manifest):
        return 1

    if is_pre_versioned:
        if not args.init_versioning:
            print("WARN: This project does not have version tracking initialized.")
            print("Run with --init-versioning to initialize versioning (AI-assisted).")
            print("This will detect your template source and create a version manifest.")
            return 1

        # AI-assisted initialization for pre-versioned projects
        print("Initializing version tracking for pre-versioned project...")

        # Try to detect template repo from git remote
        template_repo = args.template_repo
        if not template_repo:
            try:
                result = subprocess.run(
                    ["git", "remote", "get-url", "origin"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    # For now, assume origin is the template (or user can specify)
                    detected_repo = result.stdout.strip()
                    print(f"Detected git remote: {detected_repo}")
                    print("If this is not your template repo, specify --template-repo")
                    template_repo = detected_repo
            except Exception:
                pass

        if not template_repo:
            template_repo = input("Enter template repository URL: ").strip()
            if not template_repo:
                print("ERROR: Template repository URL required")
                return 1

        manifest = initialize_version_manifest(template_repo)
        
        # Validate before saving
        if not validate_before_update(manifest):
            return 1
        
        if not save_version_manifest(manifest, validate=False):
            return 1
        
        # Validate after saving
        if not validate_after_update(manifest):
            print("WARN: Manifest saved but validation failed. Review manually.")
        
        print("OK: Version tracking initialized")

        # Check if CLI has update-template command
        has_cli, cli_error = check_cli_support()
        if not has_cli:
            print("\nWARN: CLI may not have update-template command.")
            print(f"      Issue: {cli_error}")
            print("      You may need to update cli.py manually or use template_update.py directly.")
            print("      See docs/VERSIONING_MIGRATION_GUIDE.md for details.")

    # Get template repo from manifest if not provided
    template_repo = args.template_repo or manifest.get("template_repo", "")
    if not template_repo:
        print("ERROR: Template repository URL required (specify --template-repo or set in manifest)")
        return 1

    current_version = manifest.get("template_version", "unknown")
    target_version = args.version or check_for_updates(template_repo, current_version)

    if not target_version:
        if args.force:
            # Resolve "latest" to actual version before proceeding
            resolved_latest = get_latest_template_version(template_repo)
            if resolved_latest:
                target_version = resolved_latest
            else:
                target_version = "latest"
                print("WARN: Could not resolve 'latest' version, proceeding with 'latest'")
        else:
            print(f"INFO: Already at latest version ({current_version})")
            return 0

    # If target_version is still "latest", try to resolve it
    if target_version == "latest":
        resolved_latest = get_latest_template_version(template_repo)
        if resolved_latest:
            print(f"Resolved 'latest' to version {resolved_latest}")
            target_version = resolved_latest
        else:
            print("WARN: Could not resolve 'latest' version. Migrations will be skipped.")

    if not args.force and target_version == current_version:
        print(f"INFO: Already at version {current_version} (idempotent: no changes needed)")
        return 0

    print(f"Updating template from {current_version} to {target_version}...")

    # Clone template
    print("Cloning template repository...")
    try:
        template_dir = clone_template_to_temp(template_repo, target_version if target_version != "latest" else None)
    except CloneError as e:
        print(f"ERROR: {e}")
        if e.suggestion:
            print(f"  Suggestion: {e.suggestion}")
        handle_update_error(e, current_version, target_version)
        return 1

    try:
        # Get template directories and protected files
        template_dirs = get_template_directories(manifest)
        protected_files = get_protected_files(manifest)

        # Copy files using atomic update mechanism with rollback
        print("Updating template files...")
        staging_dir = None
        backup_dir = None
        try:
            if args.dry_run:
                # Dry run: use simple copy for preview
                updated, skipped = copy_template_files(
                    template_dir,
                    pathlib.Path("."),
                    template_dirs,
                    protected_files,
                    dry_run=True,
                )
            else:
                # Step 0: Create backup before update (unless --no-backup)
                target_dir = pathlib.Path(".")
                backup_dir = None
                if not args.no_backup:
                    print("  Creating backup of existing files...")
                    # Get list of files that will be updated (preview copy)
                    preview_updated, _ = copy_template_files(
                        template_dir,
                        pathlib.Path(tempfile.mkdtemp(prefix="preview_")),
                        template_dirs,
                        protected_files,
                        dry_run=True,
                    )
                    if preview_updated:
                        backup_dir = create_backup(target_dir, preview_updated)
                        print(f"  Backup created: {len(preview_updated)} file(s)")
                else:
                    print("  WARN: Backup creation skipped (--no-backup)")
                    preview_updated, _ = copy_template_files(
                        template_dir,
                        pathlib.Path(tempfile.mkdtemp(prefix="preview_")),
                        template_dirs,
                        protected_files,
                        dry_run=True,
                    )
                
                # Atomic update: copy to staging, verify, then apply
                staging_dir = pathlib.Path(tempfile.mkdtemp(prefix="template_staging_"))
                
                # Step 1: Copy to staging
                print("  Copying files to staging directory...")
                updated, skipped = copy_template_files(
                    template_dir,
                    staging_dir,
                    template_dirs,
                    protected_files,
                    dry_run=False,
                )
                
                # Step 2: Verify staging
                print("  Verifying staging directory...")
                all_valid, invalid = verify_staging_directory(
                    staging_dir,
                    template_dir,
                    updated
                )
                if not all_valid:
                    print(f"ERROR: Staging verification failed for {len(invalid)} file(s):")
                    for inv_file in invalid[:10]:
                        print(f"  - {inv_file}")
                    if len(invalid) > 10:
                        print(f"  ... and {len(invalid) - 10} more")
                    
                    rollback_staging(staging_dir)
                    if backup_dir:
                        print("  Rolling back to previous version...")
                        rollback_update(backup_dir, target_dir, preview_updated)
                    integrity_error = FileCopyError(
                        f"Staging verification failed: {len(invalid)} file(s) do not match",
                        file_path=", ".join(invalid[:5])
                    )
                    handle_update_error(integrity_error, current_version, target_version)
                    return 1
                
                # Step 3: Apply staging to target (atomic)
                print("  Applying staging to target...")
                apply_success = apply_staging_to_target(
                    staging_dir,
                    target_dir,
                    updated
                )
                if not apply_success:
                    rollback_staging(staging_dir)
                    if backup_dir and preview_updated:
                        print("  Rolling back to previous version...")
                        rollback_update(backup_dir, target_dir, preview_updated)
                    raise FileCopyError(
                        "Failed to apply staging files to target",
                        file_path="multiple files"
                    )
                
                # Step 4: Cleanup staging and backup
                rollback_staging(staging_dir)
                staging_dir = None
                if backup_dir:
                    cleanup_backup(backup_dir)
                    backup_dir = None
                print("OK: All files updated atomically")
        except FileCopyError as e:
            if staging_dir:
                rollback_staging(staging_dir)
            if backup_dir:
                print("  Rolling back to previous version...")
                try:
                    # Try to get preview_updated if not already available
                    if 'preview_updated' not in locals():
                        preview_updated, _ = copy_template_files(
                            template_dir,
                            pathlib.Path(tempfile.mkdtemp(prefix="preview_")),
                            template_dirs,
                            protected_files,
                            dry_run=True,
                        )
                    if preview_updated:
                        rollback_update(backup_dir, pathlib.Path("."), preview_updated)
                except Exception as rollback_error:
                    print(f"WARN: Rollback failed: {rollback_error}")
                    print(f"      Backup available at: {backup_dir}")
            print(f"ERROR: {e}")
            if e.file_path:
                print(f"  File: {e.file_path}")
            handle_update_error(e, current_version, target_version)
            return 1

        if args.dry_run:
            print(f"\nDRY RUN: Would update {len(updated)} files, skip {len(skipped)} protected files")
            if updated:
                print("\nFiles to be updated:")
                for f in updated[:20]:  # Show first 20
                    print(f"  - {f}")
                if len(updated) > 20:
                    print(f"  ... and {len(updated) - 20} more")
            if skipped:
                print("\nProtected files (not updated):")
                for f in skipped[:10]:
                    print(f"  - {f}")
                if len(skipped) > 10:
                    print(f"  ... and {len(skipped) - 10} more")
            return 0

        # Apply migrations (with error handling to ensure manifest is always updated)
        migration_applied = False
        migration_notes = "No migrations required"
        try:
            migration_applied, migration_notes = apply_migrations(current_version, target_version, pathlib.Path("."))
        except MigrationError as e:
            print(f"ERROR: {e}")
            if e.details:
                print(f"  Details: {e.details}")
            if e.suggestion:
                print(f"  Suggestion: {e.suggestion}")
            handle_update_error(e, current_version, target_version)
            migration_notes = f"Migration failed: {e.message}"
        except ValueError as e:
            # Handle case where version parsing fails (e.g., "latest" not resolved)
            if "latest" in str(e).lower() or "invalid literal" in str(e).lower():
                print(f"WARN: Skipping migrations due to version parsing issue: {e}")
                migration_notes = f"Skipped (version parsing issue: {e})"
            else:
                # Re-raise if it's a different error
                raise
        except Exception as e:
            print(f"WARN: Migration failed: {e}")
            migration_notes = f"Migration error: {e}"
            # Report unexpected errors
            handle_update_error(e, current_version, target_version)

        # Always update version manifest (even if migrations failed)
        manifest = update_version_manifest(manifest, target_version, migration_applied, migration_notes)
        
        # Validate before saving
        if not validate_before_update(manifest):
            return 1
        
        if not save_version_manifest(manifest, validate=False):
            return 1
        
        # Validate after saving
        if not validate_after_update(manifest):
            print("WARN: Manifest saved but validation failed. Review manually.")

        print(f"OK: Updated to version {target_version}")
        print(f"Updated {len(updated)} files, skipped {len(skipped)} protected files")
        if migration_notes:
            print(f"Migration notes: {migration_notes}")

        return 0

    finally:
        # Cleanup temp directory
        if template_dir.exists():
            shutil.rmtree(template_dir, ignore_errors=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
