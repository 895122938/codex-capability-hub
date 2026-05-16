from __future__ import annotations

import argparse
import re

from common import backup_config, load_config, read_config_text, set_toml_key_in_matching_section, write_config_text


def configured() -> dict:
    return load_config().get("mcp_servers", {}) or {}


def mcp_section_patterns(name: str) -> list[str]:
    escaped = re.escape(name)
    quoted = re.escape(f'"{name}"')
    return [
        rf"^\[mcp_servers\.{escaped}\]$",
        rf"^\[mcp_servers\.{quoted}\]$",
    ]


def set_enabled(name: str, enabled: bool) -> int:
    servers = configured()
    if name not in servers:
        print("unknown MCP", name)
        print("available:", ", ".join(sorted(servers)))
        return 2
    backup_config(f"mcp-toggle-{name}-{str(enabled).lower()}")
    text = read_config_text()
    text = set_toml_key_in_matching_section(
        text,
        mcp_section_patterns(name),
        f'mcp_servers."{name}"',
        "enabled",
        bool(enabled),
        "Codex Capability Hub on-demand MCP toggle",
    )
    write_config_text(text)
    print(name, "enabled" if enabled else "disabled")
    print("note: restart Codex or reload MCP status for this to take effect")
    return 0


def status() -> None:
    servers = configured()
    for name in sorted(servers):
        server = servers[name]
        print(f'{name}: enabled={server.get("enabled", True)} command={server.get("command", "")}')


def main() -> int:
    parser = argparse.ArgumentParser(description="Toggle MCP servers on demand.")
    parser.add_argument("cmd", choices=["list", "on", "off"])
    parser.add_argument("name", nargs="?")
    args = parser.parse_args()
    if args.cmd == "list":
        status(); return 0
    if not args.name:
        print("name required")
        return 2
    return set_enabled(args.name, args.cmd == "on")


if __name__ == "__main__":
    raise SystemExit(main())
