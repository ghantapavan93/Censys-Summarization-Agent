Write-Host "=== PATHS ==="
Write-Host "PWD: $PWD"
Write-Host

Write-Host "=== BACKEND.APP INSPECTION ==="
$ErrorActionPreference='Stop'
$env:PYTHONPATH = (Resolve-Path .\backend).Path
& .\.venv\Scripts\python.exe - << 'PYCODE'
import backend.app, sys, os
print("BACKEND_APP_FILE =", os.path.abspath(backend.app.__file__))
print("CWD               =", os.path.abspath(os.getcwd()))
print("sys.path[0]       =", sys.path[0])
PYCODE

Write-Host
Write-Host "=== API HEALTH (requires server running) ==="
try {
  $h = curl.exe -s http://127.0.0.1:8000/api/health
  Write-Host $h
} catch {
  Write-Host "(server not running)"
}
