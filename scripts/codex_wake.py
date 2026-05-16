from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from common import (
    capabilities_path,
    codex_home,
    config_path,
    cold_archive,
    interfaces_path,
    json_load,
    json_write,
    links_path,
    load_config,
    powershell_wrapper,
    repair_tools_dir,
    resolve_plugin,
    run,
    run_powershell_script,
    workflows_path,
    workflow_state_path,
)

LINKED_RELATIONS = {"requires", "validates_with", "pairs_with"}


def registry() -> dict[str, Any]:
    return json_load(capabilities_path(), {"capabilities": []})


def caps() -> dict[str, dict[str, Any]]:
    return {str(c["id"]): c for c in registry().get("capabilities", []) if isinstance(c, dict) and "id" in c}


def links_data() -> dict[str, Any]:
    return json_load(links_path(), {"links": []})


def workflows_data() -> dict[str, Any]:
    return json_load(workflows_path(), {"workflows": []})


def workflow_map() -> dict[str, dict[str, Any]]:
    return {str(w["id"]): w for w in workflows_data().get("workflows", []) if isinstance(w, dict) and "id" in w}


def interfaces_data() -> dict[str, Any]:
    return json_load(interfaces_path(), {"artifact_types": {}, "capabilities": {}})


def action_for(cap: dict[str, Any], mode: str = "wake") -> list[dict[str, Any]]:
    if mode not in {"wake", "sleep"}:
        raise ValueError(f"unknown mode {mode}")
    if cap.get("type") == "bundle":
        return list(cap.get(mode, cap.get("wake", [])) or [])
    if cap.get(mode):
        return list(cap.get(mode) or [])
    typ = cap.get("type")
    if typ in {"skill", "mcp", "plugin", "script", "instruction"}:
        return [{"type": typ, "name": cap.get("name", cap.get("id"))}]
    return []


def dedupe_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for action in actions:
        key = (str(action.get("type", "")), str(action.get("name", "")))
        if key in seen:
            continue
        seen.add(key)
        out.append(action)
    return out


def cap_sequence_for(cap_ids: list[str], mode: str = "wake") -> list[dict[str, Any]]:
    capmap = caps()
    ids = list(cap_ids)
    if mode == "sleep":
        ids = list(reversed(ids))
    actions: list[dict[str, Any]] = []
    for cap_id in ids:
        cap = capmap.get(cap_id)
        if not cap:
            print("warning: unknown capability in sequence:", cap_id, file=sys.stderr)
            continue
        actions.extend(action_for(cap, mode))
    return dedupe_actions(actions)


def linked_cap_ids(cap_id: str) -> list[str]:
    ids = [cap_id]
    for link in links_data().get("links", []):
        if link.get("from") == cap_id and link.get("relation") in LINKED_RELATIONS:
            ids.append(str(link.get("to")))
    out: list[str] = []
    for item in ids:
        if item and item not in out:
            out.append(item)
    return out


def apply_one(item: dict[str, Any], mode: str, dry: bool = False) -> int:
    typ = str(item.get("type", ""))
    name = str(item.get("name", ""))
    if typ == "skill":
        return run_powershell_script(
            powershell_wrapper("codex-skills-hotcold.ps1"),
            ["warm" if mode == "wake" else "cool", name],
            dry=dry,
        )
    if typ == "mcp":
        return run_powershell_script(
            powershell_wrapper("codex-mcp-toggle.ps1"),
            ["on" if mode == "wake" else "off", name],
            dry=dry,
        )
    if typ == "plugin":
        return run_powershell_script(
            powershell_wrapper("codex-plugin-toggle.ps1"),
            [name, "on" if mode == "wake" else "off"],
            dry=dry,
        )
    if typ == "script":
        cmd = [name] + [str(x) for x in item.get("args", [])]
        return run(cmd, dry=dry)
    if typ == "instruction":
        print(("DRY-RUN " if dry else "") + "INSTRUCTION", name)
        if item.get("description"):
            print(item["description"])
        return 0
    print("unknown item type", typ, file=sys.stderr)
    return 2


def apply_actions(actions: list[dict[str, Any]], mode: str, dry: bool = False) -> int:
    rc = 0
    for item in dedupe_actions(actions):
        rc = rc or apply_one(item, mode, dry=dry)
    if not dry:
        print("\nNote: Codex may need restart/reload for newly warmed skills/plugins/MCPs to appear in UI lists.")
    return rc


def list_caps(verbose: bool = False) -> None:
    for cap in registry().get("capabilities", []):
        print(f"{cap.get('id',''):22s} {cap.get('type',''):10s} {cap.get('description','')}")
        if verbose:
            if cap.get("triggers"):
                print("  triggers:", " / ".join(cap.get("triggers", [])[:10]))
            if cap.get("aliases"):
                print("  aliases:", " / ".join(cap.get("aliases", [])[:10]))
            outs = [link for link in links_data().get("links", []) if link.get("from") == cap.get("id")]
            if outs:
                print("  links:", "; ".join(f"{l.get('relation')}->{l.get('to')}" for l in outs[:8]))


def get_cap(cap_id: str | None) -> dict[str, Any] | None:
    if not cap_id:
        print("target required")
        return None
    cap = caps().get(cap_id)
    if not cap:
        print("Unknown capability:", cap_id)
        print("Available:")
        list_caps()
        return None
    return cap


def explain(cap_id: str | None) -> int:
    cap = get_cap(cap_id)
    if not cap:
        return 2
    print(f"# {cap['id']}")
    print("type:", cap.get("type"))
    print("description:", cap.get("description", ""))
    print("tags:", ", ".join(cap.get("tags", [])))
    print("startup_cost_if_hot:", cap.get("startup_cost_if_hot", ""))
    print("risk_level:", cap.get("risk_level", ""))
    print("sensitive:", cap.get("sensitive", False))
    if cap.get("triggers"):
        print("triggers:", " / ".join(cap.get("triggers", [])))
    if cap.get("aliases"):
        print("aliases:", " / ".join(cap.get("aliases", [])))
    print("\nwake actions:")
    for action in action_for(cap, "wake"):
        print(f"- {action.get('type')}: {action.get('name')}")
    if cap.get("validation"):
        print("\nvalidation:")
        for item in cap.get("validation", []):
            print("-", item)
    graph(cap["id"], compact=True)
    return 0


def graph(cap_id: str | None = None, compact: bool = False) -> int:
    links = links_data().get("links", [])
    if not cap_id:
        print("Capability graph edges:")
        for link in links:
            print(f"- {link.get('from')} --{link.get('relation')}--> {link.get('to')}: {link.get('reason','')}")
        return 0
    outgoing = [link for link in links if link.get("from") == cap_id]
    incoming = [link for link in links if link.get("to") == cap_id]
    if not compact:
        print(f"# graph: {cap_id}")
    if outgoing:
        print("\noutgoing links:")
        for link in outgoing:
            print(f"- --{link.get('relation')}--> {link.get('to')}: {link.get('reason','')}")
    if incoming:
        print("\nincoming links:")
        for link in incoming:
            print(f"- {link.get('from')} --{link.get('relation')}--> this: {link.get('reason','')}")
    if not outgoing and not incoming:
        print("no links")
    return 0


def interface_show(cap_id: str | None = None) -> int:
    data = interfaces_data()
    if not cap_id:
        print("Artifact types:")
        for key, value in data.get("artifact_types", {}).items():
            print(f"- {key}: {value}")
        print("\nCapability interfaces:")
        for cid, iface in sorted((data.get("capabilities", {}) or {}).items()):
            print(f"- {cid}: inputs={','.join(iface.get('inputs', []))} outputs={','.join(iface.get('outputs', []))} handoffs={','.join(iface.get('handoffs', []))}")
        return 0
    iface = (data.get("capabilities", {}) or {}).get(cap_id)
    if not iface:
        print("No interface contract for", cap_id)
        return 1
    print(f"# interface: {cap_id}")
    print("inputs:")
    for item in iface.get("inputs", []):
        print("-", item, ":", data.get("artifact_types", {}).get(item, ""))
    print("outputs:")
    for item in iface.get("outputs", []):
        print("-", item, ":", data.get("artifact_types", {}).get(item, ""))
    print("handoffs:", ", ".join(iface.get("handoffs", [])))
    return 0


def skill_state(name: str) -> str:
    hot = codex_home() / "skills" / name
    if hot.exists():
        return "hot"
    archive = cold_archive()
    if archive.exists():
        for root in archive.glob("skills-cold*"):
            direct = root / name
            if direct.exists():
                return "cold"
            for skill_md in root.rglob("SKILL.md"):
                if skill_md.parent.name == name:
                    return f"cold-nested:{skill_md.parent.relative_to(root)}"
    return "missing"


def validate_item(item: dict[str, Any]) -> str:
    typ = str(item.get("type"))
    name = str(item.get("name"))
    if typ == "skill":
        return f"skill {name}: {skill_state(name)}"
    if typ == "mcp":
        server = (load_config().get("mcp_servers") or {}).get(name)
        if not server:
            return f"mcp {name}: missing"
        return f"mcp {name}: configured, enabled={server.get('enabled', True)}"
    if typ == "plugin":
        key = resolve_plugin(name)
        plugin = (load_config().get("plugins") or {}).get(key)
        enabled = None if plugin is None else plugin.get("enabled") if isinstance(plugin, dict) else plugin
        return f"plugin {name} ({key}): configured_enabled={enabled}"
    return f"{typ} {name}: unchecked"


def validate(cap_id: str | None, linked: bool = False) -> int:
    cap = get_cap(cap_id)
    if not cap:
        return 2
    ids = linked_cap_ids(cap["id"]) if linked else [cap["id"]]
    print(f"Validation for {cap['id']}" + (" + linked:" if linked else ":"))
    for action in cap_sequence_for(ids, "wake"):
        print("-", validate_item(action))
    return 0


def apply_cap(cap_id: str | None, mode: str, dry: bool = False, linked: bool = False) -> int:
    cap = get_cap(cap_id)
    if not cap:
        return 2
    ids = linked_cap_ids(cap["id"]) if linked else [cap["id"]]
    if linked:
        print("linked capability sequence:", " -> ".join(ids))
    return apply_actions(cap_sequence_for(ids, mode), mode, dry=dry)


def workflow_list() -> None:
    for workflow in workflows_data().get("workflows", []):
        seq = " -> ".join(str(phase.get("capability")) for phase in workflow.get("phases", []))
        print(f"{workflow.get('id',''):24s} {workflow.get('description','')} [{seq}]")


def workflow_explain(wid: str | None) -> int:
    workflow = workflow_map().get(str(wid)) if wid else None
    if not workflow:
        print("Unknown workflow:", wid)
        workflow_list()
        return 2
    print(f"# workflow: {wid}")
    print(workflow.get("description", ""))
    if workflow.get("triggers"):
        print("triggers:", " / ".join(workflow.get("triggers", [])))
    print("phases:")
    for index, phase in enumerate(workflow.get("phases", []), 1):
        print(f"{index}. {phase.get('capability')} - {phase.get('role','')}")
    return 0


def workflow_apply(wid: str | None, mode: str, dry: bool = False) -> int:
    workflow = workflow_map().get(str(wid)) if wid else None
    if not workflow:
        print("Unknown workflow:", wid)
        workflow_list()
        return 2
    ids = [str(phase.get("capability")) for phase in workflow.get("phases", [])]
    shown = ids if mode == "wake" else list(reversed(ids))
    print("workflow sequence:", " -> ".join(shown))
    return apply_actions(cap_sequence_for(ids, mode), mode, dry=dry)


def workflow_start(wid: str | None, dry: bool = False) -> int:
    workflow = workflow_map().get(str(wid)) if wid else None
    if not workflow:
        print("Unknown workflow:", wid)
        workflow_list()
        return 2
    phases = workflow.get("phases", [])
    if not phases:
        print("workflow has no phases")
        return 2
    if not dry:
        json_write(workflow_state_path(), {"workflow": wid, "phase_index": 0, "status": "active"})
    first = phases[0]
    print(f"start workflow {wid}; waking phase 1/{len(phases)}: {first.get('capability')} - {first.get('role','')}")
    return apply_cap(str(first.get("capability")), "wake", dry=dry)


def workflow_clear() -> int:
    state = workflow_state_path()
    if state.exists():
        state.unlink()
        print("cleared active workflow state")
    else:
        print("no active workflow state")
    return 0


def workflow_state_show() -> int:
    state = workflow_state_path()
    if not state.exists():
        print("no active workflow state")
        return 0
    data = json_load(state, {})
    workflow = workflow_map().get(data.get("workflow"))
    print("active workflow:", data)
    if workflow:
        for index, phase in enumerate(workflow.get("phases", [])):
            mark = ">>" if index == data.get("phase_index") else "  "
            print(f"{mark} {index+1}. {phase.get('capability')} - {phase.get('role','')}")
    return 0


def workflow_next(dry: bool = False) -> int:
    state = workflow_state_path()
    if not state.exists():
        print("no active workflow state; use workflow-start <id>")
        return 2
    data = json_load(state, {})
    workflow = workflow_map().get(data.get("workflow"))
    if not workflow:
        print("active workflow missing from registry")
        return 2
    phases = workflow.get("phases", [])
    idx = int(data.get("phase_index", 0)) + 1
    if idx >= len(phases):
        data["status"] = "complete"
        if not dry:
            json_write(state, data)
        print("workflow already complete:", data.get("workflow"))
        return 0
    data["phase_index"] = idx
    if not dry:
        json_write(state, data)
    phase = phases[idx]
    print(f"waking next phase {idx+1}/{len(phases)}: {phase.get('capability')} - {phase.get('role','')}")
    return apply_cap(str(phase.get("capability")), "wake", dry=dry)


def status() -> int:
    print("Registry:", capabilities_path())
    print("Config:", config_path())
    print("Repair tools:", repair_tools_dir())
    print("\nCapabilities:")
    list_caps()
    print("\nMCP status:")
    run_powershell_script(powershell_wrapper("codex-mcp-toggle.ps1"), ["list"])
    print("\nPlugin status:")
    run_powershell_script(powershell_wrapper("codex-plugin-toggle.ps1"), ["list"])
    return 0


def main() -> int:
    commands = [
        "list", "list-verbose", "wake", "sleep", "status", "explain", "validate", "validate-linked",
        "dry-run", "graph", "interface", "wake-linked", "dry-run-linked",
        "workflow-list", "workflow-explain", "workflow-dry-run", "workflow-wake", "workflow-sleep",
        "workflow-start", "workflow-start-dry-run", "workflow-next", "workflow-next-dry-run", "workflow-state", "workflow-clear",
    ]
    parser = argparse.ArgumentParser(description="Wake/sleep Codex capability bundles, linked graphs, and workflows.")
    parser.add_argument("cmd", choices=commands)
    parser.add_argument("target", nargs="?")
    args = parser.parse_args()

    if args.cmd == "list": list_caps(); return 0
    if args.cmd == "list-verbose": list_caps(verbose=True); return 0
    if args.cmd == "status": return status()
    if args.cmd == "explain": return explain(args.target)
    if args.cmd == "validate": return validate(args.target)
    if args.cmd == "validate-linked": return validate(args.target, linked=True)
    if args.cmd == "graph": return graph(args.target)
    if args.cmd == "interface": return interface_show(args.target)
    if args.cmd == "dry-run": return apply_cap(args.target, "wake", dry=True)
    if args.cmd == "wake": return apply_cap(args.target, "wake")
    if args.cmd == "sleep": return apply_cap(args.target, "sleep")
    if args.cmd == "dry-run-linked": return apply_cap(args.target, "wake", dry=True, linked=True)
    if args.cmd == "wake-linked": return apply_cap(args.target, "wake", linked=True)
    if args.cmd == "workflow-list": workflow_list(); return 0
    if args.cmd == "workflow-explain": return workflow_explain(args.target)
    if args.cmd == "workflow-dry-run": return workflow_apply(args.target, "wake", dry=True)
    if args.cmd == "workflow-wake": return workflow_apply(args.target, "wake")
    if args.cmd == "workflow-sleep": return workflow_apply(args.target, "sleep")
    if args.cmd == "workflow-start": return workflow_start(args.target)
    if args.cmd == "workflow-start-dry-run": return workflow_start(args.target, dry=True)
    if args.cmd == "workflow-next": return workflow_next()
    if args.cmd == "workflow-next-dry-run": return workflow_next(dry=True)
    if args.cmd == "workflow-state": return workflow_state_show()
    if args.cmd == "workflow-clear": return workflow_clear()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
