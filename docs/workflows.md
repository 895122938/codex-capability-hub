# Workflows

Workflows connect multiple capability phases without waking every heavy dependency at once.

Example:

```json
{
  "id": "research-to-paper",
  "description": "From literature search to report/slides deliverable.",
  "triggers": ["find papers then write", "research to report"],
  "phases": [
    { "capability": "research-lit", "role": "collect evidence and citations" },
    { "capability": "office", "role": "produce document or slides" }
  ]
}
```

Progressive commands:

```powershell
codex-wake.ps1 workflow-list
codex-wake.ps1 workflow-start research-to-paper
codex-wake.ps1 workflow-next
codex-wake.ps1 workflow-state
codex-wake.ps1 workflow-clear
```

`workflow-start` wakes phase 1 only. This preserves startup speed and avoids loading all heavy capabilities in a pipeline at once.

Natural-language routing can prefer progressive workflows:

```powershell
codex-auto-wake.ps1 -Text "find papers then write a report" -Apply -PreferWorkflow
```

Use `-FullWorkflow` only when you intentionally want every phase woken at once.
