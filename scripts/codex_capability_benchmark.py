from __future__ import annotations

import argparse
import json
import statistics
import time
from typing import Any, Callable

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

MeasureFn = Callable[[], dict[str, Any]]


def _entry_count(value: Any, key: str) -> int:
    if isinstance(value, dict):
        item = value.get(key, [])
        if isinstance(item, (list, dict)):
            return len(item)
    return 0


def _time_measure(name: str, fn: MeasureFn, iterations: int) -> dict[str, Any]:
    durations: list[float] = []
    last_observation: dict[str, Any] = {}
    for _ in range(max(1, iterations)):
        start = time.perf_counter()
        last_observation = fn()
        durations.append((time.perf_counter() - start) * 1000)
    return {
        "name": name,
        "iterations": max(1, iterations),
        "best_ms": round(min(durations), 3),
        "avg_ms": round(statistics.fmean(durations), 3),
        "last_ms": round(durations[-1], 3),
        "observations": last_observation,
    }


def measure_config_parse() -> dict[str, Any]:
    config = load_config()
    return {
        "top_level_keys": len(config),
        "mcp_servers": len(config.get("mcp_servers", {}) or {}),
        "plugins": len(config.get("plugins", {}) or {}),
        "features": len(config.get("features", {}) or {}),
    }


def measure_registry_load() -> dict[str, Any]:
    capabilities = json_load(capabilities_path(), {"capabilities": []})
    workflows = json_load(workflows_path(), {"workflows": []})
    links = json_load(links_path(), {"links": []})
    interfaces = json_load(interfaces_path(), {"capabilities": {}})
    aliases = json_load(plugin_aliases_path(), {})
    return {
        "capabilities": _entry_count(capabilities, "capabilities"),
        "workflows": _entry_count(workflows, "workflows"),
        "links": _entry_count(links, "links"),
        "interfaces": _entry_count(interfaces, "capabilities"),
        "plugin_aliases": len(aliases) if isinstance(aliases, (list, dict)) else 0,
    }


def measure_hot_skill_scan() -> dict[str, Any]:
    root = codex_home() / "skills"
    if not root.exists():
        return {"exists": False, "hot_dir_count": 0, "skill_md_count": 0}
    hot_dirs = [p for p in root.iterdir() if p.is_dir()]
    skill_md = list(root.rglob("SKILL.md"))
    return {
        "exists": True,
        "hot_dir_count": len(hot_dirs),
        "skill_md_count": len(skill_md),
    }


def measure_cold_archive_probe() -> dict[str, Any]:
    root = cold_archive()
    if not root.exists():
        return {"exists": False, "skill_archive_roots": 0}
    # Keep this intentionally shallow: the cold archive should not be on the startup hot path.
    archive_roots = [p for p in root.glob("skills-cold*") if p.is_dir()]
    return {"exists": True, "skill_archive_roots": len(archive_roots)}


def measure_optional_plugin_resolution() -> dict[str, Any]:
    aliases = optional_plugins()
    resolved = [resolve_plugin(alias) for alias in aliases]
    return {
        "optional_aliases": len(aliases),
        "unique_plugins": len(set(resolved)),
    }


def measure_router_match(sample_text: str) -> dict[str, Any]:
    # Import lazily so a benchmark of the hot path does not require router code until requested.
    from codex_auto_wake import cap_matches, workflow_matches

    caps = cap_matches(sample_text, limit=5)
    workflows = workflow_matches(sample_text, limit=3)
    return {
        "sample_text": sample_text,
        "capability_matches": len(caps),
        "workflow_matches": len(workflows),
        "top_capability": caps[0]["id"] if caps else None,
        "top_workflow": workflows[0]["id"] if workflows else None,
    }


def collect_benchmark(iterations: int = 3, sample_text: str = "debug failing CI test") -> dict[str, Any]:
    checks: list[tuple[str, MeasureFn]] = [
        ("config_parse", measure_config_parse),
        ("registry_load", measure_registry_load),
        ("hot_skill_scan", measure_hot_skill_scan),
        ("cold_archive_probe", measure_cold_archive_probe),
        ("optional_plugin_resolution", measure_optional_plugin_resolution),
        ("router_match", lambda: measure_router_match(sample_text)),
    ]
    measurements = [_time_measure(name, fn, iterations) for name, fn in checks]
    total_avg = round(sum(float(item["avg_ms"]) for item in measurements), 3)
    return {
        "codex_home": str(codex_home()),
        "cold_archive": str(cold_archive()),
        "iterations": max(1, iterations),
        "measurements": measurements,
        "summary": {
            "total_avg_ms": total_avg,
            "hot_skill_md_count": next(
                (
                    item["observations"].get("skill_md_count")
                    for item in measurements
                    if item["name"] == "hot_skill_scan"
                ),
                0,
            ),
            "capability_count": next(
                (
                    item["observations"].get("capabilities")
                    for item in measurements
                    if item["name"] == "registry_load"
                ),
                0,
            ),
        },
    }


def render_markdown(data: dict[str, Any]) -> str:
    def cell(value: Any) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")

    lines = ["# Codex Capability Hub Benchmark", ""]
    lines.append(f"- Codex home: `{data['codex_home']}`")
    lines.append(f"- Cold archive: `{data['cold_archive']}`")
    lines.append(f"- Iterations per check: {data['iterations']}")
    lines.append(f"- Sum of average check times: **{data['summary']['total_avg_ms']} ms**")
    lines.append("")
    lines.append("| Check | Best ms | Avg ms | Last ms | Observation |")
    lines.append("| --- | ---: | ---: | ---: | --- |")
    for item in data["measurements"]:
        observation = ", ".join(f"{k}={cell(v)}" for k, v in item["observations"].items())
        lines.append(
            f"| `{item['name']}` | {item['best_ms']} | {item['avg_ms']} | {item['last_ms']} | {observation} |"
        )
    lines.append("")
    lines.append("Notes:")
    lines.append("- This is a framework-level proxy benchmark, not a direct Codex app startup timer.")
    lines.append("- The most useful trend is whether hot skill scanning, plugin state, and registry loading stay small over time.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark Capability Hub hot-path indicators.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    parser.add_argument("--iterations", "-n", type=int, default=3, help="Iterations per check. Default: 3.")
    parser.add_argument("--text", default="debug failing CI test", help="Sample text for router matching benchmark.")
    args = parser.parse_args()

    data = collect_benchmark(iterations=max(1, args.iterations), sample_text=args.text)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(data), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
