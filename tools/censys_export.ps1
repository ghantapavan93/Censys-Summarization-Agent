# Requires: Censys CLI installed and authenticated (censys config), jq installed if using -IncludeJq
# Usage examples (PowerShell):
#   ./tools/censys_export.ps1 -Query "services.service_name: SSH" -Fields @(
#     'ip','location.city','location.country','location.country_code','location.coordinates',
#     'autonomous_system.asn','autonomous_system.name','autonomous_system.country_code',
#     'dns.dns_name','services.port','services.service_name','services.banner','services.software','services.vulnerabilities'
#   ) -FileBase ssh_hosts -IncludeJq -ShapeOutput examples/hosts_dataset.json
#   ./tools/censys_export.ps1 -Query "services.service_name: HTTP" -PerPage 100 -Pages -1 -OutDir data/exports

param(
  [Parameter(Mandatory=$true)] [string]$Query,
  [string]$Index = 'hosts',
  [string[]]$Fields = @(
    'ip','location.city','location.country','location.country_code','location.coordinates',
    'autonomous_system.asn','autonomous_system.name','autonomous_system.country_code',
    'dns.dns_name','services.port','services.service_name','services.banner','services.software','services.vulnerabilities'
  ),
  [int]$Pages = -1,
  [int]$PerPage = 100,
  [ValidateSet('ndjson','json')] [string]$Format = 'ndjson',
  [string]$OutDir = 'data/exports',
  [string]$FileBase = 'export',
  [switch]$IncludeJq,
  [string]$ShapeOutput, # e.g., examples/hosts_dataset.json
  [switch]$GzipRaw
)

$ErrorActionPreference = 'Stop'

function Write-Log {
  param([string]$Message, [string]$Level = 'INFO')
  $ts = (Get-Date).ToString('s')
  Write-Host "[$ts][$Level] $Message"
}

function Get-Sha256 {
  param([string]$Path)
  if (!(Test-Path $Path)) { return $null }
  return (Get-FileHash -Algorithm SHA256 -Path $Path).Hash.ToLower()
}

function Compress-GZipFile {
  param([string]$InputPath, [string]$OutputPath)
  Add-Type -AssemblyName System.IO.Compression
  Add-Type -AssemblyName System.IO.Compression.FileSystem | Out-Null
  $inStream = [System.IO.File]::OpenRead($InputPath)
  try {
    $outStream = [System.IO.File]::Create($OutputPath)
    try {
      $gzip = New-Object System.IO.Compression.GZipStream($outStream, [System.IO.Compression.CompressionMode]::Compress)
      try { $inStream.CopyTo($gzip) } finally { $gzip.Dispose() }
    } finally { $outStream.Dispose() }
  } finally { $inStream.Dispose() }
}

# Ensure output directory
$stamp = (Get-Date).ToString('yyyy-MM-dd')
$targetDir = Join-Path $OutDir $stamp
New-Item -ItemType Directory -Path $targetDir -Force | Out-Null

# Resolve paths
$rawPath = Join-Path $targetDir ("{0}.{1}" -f $FileBase, $Format)
$rawGzPath = "$rawPath.gz"

Write-Log "Exporting query to $rawPath"
# Build CLI command (PowerShell-friendly quoting)
$fieldsArg = if ($Fields -and $Fields.Length -gt 0) { " --fields " + ($Fields -join ',') } else { '' }
$fmtArg = " --format $Format"
$cmd = "censys search $Index '$Query' --pages $Pages --per-page $PerPage$fieldsArg$fmtArg"

if ($IncludeJq.IsPresent -and $ShapeOutput) {
  # Pipe to jq to shape a single JSON document similar to examples/hosts_dataset.json
  $jqFilterPath = "tools/shape_hosts.jq"
  if (!(Test-Path $jqFilterPath)) {
    throw "Missing jq filter at $jqFilterPath. Create it or run without -IncludeJq."
  }
  Write-Log "Running with jq transform to $ShapeOutput"
  $cmd = "$cmd | jq -s -f $jqFilterPath > $ShapeOutput"
  # Also save the raw stream separately to $rawPath
  $cmd = "$cmd; censys search $Index '$Query' --pages $Pages --per-page $PerPage$fieldsArg$fmtArg > $rawPath"
} else {
  $cmd = "$cmd > $rawPath"
}

Write-Log "Running: $cmd"
# Invoke in PowerShell
Invoke-Expression $cmd

if ($GzipRaw.IsPresent) {
  Write-Log "Gzipping $rawPath -> $rawGzPath"
  Compress-GZipFile -InputPath $rawPath -OutputPath $rawGzPath
}

# Build manifest
$manifest = [ordered]@{}
$manifest.created_at = (Get-Date).ToString('s') + 'Z'
$manifest.index = $Index
$manifest.query = $Query
$manifest.pages = $Pages
$manifest.per_page = $PerPage
$manifest.fields = $Fields
$manifest.format = $Format
$manifest.raw_file = (Resolve-Path $rawPath).Path
$manifest.raw_sha256 = Get-Sha256 $rawPath
if (Test-Path $rawGzPath) { $manifest.raw_gz_file = (Resolve-Path $rawGzPath).Path }
if ($ShapeOutput) {
  if (Test-Path $ShapeOutput) {
    $manifest.shaped_file = (Resolve-Path $ShapeOutput).Path
    $manifest.shaped_sha256 = Get-Sha256 $ShapeOutput
  }
}
try {
  $ver = (& censys --version) 2>$null
  if ($ver) { $manifest.tool_version = $ver.Trim() }
} catch { }

$manifestPath = Join-Path $targetDir ("{0}.manifest.json" -f $FileBase)
$manifest | ConvertTo-Json -Depth 6 | Out-File -FilePath $manifestPath -Encoding UTF8
Write-Log "Wrote manifest: $manifestPath"

Write-Log "Done."
