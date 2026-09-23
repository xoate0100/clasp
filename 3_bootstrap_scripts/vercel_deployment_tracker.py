#!/usr/bin/env python3
"""
Vercel Deployment Tracker
Tracks Vercel project deployments and their status.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install pyyaml")
    sys.exit(1)


def get_vercel_projects() -> List[Dict[str, Any]]:
    """Get Vercel projects using CLI."""
    try:
        import platform
        vercel_cmd = "vercel.cmd" if platform.system() == "Windows" else "vercel"
        
        result = subprocess.run(
            [vercel_cmd, "projects", "ls"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        if result.returncode != 0:
            print(f"WARN: Vercel CLI failed: {result.stderr}")
            return []
        
        # Parse output - Vercel outputs a table
        projects = []
        lines = result.stdout.strip().split('\n')
        
        for line in lines[2:]:  # Skip header
            if not line.strip() or line.strip().startswith('>'):
                continue
            
            parts = [p.strip() for p in line.split()]
            if len(parts) >= 2:
                project = {
                    "name": parts[0],
                    "url": parts[1] if parts[1] != "--" else None,
                    "updated": parts[2] if len(parts) > 2 else None,
                    "node_version": parts[3] if len(parts) > 3 else None,
                }
                projects.append(project)
        
        return projects
    except Exception as e:
        print(f"ERROR: Failed to get Vercel projects: {e}")
        return []


def get_project_deployments(project_name: str) -> List[Dict[str, Any]]:
    """Get deployments for a specific project."""
    try:
        import platform
        vercel_cmd = "vercel.cmd" if platform.system() == "Windows" else "vercel"
        
        result = subprocess.run(
            [vercel_cmd, "ls", project_name, "--yes"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        if result.returncode != 0:
            return []
        
        # Parse deployments
        deployments = []
        lines = result.stdout.strip().split('\n')
        
        for line in lines[2:]:  # Skip header
            if not line.strip() or '---' in line:
                continue
            
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 3:
                deployment = {
                    "url": parts[0].strip(),
                    "state": parts[1].strip() if len(parts) > 1 else "READY",
                    "age": parts[2].strip() if len(parts) > 2 else None,
                }
                deployments.append(deployment)
        
        return deployments
    except Exception:
        return []


def track_deployments(output_file: str = "vercel_deployments.json") -> Dict[str, Any]:
    """Track all Vercel deployments."""
    print("Fetching Vercel projects...")
    projects = get_vercel_projects()
    
    if not projects:
        print("No Vercel projects found.")
        return {}
    
    print(f"Found {len(projects)} projects")
    print("Tracking deployments...")
    
    tracked_data = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_projects": len(projects),
        "projects": [],
    }
    
    for project in projects:
        project_name = project["name"]
        print(f"  Tracking {project_name}...")
        
        deployments = get_project_deployments(project_name)
        
        project_data = {
            "name": project_name,
            "production_url": project.get("url"),
            "updated": project.get("updated"),
            "node_version": project.get("node_version"),
            "is_v0": project_name.startswith("v0-"),
            "deployments": deployments,
            "deployment_count": len(deployments),
            "latest_deployment": deployments[0] if deployments else None,
        }
        
        tracked_data["projects"].append(project_data)
    
    # Save to file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(tracked_data, f, indent=2)
    
    print(f"\nDeployment tracking saved to: {output_file}")
    
    # Summary
    v0_projects = sum(1 for p in tracked_data["projects"] if p["is_v0"])
    with_urls = sum(1 for p in tracked_data["projects"] if p["production_url"])
    
    print(f"\nSummary:")
    print(f"  Total projects: {tracked_data['total_projects']}")
    print(f"  v0 projects: {v0_projects}")
    print(f"  With production URLs: {with_urls}")
    
    return tracked_data


def check_project_status(project_name: str) -> Dict[str, Any]:
    """Check status of a specific project."""
    projects = get_vercel_projects()
    project = next((p for p in projects if p["name"] == project_name), None)
    
    if not project:
        return {"error": f"Project {project_name} not found"}
    
    deployments = get_project_deployments(project_name)
    
    return {
        "name": project_name,
        "production_url": project.get("url"),
        "status": "active" if project.get("url") else "inactive",
        "deployments": len(deployments),
        "latest_deployment": deployments[0] if deployments else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="vercel_deployment_tracker.py",
        description="Track Vercel project deployments",
    )
    parser.add_argument(
        "--project",
        help="Check status of specific project",
    )
    parser.add_argument(
        "--output",
        default="vercel_deployments.json",
        help="Output file for deployment data",
    )
    
    args = parser.parse_args()
    
    if args.project:
        status = check_project_status(args.project)
        print(json.dumps(status, indent=2))
        return 0
    
    track_deployments(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

