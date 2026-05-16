# Codex Capability Hub

[中文文档](README.zh-CN.md) | English

A lightweight framework for **lazy-loading Codex capabilities**: skills, MCP servers, plugins, and multi-step workflows.

## Why this matters

Codex can become noticeably slower on Windows when too many skills, MCP servers, and plugins are kept hot at startup. Capability Hub keeps the startup hot path small, then wakes specialized capabilities only when a user request clearly needs them.

This can **significantly improve Codex app startup and UI loading speed on Windows**, especially for power users with many skills/plugins/MCP servers installed. In one real Windows setup, after moving heavy capabilities to lazy loading, `plugin/list` improved from roughly 10–15 seconds to about 22 ms, and `skills/list` improved from roughly 10 seconds to about 109 ms. Results depend on each installation, but the design goal is clear: fast startup first, rich capabilities on demand.

## Core idea

- Keep only a tiny routing layer hot.
- Describe capabilities in JSON registries.
- Let `codex-auto-wake` map natural language to a capability or workflow.
- Let `codex-wake` warm skills, toggle MCP servers, toggle plugins, or progress a workflow.
- Sleep heavy one-off capabilities after use.

## What this is

- A small always-on router (`codex-auto-wake`) that maps natural language to capabilities.
- A reversible executor (`codex-wake`) that warms skills, toggles MCP servers, toggles plugins, or starts workflows.
- A JSON registry format users can customize for their own skills/MCP/plugins.
- PowerShell wrappers and installer for Codex on Windows.
- A framework, not a fixed capability pack: users decide what to wire in.

## What this is not

This repo is **not** a backup of any private `~/.codex` directory. Do not publish:

- API keys, tokens, or `~/.codex/config.toml`.
- Private skills or proprietary plugin cache content.
- Browser profiles, cookies, or login-state data.
- Project-specific private files.

## Quick start

```powershell
git clone https://github.com/<you>/codex-capability-hub.git
cd codex-capability-hub
powershell -ExecutionPolicy Bypass -File .\powershell\install.ps1
```

Test routing:

```powershell
$env:USERPROFILE\.codex\repair-tools\codex-auto-wake.ps1 -Text "help me debug this failing test" -DryRun
$env:USERPROFILE\.codex\repair-tools\codex-wake.ps1 list
```

Enable auto-wake behavior by copying the snippet from:

```text
examples/AGENTS.capability-hub.example.md
```

into your project/global `AGENTS.md`.

## Configure your own capabilities

After install, edit the registry files in:

```text
%USERPROFILE%\.codex\repair-tools\capabilities.json
%USERPROFILE%\.codex\repair-tools\capability_workflows.json
%USERPROFILE%\.codex\repair-tools\capability_links.json
%USERPROFILE%\.codex\repair-tools\capability_interfaces.json
```

You can also point the tools at alternate files with environment variables:

- `CODEX_CAPABILITIES_JSON`
- `CODEX_CAPABILITY_WORKFLOWS_JSON`
- `CODEX_CAPABILITY_LINKS_JSON`
- `CODEX_CAPABILITY_INTERFACES_JSON`
- `CODEX_PLUGIN_ALIASES_JSON`
- `CODEX_HOME`
- `CODEX_COLD_ARCHIVE`

## Typical commands

```powershell
codex-wake.ps1 list
codex-wake.ps1 explain debug
codex-wake.ps1 dry-run office
codex-wake.ps1 wake debug
codex-wake.ps1 sleep debug
codex-auto-wake.ps1 -Text "make a PPT and export PDF" -Apply
codex-auto-wake.ps1 -Text "find papers then write a report" -Apply -PreferWorkflow
codex-plugin-toggle.ps1 --lean-startup
codex-lean-hotpath.ps1 apply
codex-capability-inventory.ps1 --json
```

## Example use cases

- Keep document/PPT/PDF plugins cold until a document task appears.
- Enable Playwright/browser MCP only for web testing or screenshot work.
- Require explicit intent before waking login-state Chrome or broad filesystem capabilities.
- Chain capabilities through progressive workflows, such as research → report → slides.

## Project layout

```text
scripts/      Python implementation
powershell/   Windows wrappers, installer, uninstaller
examples/     Safe example registries and AGENTS snippet
schemas/      JSON schema for capability registry
docs/         Architecture, workflows, Windows performance, security notes
tests/        Routing and registry tests
```

## Development

```powershell
python -m compileall scripts
python -m pytest -q
```

See `docs/` for the architecture and registry contract.
