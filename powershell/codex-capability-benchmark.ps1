param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$RemainingArgs
)

$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$ScriptName = "codex_capability_benchmark.py"
$Candidates = @(
  (Join-Path $Here $ScriptName),
  (Join-Path (Split-Path -Parent $Here) (Join-Path "scripts" $ScriptName)),
  (Join-Path $env:USERPROFILE (Join-Path ".codex\repair-tools" $ScriptName))
)
$Script = $Candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $Script) { throw "Cannot find $ScriptName. Tried: $($Candidates -join ', ')" }
$Python = if ($env:PYTHON) { $env:PYTHON } else { "python" }
& $Python $Script @RemainingArgs
exit $LASTEXITCODE
