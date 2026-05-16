from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import tomllib
from typing import Any, Iterable, Sequence

HOME = pathlib.Path.home()

DEFAULT_PLUGIN_ALIASES: dict[str, str] = {
    "browser-use": "browser-use@openai-bundled",
    "browser": "browser-use@openai-bundled",
    "chrome": "chrome@openai-bundled",
    "latex": "latex-tectonic@openai-bundled",
    "latex-tectonic": "latex-tectonic@openai-bundled",
    "documents": "documents@openai-primary-runtime",
    "presentations": "presentations@openai-primary-runtime",
    "spreadsheets": "spreadsheets@openai-primary-runtime",
    "zotero": "zotero@openai-curated",
    "scite": "scite@openai-curated",
    "game-studio": "game-studio@openai-curated",
}

DEFAULT_OPTIONAL_PLUGINS: list[str] = [
    "browser-use",
    "chrome",
    "latex-tectonic",
    "documents",
    "presentations",
    "spreadsheets",
    "zotero",
    "scite",
    "game-studio",
]

DEFAULT_BUNDLED_PLUGINS: list[str] = ["browser-use", "chrome", "latex-tectonic"]


def env_path(name: str, default: pathlib.Path | str) -> pathlib.Path:
    value = os.environ.get(name)
    return pathlib.Path(value).expanduser() if value else pathlib.Path(default).expanduser()


def codex_home() -> pathlib.Path:
    return env_path("CODEX_HOME", HOME / ".codex")


def repair_tools_dir() -> pathlib.Path:
    return env_path("CODEX_REPAIR_TOOLS", codex_home() / "repair-tools")


def cold_archive() -> pathlib.Path:
    return env_path("CODEX_COLD_ARCHIVE", HOME / "CodexColdArchive")


def config_path() -> pathlib.Path:
    return env_path("CODEX_CONFIG", codex_home() / "config.toml")


def backup_dir() -> pathlib.Path:
    return env_path("CODEX_BACKUP_DIR", HOME / "CodexCapabilityHubBackups")


def script_dir() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent


def repo_root() -> pathlib.Path:
    return script_dir().parent


def find_data_file(filename: str, env_var: str | None = None) -> pathlib.Path:
    if env_var and os.environ.get(env_var):
        return pathlib.Path(os.environ[env_var]).expanduser()
    example_name = filename[:-5] + ".example.json" if filename.endswith(".json") else filename + ".example"
    candidates = [
        script_dir() / filename,
        repo_root() / "examples" / filename,
        repo_root() / "examples" / example_name,
        repair_tools_dir() / filename,
        pathlib.Path.cwd() / filename,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def capabilities_path() -> pathlib.Path:
    return find_data_file("capabilities.json", "CODEX_CAPABILITIES_JSON")


def workflows_path() -> pathlib.Path:
    return find_data_file("capability_workflows.json", "CODEX_CAPABILITY_WORKFLOWS_JSON")


def links_path() -> pathlib.Path:
    return find_data_file("capability_links.json", "CODEX_CAPABILITY_LINKS_JSON")


def interfaces_path() -> pathlib.Path:
    return find_data_file("capability_interfaces.json", "CODEX_CAPABILITY_INTERFACES_JSON")


def plugin_aliases_path() -> pathlib.Path:
    return find_data_file("plugin_aliases.json", "CODEX_PLUGIN_ALIASES_JSON")


def workflow_state_path() -> pathlib.Path:
    return env_path("CODEX_CAPABILITY_WORKFLOW_STATE", repair_tools_dir() / "capability_workflow_state.json")


def json_load(path: pathlib.Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        print(f"warning: could not read JSON {path}: {exc}", file=sys.stderr)
        return default


def json_write(path: pathlib.Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_config_text() -> str:
    path = config_path()
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write_config_text(text: str) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def load_config() -> dict[str, Any]:
    try:
        text = read_config_text()
        return tomllib.loads(text) if text.strip() else {}
    except Exception as exc:
        print(f"warning: could not parse {config_path()}: {exc}", file=sys.stderr)
        return {}


def safe_slug(label: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", label).strip("-")
    return safe or "config"


def backup_config(label: str) -> pathlib.Path | None:
    cfg = config_path()
    if not cfg.exists():
        return None
    root = backup_dir()
    root.mkdir(parents=True, exist_ok=True)
    dest = root / f"config-{safe_slug(label)}-{time.strftime('%Y%m%d-%H%M%S')}.toml"
    shutil.copy2(cfg, dest)
    print("backup", dest)
    return dest


def toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(value, ensure_ascii=False)


def set_toml_key(text: str, section: str, key: str, value: Any, comment: str | None = None) -> str:
    value_s = toml_value(value)
    line_new = f"{key} = {value_s}" + (f"  # {comment}" if comment else "")
    header = f"[{section}]"
    lines = text.splitlines()
    out: list[str] = []
    in_section = False
    saw_section = False
    wrote = False
    key_re = re.compile(rf"^\s*{re.escape(key)}\s*=")

    for line in lines:
        stripped = line.strip()
        is_header = stripped.startswith("[") and stripped.endswith("]")
        if is_header:
            if in_section and not wrote:
                out.append(line_new)
                wrote = True
            in_section = stripped == header
            saw_section = saw_section or in_section
            out.append(line)
            continue
        if in_section and key_re.match(line):
            if not wrote:
                out.append(line_new)
                wrote = True
            continue
        out.append(line)

    if saw_section:
        if in_section and not wrote:
            out.append(line_new)
    else:
        if out and out[-1].strip():
            out.append("")
        out.extend([header, line_new])
    return "\n".join(out)


def set_toml_key_in_matching_section(
    text: str,
    section_patterns: Sequence[str],
    create_section: str,
    key: str,
    value: Any,
    comment: str | None = None,
) -> str:
    value_s = toml_value(value)
    line_new = f"{key} = {value_s}" + (f"  # {comment}" if comment else "")
    lines = text.splitlines()
    out: list[str] = []
    in_section = False
    saw_section = False
    wrote = False
    key_re = re.compile(rf"^\s*{re.escape(key)}\s*=")
    header_res = [re.compile(p) for p in section_patterns]

    for line in lines:
        stripped = line.strip()
        is_header = stripped.startswith("[") and stripped.endswith("]")
        if is_header:
            if in_section and not wrote:
                out.append(line_new)
                wrote = True
            in_section = any(rx.match(stripped) for rx in header_res)
            saw_section = saw_section or in_section
            out.append(line)
            continue
        if in_section and key_re.match(line):
            if not wrote:
                out.append(line_new)
                wrote = True
            continue
        out.append(line)

    if saw_section:
        if in_section and not wrote:
            out.append(line_new)
    else:
        if out and out[-1].strip():
            out.append("")
        out.extend([f"[{create_section}]", line_new])
    return "\n".join(out)


def powershell_wrapper(name: str) -> pathlib.Path:
    here = script_dir()
    candidates = [
        here / name,
        here.parent / "powershell" / name,
        repair_tools_dir() / name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def run(cmd: Sequence[str | pathlib.Path], *, dry: bool = False) -> int:
    shown = " ".join(str(x) for x in cmd)
    prefix = "DRY-RUN >" if dry else ">"
    print(prefix, shown)
    if dry:
        return 0
    return subprocess.run([str(x) for x in cmd], shell=False).returncode


def run_powershell_script(script: pathlib.Path, args: Iterable[str], *, dry: bool = False) -> int:
    cmd: list[str | pathlib.Path] = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script]
    cmd.extend(args)
    return run(cmd, dry=dry)


def load_plugin_aliases() -> dict[str, str]:
    aliases = dict(DEFAULT_PLUGIN_ALIASES)
    data = json_load(plugin_aliases_path(), {})
    if isinstance(data, dict):
        aliases.update({str(k): str(v) for k, v in data.items()})
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and "alias" in item and "plugin" in item:
                aliases[str(item["alias"])] = str(item["plugin"])
    return aliases


def resolve_plugin(name: str) -> str:
    return load_plugin_aliases().get(name, name)


def optional_plugins() -> list[str]:
    raw = os.environ.get("CODEX_OPTIONAL_PLUGINS")
    if raw:
        return [x.strip() for x in re.split(r"[,;]", raw) if x.strip()]
    return list(DEFAULT_OPTIONAL_PLUGINS)


def bundled_plugins() -> list[str]:
    raw = os.environ.get("CODEX_BUNDLED_PLUGINS")
    if raw:
        return [x.strip() for x in re.split(r"[,;]", raw) if x.strip()]
    return list(DEFAULT_BUNDLED_PLUGINS)


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            key = str(k).lower()
            if any(word in key for word in ["token", "secret", "password", "apikey", "api_key", "authorization"]):
                out[k] = "***REDACTED***"
            else:
                out[k] = redact(v)
        return out
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        if re.search(r"(ghp_[A-Za-z0-9_]+|sk-[A-Za-z0-9_-]+|Bearer\s+\S+)", value):
            return "***REDACTED***"
    return value
