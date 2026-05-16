from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def load(name: str):
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def test_capability_registry_shape() -> None:
    data = load("capabilities.example.json")
    assert isinstance(data.get("capabilities"), list)
    ids = set()
    for cap in data["capabilities"]:
        assert cap["id"] not in ids
        ids.add(cap["id"])
        assert cap["type"] in {"bundle", "skill", "mcp", "plugin", "script", "instruction"}
        assert cap.get("description")
        for action in cap.get("wake", []) + cap.get("sleep", []):
            assert action["type"] in {"skill", "mcp", "plugin", "script", "instruction"}
            assert action.get("name")


def test_workflow_phases_reference_existing_capabilities() -> None:
    caps = {cap["id"] for cap in load("capabilities.example.json")["capabilities"]}
    workflows = load("capability_workflows.example.json")["workflows"]
    for workflow in workflows:
        assert workflow.get("id")
        assert workflow.get("phases")
        for phase in workflow["phases"]:
            assert phase["capability"] in caps


def test_interfaces_reference_existing_capabilities() -> None:
    caps = {cap["id"] for cap in load("capabilities.example.json")["capabilities"]}
    interfaces = load("capability_interfaces.example.json").get("capabilities", {})
    for cap_id in interfaces:
        assert cap_id in caps
