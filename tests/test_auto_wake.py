from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "codex_auto_wake.py"
EXAMPLES = ROOT / "examples"


def run_auto(text: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update({
        "PYTHONIOENCODING": "utf-8",
        "CODEX_CAPABILITIES_JSON": str(EXAMPLES / "capabilities.example.json"),
        "CODEX_CAPABILITY_WORKFLOWS_JSON": str(EXAMPLES / "capability_workflows.example.json"),
        "CODEX_CAPABILITY_LINKS_JSON": str(EXAMPLES / "capability_links.example.json"),
        "CODEX_CAPABILITY_INTERFACES_JSON": str(EXAMPLES / "capability_interfaces.example.json"),
    })
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--text", text, *args],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def test_debug_routes_to_skill_bundle() -> None:
    result = run_auto("please debug this failing CI test", "--dry-run")
    assert result.returncode == 0, result.stderr + result.stdout
    assert "debug" in result.stdout
    assert "codex-skills-hotcold.ps1" in result.stdout
    assert "systematic-debugging" in result.stdout


def test_office_routes_to_document_plugins() -> None:
    result = run_auto("make a PPT and export PDF", "--dry-run")
    assert result.returncode == 0, result.stderr + result.stdout
    assert "office" in result.stdout
    assert "presentations" in result.stdout
    assert "documents" in result.stdout


def test_explicit_sensitive_chrome_login_can_dry_run() -> None:
    result = run_auto("use my Chrome login state for this authenticated page", "--dry-run")
    assert result.returncode == 0, result.stderr + result.stdout
    assert "chrome-login" in result.stdout
    assert "chrome" in result.stdout
    assert "codex-plugin-toggle.ps1" in result.stdout


def test_workflow_progressive_dry_run() -> None:
    result = run_auto("find papers then write a report", "--dry-run", "--prefer-workflow")
    assert result.returncode == 0, result.stderr + result.stdout
    assert "research-to-paper" in result.stdout
    assert "start workflow" in result.stdout
    assert "research-lit" in result.stdout
