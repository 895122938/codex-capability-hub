# Contributing

Thanks for improving Codex Capability Hub.

## Ground rules

- Do not commit private `~/.codex` files, tokens, browser profiles, plugin caches, or proprietary skills.
- Prefer examples and schemas over user-specific payloads.
- Keep the hot path lean: new features should be lazy, opt-in, or registry-driven.
- Add or update tests for routing behavior.

## Local checks

```powershell
python -m compileall scripts
python -m pytest -q
```

## Registry changes

If you add fields to `capabilities.json`, update:

- `schemas/capability_registry.schema.json`
- `docs/capability-registry.md`
- `examples/capabilities.example.json`
- tests when routing behavior changes
