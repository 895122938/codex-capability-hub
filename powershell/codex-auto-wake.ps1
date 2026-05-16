[CmdletBinding()]
param(
  [string]$Text,
  [switch]$Apply,
  [switch]$DryRun,
  [switch]$WithLinked,
  [switch]$PreferWorkflow,
  [switch]$FullWorkflow,
  [int]$Threshold = 8,
  [switch]$AllowSensitive,
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$RemainingArgs
)

$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$ScriptName = "codex_auto_wake.py"
$Candidates = @(
  (Join-Path $Here $ScriptName),
  (Join-Path (Split-Path -Parent $Here) (Join-Path "scripts" $ScriptName)),
  (Join-Path $env:USERPROFILE (Join-Path ".codex\repair-tools" $ScriptName))
)
$Script = $Candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $Script) { throw "Cannot find $ScriptName. Tried: $($Candidates -join ', ')" }
$Python = if ($env:PYTHON) { $env:PYTHON } else { "python" }
$PyArgs = @()
if ($Text) { $PyArgs += @("--text", $Text) }
if ($Apply) { $PyArgs += "--apply" }
if ($DryRun) { $PyArgs += "--dry-run" }
if ($WithLinked) { $PyArgs += "--with-linked" }
if ($PreferWorkflow) { $PyArgs += "--prefer-workflow" }
if ($FullWorkflow) { $PyArgs += "--full-workflow" }
if ($AllowSensitive) { $PyArgs += "--allow-sensitive" }
if ($PSBoundParameters.ContainsKey("Threshold")) { $PyArgs += @("--threshold", [string]$Threshold) }
$PyArgs += $RemainingArgs
& $Python $Script @PyArgs
exit $LASTEXITCODE
