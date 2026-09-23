#!/bin/bash
# Cleanup development environment resources (processes, ports, artifacts)
# Kills accumulated processes, frees occupied ports, and cleans up test artifacts

set -euo pipefail

FORCE=false
if [[ "${1:-}" == "--force" ]] || [[ "${1:-}" == "-f" ]]; then
    FORCE=true
fi

echo "Development Environment Resource Cleanup"
echo "======================================="
echo ""

# Function to kill processes by name pattern
kill_processes_by_name() {
    local pattern=$1
    local description=$2
    local pids=$(pgrep -f "$pattern" 2>/dev/null || true)
    
    if [ -n "$pids" ]; then
        echo "Stopping $description processes..."
        echo "$pids" | while read -r pid; do
            if kill -0 "$pid" 2>/dev/null; then
                kill -TERM "$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null
                echo "  Stopped: $(ps -p "$pid" -o comm= 2>/dev/null || echo "process") (PID: $pid)"
            fi
        done
    else
        echo "No $description processes found"
    fi
}

# Function to kill processes by port
kill_processes_by_port() {
    local port=$1
    local pids=$(lsof -ti ":$port" 2>/dev/null || true)
    
    if [ -n "$pids" ]; then
        echo "$pids" | while read -r pid; do
            if kill -0 "$pid" 2>/dev/null; then
                local proc_name=$(ps -p "$pid" -o comm= 2>/dev/null || echo "process")
                kill -TERM "$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null
                echo "  Freed port $port from $proc_name (PID: $pid)"
            fi
        done
    fi
}

# Cleanup Node.js processes
echo "1. Cleaning up Node.js processes..."
kill_processes_by_name "node" "Node.js"

# Cleanup test framework processes
echo ""
echo "2. Cleaning up test framework processes..."
kill_processes_by_name "playwright" "Playwright"
kill_processes_by_name "jest" "Jest"
kill_processes_by_name "vitest" "Vitest"

# Cleanup browser processes
echo ""
echo "3. Cleaning up browser processes..."
kill_processes_by_name "chrome" "Chrome"
kill_processes_by_name "chromium" "Chromium"
kill_processes_by_name "firefox" "Firefox"

# Cleanup common development ports
echo ""
echo "4. Freeing common development ports..."
COMMON_PORTS=(3000 3001 3002 3003 4000 5000 5173 8080 8081 9000)
for port in "${COMMON_PORTS[@]}"; do
    kill_processes_by_port "$port"
done

# Cleanup test artifacts
echo ""
echo "5. Cleaning up test artifacts..."
ARTIFACT_PATHS=(
    "test-results"
    "playwright-report"
    "playwright/.cache"
    "coverage"
    ".nyc_output"
    "*.log"
)

for path in "${ARTIFACT_PATHS[@]}"; do
    if [ -e "$path" ] || [ -n "$(find . -maxdepth 1 -name "$path" 2>/dev/null)" ]; then
        if [ "$FORCE" = true ]; then
            rm -rf $path 2>/dev/null && echo "  Removed: $path" || echo "  Failed to remove: $path"
        else
            echo "  Found: $path (use --force to remove)"
        fi
    fi
done

# Cleanup build artifacts
echo ""
echo "6. Cleaning up build artifacts..."
BUILD_PATHS=(
    "dist"
    "build"
    ".next"
    "out"
    ".turbo"
)

for path in "${BUILD_PATHS[@]}"; do
    if [ -e "$path" ]; then
        if [ "$FORCE" = true ]; then
            rm -rf "$path" 2>/dev/null && echo "  Removed: $path" || echo "  Failed to remove: $path"
        else
            echo "  Found: $path (use --force to remove)"
        fi
    fi
done

echo ""
echo "Cleanup complete!"
echo ""
echo "Note: Use --force flag to automatically remove artifacts"
echo "      Run 'ps aux | wc -l' to check remaining processes"

