from __future__ import annotations

import argparse
import json
from typing import Any

from codex_capability_health import collect_health, evaluate_health, overall_status, render_markdown as render_health


def _ps(script: str, args: str = "") -> str:
    suffix = f" {args}" if args else ""
    return f'& "$env:USERPROFILE\\.codex\\repair-tools\\{script}"{suffix}'


def _recommendation(rec_id: str, priority: str, title: str, reason: str, commands: list[str]) -> dict[str, Any]:
    return {
        "id": rec_id,
        "priority": priority,
        "title": title,
        "reason": reason,
        "commands": commands,
    }


def recommendations_for(data: dict[str, Any], findings: list[dict[str, str]]) -> list[dict[str, Any]]:
    recs: list[dict[str, Any]] = []
    codes = {item["code"] for item in findings}

    if "empty_capability_registry" in codes:
        recs.append(
            _recommendation(
                "install-or-point-registry",
                "critical",
                "Install or point Capability Hub registries",
                "The router cannot wake capabilities if the active registry is empty.",
                [
                    "powershell -ExecutionPolicy Bypass -File .\\powershell\\install.ps1 -ForceExamples",
                    "$env:CODEX_CAPABILITIES_JSON = \"C:\\path\\to\\capabilities.json\"",
                    _ps("codex-wake.ps1", "list"),
                    _ps("codex-capability-health.ps1"),
                ],
            )
        )

    if {"many_hot_skills", "moderate_hot_skills"} & codes:
        recs.append(
            _recommendation(
                "cool-broad-skills",
                "high" if "many_hot_skills" in codes else "medium",
                "Move broad skills out of the startup hot path",
                "Hot skill scanning is one of the easiest ways to slow Codex UI loading on Windows.",
                [
                    _ps("codex-lean-hotpath.ps1", "apply"),
                    _ps("codex-capability-health.ps1"),
                ],
            )
        )

    if "plugin_feature_hot_without_plugin" in codes or "many_optional_plugins_hot" in codes:
        recs.append(
            _recommendation(
                "cool-plugin-feature",
                "high",
                "Return plugins to lean startup mode",
                "Plugin discovery can dominate Windows UI loading when the plugin feature is hot unnecessarily.",
                [
                    _ps("codex-plugin-toggle.ps1", "--lean-startup"),
                    _ps("codex-plugin-toggle.ps1", "--repair-cache"),
                    _ps("codex-capability-health.ps1"),
                ],
            )
        )
    elif "optional_plugins_hot" in codes:
        recs.append(
            _recommendation(
                "sleep-one-off-plugins",
                "medium",
                "Sleep one-off plugin-backed capabilities after use",
                "One or more optional plugins are explicitly enabled. That is fine during a task, but should not become the default.",
                [
                    _ps("codex-wake.ps1", "sleep <capability-id>"),
                    _ps("codex-plugin-toggle.ps1", "--lean-startup"),
                ],
            )
        )

    if "unsupported_workspace_dependencies_key" in codes:
        recs.append(
            _recommendation(
                "remove-unsupported-workspace-dependencies",
                "high",
                "Remove unsupported workspace_dependencies feature key",
                "Some Codex desktop builds wait for a UI-loading timeout when an unsupported [features].workspace_dependencies key is present, even if it is set to false.",
                [
                    "Edit ~/.codex/config.toml and delete the workspace_dependencies line from [features].",
                    _ps("codex-capability-health.ps1"),
                ],
            )
        )

    if "many_mcp_enabled" in codes:
        recs.append(
            _recommendation(
                "reduce-hot-mcp",
                "medium",
                "Keep only core MCP servers enabled",
                "Enabled MCP servers can add startup or first-use overhead even when the current task does not need them.",
                [
                    _ps("codex-capability-inventory.ps1", "--json"),
                    _ps("codex-mcp-toggle.ps1", "off <mcp-name>"),
                    _ps("codex-capability-health.ps1"),
                ],
            )
        )

    if not recs:
        recs.append(
            _recommendation(
                "keep-measuring",
                "low",
                "Keep the current lean design and measure periodically",
                "No high-risk hot-path issue was detected by the health check.",
                [
                    _ps("codex-capability-health.ps1"),
                    _ps("codex-capability-benchmark.ps1"),
                    _ps("codex-auto-wake.ps1", "-Text \"make a PPT and export PDF\" -DryRun"),
                ],
            )
        )

    recs.append(
        _recommendation(
            "validate-router",
            "low",
            "Validate the router after registry changes",
            "This catches broken capability IDs, workflow phases, or aliases before they affect real work.",
            [
                _ps("codex-wake.ps1", "list"),
                _ps("codex-wake.ps1", "validate <capability-id>"),
                _ps("codex-auto-wake.ps1", "-Text \"your task text\" -DryRun -PreferWorkflow"),
            ],
        )
    )
    return recs


def collect_doctor() -> dict[str, Any]:
    data = collect_health()
    findings = evaluate_health(data)
    status = overall_status(findings)
    return {
        "status": status,
        "health": data,
        "findings": findings,
        "recommendations": recommendations_for(data, findings),
    }


def render_markdown(report: dict[str, Any], include_health: bool = False) -> str:
    lines = ["# Codex Capability Hub Doctor", ""]
    lines.append(f"- Overall health: **{report['status']}**")
    lines.append(f"- Findings: {len(report['findings'])}")
    lines.append(f"- Recommendations: {len(report['recommendations'])}")
    lines.append("")
    lines.append("## Recommended actions")
    for rec in report["recommendations"]:
        lines.append(f"### {rec['title']}")
        lines.append(f"- Priority: **{rec['priority']}**")
        lines.append(f"- Why: {rec['reason']}")
        lines.append("- Commands:")
        for command in rec["commands"]:
            lines.append(f"  ```powershell\n  {command}\n  ```")
        lines.append("")
    lines.append("## Findings")
    for item in report["findings"]:
        lines.append(f"- **{item['severity']}** `{item['code']}`: {item['message']}")
        lines.append(f"  - Fix: {item['fix']}")
    if include_health:
        lines.append("")
        lines.append("## Raw health report")
        lines.append(render_health(report["health"], report["findings"]).strip())
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Recommend safe fixes for Capability Hub hot-path health issues.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    parser.add_argument("--include-health", action="store_true", help="Append the full health report to Markdown output.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when warnings or critical findings exist.")
    args = parser.parse_args()

    report = collect_doctor()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(report, include_health=args.include_health), end="")
    return 1 if args.strict and report["status"] in {"warn", "critical"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
