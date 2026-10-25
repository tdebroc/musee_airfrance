"""Build the two visualisation pages from the ephemerides.

  carte_reseau.html  animated network map, from routes.jsonl (see extract_routes.py)
  frise_avions.html  aircraft timeline, keyword matching on every text of ephemerides.json

Usage: python3 build_viz.py
"""
import json
import re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
EPHEMERIDES = HERE / "ephemerides.json"
ROUTES = HERE / "routes.jsonl"
PLACEHOLDER = "/*__DATA__*/null"

# Ordered roughly by entry into service; a text can mention several aircraft.
AIRCRAFT = [
    ("Breguet 14", r"Br[ée]guet (XIV|14)\b"),
    ("Farman Goliath", r"Goliath"),
    ("Latécoère", r"Lat[ée]co[eè]re"),
    ("Dewoitine D.338", r"Dewoitine"),
    ("Bloch 220", r"Bloch 220"),
    ("Douglas DC-3", r"\bDC[- ]?3\b|Dakota"),
    ("Douglas DC-4", r"\bDC[- ]?4\b"),
    ("Douglas DC-6", r"\bDC[- ]?6\b"),
    ("Lockheed Constellation", r"Constellation|\bL[- ]?(049|749|1049)\b|Lockheed 1049"),
    ("Breguet Deux-Ponts", r"Deux[- ]Ponts|Br[ée]guet 76[345]"),
    ("Lockheed Starliner", r"Starliner|\bL[- ]?1649\b"),
    ("Vickers Viscount", r"Viscount"),
    ("Caravelle", r"Caravelle"),
    ("Boeing 707", r"\b(Boeing |B[- ]?)707"),
    ("Douglas DC-8", r"\bDC[- ]?8\b"),
    ("Fokker", r"Fokker"),
    ("Boeing 727", r"\b(Boeing |B[- ]?)727"),
    ("Boeing 747", r"\b(Boeing |B[- ]?)747|Jumbo"),
    ("Airbus A300", r"\bA[- ]?300(?!\d)"),
    ("Concorde", r"(?<!place de la )Concorde"),
    ("Douglas DC-10", r"\bDC[- ]?10\b"),
    ("Boeing 737", r"\b(Boeing |B[- ]?)737"),
    ("Airbus A310", r"\bA[- ]?310(?!\d)"),
    ("Airbus A320 (famille)", r"\bA[- ]?3(18|19|20|21)(?!\d)"),
    ("Airbus A340", r"\bA[- ]?340(?!\d)"),
    ("Airbus A330", r"\bA[- ]?330(?!\d)"),
    ("Boeing 777", r"\b(Boeing |B[- ]?)777"),
    ("Airbus A380", r"\bA[- ]?380(?!\d)"),
    ("Boeing 787", r"\b(Boeing |B[- ]?)787"),
    ("Airbus A350", r"\bA[- ]?350(?!\d)"),
    ("Airbus A220", r"\bA[- ]?220(?!\d)"),
]


def excerpt(text, size=220):
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= size else text[:size].rsplit(" ", 1)[0] + "…"


def frise_data(entries):
    patterns = [(name, re.compile(rx, re.I)) for name, rx in AIRCRAFT]
    events = defaultdict(list)
    for e in entries:
        text = e["body_value"]
        for name, rx in patterns:
            if rx.search(text):
                events[name].append({"d": e["field_date_value"][:10], "t": excerpt(text)})
    lanes = []
    for name, _ in AIRCRAFT:
        evts = sorted(events[name], key=lambda x: x["d"])
        if len(evts) >= 3:  # below that it is noise, not a fleet history
            lanes.append({"name": name, "events": evts})
    years = [int(e["field_date_value"][:4]) for e in entries]
    return {"lanes": lanes, "minYear": min(years), "maxYear": max(years)}


def carte_data():
    records = [json.loads(line) for line in ROUTES.read_text().splitlines() if line.strip()]
    routes = []
    for r in records:
        for route in r["routes"]:
            cities = [c for c in route["cities"] if -90 <= c["lat"] <= 90 and -180 <= c["lon"] <= 180]
            if len(cities) < 2:
                continue
            routes.append({
                "date": r["date"],
                "year": int(r["date"][:4]),
                "title": r["title"],
                "text": excerpt(r["text"], 400),
                "aircraft": route["aircraft"],
                "cargo": route["cargo"],
                "cities": [{"name": c["name"], "lat": c["lat"], "lon": c["lon"]} for c in cities],
            })
    routes.sort(key=lambda x: x["date"])
    return {"routes": routes, "analysed": len(records), "withRoutes": sum(1 for r in records if r["routes"])}


def render(template, data, output):
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = (HERE / template).read_text()
    assert PLACEHOLDER in html, f"{template} has no {PLACEHOLDER}"
    (HERE / output).write_text(html.replace(PLACEHOLDER, payload))
    print(f"{output} écrit")


def main():
    entries = json.loads(EPHEMERIDES.read_text())
    entries = [e for e in entries if e.get("body_value") and e.get("field_date_value")]
    data = carte_data()
    data["totalTexts"] = len(entries)
    render("carte_template.html", data, "carte_reseau.html")
    render("frise_template.html", frise_data(entries), "frise_avions.html")


if __name__ == "__main__":
    main()
