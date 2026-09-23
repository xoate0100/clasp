#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Cleanup development environment resources (processes, ports, artifacts)

.DESCRIPTION
    Kills accumulated processes, frees occupied ports, and cleans up test artifacts
    to prevent resource accumulation in development environments.

.EXAMPLE
    .\cleanup-dev.ps1
    .\cleanup-dev.ps1 -Force
#>

param(
    [switch]$Force
)

$ErrorActionPreference = "Continue"

Write-Host "Development Environment Resource Cleanup" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""

# Function to kill processes by name pattern
function Stop-ProcessesByName {
    param([string]$NamePattern, [string]$Description)
    
    $processes = Get-Process -Name $NamePattern -ErrorAction SilentlyContinue
    if ($processes) {
        Write-Host "Stopping $Description processes..." -ForegroundColor Yellow
        $processes | ForEach-Object {
            try {
                Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
                Write-Host "  Stopped: $($_.ProcessName) (PID: $($_.Id))" -ForegroundColor Green
            } catch {
                Write-Host "  Failed to stop: $($_.ProcessName) (PID: $($_.Id))" -ForegroundColor Red
            }
        }
    } else {
        Write-Host "No $Description processes found" -ForegroundColor Gray
    }
}

# Function to kill processes by port
function Stop-ProcessesByPort {
    param([int[]]$Ports, [string]$Description)
    
    foreach ($port in $Ports) {
        $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
        if ($connections) {
            $processIds = $connections | Select-Object -ExpandProperty OwningProcess -Unique
            foreach ($pid in $processIds) {
                try {
                    $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
                    if ($proc) {
                        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                        Write-Host "  Freed port $port from $($proc.ProcessName) (PID: $pid)" -ForegroundColor Green
                    }
                } catch {
                    Write-Host "  Failed to free port $port (PID: $pid)" -ForegroundColor Red
                }
            }
        }
    }
}

# Cleanup Node.js processes
Write-Host "1. Cleaning up Node.js processes..." -ForegroundColor Cyan
Stop-ProcessesByName "node" "Node.js"

# Cleanup test framework processes
Write-Host "`n2. Cleaning up test framework processes..." -ForegroundColor Cyan
Stop-ProcessesByName "playwright" "Playwright"
Stop-ProcessesByName "jest" "Jest"
Stop-ProcessesByName "vitest" "Vitest"

# Cleanup browser processes
Write-Host "`n3. Cleaning up browser processes..." -ForegroundColor Cyan
Stop-ProcessesByName "chrome" "Chrome"
Stop-ProcessesByName "chromium" "Chromium"
Stop-ProcessesByName "msedge" "Edge"
Stop-ProcessesByName "firefox" "Firefox"

# Cleanup common development ports
Write-Host "`n4. Freeing common development ports..." -ForegroundColor Cyan
$commonPorts = @(3000, 3001, 3002, 3003, 4000, 5000, 5173, 8080, 8081, 9000)
Stop-ProcessesByPort $commonPorts "development"

# Cleanup test artifacts
Write-Host "`n5. Cleaning up test artifacts..." -ForegroundColor Cyan
$artifactPaths = @(
    "test-results",
    "playwright-report",
    "playwright/.cache",
    "coverage",
    ".nyc_output",
    "*.log"
)

foreach ($path in $artifactPaths) {
    if (Test-Path $path) {
        try {
            if ($Force) {
                Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue
                Write-Host "  Removed: $path" -ForegroundColor Green
            } else {
                Write-Host "  Found: $path (use -Force to remove)" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "  Failed to remove: $path" -ForegroundColor Red
        }
    }
}

# Cleanup build artifacts
Write-Host "`n6. Cleaning up build artifacts..." -ForegroundColor Cyan
$buildPaths = @(
    "dist",
    "build",
    ".next",
    "out",
    ".turbo"
)

foreach ($path in $buildPaths) {
    if (Test-Path $path) {
        try {
            if ($Force) {
                Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue
                Write-Host "  Removed: $path" -ForegroundColor Green
            } else {
                Write-Host "  Found: $path (use -Force to remove)" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "  Failed to remove: $path" -ForegroundColor Red
        }
    }
}

# WSL cleanup (if on Windows)
if ($IsWindows -or $env:OS -like "*Windows*") {
    Write-Host "`n7. Checking WSL processes..." -ForegroundColor Cyan
    $wslProcesses = Get-Process -Name "wsl" -ErrorAction SilentlyContinue
    if ($wslProcesses) {
        Write-Host "  Found WSL processes (manual cleanup may be needed)" -ForegroundColor Yellow
        if ($Force) {
            Write-Host "  Use 'wsl --shutdown' to stop all WSL instances" -ForegroundColor Yellow
        }
    }
}

Write-Host "`nCleanup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Note: Use -Force flag to automatically remove artifacts" -ForegroundColor Gray
Write-Host "      Run 'Get-Process | Measure-Object' to check remaining processes" -ForegroundColor Gray

