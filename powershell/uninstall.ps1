[CmdletBinding()]
param(
  [string]$CodexHome = $(if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE ".codex" }),
  [switch]$RemoveRegistries
)

$ErrorActionPreference = "Stop"
$Tools = Join-Path $CodexHome "repair-tools"
$Files = @(
  "common.py",
  "codex_auto_wake.py",
  "codex_wake.py",
  "codex_plugin_toggle.py",
  "codex_mcp_toggle.py",
  "codex_skills_hotcold.py",
  "codex_lean_hotpath.py",
  "codex_capability_inventory.py",
  "codex-auto-wake.ps1",
  "codex-wake.ps1",
  "codex-plugin-toggle.ps1",
  "codex-mcp-toggle.ps1",
  "codex-skills-hotcold.ps1",
  "codex-lean-hotpath.ps1",
  "codex-capability-inventory.ps1"
)
if ($RemoveRegistries) {
  $Files += @("capabilities.json", "capability_workflows.json", "capability_links.json", "capability_interfaces.json", "plugin_aliases.json")
}
foreach ($file in $Files) {
  $path = Join-Path $Tools $file
  if (Test-Path -LiteralPath $path) {
    Remove-Item -LiteralPath $path -Force
    Write-Host "removed $path"
  }
}
Write-Host "Uninstall complete. Backups, skills, plugins, and Codex config were not removed."
