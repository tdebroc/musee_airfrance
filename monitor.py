"""Watch the enrichment run: progress in %, and an exception message as soon as something is wrong.

Every INTERVAL seconds it checks that enrich.py is alive, how many texts are in enriched.jsonl, that the count
is still moving, and whether the log shows new failed batches or a stop.

Usage:
  .venv/bin/python monitor.py            # runs until Ctrl-C
  .venv/bin/python monitor.py --once     # a single check (exit code 1 if a problem is found)
"""
import argparse
import json
import subprocess
import sys
import time
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).parent
INPUT = HERE / "ephemerides.json"
OUTPUT = HERE / "enriched.jsonl"
LOG = HERE / "enrich_gemini.log"

INTERVAL = 30
SPEED_WINDOW = 600  # seconds of history used to measure the speed: smooths out rate-limit pauses
STALL_CHECKS = 6  # no new text for 6 checks (3 min) = stuck, even though the process is alive
PROBLEM_MARKERS = ("erreur", "non exploitable", "en échec d'affilée", "finishReason", "Traceback", "Pas de clé")


class MonitorError(Exception):
    pass


def total_texts():
    entries = json.loads(INPUT.read_text())
    return sum(1 for e in entries if (e.get("body_value") or "").strip() and e.get("field_date_value"))


def done_texts():
    if not OUTPUT.exists():
        return 0
    ids, bad = set(), 0
    for line in OUTPUT.read_text().splitlines():
        try:
            ids.add(json.loads(line)["id"])
        except (json.JSONDecodeError, KeyError):
            bad += 1
    if bad:
        raise MonitorError(f"enriched.jsonl contient {bad} ligne(s) illisible(s)")
    return len(ids)


def is_running():
    return subprocess.run(["pgrep", "-f", "enrich.py --all"], capture_output=True).returncode == 0


def new_log_problems(offset):
    """Problem lines appended to the log since `offset`; returns (lines, new_offset)."""
    if not LOG.exists():
        return [], 0
    size = LOG.stat().st_size
    if size < offset:  # log was recreated by a relaunch
        offset = 0
    with LOG.open("rb") as f:
        f.seek(offset)
        text = f.read().decode("utf-8", errors="replace")
    return [l.strip() for l in text.splitlines() if any(m in l for m in PROBLEM_MARKERS)], size


def speed_and_eta(samples, done, total):
    """Texts per minute over the recent window, and the matching finish estimate (None until measurable)."""
    (t0, d0), (t1, d1) = samples[0], samples[-1]
    if t1 <= t0 or d1 <= d0:
        return None
    per_minute = (d1 - d0) / (t1 - t0) * 60
    return per_minute, timedelta(minutes=(total - done) / per_minute)


def check(total, state):
    """One check; returns the status line, raises MonitorError on a problem."""
    done = done_texts()
    pct = done / total * 100
    problems, state["offset"] = new_log_problems(state["offset"])
    status = f"{datetime.now():%H:%M:%S}  {done}/{total} textes  {pct:5.1f} %"

    now = time.time()
    samples = state["samples"]
    samples.append((now, done))
    while now - samples[0][0] > SPEED_WINDOW:
        samples.popleft()

    if done >= total:
        return status + "  TERMINÉ"
    if not is_running():
        raise MonitorError(f"{status}  enrich.py ne tourne plus ({total - done} textes restants) : supervisor.py le relance, sinon voir STATUS.md")
    if problems:
        raise MonitorError(f"{status}  {len(problems)} problème(s) dans {LOG.name}, dernier : {problems[-1][:200]}")

    state["stalled"] = state["stalled"] + 1 if done == state["last_done"] else 0
    state["last_done"] = done
    if state["stalled"] >= STALL_CHECKS:
        raise MonitorError(f"{status}  aucun nouveau texte depuis {state['stalled'] * INTERVAL} s (quota Gemini ?)")
    measured = speed_and_eta(samples, done, total)
    if measured is None:
        return status + "  OK  vitesse : mesure en cours"
    per_minute, remaining = measured
    finish = datetime.now() + remaining
    hours, rest = divmod(int(remaining.total_seconds()), 3600)
    return status + f"  OK  {per_minute:.0f} textes/min  reste ~{hours} h {rest // 60:02d} min  fin vers {finish:%H:%M}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    total = total_texts()
    # Start reading the log from its end so old, already-handled errors are not reported again.
    state = {"offset": LOG.stat().st_size if LOG.exists() else 0, "last_done": -1, "stalled": 0, "samples": deque()}
    print(f"Surveillance de {OUTPUT.name} : {total} textes, contrôle toutes les {INTERVAL} s (Ctrl-C pour quitter)")
    while True:
        try:
            line = check(total, state)
            print(line, flush=True)
            if "TERMINÉ" in line:
                return 0
        except MonitorError as err:
            print(f"EXCEPTION MonitorError: {err}", file=sys.stderr, flush=True)
            if args.once:
                return 1
        except Exception as err:  # the monitor itself must not die on a transient read error
            print(f"EXCEPTION {type(err).__name__}: {err}", file=sys.stderr, flush=True)
            if args.once:
                return 1
        if args.once:
            return 0
        time.sleep(INTERVAL)


if __name__ == "__main__":
    sys.exit(main())
