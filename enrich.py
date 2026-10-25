"""Structure every ephemeris with Claude Haiku 5.5, in a single pass that feeds all the visualisations.

One record per text (enriched.jsonl): title + short sentence, categories, tone, interest score,
people, places, aircraft, opened/closed routes, records, key figures, casualties.

Backends:
  gemini  Gemini Flash-Lite through the AI Studio API key of the wine-testing-quizz project (default)
  vertex  Claude Haiku 5.5 on Vertex AI, project grooptown-lab-thibaut, billed to that project
  cli     `claude -p` on the claude.ai subscription (csw perso): no extra cost, consumes the quota

Usage:
  .venv/bin/python enrich.py --sample 24              # stratified sample by decade
  .venv/bin/python enrich.py --all                    # the 10 436 texts
  .venv/bin/python enrich.py --sample 24 --backend cli

Gemini key: GEMINI_API_KEY, else ~/.config/musee_airfrance/gemini_key (paid, wine-testing-quizz), else the free key of the wine quiz backend .env.

Vertex setup (once): `gcloud auth login thibaut@grooptown.com`, then enable "Claude Haiku 5.5" in Model Garden
for grooptown-lab-thibaut. The script uses that gcloud account's token, so the Kering ADC is left untouched.

Results are appended to enriched.jsonl, so an interrupted run resumes where it stopped.
"""
import argparse
import json
import os
import random
import subprocess
import sys
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Literal, Optional

import httpx
from pydantic import BaseModel, Field, ValidationError

HERE = Path(__file__).parent
INPUT = HERE / "ephemerides.json"
OUTPUT = HERE / "enriched.jsonl"

PROJECT = "grooptown-lab-thibaut"
REGION = "global"
MODEL = "claude-haiku-5-5"
ACCOUNT = "thibaut@grooptown.com"
# Anthropic list price per million tokens (prompts under 100K); Vertex billing may differ slightly.
PRICE_IN, PRICE_OUT = 0.10, 0.50

# Free-tier daily limits are per model: when one is spent, the next takes over.
GEMINI_MODELS = ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.7-flash",
                 "gemini-3-flash-preview"]
PAID_KEY_FILE = Path.home() / ".config/musee_airfrance/gemini_key"  # wine-testing-quizz, prepaid credits
GEMINI_ENV = Path.home() / "Documents/perso/wine-quizz-testing-ag/backend/.env"

# Stop after this many failed batches in a row: past it, it is a quota or auth problem, not a bad text.
MAX_FAILURES = 6

# A request groups several texts so the instructions are paid once per batch, not once per text.
BATCH_TEXTS = 8
BATCH_CHARS = 8000

Category = Literal[
    "ouverture_ligne", "fermeture_ligne", "flotte", "premier_vol", "record", "accident_incident",
    "greve_social", "direction_nomination", "entreprise_capital", "resultats_trafic", "commercial_produit",
    "service_bord_equipage", "infrastructure_aeroport", "technique_maintenance", "guerre_crise",
    "securite_surete", "communication_culture", "environnement", "autre",
]


class Person(BaseModel):
    name: str = Field(description="Prénom Nom complet si déductible, ex. 'Jean Mermoz'")
    role: str = Field(description="Rôle dans le texte, ex. 'pilote', 'Président d'Air France'")
    kind: Literal["navigant", "dirigeant", "personnel", "politique", "personnalite", "autre"]


class Place(BaseModel):
    name: str = Field(description="Nom actuel en français, ex. 'Hô Chi Minh-Ville'")
    historical_name: Optional[str] = Field(description="Nom employé dans le texte s'il diffère, ex. 'Saïgon'")
    country: str = Field(description="Pays actuel")
    lat: float
    lon: float


class Aircraft(BaseModel):
    model: str = Field(description="Désignation normalisée la plus précise que le texte permet, ex. 'de Havilland Comet 1A'")
    family: str = Field(description="Famille, ex. 'de Havilland Comet', 'Boeing 747', 'SNCASE Languedoc'")
    manufacturer: str
    registration: Optional[str] = Field(description="Immatriculation, ex. 'F-BATV'")
    name: Optional[str] = Field(description="Nom de baptême de l'appareil")
    event: Literal["commande", "livraison", "mise_en_service", "premier_vol", "exploitation", "record", "accident", "retrait", "mention"]


class Route(BaseModel):
    cities: List[Place] = Field(description="Villes dans l'ordre de l'itinéraire, escales comprises")
    action: Literal["ouverture", "reprise", "fermeture", "suspension", "vol_essai"]
    aircraft: Optional[str] = Field(description="Famille d'avion utilisée, même libellé que aircraft.family")
    cargo: bool
    duration_hours: Optional[float] = Field(description="Durée du trajet complet si le texte la donne")
    flights_per_week: Optional[float]


class Figure(BaseModel):
    label: str = Field(description="Ce qui est mesuré, ex. 'passagers transportés', 'effectif', 'flotte', 'tarif Paris-Alger'")
    value: float
    unit: str = Field(description="ex. 'passagers', 'avions', 'km/h', 'heures', 'francs', 'euros'")
    year: Optional[int] = Field(description="Année ou exercice concerné s'il diffère de la date")


class Entry(BaseModel):
    id: int
    title: str = Field(description="Titre court, 8 mots maximum")
    summary: str = Field(description="Une phrase courte, compréhensible sans le texte")
    categories: List[Category] = Field(description="1 à 3 catégories, la principale d'abord")
    tone: Literal["positif", "negatif", "neutre"] = Field(description="Pour l'histoire de la compagnie")
    interest: int = Field(description="1 (routine administrative) à 5 (moment marquant ou anecdote étonnante pour le grand public)")
    companies: List[str] = Field(description="Compagnies citées, noms normalisés, ex. 'Air France', 'Aéropostale', 'Air Inter', 'UTA', 'KLM'")
    people: List[Person]
    places: List[Place] = Field(description="Lieux de l'événement ou cités, HORS villes déjà présentes dans routes")
    aircraft: List[Aircraft]
    routes: List[Route]
    records: List[str] = Field(description="Records ou premières, une phrase chacun, ex. 'Paris-New York en 3 h 30 par Concorde'")
    figures: List[Figure] = Field(description="Chiffres clés de la compagnie (trafic, flotte, effectifs, résultats) et prix des billets")
    casualties: Optional[int] = Field(description="Nombre de morts si le texte relate un accident ou un drame")


class Batch(BaseModel):
    items: List[Entry]


SYSTEM = """Tu structures les éphémérides historiques d'Air France (et de ses compagnies d'origine ou partenaires) pour un musée.
Tu reçois plusieurs textes numérotés [id] avec leur date. Renvoie exactement un élément par texte, avec le même id.

Règles :
- Ne mets que ce que le texte dit ou permet de déduire sans doute raisonnable ; listes vides plutôt qu'inventions.
- Avions : désignation la plus précise justifiée par le texte et l'époque (« Comet » en 1953 chez Air France = de Havilland Comet 1A). Si seul le constructeur est cité (« trois BOEING »), mets model = family = le constructeur.
- Lieux : coordonnées approximatives de la ville (ou de l'aéroport s'il est nommé), nom et pays actuels, nom d'époque dans historical_name.
- routes : seulement les lignes dont le texte annonce l'ouverture, la reprise, la fermeture, la suspension ou un vol d'essai ; pas les simples mentions.
- people : personnes nommées qui jouent un rôle dans l'événement (pas « le commandant de bord » anonyme) ; pour une liste de nominations, garde les 5 plus importantes.
- Durée et fréquence d'une ligne : dans routes, pas dans figures.
- figures : chiffres explicites sur la compagnie entière (passagers, fret, flotte, effectifs, chiffre d'affaires, résultat) ou prix d'un billet ; pas les dates, numéros de vol ni chiffres d'un accord ponctuel.
- Rédige title et summary en français."""


def chunk(entries):
    batches, current, size = [], [], 0
    for e in entries:
        if current and (len(current) >= BATCH_TEXTS or size + len(e["text"]) > BATCH_CHARS):
            batches.append(current)
            current, size = [], 0
        current.append(e)
        size += len(e["text"])
    if current:
        batches.append(current)
    return batches


def prompt(batch):
    return "\n\n".join(f"[{e['id']}] Date : {e['date']}\n{e['text']}" for e in batch)


def call_vertex(client, batch):
    response = client.messages.parse(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM,
        thinking={"type": "disabled"},
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": prompt(batch)}],
        output_format=Batch,
    )
    usage = (response.usage.input_tokens + (response.usage.cache_read_input_tokens or 0), response.usage.output_tokens)
    if response.stop_reason != "end_turn" or response.parsed_output is None:
        return None, usage
    return response.parsed_output, usage


def gemini_key():
    """(key, paid): GEMINI_API_KEY, else the paid wine-testing-quizz key, else the free key of the wine quiz backend."""
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key, False
    if PAID_KEY_FILE.exists():
        return PAID_KEY_FILE.read_text().strip(), True
    if GEMINI_ENV.exists():
        for line in GEMINI_ENV.read_text().splitlines():
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"'), False
    sys.exit(f"Pas de clé Gemini : définir GEMINI_API_KEY, ou la mettre dans {PAID_KEY_FILE} ou {GEMINI_ENV}.")


EXHAUSTED, EXHAUSTED_LOCK = set(), threading.Lock()
COOLDOWN = {}  # model -> epoch until which it is skipped after a server error


def retry_delay(response):
    """Seconds to wait before retrying a 429, from its RetryInfo detail (falls back to 30 s)."""
    for detail in response.json().get("error", {}).get("details", []):
        if detail.get("@type", "").endswith("RetryInfo"):
            return float(detail.get("retryDelay", "30s").rstrip("s")) + 1
    return 30


def call_gemini(http, batch):
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": prompt(batch)}]}],
        "generationConfig": {"responseMimeType": "application/json",
                             "responseJsonSchema": Batch.model_json_schema(),
                             "maxOutputTokens": 32000},
    }
    for _ in range(30):
        now = time.time()
        with EXHAUSTED_LOCK:
            usable = [m for m in GEMINI_MODELS if m not in EXHAUSTED]
            model = next((m for m in usable if COOLDOWN.get(m, 0) <= now), None)
            pause = min((COOLDOWN.get(m, 0) for m in usable), default=0) - now
        if not usable:
            raise RuntimeError("quota journalier épuisé sur tous les modèles Gemini")
        if model is None:  # every remaining model is cooling down after a server error
            time.sleep(max(1, min(pause, 60)))
            continue
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        try:
            response = http.post(url, json=body)
        except httpx.TransportError as err:  # timeout, connection reset: same treatment as a 5xx
            print(f"  {model} : {type(err).__name__}, pause de 2 min sur ce modèle", file=sys.stderr)
            COOLDOWN[model] = time.time() + 120
            continue
        if response.status_code >= 500:  # overloaded or unavailable: try another model, come back later
            print(f"  {model} : HTTP {response.status_code}, pause de 2 min sur ce modèle", file=sys.stderr)
            COOLDOWN[model] = time.time() + 120
            continue
        if response.status_code != 429:
            break
        message = response.json().get("error", {}).get("message", "")
        if "per day" in message:
            with EXHAUSTED_LOCK:
                EXHAUSTED.add(model)
            print(f"  {model} : quota journalier épuisé, on passe au modèle suivant", file=sys.stderr)
            continue
        print(f"  gemini 429 : {message[:300]}", file=sys.stderr)
        time.sleep(retry_delay(response))
    else:
        raise RuntimeError("Gemini indisponible après 30 tentatives")
    response.raise_for_status()
    data = response.json()
    usage = data.get("usageMetadata", {})
    tokens = (usage.get("promptTokenCount", 0), usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0))
    candidate = (data.get("candidates") or [{}])[0]
    if candidate.get("finishReason") != "STOP":
        print(f"  gemini : finishReason {candidate.get('finishReason')}", file=sys.stderr)
        return None, tokens
    try:
        return Batch.model_validate_json(candidate["content"]["parts"][0]["text"]), tokens
    except (ValidationError, KeyError):
        return None, tokens


def call_cli(batch):
    # Strip the variables of the calling Claude Code session so the child runs as a fresh, subscription-backed session.
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_CODE_") and k != "CLAUDECODE"}
    out = subprocess.run(
        ["claude", "-p", "--model", "haiku", "--effort", "low", "--tools", "", "--no-session-persistence",
         "--system-prompt", SYSTEM, "--output-format", "json",
         "--json-schema", json.dumps(Batch.model_json_schema()), prompt(batch)],
        capture_output=True, text=True, env=env, cwd="/tmp", timeout=600,
    )
    data = json.loads(out.stdout)
    usage = data.get("usage", {})
    tokens = (usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0) + usage.get("cache_read_input_tokens", 0),
              usage.get("output_tokens", 0))
    providers = {m.get("provider") for m in data.get("modelUsage", {}).values()}
    if providers - {"firstParty"}:
        sys.exit(f"Le profil Claude Code actif n'est pas l'abonnement ({providers}) : lance `csw perso`.")
    if data.get("is_error") or not data.get("structured_output"):
        print(f"  claude -p : {str(data.get('result'))[:200]}", file=sys.stderr)
        return None, tokens
    try:
        return Batch.model_validate(data["structured_output"]), tokens
    except ValidationError:
        return None, tokens


def vertex_client():
    from datetime import datetime, timedelta

    import google.auth.credentials
    from anthropic import AnthropicVertex

    class GcloudAccountCredentials(google.auth.credentials.Credentials):
        """Token of a given gcloud account, refreshed before its one-hour expiry."""

        def refresh(self, request):
            self.token = subprocess.run(["gcloud", "auth", "print-access-token", "--account", ACCOUNT],
                                        capture_output=True, text=True, check=True).stdout.strip()
            self.expiry = datetime.utcnow() + timedelta(minutes=45)

    credentials = GcloudAccountCredentials()
    try:
        credentials.refresh(None)
    except subprocess.CalledProcessError as err:
        sys.exit(f"Pas de jeton gcloud pour {ACCOUNT} : lance `gcloud auth login {ACCOUNT} --force`.\n{err.stderr}")
    return AnthropicVertex(project_id=PROJECT, region=REGION, credentials=credentials)


def load_entries():
    return [{"id": i, "date": e["field_date_value"][:10], "text": e["body_value"].strip()}
            for i, e in enumerate(json.loads(INPUT.read_text()))
            if (e.get("body_value") or "").strip() and e.get("field_date_value")]


def pick_sample(entries, size, seed=42):
    by_decade = defaultdict(list)
    for e in entries:
        by_decade[int(e["date"][:4]) // 10 * 10].append(e)
    rng = random.Random(seed)
    per_decade = max(1, size // len(by_decade))
    sample = []
    for decade in sorted(by_decade):
        sample += rng.sample(by_decade[decade], min(per_decade, len(by_decade[decade])))
    return sorted(sample[:size], key=lambda e: e["id"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=24)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--backend", choices=["gemini", "vertex", "cli"], default="gemini")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    entries = load_entries()
    todo = entries if args.all else pick_sample(entries, args.sample)
    done = set()
    if OUTPUT.exists():
        done = {json.loads(line)["id"] for line in OUTPUT.read_text().splitlines() if line.strip()}
    todo = [e for e in todo if e["id"] not in done]
    batches = chunk(todo)
    print(f"{len(entries)} textes, {len(todo)} à traiter en {len(batches)} requêtes ({len(done)} déjà faits)")

    if args.backend == "gemini":
        key, paid = gemini_key()
        if paid:  # no daily limit: the cheapest model alone, no need for the free-tier fallbacks
            GEMINI_MODELS[:] = ["gemini-3.5-flash-lite"]
        print(f"Clé Gemini {'payante (crédits prépayés)' if paid else 'gratuite'}, modèles : {', '.join(GEMINI_MODELS)}")
        http = httpx.Client(headers={"x-goog-api-key": key}, timeout=600)
        call = lambda b: call_gemini(http, b)
    elif args.backend == "vertex":
        client = vertex_client()
        call = lambda b: call_vertex(client, b)
    else:
        call = call_cli
        args.workers = min(args.workers, 3)  # the subscription quota is the bottleneck, not latency

    tokens_in = tokens_out = written = failures = 0
    stopped = False
    with OUTPUT.open("a") as out, ThreadPoolExecutor(args.workers) as pool:
        futures = {pool.submit(call, b): b for b in batches}
        for n, future in enumerate(as_completed(futures), 1):
            batch = futures[future]
            by_id = {e["id"]: e for e in batch}
            result = None
            try:
                result, usage = future.result()
                tokens_in += usage[0]
                tokens_out += usage[1]
                if result is None:
                    print(f"  lot {n}: réponse non exploitable", file=sys.stderr)
            except Exception as err:  # one failed batch must not stop a 1 300-request run; it is retried on the next run
                print(f"  lot {n}: erreur {type(err).__name__}: {str(err)[:200]}", file=sys.stderr)
            if result is None:
                failures += 1
                if failures >= MAX_FAILURES:
                    print(f"{failures} lots en échec d'affilée : arrêt, relancer plus tard pour reprendre.", file=sys.stderr)
                    for f in futures:
                        f.cancel()
                    stopped = True
                    break
                continue
            failures = 0
            for item in result.items:
                if item.id in by_id:  # ignore ids the model may have invented
                    out.write(json.dumps({"date": by_id[item.id]["date"], **item.model_dump()}, ensure_ascii=False) + "\n")
                    written += 1
            out.flush()
            print(f"  {n}/{len(batches)} lots, {written} textes écrits")

    cost = tokens_in / 1e6 * PRICE_IN + tokens_out / 1e6 * PRICE_OUT
    print(f"\nTokens : {tokens_in} entrée, {tokens_out} sortie → ~{cost:.4f} $ au prix catalogue Haiku 5.5"
          + (" (à recaler sur le tarif Gemini)" if args.backend == "gemini" else ""))
    if written:
        print(f"Extrapolation aux {len(entries)} textes : ~{cost / written * len(entries):.2f} $")
    return 1 if stopped else 0


if __name__ == "__main__":
    sys.exit(main())
