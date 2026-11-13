"""Diagnose perturbed SetConfCrDdl episodes: for each target conference, find the agent's
reminder events, compute the offset it actually used, and decode which revisions it applied
(deltas are powers of two, so every subset of applied revisions gives a unique offset).

Usage (from repo root):
    PYTHONPATH=. python scripts/diagnose_perturbation.py                   # failed perturbed episodes, most recent run
    PYTHONPATH=. python scripts/diagnose_perturbation.py --all             # all perturbed episodes, most recent run
    PYTHONPATH=. python scripts/diagnose_perturbation.py outputs/<run>     # failed perturbed episodes in that run
    PYTHONPATH=. python scripts/diagnose_perturbation.py <.../state0>      # one episode
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from mcp_convert.mcps.calendar.database_utils import CalendarDatabase


def diagnose(task):
    gt = task / "groundtruth_workspace"
    schedule = json.load(open(gt / "perturbations.json"))
    base = schedule.get("base_offset_hours", 3)
    revs = {r["id"]: r for r in schedule["revisions"]}
    log_file = task / "perturbation_log.json"
    delivered_ids = [d["id"] for d in json.load(open(log_file))["delivered"]] if log_file.exists() else []
    expected = base + sum(revs[i]["delta_hours"] for i in delivered_ids)

    print(f"Delivered: {delivered_ids} of {list(revs)}")
    missing = [i for i in revs if i not in delivered_ids]
    if missing:
        print(f"  !! never delivered: {missing}  (agent finished first)")
    print(f"Expected offset: {expected}h  (base {base}h + delivered deltas)\n")

    def decode(offset_h):
        """Which delivered revisions sum to (offset - base)? None if no subset matches."""
        extra = round(offset_h - base)
        applied = [i for i in delivered_ids if extra & revs[i]["delta_hours"]]
        return applied if sum(revs[i]["delta_hours"] for i in applied) == extra else None

    confs = json.load(open(gt / "conference_metadata.json"))["target_info"]["conferences"]
    events = CalendarDatabase(data_dir=str(task / "local_db" / "calendar")).list_events(
        time_min="2000-01-01T00:00:00Z", time_max="2100-01-01T00:00:00Z")

    n_ok = 0
    for c in confs:
        key = c["conference"]
        deadline = datetime.fromisoformat(c["deadline"])
        mine = [e for e in events if re.search(r"\b" + re.escape(key.lower()) + r"\b", e.get("summary", "").lower())]
        if not mine:
            print(f"{key:6s} NO EVENT")
            continue
        conf_ok = False
        for e in mine:
            start = datetime.fromisoformat(e["start"]["dateTime"])
            off = (deadline - start).total_seconds() / 3600
            ok = abs(off - expected) < 5 / 60
            conf_ok |= ok
            applied = decode(off)
            dec = f"applied {applied}" if applied is not None else "offset matches no revision subset"
            dup = f" (1 of {len(mine)} events)" if len(mine) > 1 else ""
            print(f"{key:6s} {'OK ' if ok else 'BAD'} offset {off:5.1f}h | {dec}{dup} | '{e.get('summary', '')}'")
        n_ok += conf_ok

    print(f"\n{n_ok}/{len(confs)} conferences have a correct reminder")


args = [a for a in sys.argv[1:] if not a.startswith("--")]
show_all = "--all" in sys.argv

if args and (Path(args[0]) / "groundtruth_workspace").exists():
    episodes = [Path(args[0])]  # a single episode folder
else:
    if args:
        run = Path(args[0])
    else:
        run = max((p for p in Path("outputs").iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime)
    print(f"Run: {run}")
    episodes = []
    for state in sorted(run.glob("tasks/*/state*")):
        traj = state / "trajectory.json"
        if not (state / "groundtruth_workspace" / "perturbations.json").exists():
            continue  # vanilla episode
        if not traj.exists():
            print(f"  (skipping {state.relative_to(run)}: still running)")
            continue
        if show_all or json.load(open(traj))["metrics"].get("accuracy") != 1.0:
            episodes.append(state)
    print(f"{len(episodes)} {'perturbed' if show_all else 'failed perturbed'} episode(s)")

for ep in episodes:
    print("\n" + "=" * 90 + f"\n{ep}\n" + "=" * 90)
    diagnose(ep)