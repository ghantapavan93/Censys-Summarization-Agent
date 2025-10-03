param(
  [string]$File = 'examples/hosts_dataset.json',
  [string]$Schema = 'schemas/hosts_dataset.schema.json'
)

$ErrorActionPreference = 'Stop'

function Write-Log {
  param([string]$Message, [string]$Level = 'INFO')
  $ts = (Get-Date).ToString('s')
  Write-Host "[$ts][$Level] $Message"
}

if (!(Test-Path $File)) { throw "File not found: $File" }
if (!(Test-Path $Schema)) { throw "Schema not found: $Schema" }

# Basic checks without external deps
Write-Log "Loading $File"
$json = Get-Content $File -Raw | ConvertFrom-Json -Depth 20
if (-not $json.metadata -or -not $json.hosts) {
  throw "Missing required top-level keys: metadata or hosts"
}

$hostCount = $json.hosts.Count
if ($json.metadata.hosts_count -ne $hostCount) {
  Write-Log "Fixing metadata.hosts_count from $($json.metadata.hosts_count) to $hostCount" 'WARN'
  $json.metadata.hosts_count = $hostCount
}

# Simple structural checks
$missingIp = @()
foreach ($h in $json.hosts) {
  if (-not $h.ip) { $missingIp += $h }
}
if ($missingIp.Count -gt 0) {
  throw "Found hosts without ip: $($missingIp.Count)"
}

# Write back if changed
($json | ConvertTo-Json -Depth 50) | Out-File -FilePath $File -Encoding UTF8
Write-Log "Validation passed for $File (hosts=$hostCount)"
