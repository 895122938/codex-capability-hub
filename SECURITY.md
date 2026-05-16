# Security Policy

Capability Hub edits local Codex configuration and can enable tools that read files, browse pages, or use authenticated browser state.

Never commit:

- `~/.codex/config.toml`
- API keys, GitHub PATs, OAuth tokens, cookies, browser profiles
- private skills or private documents
- proprietary plugin cache directories

Mark filesystem MCP, authenticated Chrome, and full browser plugins as `sensitive: true`.
