# Capability Hub auto-wake

This Codex installation uses a lean hot path. Most skills, MCP servers, and plugins are intentionally cold.

At the start of a task, if the request clearly needs a specialized capability, run:

```powershell
$env:USERPROFILE\.codex\repair-tools\codex-auto-wake.ps1 -Text "<user request>" -Apply
```

For workflows or end-to-end requests, prefer:

```powershell
$env:USERPROFILE\.codex\repair-tools\codex-auto-wake.ps1 -Text "<user request>" -Apply -PreferWorkflow
```

Sensitive capabilities such as authenticated Chrome, filesystem MCP, or full browser plugins require explicit user intent.
