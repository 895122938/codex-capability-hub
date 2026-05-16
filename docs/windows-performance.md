# Windows Performance

[中文](windows-performance.zh-CN.md) | English

Capability Hub is designed to improve Codex app startup and UI loading speed on Windows by keeping the startup hot path small.

## The problem

On Windows, Codex can become slow when many optional capabilities are hot at the same time:

- Large skill packs add file scanning overhead.
- Plugin discovery can dominate UI loading if many plugins are enabled or cache metadata is inconsistent.
- MCP servers can add startup work when they are enabled even though the current task does not need them.

## The approach

Recommended default on Windows:

- Keep broad skill packs cold.
- Keep `[features].plugins = false` until a plugin-backed capability is needed.
- Keep only tiny system skills hot.
- Prefer direct installed MCP commands over `npx`/`uvx` wrappers when possible.
- Wake capabilities only when a request clearly needs them.
- Sleep heavy one-off capabilities after use.

## Observed improvement

In one real Windows setup, moving heavy skills/plugins/MCPs to lazy wake produced a large improvement in Codex app loading-related operations:

| Operation | Before | After |
| --- | ---: | ---: |
| `plugin/list` | ~10–15 s | ~22 ms |
| `skills/list` | ~10 s | ~109 ms |

Your exact numbers will depend on hardware, installed capabilities, plugin cache state, antivirus scanning, and Codex version. The framework does not promise a fixed benchmark, but it targets the main cause: too much work on startup.

## Reset to lean startup

```powershell
$env:USERPROFILE\.codex\repair-tools\codex-plugin-toggle.ps1 --lean-startup
$env:USERPROFILE\.codex\repair-tools\codex-lean-hotpath.ps1 apply
```

## Repair bundled plugin cache

If OpenAI bundled plugin cache is locked or corrupt, try:

```powershell
$env:USERPROFILE\.codex\repair-tools\codex-plugin-toggle.ps1 --repair-cache
```

## Validate routing without changing state

```powershell
$env:USERPROFILE\.codex\repair-tools\codex-auto-wake.ps1 -Text "make a PPT and export PDF" -DryRun
```
