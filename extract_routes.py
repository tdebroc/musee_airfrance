"""Extract opened routes (cities + coordinates + aircraft) from the ephemerides with Claude on Vertex AI.

Usage:
  .venv/bin/python extract_routes.py               # sample mode: ~80 texts spread across decades
  .venv/bin/python extract_routes.py --sample 200
  .venv/bin/python extract_routes.py --strict      # sample among texts starting with "Ouverture de la ligne..."
  .venv/bin/python extract_routes.py --all         # every text that looks like a route opening
  .venv/bin/python extract_routes.py --model claude-haiku-5-5

Results are appended to routes.jsonl, so an interrupted run resumes where it stopped.
"""
import argparse
import json
import random
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional

import anthropic
from anthropic import AnthropicVertex
from pydantic import BaseModel, ValidationError

HERE = Path(__file__).parent
INPUT = HERE / "ephemerides.json"
OUTPUT = HERE / "routes.jsonl"

PROJECT = "ke-data-catalog-dev"
REGION = "global"
# Only Opus 5.5 is enabled on ke-data-catalog-dev; Haiku 5.5 would be ~40x cheaper once enabled.
DEFAULT_MODEL = "claude-opus-5-5"

# Texts that start by announcing an opening: far denser in routes than ROUTE_HINT matches.
STRICT_HINT = re.compile(r"^(Ouverture|Inauguration) (de la |des |d.une )?(ligne|liaison|escale)|^Ouverture (en|par|d)", re.I)
ROUTE_HINT = re.compile(r"ouverture|inaugur|nouvelle (ligne|liaison|escale)|dessert|desserte|liaison|ligne", re.I)

# List prices per million tokens (Anthropic); Vertex billing may differ slightly.
PRICES = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.0, 10.0), "claude-opus-5-5": (4.0, 20.0)}

SYSTEM = """Tu analyses des éphémérides de l'histoire d'Air France (et de ses compagnies d'origine/partenaires).
Pour chaque texte, extrais les lignes aériennes OUVERTES ou INAUGURÉES (pas celles simplement citées, fermées ou suspendues).
Chaque ligne est une suite de villes dans l'ordre de l'itinéraire (escales comprises), avec des coordonnées géographiques approximatives de l'aéroport ou de la ville.
Si le texte n'annonce aucune ouverture de ligne, renvoie routes = [].
title : un titre court (max 8 mots) qui résume l'événement.

Réponds UNIQUEMENT avec un objet JSON (sans texte autour) de la forme :
{"title": "...", "routes": [{"cities": [{"name": "Paris", "country": "France", "lat": 49.0, "lon": 2.55}, ...], "aircraft": "Boeing 747" ou null, "cargo": false}]}"""

JSON_BLOCK = re.compile(r"\{.*\}", re.S)


class City(BaseModel):
    name: str
    country: str
    lat: float
    lon: float


class Route(BaseModel):
    cities: List[City]
    aircraft: Optional[str]
    cargo: bool


class Extraction(BaseModel):
    title: str
    routes: List[Route]


def pick_sample(entries, size, seed=42):
    by_decade = defaultdict(list)
    for e in entries:
        by_decade[int(e["date"][:4]) // 10 * 10].append(e)
    rng = random.Random(seed)
    per_decade = max(1, size // len(by_decade))
    sample = []
    for decade in sorted(by_decade):
        pool = by_decade[decade]
        sample += rng.sample(pool, min(per_decade, len(pool)))
    return sample[:size]


def load_entries(strict=False):
    hint = STRICT_HINT if strict else ROUTE_HINT
    entries = []
    for i, e in enumerate(json.loads(INPUT.read_text())):
        body = e["body_value"].strip()
        # Long texts are press releases, rarely route openings; they also cost the most.
        if hint.search(body) and len(body) < 3000:
            entries.append({"id": i, "date": e["field_date_value"][:10], "text": body})
    return entries


def extract(client, model, entry):
    # The Kering org policy forbids Vertex structured outputs, so the JSON is asked in the prompt and validated here.
    usage_in = usage_out = 0
    for _ in range(2):
        response = client.messages.create(
            model=model,
            max_tokens=4000,
            system=SYSTEM,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": f"Date : {entry['date']}\n\n{entry['text']}"}],
        )
        usage_in += response.usage.input_tokens
        usage_out += response.usage.output_tokens
        if response.stop_reason == "refusal":
            break
        text = "".join(b.text for b in response.content if b.type == "text")
        match = JSON_BLOCK.search(text)
        try:
            return Extraction.model_validate_json(match.group(0) if match else text), (usage_in, usage_out)
        except ValidationError:
            continue
    return None, (usage_in, usage_out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=80)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--strict", action="store_true", help="only texts that start with an opening announcement")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--model", default=DEFAULT_MODEL, choices=sorted(PRICES))
    args = parser.parse_args()

    entries = load_entries(args.strict)
    todo = entries if args.all else pick_sample(entries, args.sample)
    done = set()
    if OUTPUT.exists():
        done = {json.loads(line)["id"] for line in OUTPUT.read_text().splitlines() if line.strip()}
    todo = [e for e in todo if e["id"] not in done]
    print(f"{len(entries)} textes candidats, {len(todo)} à traiter ({len(done)} déjà faits)")

    client = AnthropicVertex(project_id=PROJECT, region=REGION)
    tokens_in = tokens_out = 0
    with OUTPUT.open("a") as out, ThreadPoolExecutor(args.workers) as pool:
        futures = {pool.submit(extract, client, args.model, e): e for e in todo}
        for n, future in enumerate(as_completed(futures), 1):
            entry = futures[future]
            try:
                result, usage = future.result()
            except anthropic.APIStatusError as err:
                print(f"  [{entry['id']}] erreur API {err.status_code}: {str(err.message)[:200]}", file=sys.stderr)
                continue
            except anthropic.APIConnectionError as err:
                print(f"  [{entry['id']}] erreur réseau: {err}", file=sys.stderr)
                continue
            tokens_in += usage[0]
            tokens_out += usage[1]
            if result is None:
                print(f"  [{entry['id']}] réponse non exploitable", file=sys.stderr)
                continue
            record = {**entry, **result.model_dump()}
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            out.flush()
            print(f"  {n}/{len(todo)} {entry['date']} {result.title} — {len(result.routes)} ligne(s)")

    price_in, price_out = PRICES[args.model]
    cost = tokens_in / 1e6 * price_in + tokens_out / 1e6 * price_out
    print(f"\nTokens : {tokens_in} entrée, {tokens_out} sortie → ~{cost:.4f} $ (prix catalogue {args.model})")
    if todo:
        print(f"Extrapolation sur les {len(entries)} textes candidats : ~{cost / len(todo) * len(entries):.2f} $")


if __name__ == "__main__":
    main()
