import html
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
INPUT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "ephemerides.json"
TEMPLATE = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "template.html"
OUTPUT = Path(sys.argv[3]) if len(sys.argv) > 3 else HERE / "ephemerides.html"

PLACEHOLDER = "{{BODY_TO_INSERT}}"

ENTRY = """\
<div class="title"{year_id}>
    <a name="{anchor}"></a>
    <h3>{heading}</h3>
</div>
{body}
"""

BACK_TO_TOP = """\
<div class="col-lg-12 text-right">
    <a href="#top"><span class="icon-af icon-af-A-basic-chevron-up"></span> retour haut de page</a>
</div>
"""

# Real HTML markup; a bare "<" in plain text (e.g. "<Keren Ann>") must be escaped, not parsed as a tag.
HTML_TAG = re.compile(r"</?(?:p|br|div|span|font|strong|b|i|em|u|sup|sub|a|ul|ol|li|table|tr|td|th|h[1-6])\b[^>]*>", re.I)

# Titles the heuristic cannot detect (mixed case, no separator before the body): matched literally at the start of the body.
SPECIAL_TITLES = [
    "Ligne B : EXPOSITION « A CIEL OUVERT »",
]

LEADING_TAGS = re.compile(r"\s*(?:<[^>]+>\s*)*")
# C1 control characters (\x80-\x9f) come from cp1252 text decoded as latin-1 (\x92 -> ’, \x9c -> œ).
C1_CHARS = re.compile(r"[\x80-\x9f]")
LINE_BREAK = re.compile(r"\r?\n|<br\s*/?>\s*")
CONTINUATION = (",", " DU", " DE", " DES", " ET", " LA", " LE", " LES", " AU", " AUX", " POUR", " EN", " SUR", " D'", " L'")
HONORIFIC = re.compile(r"(?:M|MM|S\.E\.M|S\.E|MME|MLLE)\b\.?")


def format_date(raw):
    return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")


def fix_cp1252(text):
    return C1_CHARS.sub(lambda m: m.group().encode("latin-1").decode("cp1252", errors="replace"), text)


def letters(text):
    return [c for c in html.unescape(text) if c.isalpha()]  # unescape: "&nbsp;" must not count as lowercase letters


def is_upper_word(token):
    return not any(c.islower() for c in html.unescape(token))


def words(text):
    return [w for w in text.split() if len(letters(w)) >= 2]


def first_line(text, start):
    line_end = min((i for i in (text.find("\n", start), text.find("<", start)) if i != -1), default=len(text))
    return text[start:line_end].rstrip(), line_end


def is_mostly_upper(line):
    chars = letters(line)
    return bool(chars) and sum(c.isupper() for c in chars) / len(chars) >= 0.7


def find_title(text):
    """Return (start, end) of the all-uppercase title at the beginning of text, or None."""
    start = LEADING_TAGS.match(text).end()
    for special in SPECIAL_TITLES:
        if text.startswith(special, start):
            return start, start + len(special)
    line, line_end = first_line(text, start)

    # Whole first line is the title (brand names such as "Air France" may be in mixed case inside it).
    if is_mostly_upper(line) and (len(words(line)) >= 2 or len(letters(line)) >= 4):
        end = start + len(line)
        # Title wrapped on the next line ("..., \nSUITE" or "... DU\n12 SEPTEMBRE").
        while line.endswith(CONTINUATION):
            br = LINE_BREAK.match(text, line_end)
            if not br:
                break
            nxt, nxt_end = first_line(text, br.end())
            if not is_mostly_upper(nxt):
                break
            line, line_end, end = nxt, nxt_end, br.end() + len(nxt)
        return start, end

    # Title followed by body text on the same line: take the leading run of uppercase tokens,
    # which must be followed by a capitalised word (a new sentence), not by a lowercase one.
    # A mixed-case word inside the title ("SkyTeam", "France", "60eme") is kept when more uppercase follows.
    if HONORIFIC.match(line):
        return None
    tokens = list(re.finditer(r"\S+", line))
    end = start
    last_token = None
    mixed_inside = False
    for i, match in enumerate(tokens):
        token = match.group()
        if is_upper_word(token):
            end = start + match.end()
            last_token = match
            continue
        following = tokens[i + 1].group() if i + 1 < len(tokens) else ""
        if last_token and not token[0].islower() and is_upper_word(following) and len(letters(following)) >= 2:
            mixed_inside = True
            continue
        if token[0].islower():
            if mixed_inside and len(words(text[start:end])) >= 4:
                break  # long title with a mixed-case word, then a lowercase subtitle: keep the whole run
            # "TITLE A compter du..." : a one-letter word (A, À) is the start of the body sentence.
            if last_token is None or len(letters(last_token.group())) != 1:
                return None
            end = start + last_token.start()
        break
    if len(words(text[start:end])) >= 3:
        return start, end
    return None


def split_title(text):
    """Return (title, remaining body). Title is '' when the body has no uppercase title."""
    span = find_title(text)
    if not span:
        return "", text
    start, end = span
    title = re.sub(r"\s+", " ", re.sub(r"<br\s*/?>|&nbsp;", " ", text[start:end])).strip().rstrip(":").strip()
    rest = text[:start] + text[end:]
    rest = re.sub(r"<p[^>]*>\s*</p>", "", rest, count=1)  # <p> that only held the title
    rest = re.sub(r"^(?:\s|<br\s*/?>|&nbsp;)+", "", rest)
    return title, rest


def format_body(text):
    # Some entries already contain HTML (<p>...): keep it rather than nesting <p> in <p>.
    if HTML_TAG.search(text):
        return text.strip()
    if not text.strip():
        return ""
    return "<p>" + html.escape(text.strip(), quote=False).replace("\r\n", "<br>\n").replace("\n", "<br>\n") + "</p>"


def slug(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"\W+", "_", text).strip("_")


def main():
    entries = json.loads(INPUT.read_text(encoding="utf-8"))
    # Most recent first (sorted() is stable, so same-day entries keep their JSON order).
    entries = sorted(entries, key=lambda e: e["field_date_value"], reverse=True)

    blocks = []
    titled = 0
    years_seen = set()
    for i, entry in enumerate(entries):
        date = format_date(entry["field_date_value"])
        raw = fix_cp1252(entry["body_value"])
        title, body = split_title(raw)
        titled += bool(title)
        title_html = title if HTML_TAG.search(raw) else html.escape(title, quote=False)  # HTML bodies are already escaped
        heading = f"{date} {title_html}".strip()
        anchor = f"{date.replace('/', '')}_{i}_{slug(title)}".rstrip("_")
        # First (most recent) entry of each year: target of the year/decade timeline on the right of the page.
        year = date[-4:]
        year_id = "" if year in years_seen else f' id="annee_{year}"'
        years_seen.add(year)
        blocks.append(ENTRY.format(year_id=year_id, anchor=anchor, heading=heading, body=format_body(body)))

    template = TEMPLATE.read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        sys.exit(f"{PLACEHOLDER} introuvable dans {TEMPLATE}")
    OUTPUT.write_text(template.replace(PLACEHOLDER, ("\n" + BACK_TO_TOP + "\n").join(blocks)), encoding="utf-8")
    print(f"{len(blocks)} éphémérides ({titled} avec titre) écrites dans {OUTPUT}")


if __name__ == "__main__":
    main()
