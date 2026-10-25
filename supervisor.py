"""Keep a Claude agent working through STATUS.md until every page is built, and resume it when the quota returns.

Every INTERVAL seconds it:
  - reads the enrichment progress, restarts enrich.py when it died before the end (the agents only start once
    enriched.jsonl is complete);
  - counts the tasks left in STATUS.md;
  - makes sure an agent is running on them: starts `claude -p` (claude.ai subscription) when none is,
    kills it when it has produced nothing for STALL_SECONDS, and when it stopped on the usage limit,
    waits for the reset time before starting it again.
One agent handles one task then exits; the supervisor starts the next one with a clean context.

Usage:
  .venv/bin/python supervisor.py              # runs until every task is done (Ctrl-C to quit; a running agent keeps going)
  .venv/bin/python supervisor.py --dry-run    # one check, prints what it would do, starts nothing
  .venv/bin/python supervisor.py --model opus # model of the agents (default sonnet)

Problems are printed as `EXCEPTION <Type>: <detail>` on stderr; the supervisor keeps running.
"""
import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import monitor  # enrichment progress helpers

HERE = Path(__file__).parent
STATUS = HERE / "STATUS.md"
SITE = HERE / "site"
LOG = HERE / "agent.log"
PIDFILE = HERE / ".agent.pid"

INTERVAL = 30
STALL_SECONDS = 20 * 60  # an agent alive but silent this long is stuck
QUICK_EXIT = 90  # an agent that ends sooner than this without finishing a task is a failure
MAX_QUICK_FAILURES = 3
BACKOFF = [15 * 60, 30 * 60, 60 * 60]  # waits when the quota end time is unknown

ENRICH_LOG = HERE / "enrich_gemini.log"
ENRICH_CMD = [sys.executable, "-u", "enrich.py", "--all", "--backend", "gemini", "--workers", "8"]
# Wait before restarting enrich.py: none after a run that made progress, then longer after each run that did not
# (daily Gemini quota spent: it comes back overnight, so retrying every minute would be pointless).
ENRICH_DELAYS = [0, 60, 300, 900, 1800, 3600]

TOOLS = ",".join([
    "Read", "Write", "Edit", "Glob", "Grep", "Skill",
    "Bash(.venv/bin/python:*)", "Bash(python3:*)", "Bash(ls:*)", "Bash(wc:*)", "Bash(head:*)", "Bash(tail:*)", "Bash(cat:*)", "Bash(grep:*)",
])

PROMPT = """Tu es l'agent chargé du projet « Musée Air France » (répertoire courant). Un superviseur te lance pour UNE tâche à la fois.

1. Lis STATUS.md en entier : conventions, tâches, journal.
2. Vérifie la cohérence : une tâche cochée [x] dont site/<slug>.html n'existe pas repasse à [ ].
3. Prends la première tâche [~] de la section Pages, sinon la première [ ]. Passe-la à [~] tout de suite dans STATUS.md.
4. Réalise-la complètement en respectant les conventions (module pages/<slug>.py, build avec `.venv/bin/python build_site.py <slug>`). Regarde les vraies données de enriched.jsonl avant de concevoir la page.
5. Vérifie : la page se construit, la logique JS est relue et les calculs sont testés sur les vraies données, le résultat est lisible.
6. Passe la tâche à [x] et ajoute une ligne datée au Journal (ce qui est fait, limites connues). Si tu es bloqué, passe-la à [!] avec la raison.
7. Arrête-toi : le superviseur te relancera pour la tâche suivante.

Si tu es interrompu (quota), c'est normal : tiens STATUS.md à jour au fil de l'eau, le prochain agent reprend la tâche [~]."""

QUOTA = re.compile(r"usage limit|limit reached|hit your limit|rate.?limit|overloaded|too many requests|credit balance|\b429\b", re.I)


class SupervisorError(Exception):
    pass


def report(err):
    print(f"EXCEPTION {type(err).__name__}: {err}", file=sys.stderr, flush=True)


def tasks():
    """[(mark, slug)] for every task line of STATUS.md, enrichment excluded (it is monitored separately)."""
    found = re.findall(r"^- \[([ x~!])\] \*\*([a-z0-9-]+)\*\*", STATUS.read_text(), re.M)
    return [(mark, slug) for mark, slug in found if slug != "enrichissement"]


def pid_alive(pid):
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True


def agent_pid():
    """PID of a running agent started by a previous supervisor, if any."""
    try:
        pid = int(PIDFILE.read_text())
    except (FileNotFoundError, ValueError):
        return None
    if not pid_alive(pid):
        return None
    command = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True).stdout
    return pid if "claude" in command else None


def quota_reset(log_tail):
    """Epoch at which the usage limit lifts, from the agent's output; None when it does not say."""
    match = re.search(r"usage limit reached\|(\d{9,10})", log_tail, re.I) or re.search(r'"resetsAt"\s*:\s*(\d{9,10})', log_tail)
    if match:
        return int(match.group(1))
    match = re.search(r"resets?\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)", log_tail, re.I)
    if match:
        hour = int(match.group(1)) % 12 + (12 if match.group(3).lower() == "pm" else 0)
        reset = datetime.now().replace(hour=hour, minute=int(match.group(2) or 0), second=0, microsecond=0)
        if reset <= datetime.now():
            reset += timedelta(days=1)
        return reset.timestamp()
    return None


def final_result(log_tail):
    """The last `result` event of the stream, or None if the agent died before sending one."""
    for line in reversed(log_tail.splitlines()):
        if line.startswith("{") and '"type":"result"' in line.replace(" ", ""):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return None


def read_tail(path, size=60000):
    if not path.exists():
        return ""
    with path.open("rb") as f:
        f.seek(max(0, path.stat().st_size - size))
        return f.read().decode("utf-8", errors="replace")


def check_profile():
    """The agents must run on the claude.ai subscription, never on Vertex (billed to Kering)."""
    settings = Path.home() / ".claude/settings.json"
    env = json.loads(settings.read_text()).get("env", {}) if settings.exists() else {}
    if env.get("CLAUDE_CODE_USE_VERTEX") or env.get("ANTHROPIC_VERTEX_PROJECT_ID"):
        raise SupervisorError("le profil Claude Code actif est Vertex (Kering) : lance `csw perso` avant de démarrer des agents")


def start_agent(model):
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_CODE_") and k != "CLAUDECODE"}
    log = LOG.open("ab")
    log.write(f"\n=== {datetime.now():%Y-%m-%d %H:%M:%S} démarrage de l'agent ===\n".encode())
    log.flush()
    process = subprocess.Popen(
        ["claude", "-p", "--model", model, "--permission-mode", "acceptEdits", "--allowedTools", TOOLS,
         "--output-format", "stream-json", "--verbose", "--no-session-persistence"],
        stdin=subprocess.PIPE, stdout=log, stderr=log, cwd=HERE, env=env, start_new_session=True,
    )
    process.stdin.write(PROMPT.encode())
    process.stdin.close()
    PIDFILE.write_text(str(process.pid))
    return process


def ensure_enrichment(state, done, total, dry_run):
    """Restart enrich.py when it died before finishing; returns a note for the status line ("" when all is well)."""
    proc = state["proc"]
    if done >= total:
        return ""
    if monitor.is_running() and not (proc is not None and proc.poll() is not None):
        state["dead_since"] = None
        return ""
    if state["dead_since"] is None:  # first check that sees it dead
        state["dead_since"] = time.time()
        if state["start_done"] is not None and done <= state["start_done"]:
            state["step"] += 1  # the last run wrote nothing: back off further
        else:
            state["step"] = 0
        delay = ENRICH_DELAYS[min(state["step"], len(ENRICH_DELAYS) - 1)]
        state["restart_at"] = state["dead_since"] + delay
        report(SupervisorError(f"enrich.py s'est arrêté à {done}/{total} : relance automatique vers {datetime.fromtimestamp(state['restart_at']):%H:%M}"))
    if time.time() < state["restart_at"]:
        return f"  |  enrich.py arrêté, relance vers {datetime.fromtimestamp(state['restart_at']):%H:%M}"
    if dry_run:
        return "  |  enrich.py arrêté : serait relancé"
    log = ENRICH_LOG.open("ab")
    log.write(f"\n=== {datetime.now():%Y-%m-%d %H:%M:%S} relance par le superviseur ===\n".encode())
    log.flush()
    state["proc"] = subprocess.Popen(ENRICH_CMD, stdin=subprocess.DEVNULL, stdout=log, stderr=log, cwd=HERE, start_new_session=True,
                                     env={**os.environ, "PYTHONUNBUFFERED": "1"})
    state["start_done"], state["dead_since"] = done, None
    return "  |  enrich.py relancé"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--model", default="sonnet")
    args = parser.parse_args()

    total = monitor.total_texts()
    process = None  # agent started by this supervisor
    started_at = 0.0
    wait_until = 0.0
    wait_reason = ""
    quick_failures = backoff_step = 0
    enrich_state = {"proc": None, "start_done": None, "dead_since": None, "restart_at": 0.0, "step": 0}
    print(f"Superviseur : contrôle toutes les {INTERVAL} s, agents `claude -p --model {args.model}` ({LOG.name}). Ctrl-C pour quitter.")

    while True:
        try:
            done = monitor.done_texts()
            marks = tasks()
            finished = sum(1 for m, _ in marks if m == "x")
            left = [slug for m, slug in marks if m != "x"]
            line = f"{datetime.now():%H:%M:%S}  enrichissement {done}/{total} {done / total * 100:5.1f} %  |  pages {finished}/{len(marks)}"
            line += ensure_enrichment(enrich_state, done, total, args.dry_run)

            for mark, slug in marks:
                if mark == "x" and not (SITE / f"{slug}.html").exists() and slug != "accueil":
                    report(SupervisorError(f"{slug} est cochée [x] mais site/{slug}.html n'existe pas"))

            pid = None
            if process is not None and process.poll() is None:
                pid = process.pid
            elif process is not None:  # our agent just ended
                code, process = process.returncode, None
                tail = read_tail(LOG)
                result = final_result(tail)
                failed = result is None or result.get("is_error")
                text = (result or {}).get("result", "") if result else tail[-600:]
                if failed and (QUOTA.search(str(text)) or QUOTA.search(tail[-3000:])):
                    reset = quota_reset(tail[-6000:])
                    if reset is None:
                        reset = time.time() + BACKOFF[min(backoff_step, len(BACKOFF) - 1)]
                        backoff_step += 1
                    wait_until, wait_reason = reset + 60, "quota Claude atteint"
                    print(f"  agent arrêté par le quota : reprise vers {datetime.fromtimestamp(wait_until):%H:%M}", flush=True)
                elif failed:
                    quick_failures += 1 if time.time() - started_at < QUICK_EXIT else 0
                    report(SupervisorError(f"l'agent s'est terminé en erreur (code {code}) : {str(text)[:300]}"))
                    if quick_failures >= MAX_QUICK_FAILURES:
                        wait_until, wait_reason = time.time() + 30 * 60, "échecs répétés"
                        quick_failures = 0
                else:
                    quick_failures = backoff_step = 0
            else:
                pid = agent_pid()  # started by an earlier supervisor

            if pid is not None:
                idle = time.time() - (LOG.stat().st_mtime if LOG.exists() else time.time())
                line += f"  |  agent {pid} actif (silencieux depuis {int(idle // 60)} min)"
                if idle > STALL_SECONDS:
                    report(SupervisorError(f"l'agent {pid} ne produit plus rien depuis {int(idle // 60)} min : arrêt"))
                    os.killpg(os.getpgid(pid), signal.SIGTERM)
            elif not left:
                print(line + "  |  TOUTES LES TÂCHES SONT TERMINÉES", flush=True)
                return 0
            elif done < total:
                line += "  |  agent : en attente de la fin de l'enrichissement"
            elif time.time() < wait_until:
                line += f"  |  agent : {wait_reason}, reprise vers {datetime.fromtimestamp(wait_until):%H:%M}"
            else:
                check_profile()
                line += f"  |  démarrage d'un agent ({len(left)} tâches restantes, prochaine : {left[0]})"
                if not args.dry_run:
                    process, started_at = start_agent(args.model), time.time()
            print(line, flush=True)
        except SupervisorError as err:
            report(err)
        except Exception as err:  # the supervisor itself must not die on a transient error
            report(err)
        if args.dry_run:
            return 0
        time.sleep(INTERVAL)


if __name__ == "__main__":
    sys.exit(main())
