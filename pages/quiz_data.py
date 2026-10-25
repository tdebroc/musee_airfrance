"""Questions du quiz, toutes tirées des éphémérides.

- carte : lieux et coordonnées (médiane des coordonnées du modèle sur toutes ses mentions) ;
- année / ordre : sélection automatique et reproductible dans enriched.jsonl ;
- estimation / devinette : questions écrites à la main, chaque réponse vérifiée dans le texte de l'éphéméride citée par son id.
"""
import html
import random
import re
import statistics
import unicodedata
from collections import Counter, defaultdict

LEVELS = ("facile", "moyen", "difficile")

YEAR = re.compile(r"(?<!\d)(1[89]\d\d|20[0-3]\d)(?!\d)")
HINT = re.compile(
    r"anniversaire|centenaire|cinquantenaire|il y a \d+ ans|\b\d+\s*ans\s+(plus tôt|après|auparavant)|\d{1,2}\.\d{1,2}\.\d{2}\b|[ée]ph[ée]m[ée]rides? n",
    re.I,
)
PLACEHOLDER = re.compile(r"\s*(date|jour et mois)( exacte)?\s+à\s+(déterminer|rechercher)\.?", re.I)


def clean(raw_html):
    """Texte brut lisible : sans balises HTML, sans mention « date à déterminer »."""
    text = re.sub(r"<br\s*/?>|</p>", "\n", raw_html)
    text = html.unescape(re.sub(r"<[^>]+>", "", text)).replace("\xa0", " ").replace("\r", "")
    text = PLACEHOLDER.sub("", text)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n", text).strip()


def fold(text):
    """Minuscules sans accents ni ponctuation, pour comparer des noms."""
    text = unicodedata.normalize("NFD", text.lower().replace("’", "'"))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


# --- Carte -----------------------------------------------------------------------------------------------------
# (nom exact dans enriched.jsonl, libellé affiché si différent)
MAP_PLACES = {
    "facile": ["New York", "Tokyo", "Rio de Janeiro", "Le Caire", "Moscou", "Sydney", "Los Angeles", "Pékin", "Mexico", "Buenos Aires"],
    "moyen": ["Dakar", "Antananarivo", "Hô Chi Minh-Ville", "Nouméa", "Papeete", "Anchorage", "Johannesburg", "Téhéran", "Lima", "Karachi"],
    "difficile": ["Niamey", "N'Djamena", "Bangui", "Port-Louis", "Ouagadougou", "Libreville", "Djibouti", "Natal", "Shannon", "Phnom Penh"],
}
MAP_LABELS = {"Hô Chi Minh-Ville": "Hô Chi Minh-Ville (Saïgon)"}
OLD_NAMES = {"Hô Chi Minh-Ville": "saigon", "Antananarivo": "tananarive", "N'Djamena": "fort lamy", "Pékin": "pekin"}


def map_questions(data):
    spots = defaultdict(list)
    opening = {}
    for rec in data.records():
        for place in rec["places"]:
            if place["lat"] is not None and place["lon"] is not None:
                spots[place["name"]].append(place)
        for route in rec["routes"]:
            if route["action"] == "ouverture":
                for city in route["cities"]:
                    names = {fold(city["name"]), OLD_NAMES.get(city["name"])}
                    if any(n and n in fold(rec["title"]) for n in names) and not re.search(r"KLM|Ryan", rec["title"]):  # the title must name the city: the model's route tags are noisy
                        opening.setdefault(city["name"], rec)  # records are sorted by date: the first one is the earliest
    questions = []
    for level, names in MAP_PLACES.items():
        for name in names:
            found = spots[name]
            country = Counter(p["country"] for p in found if p["country"]).most_common(1)[0][0]
            first = opening.get(name)
            questions.append({
                "mode": "carte", "level": level, "label": MAP_LABELS.get(name, name), "country": country,
                "lat": round(statistics.median(p["lat"] for p in found), 3),
                "lon": round(statistics.median(p["lon"] for p in found), 3),
                "fact": [first["date"], first["title"]] if first else None,
            })
    return questions


# --- Année -----------------------------------------------------------------------------------------------------
FAMOUS = re.compile(r"Concorde|Caravelle|747|Airbus|A380|TGV|Minitel|Boeing 707", re.I)
GRIM = {"accident_incident", "securite_surete", "greve_social"}  # no points to win on crashes, hijackings or strikes


def year_questions(data, per_level=7):
    rng = random.Random(2026)
    pools = {level: [] for level in LEVELS}
    for rec in data.records():
        if rec["interest"] < 4 or GRIM & set(rec["categories"]) or '"' in rec["title"]:
            continue
        text = clean(data.raw[rec["id"]]["body_value"])
        if not 90 <= len(text) <= 560 or YEAR.search(text) or YEAR.search(rec["title"]) or HINT.search(text):
            continue
        year = int(rec["date"][:4])
        level = "facile" if FAMOUS.search(text) and year >= 1955 else "moyen" if rec["interest"] == 5 and year >= 1946 else "difficile"
        pools[level].append({"mode": "annee", "level": level, "text": text, "year": year, "date": rec["date"], "title": rec["title"]})
    questions = []
    for level in LEVELS:
        pool = pools[level]
        rng.shuffle(pool)
        decades = Counter()
        for item in pool:
            decade = item["year"] // 10
            if decades[decade] < 2 and len(questions) < per_level * (LEVELS.index(level) + 1):
                decades[decade] += 1
                questions.append(item)
    return questions


# --- Ordre chronologique ---------------------------------------------------------------------------------------
MIN_GAP = {"facile": 12, "moyen": 6, "difficile": 2}
BROKEN_TITLES = set()  # titles damaged by the source's encoding (missing accents), filled after a read-through


def order_questions(data, per_level=5):
    rng = random.Random(7)
    pools = {"strong": [], "wide": []}
    for rec in data.records():
        title = rec["title"]
        if (rec["interest"] >= 4 and not GRIM & set(rec["categories"]) and 18 <= len(title) <= 80
                and not YEAR.search(title) and not HINT.search(title) and not re.search(r"\d|\"", title) and title not in BROKEN_TITLES):
            item = (int(rec["date"][:4]), rec["date"], title)
            pools["wide"].append(item)
            if rec["interest"] == 5:
                pools["strong"].append(item)
    questions, used = [], set()
    for level in LEVELS:
        pool = pools["wide" if level == "difficile" else "strong"]
        made, attempts = 0, 0
        while made < per_level and attempts < 20000:
            attempts += 1
            picks = sorted(rng.sample(pool, 4))
            years = [p[0] for p in picks]
            if (all(b - a >= MIN_GAP[level] for a, b in zip(years, years[1:])) and not used & {p[2] for p in picks}
                    and (level != "difficile" or years[-1] - years[0] <= 40)):
                used |= {p[2] for p in picks}
                questions.append({"mode": "ordre", "level": level, "items": [{"year": y, "date": d, "title": t} for y, d, t in picks]})
                made += 1
    return questions


# --- Estimation (numérique) -------------------------------------------------------------------------------------
# (id éphéméride, niveau, question, réponse, unité, décimales affichées)
NUMBERS = [
    (1720, "facile", "En 1956, Air France ouvre un troisième service hebdomadaire Paris-Tokyo en Super Constellation. Combien d'heures dure le voyage, escales comprises ?", 45, "heures"),
    (745, "facile", "Le premier vol commercial d'Air France vers la Nouvelle-Calédonie : combien de jours dure ce voyage en DC-4 ?", 6, "jours"),
    (4978, "facile", "Premier vol Paris-Tokyo « non-stop » d'Air France en Boeing 747. Combien d'heures dure-t-il dans le sens Paris-Tokyo ?", 11.67, "heures"),
    (4565, "facile", "Un commandant de bord Concorde bat le record Paris-New York. En combien de minutes (environ) ?", 210, "minutes"),
    (4710, "facile", "Le TGV Sud-Est est mis en service et fait concurrence à Air Inter. En combien de minutes met-il Lyon à Paris ?", 160, "minutes"),
    (4469, "facile", "Ouverture de Paris-Caracas en Concorde, avec escale aux Açores. Combien d'heures de voyage ?", 6, "heures"),
    (4402, "moyen", "Air France inaugure une desserte directe Fort-de-France-Paris en Boeing 747. Combien de sièges compte l'appareil ?", 435, "sièges"),
    (1979, "moyen", "Air Inter inaugure sa première ligne intérieure, Paris-Strasbourg, en DC-3. Combien de minutes dure la liaison ?", 105, "minutes"),
    (2124, "moyen", "Une Caravelle d'Air France fait un vol plané, réacteurs à l'extrême ralenti, entre Paris et Dijon. Sur combien de kilomètres ?", 265, "km"),
    (12, "moyen", "Inauguration de la ligne Toulouse-Rabat en Breguet XIV, pour Latécoère. Combien d'heures dure le trajet ?", 32, "heures"),
    (4112, "moyen", "Le premier DC-10 d'U.T.A. est mis en service sur Paris-Nouméa. Combien de passagers peut-il emporter ?", 273, "passagers"),
    (5625, "moyen", "Air France relie Paris à Tokyo sans escale en Boeing 747-400. Combien de sièges compte cet appareil ?", 371, "sièges"),
    (1169, "moyen", "Conférence de presse du président d'Air France sur les résultats de 1952 : combien de passagers la compagnie a-t-elle transportés cette année-là ?", 1075000, "passagers"),
    (440, "difficile", "Air France fait immatriculer son premier Caudron Goéland. Combien d'exemplaires de cet appareil ont été construits au total ?", 1702, "exemplaires"),
    (583, "difficile", "Le premier Douglas DC-4 d'Air France est baptisé « Ciel de Bretagne ». Combien d'exemplaires furent exploités par Air France, la TAI et l'UAT ?", 67, "exemplaires"),
    (1918, "difficile", "Un Super Starliner d'Air France décolle de Burbank pour rallier Orly sans escale. Quelle distance, en kilomètres ?", 9343, "km"),
    (377, "difficile", "Record sur la ligne Paris-Tananarive en Caudron Simoun, en deux jours et neuf heures. Quelle distance, en kilomètres ?", 8665, "km"),
    (134, "difficile", "Bossoutrot, à bord d'un Super Goliath chargé de 4 000 kg, bat sept records du monde. À quelle altitude monte-t-il, en mètres ?", 4990, "mètres"),
    (3296, "difficile", "Premier vol régulier du Jet Cargo DC-8F d'UTA, sur Paris-Abidjan-Douala-Fort Lamy. Combien de tonnes de fret emporte-t-il ?", 35, "tonnes"),
    (4854, "difficile", "Le satellite Télécom 1 voyage de Toulouse à Cayenne dans un Boeing 747 cargo d'Air France. Combien de tonnes pèse l'ensemble du matériel (250 caisses) ?", 55, "tonnes"),
]


def number_questions(data):
    questions = []
    for entry_id, level, prompt, answer, unit in NUMBERS:
        rec = data.enriched[entry_id]
        questions.append({"mode": "nombre", "level": level, "prompt": prompt, "answer": answer, "unit": unit,
                          "source": clean(data.raw[entry_id]["body_value"]), "date": rec["date"], "title": rec["title"]})
    return questions


# --- Devinette (réponse tapée) ---------------------------------------------------------------------------------
# (id éphéméride, niveau, question, réponses acceptées dont la première est affichée ; termes masqués en plus)
TEXTS = [
    (4454, "facile", "Quel avion ?", ["Concorde"]),
    (3900, "facile", "Quel avion ?", ["Boeing 747", "747", "B747"]),
    (153, "facile", "Quel aviateur ?", ["Mermoz", "Jean Mermoz"]),
    (4592, "facile", "Quel président de la République ?", ["Giscard d'Estaing", "Giscard", "Valéry Giscard d'Estaing"]),
    (3189, "facile", "Quel général ?", ["de Gaulle", "Charles de Gaulle", "Gaulle"]),
    (2937, "facile", "Quel acteur ?", ["Roger Moore", "Moore"]),
    (4710, "facile", "Quel train ?", ["TGV", "TGV Sud-Est"]),
    (5288, "facile", "Quel service ?", ["Minitel"]),
    (3741, "facile", "Quel avion ?", ["Airbus"]),
    (1720, "facile", "Quelle ville ?", ["Tokyo"]),
    (1547, "moyen", "Quel avion ?", ["Vickers Viscount", "Viscount"]),
    (2470, "moyen", "Quel avion ?", ["Boeing 707", "707", "B707"]),
    (4819, "moyen", "Quel avion ?", ["Airbus A320", "A320"]),
    (7619, "moyen", "Quel aviateur ?", ["Henri Farman", "Farman"]),
    (383, "moyen", "Quel aviateur ?", ["Howard Hughes", "Hughes"]),
    (12, "moyen", "Quel pilote ?", ["Didier Daurat", "Daurat"]),
    (231, "moyen", "Qui aurait proposé le nom « Air France » ?", ["Maurice Noguès", "Noguès", "Nogues"]),
    (827, "moyen", "Quel sommet ?", ["Annapurna"]),
    (2782, "moyen", "Quel satellite ?", ["Telstar"]),
    (4469, "moyen", "Quelle ville ?", ["Caracas"]),
    (4566, "moyen", "Quelle ville ?", ["Mexico", "Mexico City"]),
    (5365, "moyen", "Quel territoire ?", ["Nouvelle-Calédonie", "Nouméa", "Calédonie"]),
    (351, "difficile", "Quel hydravion ?", ["Latécoère 300", "Croix du Sud", "Laté 300", "Latécoère"]),
    (203, "difficile", "Quel avion ?", ["Arc en Ciel", "Couzinet 70", "Couzinet"]),
    (249, "difficile", "Quel trimoteur ?", ["Dewoitine 332", "Emeraude", "Dewoitine"]),
    (105, "difficile", "Quel avion ?", ["Farman F.60", "Goliath", "Farman F60", "F.60"]),
    (81, "difficile", "Quel avion ?", ["Spad 46", "Spad"]),
    (125, "difficile", "Quel avion ?", ["Breguet XIV", "Breguet 14", "Bréguet XIV"]),
    (4844, "difficile", "Quel avion ?", ["Airbus A310", "A310"]),
    (327, "difficile", "Quel chef pilote ?", ["Robert Bajac", "Bajac"]),
]


def _plain(text):
    """Même longueur que `text` : chaque caractère remplacé par sa lettre de base en minuscule (é → e, ’ → ')."""
    return "".join("'" if c == "’" else unicodedata.normalize("NFD", c)[0].lower() for c in text)


def mask(text, aliases):
    """Remplace chaque occurrence d'un alias (sans tenir compte de la casse, des accents, des apostrophes) par ▒▒▒."""
    plain, spans = _plain(text), []
    for alias in aliases:
        words = [re.escape(w) for w in re.split(r"[\s'’\-]+", _plain(alias)) if w]
        spans += [m.span() for m in re.finditer(r"(?<!\w)" + r"[\s'\-]*".join(words) + r"(?!\w)", plain)]
    merged = []
    for start, end in sorted(spans):  # overlapping aliases ("Boeing 747" / "747") become one block
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    for start, end in reversed(merged):  # right to left keeps earlier offsets valid
        text = text[:start] + "▒▒▒" + text[end:]
    return text


def text_questions(data):
    questions = []
    for entry_id, level, prompt, aliases in TEXTS:
        rec = data.enriched[entry_id]
        full = clean(data.raw[entry_id]["body_value"])
        questions.append({"mode": "texte", "level": level, "prompt": prompt, "masked": mask(full, aliases), "full": full,
                          "answer": aliases[0], "aliases": aliases, "date": rec["date"], "title": rec["title"]})
    return questions


def all_questions(data):
    questions = (map_questions(data) + year_questions(data) + order_questions(data)
                 + number_questions(data) + text_questions(data))
    counter = Counter()
    for q in questions:
        counter[(q["mode"], q["level"])] += 1
        q["id"] = f"{q['mode']}-{q['level']}-{counter[(q['mode'], q['level'])]}"
    return questions
