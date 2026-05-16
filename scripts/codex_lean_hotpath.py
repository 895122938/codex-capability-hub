from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from pathlib import Path

from common import codex_home, cold_archive


def keep_dirs() -> set[str]:
    raw = os.environ.get("CODEX_HOT_SKILL_DIRS", ".system")
    return {x.strip() for x in raw.split(",") if x.strip()}


def skills_dir() -> Path:
    return codex_home() / "skills"


def status() -> None:
    root = skills_dir()
    hot = [p for p in root.iterdir() if p.is_dir()] if root.exists() else []
    count = sum(1 for _ in root.rglob("SKILL.md")) if root.exists() else 0
    print("hot_skill_md_count", count)
    print("hot_dirs", ", ".join(sorted(p.name for p in hot)))


def apply() -> int:
    root = skills_dir()
    if not root.exists():
        print("skills directory not found", root)
        status()
        return 0
    stamp = time.strftime("%Y%m%d-%H%M%S")
    cold = cold_archive() / f"skills-cold-lean-hotpath-{stamp}"
    keep = keep_dirs()
    move = [p for p in root.iterdir() if p.is_dir() and p.name not in keep]
    manifest = []
    if move:
        cold.mkdir(parents=True, exist_ok=True)
        for item in move:
            dst = cold / item.name
            if dst.exists():
                i = 1
                while (cold / f"{item.name}-{i}").exists():
                    i += 1
                dst = cold / f"{item.name}-{i}"
            shutil.move(str(item), str(dst))
            manifest.append({"name": item.name, "from": str(item), "to": str(dst)})
        (cold / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("lean hotpath applied; moved", len(manifest))
    if manifest:
        print("cold_dir", cold)
    status()
    return 0


def restore_latest() -> int:
    root = skills_dir()
    root.mkdir(parents=True, exist_ok=True)
    dirs = sorted(
        [p for p in cold_archive().glob("skills-cold-lean-hotpath-*") if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not dirs:
        print("no lean hotpath archive found")
        return 0
    srcroot = dirs[0]
    moved = 0
    for item in srcroot.iterdir():
        if item.name == "manifest.json" or not item.is_dir():
            continue
        dst = root / item.name
        if dst.exists():
            print("skip existing hot", item.name)
            continue
        shutil.move(str(item), str(dst))
        moved += 1
        print("restored", item.name)
    print("restored from", srcroot, "count", moved)
    status()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Keep the Codex skill hot path lean.")
    parser.add_argument("cmd", choices=["apply", "status", "restore-latest"])
    args = parser.parse_args()
    if args.cmd == "apply":
        return apply()
    if args.cmd == "restore-latest":
        return restore_latest()
    status(); return 0


if __name__ == "__main__":
    raise SystemExit(main())
