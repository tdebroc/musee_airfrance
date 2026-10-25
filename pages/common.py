"""Shared helpers for the page builders in pages/.

A page module (an "exhibit") defines:
  META  = {"slug": "carte-reseau", "title": "...", "description": "one sentence for the home page", "order": 1}
  build(data) -> Exhibit   its content only (see page_shell); `data` is the Data object below.
The page never decides how the site looks: the active design (design/) wraps every exhibit into a full page,
so a design can be swapped without touching the pages. Exhibits only rely on the CSS variables
--bg --card --ink --muted --line --accent --accent2 and the .card class, which every design defines.
"""
import json
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
RAW = HERE / "ephemerides.json"
ENRICHED = HERE / "enriched.jsonl"


class Data:
    """Raw texts (by id) and their enriched records (by id), loaded once."""

    def __init__(self):
        raw = json.loads(RAW.read_text())
        self.raw = {i: e for i, e in enumerate(raw) if (e.get("body_value") or "").strip() and e.get("field_date_value")}
        self.enriched = {}
        for line in ENRICHED.read_text().splitlines():
            if line.strip():
                record = json.loads(line)
                self.enriched[record["id"]] = record

    def text(self, entry_id):
        return self.raw[entry_id]["body_value"].strip()

    def records(self):
        """Enriched records sorted by date."""
        return sorted(self.enriched.values(), key=lambda r: (r["date"], r["id"]))


def embed(data):
    """JSON safe to inline in a <script> tag."""
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


@dataclass
class Exhibit:
    """The content of one page; the design adds the page around it (header, navigation, global style)."""
    title: str
    lead: str
    body: str
    head_extra: str = ""   # <script src>/<style> tags for the <head>
    script: str = ""       # inline JS, run after the body


def page_shell(title, lead, body, head_extra="", script=""):
    """Kept under this name for the page modules: returns the Exhibit, the design builds the HTML."""
    return Exhibit(title, lead, body, head_extra, script)
