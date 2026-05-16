from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from common import (
    capabilities_path,
    codex_home,
    cold_archive,
    interfaces_path,
    json_load,
    links_path,
    load_config,
    redact,
    resolve_plugin,
    workflows_path,
)


def hot_skills() -> list[dict[str, Any]]:
    root = codex_home() / "skills"
    rows = []
    if root.exists():
        for skill_md in sorted(root.rglob("SKILL.md")):
            rows.append({"name": skill_md.parent.name, "path": str(skill_md.parent)})
    return rows


def cold_skills() -> list[dict[str, Any]]:
    root = cold_archive()
    rows = []
    if root.exists():
        for skill_md in sorted(root.rglob("SKILL.md")):
            rows.append({"name": skill_md.parent.name, "path": str(skill_md.parent)})
    return rows


def configured_mcp() -> dict[str, Any]:
    return redact(load_config().get("mcp_servers", {}) or {})


def configured_plugins() -> dict[str, Any]:
    return redact(load_config().get("plugins", {}) or {})


def registries() -> dict[str, str]:
    return {
        "capabilities": str(capabilities_path()),
        "workflows": str(workflows_path()),
        "links": str(links_path()),
        "interfaces": str(interfaces_path()),
    }


def inventory() -> dict[str, Any]:
    capabilities = json_load(capabilities_path(), {"capabilities": []}).get("capabilities", [])
    return {
        "codex_home": str(codex_home()),
        "cold_archive": str(cold_archive()),
        "registries": registries(),
        "capability_count": len(capabilities),
        "capabilities": [
            {
                "id": item.get("id"),
                "type": item.get("type"),
                "description": item.get("description"),
                "risk_level": item.get("risk_level"),
                "sensitive": bool(item.get("sensitive")),
                "startup_cost_if_hot": item.get("startup_cost_if_hot"),
            }
            for item in capabilities if isinstance(item, dict)
        ],
        "hot_skills": hot_skills(),
        "cold_skill_count": len(cold_skills()),
        "mcp_servers": configured_mcp(),
        "plugins": configured_plugins(),
    }


def markdown(data: dict[str, Any]) -> str:
    lines = ["# Codex Capability Inventory", ""]
    lines.append(f"- Codex home: `{data['codex_home']}`")
    lines.append(f"- Cold archive: `{data['cold_archive']}`")
    lines.append(f"- Capabilities: {data['capability_count']}")
    lines.append(f"- Hot skills: {len(data['hot_skills'])}")
    lines.append(f"- Cold skills: {data['cold_skill_count']}")
    lines.append("")
    lines.append("## Registries")
    for key, value in data["registries"].items():
        lines.append(f"- {key}: `{value}`")
    lines.append("")
    lines.append("## Capabilities")
    for cap in data["capabilities"]:
        sensitive = " sensitive" if cap.get("sensitive") else ""
        lines.append(f"- `{cap.get('id')}` ({cap.get('type')}, risk={cap.get('risk_level')}{sensitive}): {cap.get('description')}")
    lines.append("")
    lines.append("## Hot skills")
    for skill in data["hot_skills"]:
        lines.append(f"- `{skill['name']}`")
    lines.append("")
    lines.append("## MCP servers")
    for name, server in sorted(data["mcp_servers"].items()):
        enabled = server.get("enabled", True) if isinstance(server, dict) else "unknown"
        lines.append(f"- `{name}` enabled={enabled}")
    lines.append("")
    lines.append("## Plugins")
    for name, plugin in sorted(data["plugins"].items()):
        enabled = plugin.get("enabled", "default") if isinstance(plugin, dict) else "unknown"
        lines.append(f"- `{name}` enabled={enabled}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a redacted inventory of Capability Hub inputs.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown")
    parser.add_argument("--output", "-o", help="Write to file")
    args = parser.parse_args()
    data = inventory()
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n" if args.json else markdown(data)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print("wrote", args.output)
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
