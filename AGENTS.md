# Musée Air France — contexte pour une IA

Lire ce fichier avant de toucher au projet. `STATUS.md` est la source de vérité de l'avancement (cases à cocher + journal daté) ; ce fichier-ci explique *comment* le projet marche et où sont les pièges.

En ligne : **https://tdebroc.github.io/musee_airfrance/** (GitHub Pages, publie `site/` à chaque push sur `main`, voir `.github/workflows/pages.yml`). Dépôt : https://github.com/tdebroc/musee_airfrance (public).

## But

Les 10 436 « éphémérides » Air France (un court texte daté par événement, 1908 → 2022) sont transformées en **musée virtuel statique** : un accueil en forme d'aérogare et 16 salles (visualisations D3, quiz, recherche). Tout est en français, pages autonomes, aucun backend.

## Données (à la racine)

| Fichier | Contenu |
|---|---|
| `ephemerides.json` | Source brute : liste de 10 436 `{field_date_value, body_value}`. L'**index** dans la liste = `id`. `body_value` contient du HTML (balises `<p>`, entités, parfois du bruit). Titres parfois abîmés (accents perdus). |
| `enriched.jsonl` | 1 ligne JSON par texte, produite par LLM (terminée, **ne pas modifier ni régénérer**). Champs : `date`, `id`, `title`, `summary`, `categories` (liste), `tone` (`positif`/`neutre`/`negatif`), `interest` (1–5), `companies` (liste de noms), `people` [{name, role, kind}], `places` [{name, historical_name, country, lat, lon}], `aircraft` [{model, family, manufacturer, registration, name, event}], `routes` [{cities, action, aircraft, cargo, duration_hours, flights_per_week}], `records` (liste de phrases), `figures` [{label, value, unit, year}], `casualties` (nombre ou null). |
| `routes.jsonl` | Ancienne extraction de lignes (pré-enrichissement, `extract_routes.py`). |

Catégories : commercial_produit, ouverture_ligne, entreprise_capital, flotte, communication_culture, infrastructure_aeroport, greve_social, autre, technique_maintenance, direction_nomination, service_bord_equipage, resultats_trafic, securite_surete, accident_incident, fermeture_ligne, guerre_crise, premier_vol, record, environnement.

Pièges connus des données :
- La date est celle de l'éphéméride, pas toujours celle de l'événement (rétrospectives).
- `historical_name` = nom employé dans le texte, donc bruité (aéroports, variantes d'orthographe) — ce n'est pas forcément un ancien nom.
- Fermetures de lignes rarement citées ; noms d'avions à normaliser (alias fusionnés à la main dans `pages/frise_avions.py`).
- Ne jamais inventer de données : une page qui manque de matière le dit.

## Pipeline d'enrichissement (terminé)

- `enrich.py --all --backend gemini --workers 4` → `enriched.jsonl` (reprend où il s'est arrêté). Backends `gemini` (défaut), `vertex`, `cli`.
- Clé Gemini payante : `~/.config/musee_airfrance/gemini_key` (hors dépôt). **Ne jamais l'afficher, la copier ni la committer.** Ne pas appeler d'API payante sans demande explicite.
- `monitor.py` : progression ; `supervisor.py` : relance un agent Claude tant que `STATUS.md` a des cases `[ ]`/`[~]` (refuse le profil Vertex : `csw perso` d'abord).
- Fichiers historiques à la racine (`generate_html.py`, `build_viz.py`, `ephemerides.html`, `carte_reseau.html`, `frise_avions.html`, `*_template.html`, `serve_local.py`) : première version, plus utilisée par le site.

## Construire le site

```bash
cd ~/Documents/perso/musee_airfrance
.venv/bin/python build_site.py                    # toutes les pages + accueil, design par défaut (musee)
.venv/bin/python build_site.py quiz chiffres      # seulement ces pages (slug avec tirets)
.venv/bin/python build_site.py --design sobre     # ancien habillage (barre + grille de tuiles)
cd site && python3 -m http.server 8765 --bind 127.0.0.1   # http://127.0.0.1:8765/
```

`.venv` = Python **3.9.6** (pas de guillemets du même type imbriqués dans une f-string : sortir l'expression dans une variable). Sortie dans `site/` (committée : c'est ce que publie GitHub Pages). **Après un changement de design, reconstruire toutes les pages.**

## Architecture : pages (contenu) ⟂ design (habillage)

### Contrat d'une page — `pages/<slug_avec_underscores>.py`

```python
META = {"slug": "prix-billets", "title": "...", "description": "...", "order": 11}
def build(data) -> Exhibit:          # data = pages.common.Data
    return page_shell(title, lead, body_html, head_extra="", script="js")
```

- `pages/common.py` : `Data` (`.raw` = ephemerides.json, `.enriched`, `.text(id)` = texte nettoyé, `.records()`), `embed(obj)` (JSON sûr à inliner dans `<script>`), `Exhibit(title, lead, body, head_extra, script)`, `page_shell(...)` qui renvoie un `Exhibit`.
- `build_site.discover()` ignore `common` et les modules `*_data` (ex. `pages/quiz_data.py` = banque de questions).
- Une page ne produit **que son contenu** : données inlinées, seules dépendances externes = D3 v7 et topojson `world-atlas` via jsdelivr. Elle n'utilise que les variables CSS `--bg --card --ink --muted --line --accent --accent2` et la classe `.card`. Lisible en clair et en sombre.
- Une erreur dans `build()` n'arrête pas la construction : la page est marquée en erreur dans l'accueil.
- JS : pas de fonctions globales aux noms réservés du navigateur (`top`, `name`, `status`, `parent`…) — `barometre-crises` a planté à cause d'une fonction `top()`. Préférer une IIFE.

### Contrat d'un design — `design/<nom>.py` (voir `design/__init__.py`)

```python
NAME = "..."
def render_room(exhibit, slug, pages, ctx) -> str   # HTML complet de site/<slug>.html
def render_home(pages, ctx) -> str                  # HTML complet de site/index.html
# pages = [{"meta": META, "error": None | str}], ctx = {"texts": 10436}
```

Le design définit les variables CSS et `.card`, et **ne doit pas mettre d'ancêtre avec `transform`/`filter` autour de l'exposition** (les infobulles sont en `position:fixed`).

### Design `musee` (défaut) — `design/musee.py`

- `PLAN` = disposition des salles, dans l'ordre de visite. Ajouter une page = l'ajouter à une jetée de `PLAN` ; sinon elle tombe dans la jetée `EXTRA` « E — Nouvelles acquisitions ».
  - A « Le Réseau » `#1f5fbf` : carte-reseau, monde-retrecit, villes-renommees, prix-billets
  - B « La Flotte » `#0f7f7a` : frise-avions, vie-avion, chiffres
  - C « Les Mémoires » `#b35f12` : ce-jour-la, personnages-lieux, graphe-personnes, genealogie
  - D « Les Turbulences » `#c0283a` : greves-records, barometre-crises
  - K « À bord du Concorde » `#6a4cb5` (kind `avion`) : quiz (cabine avant), devine-annee (cabine arrière)
  - H « Hall d'accueil » `#b0307a` (kind `hall`) : demande-musee (comptoir Information)
- `museum(pages)` calcule la géométrie (jetées alternées haut/bas depuis x=330 par pas de 240, aérogare à y=500, plan 1000 de haut, salles 190×80, points de passage du visiteur). `plan_svg(m, current, mini, links)` dessine le plan SVG (pistes et avions animés en SMIL, tarmac, jetées, Concorde à sa passerelle, salles = `<a>`, visiteur `#mu-me`).
- Salle : signalétique collante `header.mu-sign`, cartel `.mu-plaque` (+ bouton mini-plan `.mu-thumb`), vitrine `main.mu-vitrine` (l'exposition), portes `nav.mu-doors` (précédente / hall / suivante), tiroir plan `#mu-drawer`. Clavier : ← → salle voisine (ignoré dans input/textarea/select/contenteditable/`[role=slider]`), P = plan, Échap = fermer. Transitions `@view-transition {navigation:auto}`.
- Accueil : carte d'embarquement (salles visitées, tampons, prochaine salle), plan cliquable (le visiteur marche jusqu'à la salle en rAF, puis navigation ; repli `setTimeout(dur+400)`), tableau des départs à palettes.
- Toutes les classes du thème sont préfixées `mu-` pour ne pas entrer en collision avec le CSS des expositions.
- `localStorage` : `musee-af-visites` (salles visitées), `musee-af-quiz-classement` (classement du quiz). Tout reste local au navigateur.

### Quiz — `pages/quiz.py` + `pages/quiz_data.py`

116 questions (30 carte, 21 année, 20 nombre, 15 ordre, 30 texte), 3 niveaux. Une partie = 5 questions, une par mode (carte cliquable, frise d'années, estimation, chronologie, devinette). Points = 5000 × précision × (1 − 0,5·t/T). Classement local avec export/import JSON.

## Tester

- Syntaxe JS d'une page : extraire les `<script>` et `node --check` (node v20 dispo).
- Navigateur sans tête : `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --virtual-time-budget=8000 --enable-logging=stderr --dump-dom http://127.0.0.1:8765/<slug>.html` (erreurs JS dans stderr) ; `--screenshot=x.png --window-size=1400,1000` ; `--blink-settings=preferredColorScheme=1` = mode clair. Largeur mini ~500 px. `requestAnimationFrame` ne tourne pas en temps virtuel (d'où le repli `setTimeout`).
- Avant de cocher une tâche : la page se construit, pas d'erreur JS, le fichier est dans `site/`, la logique a été vérifiée sur les vraies données.

## Conventions

- Tout texte affiché est en français avec les accents corrects.
- Mettre à jour `STATUS.md` (case + ligne datée dans le Journal : fait, reste, pièges).
- Ne pas modifier `enriched.jsonl` ; ne jamais exposer la clé Gemini.
- `scratch/` (ignoré par git) : brouillons et sauvegarde de l'ancien design (`scratch/backup-design-v1/`).
- Publication : committer `site/` reconstruit et pousser sur `main` → GitHub Actions déploie Pages en ~1 min.
