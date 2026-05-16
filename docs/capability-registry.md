# Capability Registry

A capability is a named unit of power that can be woken only when needed.

By default the tools read:

```text
%USERPROFILE%\.codex\repair-tools\capabilities.json
```

In a cloned repo, the safe example file is used as a fallback:

```text
examples/capabilities.example.json
```

## Minimal capability

```json
{
  "id": "debug",
  "type": "bundle",
  "description": "Root-cause debugging helpers.",
  "triggers": ["bug", "test failure", "debug"],
  "aliases": ["bug", "debug"],
  "tags": ["debug", "test"],
  "risk_level": "low",
  "startup_cost_if_hot": "medium",
  "wake": [{ "type": "skill", "name": "systematic-debugging" }],
  "sleep": [{ "type": "skill", "name": "systematic-debugging" }]
}
```

## Action types

- `skill`: move a skill directory from cold archive into `CODEX_HOME/skills`.
- `mcp`: toggle an MCP server's `enabled` key in `config.toml`.
- `plugin`: toggle a Codex plugin's `enabled` key and `[features].plugins`.
- `script`: run a local command.
- `instruction`: print guidance only.

## Sensitive capabilities

Use `"sensitive": true` for capabilities involving login state, browser cookies, broad filesystem access, or other privileged local state. The auto-router will not apply sensitive capabilities unless the request explicitly matches that capability.

## Plugin aliases

Plugin action names can be friendly aliases:

```json
{ "type": "plugin", "name": "presentations" }
```

Aliases resolve through built-ins and optional `plugin_aliases.json`. Override with:

```powershell
$env:CODEX_PLUGIN_ALIASES_JSON = "C:\path\to\plugin_aliases.json"
```
