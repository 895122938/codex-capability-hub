[CmdletBinding()]
param(
  [string]$CodexHome = $(if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE ".codex" }),
  [switch]$ForceExamples,
  [switch]$NoExamples
)

$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $Here
$Tools = Join-Path $CodexHome "repair-tools"
New-Item -ItemType Directory -Force -Path $Tools | Out-Null

Write-Host "Installing Codex Capability Hub tools to $Tools"
Get-ChildItem -Path (Join-Path $RepoRoot "scripts\*.py") | Copy-Item -Destination $Tools -Force
Get-ChildItem -Path (Join-Path $RepoRoot "powershell\codex-*.ps1") | Copy-Item -Destination $Tools -Force

if (-not $NoExamples) {
  $Mappings = @{
    "capabilities.example.json" = "capabilities.json"
    "capability_workflows.example.json" = "capability_workflows.json"
    "capability_links.example.json" = "capability_links.json"
    "capability_interfaces.example.json" = "capability_interfaces.json"
    "plugin_aliases.example.json" = "plugin_aliases.json"
  }
  foreach ($item in $Mappings.GetEnumerator()) {
    $src = Join-Path $RepoRoot (Join-Path "examples" $item.Key)
    $dst = Join-Path $Tools $item.Value
    if ((Test-Path -LiteralPath $src) -and ($ForceExamples -or -not (Test-Path -LiteralPath $dst))) {
      Copy-Item -LiteralPath $src -Destination $dst -Force
      Write-Host "registry example -> $dst"
    }
  }
}

Write-Host ""
Write-Host "Installed. Try:"
Write-Host "  powershell -ExecutionPolicy Bypass -File `"$Tools\codex-wake.ps1`" list"
Write-Host "  powershell -ExecutionPolicy Bypass -File `"$Tools\codex-auto-wake.ps1`" -Text `"debug failing tests`" -DryRun"
Write-Host "  powershell -ExecutionPolicy Bypass -File `"$Tools\codex-capability-health.ps1`""
Write-Host "  powershell -ExecutionPolicy Bypass -File `"$Tools\codex-capability-benchmark.ps1`""
Write-Host ""
Write-Host "Add the snippet from examples\AGENTS.capability-hub.example.md to your AGENTS.md to enable auto-wake behavior."
