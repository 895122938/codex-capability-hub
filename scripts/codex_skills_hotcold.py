from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from common import codex_home, cold_archive


def skills_dir() -> Path:
    return codex_home() / "skills"


def find_cold(name: str) -> list[Path]:
    archive = cold_archive()
    hits: list[Path] = []
    if not archive.exists():
        return hits
    for root in archive.glob("skills-cold*"):
        if not root.is_dir():
            continue
        direct = root / name
        if direct.exists():
            hits.append(direct)
        for skill_md in root.rglob("SKILL.md"):
            if skill_md.parent.name == name:
                hits.append(skill_md.parent)
    unique: dict[str, Path] = {str(p.resolve()): p for p in hits}
    return sorted(unique.values(), key=lambda p: p.stat().st_mtime, reverse=True)


def list_hot() -> None:
    root = skills_dir()
    if not root.exists():
        return
    for item in sorted([p for p in root.iterdir() if p.is_dir()], key=lambda x: x.name.lower()):
        print(item.name)


def list_cold() -> None:
    archive = cold_archive()
    seen: dict[str, list[str]] = {}
    if archive.exists():
        for root in archive.glob("skills-cold*"):
            if not root.is_dir():
                continue
            for skill_md in root.rglob("SKILL.md"):
                seen.setdefault(skill_md.parent.name, []).append(str(skill_md.parent))
            for item in root.iterdir():
                if item.is_dir():
                    seen.setdefault(item.name, []).append(str(item))
    for name in sorted(seen):
        print(name)


def warm(names: list[str]) -> int:
    root = skills_dir()
    root.mkdir(parents=True, exist_ok=True)
    rc = 0
    for name in names:
        dst = root / name
        if dst.exists():
            print("already hot", name)
            continue
        hits = find_cold(name)
        if not hits:
            print("not found in cold archive", name)
            rc = rc or 1
            continue
        shutil.move(str(hits[0]), str(dst))
        print("warmed", name)
    return rc


def cool(names: list[str]) -> int:
    root = skills_dir()
    dstroot = cold_archive() / "skills-cold-manual"
    dstroot.mkdir(parents=True, exist_ok=True)
    rc = 0
    for name in names:
        src = root / name
        if not src.exists():
            print("not hot", name)
            rc = rc or 1
            continue
        dst = dstroot / name
        if dst.exists():
            i = 1
            while (dstroot / f"{name}-{i}").exists():
                i += 1
            dst = dstroot / f"{name}-{i}"
        shutil.move(str(src), str(dst))
        print("cooled", name)
    return rc


def main() -> int:
    parser = argparse.ArgumentParser(description="Move Codex skills between hot and cold locations.")
    parser.add_argument("cmd", choices=["list-hot", "list-cold", "warm", "cool"])
    parser.add_argument("names", nargs="*")
    args = parser.parse_args()
    if args.cmd == "list-hot":
        list_hot(); return 0
    if args.cmd == "list-cold":
        list_cold(); return 0
    if args.cmd == "warm":
        return warm(args.names)
    return cool(args.names)


if __name__ == "__main__":
    raise SystemExit(main())
