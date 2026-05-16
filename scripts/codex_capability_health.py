from __future__ import annotations

import argparse
import json
from typing import Any

from common import (
    capabilities_path,
    codex_home,
    cold_archive,
    interfaces_path,
    json_load,
    links_path,
    load_config,
    optional_plugins,
    plugin_aliases_path,
    resolve_plugin,
    workflows_path,
)


SEVERITY_ORDER = {"ok": 0, "info": 1, "warn": 2, "critical": 3}


def _enabled(value: Any, default: bool = True) -> bool:
    if isinstance(value, dict):
        return bool(value.get("enabled", default))
    return default


def _explicit_enabled(value: Any) -> bool:
    return isinstance(value, dict) and value.get("enabled") is True


def collect_health() -> dict[str, Any]:
    config = load_config()
    features = config.get("features", {}) or {}
    plugins = config.get("plugins", {}) or {}
    mcp_servers = config.get("mcp_servers", {}) or {}

    skills_root = codex_home() / "skills"
    hot_skill_dirs = sorted([p.name for p in skills_root.iterdir() if p.is_dir()]) if skills_root.exists() else []
    hot_skill_md_count = sum(1 for _ in skills_root.rglob("SKILL.md")) if skills_root.exists() else 0

    archive = cold_archive()
    cold_archive_roots = sorted([p.name for p in archive.glob("skills-cold*") if p.is_dir()]) if archive.exists() else []

    optional_plugin_rows = []
    for alias in optional_plugins():
        plugin = resolve_plugin(alias)
        value = plugins.get(plugin, {})
        optional_plugin_rows.append(
            {
                "alias": alias,
                "plugin": plugin,
                "enabled": value.get("enabled", "default") if isinstance(value, dict) else "default",
                "explicit_enabled": _explicit_enabled(value),
            }
        )

    explicit_enabled_plugins = [
        name for name, value in sorted(plugins.items()) if isinstance(value, dict) and value.get("enabled") is True
    ]
    enabled_mcp = [name for name, value in sorted(mcp_servers.items()) if _enabled(value, default=True)]
    disabled_mcp = [name for name, value in sorted(mcp_servers.items()) if not _enabled(value, default=True)]

    capabilities_data = json_load(capabilities_path(), {"capabilities": []})
    workflows_data = json_load(workflows_path(), {"workflows": []})
    links_data = json_load(links_path(), {"links": []})
    interfaces_data = json_load(interfaces_path(), {"capabilities": {}})
    capabilities = capabilities_data.get("capabilities", []) if isinstance(capabilities_data, dict) else []
    workflows = workflows_data.get("workflows", []) if isinstance(workflows_data, dict) else []
    links = links_data.get("links", []) if isinstance(links_data, dict) else []
    interfaces = interfaces_data.get("capabilities", {}) if isinstance(interfaces_data, dict) else {}

    return {
        "codex_home": str(codex_home()),
        "cold_archive": str(cold_archive()),
        "paths": {
            "capabilities": str(capabilities_path()),
            "workflows": str(workflows_path()),
            "links": str(links_path()),
            "interfaces": str(interfaces_path()),
            "plugin_aliases": str(plugin_aliases_path()),
        },
        "skills": {
            "hot_dir_count": len(hot_skill_dirs),
            "hot_skill_md_count": hot_skill_md_count,
            "hot_dirs": hot_skill_dirs,
            "cold_archive_roots": cold_archive_roots,
        },
        "features": {
            "plugins": features.get("plugins", "default"),
            "workspace_dependencies": features.get("workspace_dependencies", "default"),
        },
        "plugins": {
            "configured_count": len(plugins),
            "explicit_enabled_count": len(explicit_enabled_plugins),
            "explicit_enabled": explicit_enabled_plugins,
            "optional": optional_plugin_rows,
            "optional_explicit_enabled_count": sum(1 for row in optional_plugin_rows if row["explicit_enabled"]),
        },
        "mcp": {
            "configured_count": len(mcp_servers),
            "enabled_count": len(enabled_mcp),
            "disabled_count": len(disabled_mcp),
            "enabled": enabled_mcp,
            "disabled": disabled_mcp,
        },
        "registry": {
            "capability_count": len(capabilities),
            "sensitive_count": sum(1 for item in capabilities if isinstance(item, dict) and item.get("sensitive")),
            "workflow_count": len(workflows),
            "link_count": len(links),
            "interface_count": len(interfaces) if isinstance(interfaces, dict) else 0,
        },
    }


def evaluate_health(data: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []

    hot_skill_md = int(data["skills"]["hot_skill_md_count"])
    hot_dirs = int(data["skills"]["hot_dir_count"])
    if hot_skill_md > 40:
        findings.append(
            {
                "severity": "warn",
                "code": "many_hot_skills",
                "message": f"{hot_skill_md} SKILL.md files are hot. This may slow skill discovery.",
                "fix": "Run codex-lean-hotpath.ps1 apply, then wake skills on demand.",
            }
        )
    elif hot_skill_md > 15:
        findings.append(
            {
                "severity": "info",
                "code": "moderate_hot_skills",
                "message": f"{hot_skill_md} SKILL.md files are hot. Keep this low for fastest startup.",
                "fix": "Consider moving broad skill packs to the cold archive.",
            }
        )
    if hot_dirs == 0:
        findings.append(
            {
                "severity": "info",
                "code": "no_hot_skills",
                "message": "No hot skill directories were found.",
                "fix": "This is fine for a very lean setup; install/warm skills when needed.",
            }
        )

    features = data["features"]
    optional_enabled = int(data["plugins"]["optional_explicit_enabled_count"])
    plugins_feature = features.get("plugins")
    if plugins_feature is True and optional_enabled == 0:
        findings.append(
            {
                "severity": "warn",
                "code": "plugin_feature_hot_without_plugin",
                "message": "[features].plugins is true, but no optional plugin is explicitly enabled.",
                "fix": "Run codex-plugin-toggle.ps1 --lean-startup to cool the plugin feature.",
            }
        )
    elif optional_enabled > 3:
        findings.append(
            {
                "severity": "warn",
                "code": "many_optional_plugins_hot",
                "message": f"{optional_enabled} optional plugins are explicitly enabled.",
                "fix": "Sleep one-off plugin capabilities after use, or run codex-plugin-toggle.ps1 --lean-startup.",
            }
        )
    elif optional_enabled > 0:
        findings.append(
            {
                "severity": "info",
                "code": "optional_plugins_hot",
                "message": f"{optional_enabled} optional plugin(s) are explicitly enabled.",
                "fix": "This is fine if you are using them now; sleep them after the task.",
            }
        )

    if features.get("workspace_dependencies") is True:
        findings.append(
            {
                "severity": "warn",
                "code": "workspace_dependencies_hot",
                "message": "[features].workspace_dependencies is true.",
                "fix": "Disable workspace dependencies unless the current task needs them.",
            }
        )

    enabled_mcp = int(data["mcp"]["enabled_count"])
    if enabled_mcp > 8:
        findings.append(
            {
                "severity": "warn",
                "code": "many_mcp_enabled",
                "message": f"{enabled_mcp} MCP servers are enabled.",
                "fix": "Keep only core MCP servers hot; wake heavy MCP servers on demand.",
            }
        )

    if int(data["registry"]["capability_count"]) == 0:
        findings.append(
            {
                "severity": "critical",
                "code": "empty_capability_registry",
                "message": "No capabilities were found in the active registry.",
                "fix": "Install example registries or set CODEX_CAPABILITIES_JSON.",
            }
        )

    if not findings:
        findings.append(
            {
                "severity": "ok",
                "code": "healthy",
                "message": "Capability Hub appears lean and ready.",
                "fix": "No action required.",
            }
        )
    return findings


def overall_status(findings: list[dict[str, str]]) -> str:
    worst = max(SEVERITY_ORDER.get(item["severity"], 0) for item in findings)
    if worst >= SEVERITY_ORDER["critical"]:
        return "critical"
    if worst >= SEVERITY_ORDER["warn"]:
        return "warn"
    if worst >= SEVERITY_ORDER["info"]:
        return "info"
    return "ok"


def render_markdown(data: dict[str, Any], findings: list[dict[str, str]]) -> str:
    lines = ["# Codex Capability Hub Health", ""]
    lines.append(f"- Overall: **{overall_status(findings)}**")
    lines.append(f"- Codex home: `{data['codex_home']}`")
    lines.append(f"- Cold archive: `{data['cold_archive']}`")
    lines.append("")
    lines.append("## Hot path")
    lines.append(f"- Hot skill dirs: {data['skills']['hot_dir_count']}")
    lines.append(f"- Hot `SKILL.md` files: {data['skills']['hot_skill_md_count']}")
    lines.append(f"- `[features].plugins`: `{data['features']['plugins']}`")
    lines.append(f"- `[features].workspace_dependencies`: `{data['features']['workspace_dependencies']}`")
    lines.append(f"- Optional plugins explicitly enabled: {data['plugins']['optional_explicit_enabled_count']}")
    lines.append(f"- MCP enabled/configured: {data['mcp']['enabled_count']}/{data['mcp']['configured_count']}")
    lines.append("")
    lines.append("## Registry")
    lines.append(f"- Capabilities: {data['registry']['capability_count']}")
    lines.append(f"- Sensitive capabilities: {data['registry']['sensitive_count']}")
    lines.append(f"- Workflows: {data['registry']['workflow_count']}")
    lines.append("")
    lines.append("## Findings")
    for item in findings:
        lines.append(f"- **{item['severity']}** `{item['code']}`: {item['message']}")
        lines.append(f"  - Fix: {item['fix']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Report Capability Hub health and startup hot-path risk.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when warnings or critical findings exist.")
    args = parser.parse_args()

    data = collect_health()
    findings = evaluate_health(data)
    status = overall_status(findings)
    if args.json:
        print(json.dumps({"status": status, "health": data, "findings": findings}, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(data, findings), end="")
    return 1 if args.strict and status in {"warn", "critical"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
