$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
Start-Process powershell -ArgumentList '-NoExit','-Command',"cd `"$PSScriptRoot`"; .\run_backend.ps1"
Start-Process powershell -ArgumentList '-NoExit','-Command',"cd `"$PSScriptRoot\frontend`"; npm run dev"
