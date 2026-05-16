from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
EXAMPLES = ROOT / "examples"
HEALTH = SCRIPTS / "codex_capability_health.py"
BENCHMARK = SCRIPTS / "codex_capability_benchmark.py"
DOCTOR = SCRIPTS / "codex_capability_doctor.py"
PLUGIN_TOGGLE = SCRIPTS / "codex_plugin_toggle.py"


def base_env(tmp_path: Path, *, examples: bool = True) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "PYTHONIOENCODING": "utf-8",
            "CODEX_HOME": str(tmp_path / "codex-home"),
            "CODEX_COLD_ARCHIVE": str(tmp_path / "cold-archive"),
            "CODEX_CONFIG": str(tmp_path / "codex-home" / "config.toml"),
        }
    )
    if examples:
        env.update(
            {
                "CODEX_CAPABILITIES_JSON": str(EXAMPLES / "capabilities.example.json"),
                "CODEX_CAPABILITY_WORKFLOWS_JSON": str(EXAMPLES / "capability_workflows.example.json"),
                "CODEX_CAPABILITY_LINKS_JSON": str(EXAMPLES / "capability_links.example.json"),
                "CODEX_CAPABILITY_INTERFACES_JSON": str(EXAMPLES / "capability_interfaces.example.json"),
                "CODEX_PLUGIN_ALIASES_JSON": str(EXAMPLES / "plugin_aliases.example.json"),
            }
        )
    else:
        env.update(
            {
                "CODEX_CAPABILITIES_JSON": str(tmp_path / "missing-capabilities.json"),
                "CODEX_CAPABILITY_WORKFLOWS_JSON": str(tmp_path / "missing-workflows.json"),
                "CODEX_CAPABILITY_LINKS_JSON": str(tmp_path / "missing-links.json"),
                "CODEX_CAPABILITY_INTERFACES_JSON": str(tmp_path / "missing-interfaces.json"),
                "CODEX_PLUGIN_ALIASES_JSON": str(tmp_path / "missing-plugin-aliases.json"),
            }
        )
    return env


def run_script(script: Path, args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        capture_output=True,
        env=env,
        check=False,
    )


def test_health_json_reports_registry_and_status(tmp_path: Path) -> None:
    env = base_env(tmp_path, examples=True)
    skills = Path(env["CODEX_HOME"]) / "skills" / "example-skill"
    skills.mkdir(parents=True)
    (skills / "SKILL.md").write_text("# Example\n", encoding="utf-8")

    result = run_script(HEALTH, ["--json"], env)

    assert result.returncode == 0, result.stderr + result.stdout
    data = json.loads(result.stdout)
    assert data["status"] in {"ok", "info", "warn", "critical"}
    assert data["health"]["registry"]["capability_count"] > 0
    assert data["health"]["skills"]["hot_skill_md_count"] == 1
    assert isinstance(data["findings"], list)


def test_health_empty_registry_is_critical(tmp_path: Path) -> None:
    env = base_env(tmp_path, examples=False)

    result = run_script(HEALTH, ["--json"], env)

    assert result.returncode == 0, result.stderr + result.stdout
    data = json.loads(result.stdout)
    assert data["status"] == "critical"
    assert any(item["code"] == "empty_capability_registry" for item in data["findings"])


def test_benchmark_json_has_expected_measurements(tmp_path: Path) -> None:
    env = base_env(tmp_path, examples=True)

    result = run_script(BENCHMARK, ["--json", "--iterations", "1"], env)

    assert result.returncode == 0, result.stderr + result.stdout
    data = json.loads(result.stdout)
    names = {item["name"] for item in data["measurements"]}
    assert {"config_parse", "registry_load", "hot_skill_scan", "router_match"}.issubset(names)
    assert data["summary"]["capability_count"] > 0
    assert isinstance(data["summary"]["total_avg_ms"], (int, float))


def test_doctor_recommends_commands_for_empty_registry(tmp_path: Path) -> None:
    env = base_env(tmp_path, examples=False)

    result = run_script(DOCTOR, [], env)

    assert result.returncode == 0, result.stderr + result.stdout
    assert "Install or point Capability Hub registries" in result.stdout
    assert "codex-capability-health.ps1" in result.stdout
    assert "codex-wake.ps1" in result.stdout


def test_doctor_json_includes_recommendations(tmp_path: Path) -> None:
    env = base_env(tmp_path, examples=True)

    result = run_script(DOCTOR, ["--json"], env)

    assert result.returncode == 0, result.stderr + result.stdout
    data = json.loads(result.stdout)
    assert data["recommendations"]
    assert all("commands" in item for item in data["recommendations"])


def test_health_warns_when_unsupported_workspace_dependencies_key_exists(tmp_path: Path) -> None:
    env = base_env(tmp_path, examples=True)
    config = Path(env["CODEX_CONFIG"])
    config.parent.mkdir(parents=True)
    config.write_text("[features]\nplugins = false\nworkspace_dependencies = false\n", encoding="utf-8")

    result = run_script(HEALTH, ["--json"], env)

    assert result.returncode == 0, result.stderr + result.stdout
    data = json.loads(result.stdout)
    assert data["status"] == "warn"
    assert any(item["code"] == "unsupported_workspace_dependencies_key" for item in data["findings"])


def test_plugin_lean_startup_removes_unsupported_workspace_dependencies_key(tmp_path: Path) -> None:
    env = base_env(tmp_path, examples=True)
    config = Path(env["CODEX_CONFIG"])
    config.parent.mkdir(parents=True)
    config.write_text(
        "[features]\nplugins = true\nworkspace_dependencies = false\n\n[plugins.\"browser-use@openai-bundled\"]\nenabled = true\n",
        encoding="utf-8",
    )

    result = run_script(PLUGIN_TOGGLE, ["--lean-startup"], env)

    assert result.returncode == 0, result.stderr + result.stdout
    text = config.read_text(encoding="utf-8")
    assert "plugins = false" in text
    assert "workspace_dependencies" not in text
