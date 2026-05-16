from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
from typing import Any

from common import (
    backup_config,
    bundled_plugins,
    codex_home,
    load_config,
    optional_plugins,
    read_config_text,
    resolve_plugin,
    set_toml_key,
    write_config_text,
)


def set_feature(name: str, on: bool, *, write: bool = True) -> str:
    text = read_config_text()
    text = set_toml_key(text, "features", name, on, "Codex Capability Hub lean/on-demand feature toggle")
    if write:
        write_config_text(text)
    return text


def remove_feature(name: str, *, write: bool = True) -> bool:
    """Remove an unsupported/obsolete feature key instead of setting it false.

    Some Codex builds treat unknown [features] keys as feature-enable requests and
    wait for a timeout during UI loading. For those keys, absence is safer than
    `false`.
    """
    import re

    header = "[features]"
    key_re = re.compile(rf"^\s*{re.escape(name)}\s*=")
    lines = read_config_text().splitlines()
    out: list[str] = []
    in_section = False
    removed = False
    for line in lines:
        stripped = line.strip()
        is_header = stripped.startswith("[") and stripped.endswith("]")
        if is_header:
            in_section = stripped == header
            out.append(line)
            continue
        if in_section and key_re.match(line):
            removed = True
            continue
        out.append(line)
    if write and removed:
        write_config_text("\n".join(out))
    return removed


def plugin_section(plugin: str) -> str:
    escaped = plugin.replace('"', '\\"')
    return f'plugins."{escaped}"'


def ensure_plugin(name: str, on: bool, *, auto_feature: bool = True, write_backup: bool = True) -> None:
    plugin = resolve_plugin(name)
    if write_backup:
        backup_config(f"plugin-toggle-{plugin}-{str(on).lower()}")
    text = read_config_text()
    text = set_toml_key(text, plugin_section(plugin), "enabled", bool(on), "Codex Capability Hub on-demand plugin toggle")
    write_config_text(text)
    if auto_feature:
        if on:
            set_feature("plugins", True)
        else:
            auto_set_plugins_feature()
    print(plugin, "enabled" if on else "disabled")


def plugin_enabled_explicit(plugin: str) -> bool:
    plugins = load_config().get("plugins", {}) or {}
    value = plugins.get(plugin, {})
    return bool(isinstance(value, dict) and value.get("enabled") is True)


def any_optional_plugin_enabled() -> bool:
    return any(plugin_enabled_explicit(resolve_plugin(name)) for name in optional_plugins())


def auto_set_plugins_feature() -> None:
    set_feature("plugins", any_optional_plugin_enabled())


def disable_optionals(*, write_backup: bool = True) -> None:
    if write_backup:
        backup_config("plugin-optionals-off")
    for name in optional_plugins():
        ensure_plugin(name, False, auto_feature=False, write_backup=False)
    set_feature("plugins", False)


def lean_startup() -> None:
    backup_config("plugin-lean-startup")
    disable_optionals(write_backup=False)
    removed = remove_feature("workspace_dependencies")
    suffix = "; removed unsupported workspace_dependencies key" if removed else ""
    print("lean-startup applied: optional plugins are cold; [features].plugins=false" + suffix)


def status() -> None:
    config = load_config()
    features = config.get("features", {}) or {}
    print("features.plugins=", features.get("plugins", "default"))
    print("features.workspace_dependencies=", features.get("workspace_dependencies", "absent"))
    plugins = config.get("plugins", {}) or {}
    seen: set[str] = set()
    for alias in optional_plugins():
        plugin = resolve_plugin(alias)
        if plugin in seen:
            continue
        seen.add(plugin)
        enabled = plugins.get(plugin, {}).get("enabled", "default") if isinstance(plugins.get(plugin, {}), dict) else "default"
        print(f"{alias:18s} {plugin:42s} enabled={enabled}")


def bundled_source_root() -> pathlib.Path | None:
    env = os.environ.get("CODEX_BUNDLED_PLUGIN_SOURCE")
    candidates: list[pathlib.Path] = []
    if env:
        candidates.append(pathlib.Path(env).expanduser())
    try:
        cmd = [
            "powershell", "-NoProfile", "-Command",
            "$p=(Get-Process Codex -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Path); if($p){ Join-Path (Split-Path -Parent $p) 'resources\\plugins\\openai-bundled\\plugins' }",
        ]
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=5).strip()
        if out:
            candidates.append(pathlib.Path(out))
    except Exception:
        pass
    try:
        cmd = [
            "powershell", "-NoProfile", "-Command",
            "$pkg=Get-AppxPackage -Name OpenAI.Codex -ErrorAction SilentlyContinue | Select-Object -First 1; if($pkg){ Join-Path $pkg.InstallLocation 'app\\resources\\plugins\\openai-bundled\\plugins' }",
        ]
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=5).strip()
        if out:
            candidates.append(pathlib.Path(out))
    except Exception:
        pass
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def copy_missing_tree(src: pathlib.Path, dst: pathlib.Path) -> tuple[int, int]:
    copied = 0
    skipped = 0
    for root, _dirs, files in os.walk(src):
        rel = pathlib.Path(root).relative_to(src)
        target_dir = dst / rel
        target_dir.mkdir(parents=True, exist_ok=True)
        for filename in files:
            source = pathlib.Path(root) / filename
            target = target_dir / filename
            force = ".codex-plugin" in source.parts or filename in {"plugin.json", "openai.yaml"}
            try:
                if force or not target.exists():
                    shutil.copy2(source, target)
                    copied += 1
                else:
                    skipped += 1
            except PermissionError as exc:
                print("warning: locked, skipped", target, exc)
                skipped += 1
    return copied, skipped


def remove_stale_junction(path: pathlib.Path) -> bool:
    if not path.exists():
        return False
    try:
        is_junction = getattr(path, "is_junction", lambda: False)()
        if path.is_symlink() or is_junction:
            os.rmdir(path)
            return True
    except Exception as exc:
        print("warning: could not remove stale junction", path, repr(exc))
    return False


def repair_cache() -> None:
    backup_config("plugin-cache-repair")
    src_root = bundled_source_root()
    if not src_root:
        print("warning: bundled plugin source not found; set CODEX_BUNDLED_PLUGIN_SOURCE if needed")
        return
    dst_root = codex_home() / "plugins" / "cache" / "openai-bundled"
    total_copied = total_skipped = 0
    for name in bundled_plugins():
        src = src_root / name
        manifest = src / ".codex-plugin" / "plugin.json"
        if not manifest.exists():
            print("warning: source manifest missing", manifest)
            continue
        try:
            version = json.loads(manifest.read_text(encoding="utf-8")).get("version")
        except Exception:
            version = None
        if not version:
            print("warning: cannot determine version for", name)
            continue
        dst = dst_root / name / str(version)
        copied, skipped = copy_missing_tree(src, dst)
        total_copied += copied
        total_skipped += skipped
        latest = dst_root / name / "latest"
        if remove_stale_junction(latest):
            print("removed stale junction", latest)
        ok = (dst / ".codex-plugin" / "plugin.json").exists()
        print(f"{name}@{version}: manifest_ok={ok} copied={copied} skipped={skipped}")
    print(f"cache repair complete: copied={total_copied} skipped={total_skipped}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Toggle Codex plugins as cold/on-demand capabilities.")
    parser.add_argument("plugin", nargs="?", default="list")
    parser.add_argument("state", nargs="?", choices=["on", "off", "status"])
    parser.add_argument("--disable-optionals", action="store_true")
    parser.add_argument("--lean-startup", action="store_true")
    parser.add_argument("--repair-cache", action="store_true")
    parser.add_argument("--feature", choices=["on", "off", "status"])
    args = parser.parse_args()

    if args.feature:
        if args.feature == "status":
            print("features.plugins=", (load_config().get("features") or {}).get("plugins", "default"))
        else:
            backup_config(f"plugins-feature-{args.feature}")
            set_feature("plugins", args.feature == "on")
            print("features.plugins=", args.feature == "on")
        return 0
    if args.lean_startup:
        lean_startup(); return 0
    if args.repair_cache:
        repair_cache(); return 0
    if args.disable_optionals:
        disable_optionals(); return 0
    if args.plugin in {"list", "status"} or args.state == "status":
        status(); return 0
    if args.state is None:
        status(); return 0
    ensure_plugin(args.plugin, args.state == "on")
    print("note: restart Codex or reload plugin list to fully apply plugin UI changes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
