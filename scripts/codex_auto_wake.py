from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from common import capabilities_path, json_load, workflows_path

WORKFLOW_HINTS = [
    "workflow", "pipeline", "handoff", "end to end", "from", "to", "then", "integrate", "integration",
]


def norm(value: str) -> str:
    return (value or "").lower()


def tokenize(value: str) -> list[str]:
    return [x for x in re.split(r"[^a-z0-9\u4e00-\u9fff+#.]+", norm(value)) if x]


def registry() -> dict[str, Any]:
    return json_load(capabilities_path(), {"capabilities": []})


def workflows() -> dict[str, Any]:
    return json_load(workflows_path(), {"workflows": []})


def score_text_list(items: list[str], text: str, token_set: set[str], *, label: str, strong: int, weak: int) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    whole = norm(text)
    for item in items:
        value = norm(str(item))
        if not value:
            continue
        if value in whole:
            score += strong if len(value) >= 3 else weak
            reasons.append(f"{label}:{item}")
        elif value in token_set:
            score += weak
            reasons.append(f"{label}:{item}")
    return score, reasons


def score_cap(cap: dict[str, Any], text: str) -> tuple[int, list[str]]:
    whole = norm(text)
    tokens = set(tokenize(text))
    score = 0
    reasons: list[str] = []
    cap_id = str(cap.get("id", ""))
    if cap_id and (cap_id in whole or cap_id.replace("-", " ") in whole):
        score += 8
        reasons.append(f"id:{cap_id}")
    part, why = score_text_list(list(cap.get("triggers", []) or []), text, tokens, label="trigger", strong=10, weak=5)
    score += part; reasons.extend(why)
    part, why = score_text_list(list(cap.get("aliases", []) or []), text, tokens, label="alias", strong=9, weak=4)
    score += part; reasons.extend(why)
    part, why = score_text_list(list(cap.get("tags", []) or []), text, tokens, label="tag", strong=3, weak=3)
    score += part; reasons.extend(why)
    return score, reasons[:10]


def cap_matches(text: str, limit: int = 8) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cap in registry().get("capabilities", []):
        if not isinstance(cap, dict):
            continue
        score, reasons = score_cap(cap, text)
        if score > 0:
            rows.append({
                "type": "capability",
                "id": cap.get("id"),
                "score": score,
                "risk": cap.get("risk_level", ""),
                "cost": cap.get("startup_cost_if_hot", ""),
                "description": cap.get("description", ""),
                "sensitive": bool(cap.get("sensitive")),
                "reasons": reasons,
            })
    rows.sort(key=lambda x: x["score"], reverse=True)
    return rows[:limit]


def score_workflow(workflow: dict[str, Any], text: str, cap_scores: dict[str, int]) -> tuple[int, list[str]]:
    whole = norm(text)
    tokens = set(tokenize(text))
    score = 0
    reasons: list[str] = []
    wid = str(workflow.get("id", ""))
    if wid and (wid in whole or wid.replace("-", " ") in whole):
        score += 12
        reasons.append(f"id:{wid}")
    part, why = score_text_list(list(workflow.get("triggers", []) or []), text, tokens, label="trigger", strong=14, weak=6)
    score += part; reasons.extend(why)
    phase_ids = [str(p.get("capability")) for p in workflow.get("phases", []) if isinstance(p, dict)]
    matched = [cid for cid in phase_ids if cap_scores.get(cid, 0) > 0]
    if len(matched) >= 2:
        score += 8 + 3 * len(matched)
        reasons.append("multi-cap:" + ",".join(matched[:5]))
    elif len(matched) == 1:
        score += 3
        reasons.append("phase-cap:" + matched[0])
    if any(hint in whole for hint in WORKFLOW_HINTS) and matched:
        score += 8
        reasons.append("workflow-hint")
    return score, reasons[:10]


def workflow_matches(text: str, limit: int = 5) -> list[dict[str, Any]]:
    cap_scores = {str(cap.get("id")): score_cap(cap, text)[0] for cap in registry().get("capabilities", []) if isinstance(cap, dict)}
    rows: list[dict[str, Any]] = []
    for workflow in workflows().get("workflows", []):
        if not isinstance(workflow, dict):
            continue
        score, reasons = score_workflow(workflow, text, cap_scores)
        if score > 0:
            seq = " -> ".join(str(p.get("capability")) for p in workflow.get("phases", []) if isinstance(p, dict))
            rows.append({
                "type": "workflow",
                "id": workflow.get("id"),
                "score": score,
                "description": workflow.get("description", ""),
                "sequence": seq,
                "reasons": reasons,
            })
    rows.sort(key=lambda x: x["score"], reverse=True)
    return rows[:limit]


def explicit_sensitive_intent(cap_id: str, text: str, reasons: list[str]) -> bool:
    whole = norm(text)
    if cap_id and (cap_id in whole or cap_id.replace("-", " ") in whole):
        return True
    return any(reason.startswith("trigger:") or reason.startswith("alias:") or reason.startswith("id:") for reason in reasons)


def wake_script() -> Path:
    return Path(__file__).resolve().parent / "codex_wake.py"


def call_wake(cmd: str, target: str) -> int:
    return subprocess.run([sys.executable, str(wake_script()), cmd, target], shell=False).returncode


def print_matches(cap_rows: list[dict[str, Any]], wf_rows: list[dict[str, Any]]) -> None:
    if wf_rows:
        print("WORKFLOW_MATCHES")
        for row in wf_rows:
            print(f"- {row['id']} score={row['score']} :: {row['description']} [{row['sequence']}]")
            if row.get("reasons"):
                print("  reasons:", "; ".join(row["reasons"]))
    if cap_rows:
        print("CAPABILITY_MATCHES")
        for row in cap_rows:
            print(f"- {row['id']} score={row['score']} risk={row['risk']} cost={row['cost']} :: {row['description']}")
            if row.get("reasons"):
                print("  reasons:", "; ".join(row["reasons"]))


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect and optionally wake a Capability Hub bundle/workflow from natural language text.")
    parser.add_argument("--text", "-t", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--with-linked", action="store_true", help="For capability matches, wake linked validation/pair capabilities too")
    parser.add_argument("--prefer-workflow", action="store_true", help="Prefer workflow matches when available")
    parser.add_argument("--full-workflow", action="store_true", help="Wake the whole workflow instead of only starting phase 1")
    parser.add_argument("--threshold", type=int, default=8)
    parser.add_argument("--allow-sensitive", action="store_true")
    parser.add_argument("rest", nargs="*")
    args = parser.parse_args()

    text = args.text or " ".join(args.rest)
    if not text.strip():
        print("No text provided.")
        return 2

    cap_rows = cap_matches(text)
    wf_rows = workflow_matches(text)
    if not cap_rows and not wf_rows:
        print("NO_CAPABILITY_MATCH")
        return 0
    print_matches(cap_rows, wf_rows)
    sys.stdout.flush()

    best_cap = cap_rows[0] if cap_rows else None
    best_wf = wf_rows[0] if wf_rows else None
    workflow_hint = any(hint in norm(text) for hint in WORKFLOW_HINTS)
    choose_wf = False
    if best_wf and best_wf["score"] >= args.threshold:
        if args.prefer_workflow or workflow_hint or not best_cap or best_wf["score"] >= best_cap["score"] + 4:
            choose_wf = True

    if choose_wf and best_wf:
        cmd = "workflow-dry-run" if args.full_workflow and args.dry_run else \
              "workflow-wake" if args.full_workflow else \
              "workflow-start-dry-run" if args.dry_run else \
              "workflow-start"
        if args.apply or args.dry_run:
            return call_wake(cmd, str(best_wf["id"]))
        print("SUGGEST_WORKFLOW", best_wf["id"])
        print("SUGGEST_PROGRESSIVE_START", best_wf["id"])
        return 0

    if not best_cap or best_cap["score"] < args.threshold:
        print(f"BEST_BELOW_THRESHOLD threshold={args.threshold}; no wake")
        return 0

    if best_cap.get("sensitive") and args.apply and not args.allow_sensitive:
        if not explicit_sensitive_intent(str(best_cap["id"]), text, list(best_cap.get("reasons", []))):
            print(f"SENSITIVE_MATCH {best_cap['id']}; explicit intent or --allow-sensitive required")
            return 0

    if args.dry_run:
        return call_wake("dry-run-linked" if args.with_linked else "dry-run", str(best_cap["id"]))
    if args.apply:
        return call_wake("wake-linked" if args.with_linked else "wake", str(best_cap["id"]))
    print("SUGGEST_WAKE", best_cap["id"])
    if best_wf:
        print("SUGGEST_WORKFLOW_OPTION", best_wf["id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
