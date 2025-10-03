param([int]$Port=8000)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
cd $PSScriptRoot
if (Test-Path .\.venv\Scripts\Activate.ps1) { & .\.venv\Scripts\Activate.ps1 }
$env:PYTHONPATH = (Resolve-Path .\backend).Path
# Free the port if already bound
$pids = (& netstat -ano | Select-String ":$Port" | ForEach-Object { ($_ -split '\s+')[-1] } | Select-Object -Unique)
if ($pids) {
  foreach ($p in $pids) { try { taskkill /PID $p /F | Out-Null } catch {} }
}
python -m uvicorn backend.app:app --host 127.0.0.1 --port $Port --reload
