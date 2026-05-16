# Architecture

Capability Hub separates a tiny always-on router from heavy capability payloads.

```mermaid
flowchart LR
  U["User request"] --> A["AGENTS.md auto-wake rule"]
  A --> R["codex-auto-wake"]
  R --> C["capabilities.json"]
  R --> W["capability_workflows.json"]
  C --> K["codex-wake"]
  W --> K
  K --> S["skills hot/cold"]
  K --> M["MCP enabled toggle"]
  K --> P["plugin enabled toggle"]
```

Layers:

1. Instruction layer: `AGENTS.md` tells Codex when to route.
2. Registry layer: JSON files describe capabilities and workflows.
3. Execution layer: scripts make reversible local changes.
4. Payload layer: the user's actual skills, MCP servers, plugins, and tools.
