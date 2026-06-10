from __future__ import annotations

import html
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROFILES_PATH = ROOT / "internship_profiles.json"
OUT_HTML = ROOT / "senior_internship_finder.html"
OUT_MD = ROOT / "internship_profiles_copyable.md"


WEB_ENRICHMENT = {
    "Fred Hutchinson Cancer Center": {
        "url": "https://www.fredhutch.org/en/about.html",
        "label": "Fred Hutch About",
        "note": "Major Seattle cancer research and care center. Its official site describes 50 years of research and care, global research reach, 6000+ employees, and three Nobel Prize winners associated with Fred Hutch researchers.",
        "verified": True,
    },
    "UW Elementary Particle Experiment Group": {
        "url": "https://phys.washington.edu/people/shih-chieh-hsu",
        "label": "UW Physics: Shih-Chieh Hsu",
        "note": "Professor Shih-Chieh Hsu is a UW Physics professor in nuclear and particle experiment whose biography includes ATLAS/LHC work, electroweak leadership, and physics-plus-machine-learning courses.",
        "verified": True,
    },
    "University of Washington": {
        "url": "https://www.washington.edu/",
        "label": "University of Washington",
        "note": "Large public research university. Treat broad UW listings as lab-specific: the mentor and department matter more than the umbrella name.",
        "verified": True,
    },
    "UW Medicine": {
        "url": "https://www.uwmedicine.org/",
        "label": "UW Medicine",
        "note": "Academic medical system connected to University of Washington research and clinical departments. Strong fit when the catalog entry has a named lab or faculty mentor.",
        "verified": True,
    },
    "Institute for Systems Biology": {
        "url": "https://isbscience.org/",
        "label": "Institute for Systems Biology",
        "note": "Seattle-based interdisciplinary research institute. Its official site emphasizes molecular biology, genetics, software engineering, microbial ecology, and systems approaches to health.",
        "verified": True,
    },
    "Seattle Children's Research Institute": {
        "url": "https://www.seattlechildrens.org/research/",
        "label": "Seattle Children's Research",
        "note": "Pediatric research institute with internationally recognized work in cancer therapies, genetics, neuroscience, immunology, infectious disease, and bioethics.",
        "verified": True,
    },
    "City of Bellevue Transportation Department": {
        "url": "https://bellevuewa.gov/city-government/departments/transportation",
        "label": "Bellevue Transportation",
        "note": "City department whose official page says it plans, designs, builds, operates, and maintains Bellevue's transportation system. Good for civil engineering, urban planning, public sector, GIS, and policy interests.",
        "verified": True,
    },
    "Kirkland Arts Center": {
        "url": "https://kirklandartscenter.org/",
        "label": "Kirkland Arts Center",
        "note": "Community arts nonprofit in Kirkland with classes, gallery work, events, open studios, and a mission around quality arts experiences and community connection.",
        "verified": True,
    },
    "The Vera Project": {
        "url": "https://theveraproject.org/",
        "label": "The Vera Project",
        "note": "All-ages Seattle nonprofit music and arts space with venue, screen print shop, recording studio, art gallery, and youth-driven programming.",
        "verified": True,
    },
    "World Affairs Council": {
        "url": "https://www.world-affairs.org/",
        "label": "World Affairs Council",
        "note": "Nonpartisan Seattle nonprofit founded in 1951 that hosts programs around global understanding, civic dialogue, and international relationships.",
        "verified": True,
    },
    "Seattle Litigation Group": {
        "url": "https://www.seattlelitigation.com/",
        "label": "Seattle Litigation Group",
        "note": "Seattle law firm focused on employment rights, civil litigation, professional license defense, and school mistreatment/injury. Good for students considering law or public-interest advocacy.",
        "verified": True,
    },
    "Bellevue Arts Museum": {
        "url": "https://www.bellevuearts.org/",
        "label": "Bellevue Arts Museum",
        "note": "Bellevue arts institution founded by volunteers in 1975 from the historic Pacific Northwest Arts & Crafts Fair; current site emphasizes Bellevue Arts Fair Weekend and community arts programming.",
        "verified": True,
    },
}


THEMES = [
    ("CS / AI / Data", ["computer", "software", "data", "machine learning", " ai ", "coding", "web", "python", "react", "cyber"]),
    ("Biomedical / Health", ["medical", "medicine", "health", "bio", "cancer", "clinical", "hospital", "neuro", "psych", "lab"]),
    ("Research", ["research", "study", "scientific", "experiment", "paper", "analysis", "publication"]),
    ("Engineering / Physics", ["engineering", "physics", "aerospace", "mechanical", "electrical", "particle", "transportation", "construction"]),
    ("Business / Marketing", ["business", "finance", "marketing", "operations", "real estate", "sales", "social media"]),
    ("Government / Law", ["government", "law", "legal", "policy", "public sector", "litigation", "city of"]),
    ("Arts / Media / Music", ["art", "design", "music", "media", "video", "gallery", "museum", "creative"]),
    ("Education / TA", ["school", "teaching", "teacher", "ta", "education", "classroom"]),
    ("Nonprofit / Community", ["non-profit", "nonprofit", "community", "volunteer", "council"]),
    ("Environment", ["environment", "sustainability", "climate", "ecology", "waste", "energy"]),
]


def clean(value: object) -> str:
    text = str(value or "")
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace(" LIW ", " UW ").replace(" IOW ", " UW ")
    return text


def short(value: object, limit: int = 360) -> str:
    text = clean(value)
    text = re.sub(r"(?i)\b(internship description|unique experiences|what surprised.*?|my greatest takeaways.*?)\s*:?", "", text)
    text = text.strip(" -:")
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut + "..."


def first_sentences(values: list[str], limit: int = 520) -> str:
    pieces: list[str] = []
    seen = set()
    for value in values:
        value = clean(value)
        for sentence in re.split(r"(?<=[.!?])\s+", value):
            sentence = short(sentence, 220)
            low = sentence.lower()
            if len(sentence) < 35 or low in seen:
                continue
            if any(bad in low for bad in ["what surprised", "mentor's", "category:", "company:"]):
                continue
            seen.add(low)
            pieces.append(sentence)
            if len(" ".join(pieces)) > limit:
                return " ".join(pieces)[:limit].rsplit(" ", 1)[0] + "..."
    return " ".join(pieces)[:limit]


def theme_for(profile: dict) -> list[str]:
    text = " ".join(
        [
            clean(profile.get("organization")),
            " ".join(clean(c) for c in profile.get("categories", [])),
            " ".join(clean(r.get("description")) for r in profile.get("records", [])[:8]),
        ]
    ).lower()
    scored = []
    padded = f" {text} "
    for label, words in THEMES:
        score = 0
        for word in words:
            token = word.strip()
            if not token:
                continue
            if " " in token:
                score += padded.count(token) * 2
            else:
                score += len(re.findall(rf"\b{re.escape(token)}\b", padded))
        if score:
            scored.append((score, label))
    scored.sort(reverse=True)
    return [label for _, label in scored[:3]] or ["Other"]


def location_group(locations: list[str]) -> str:
    text = " ".join(clean(location) for location in locations).lower()
    if "remote" in text or "online" in text or "virtual" in text:
        if any(place in text for place in ["seattle", "bellevue", "kirkland", "redmond", "uw"]):
            return "Hybrid / flexible"
        return "Remote"
    if any(place in text for place in ["bellevue", "redmond", "kirkland", "issaquah", "bothell"]):
        return "Eastside"
    if any(place in text for place in ["seattle", "uw", "south lake union"]):
        return "Seattle"
    return "Unclear"


def signal_tags(profile: dict) -> list[str]:
    tags = []
    if profile.get("student_count", 0) >= 5:
        tags.append("repeat placement")
    if any("2026" == year or "2025" == year for year in profile.get("years", [])):
        tags.append("recent")
    if profile.get("mentors"):
        if any(clean(m.get("email")) for m in profile["mentors"]):
            tags.append("direct email")
    if profile["organization"] in WEB_ENRICHMENT:
        tags.append("web-checked")
    if any(".edu" in clean(m.get("email")).lower() for m in profile.get("mentors", [])):
        tags.append("academic mentor")
    if any(r.get("ocr_recovered") for r in profile.get("records", [])):
        tags.append("OCR recovered")
    return tags


def contact_list(profile: dict) -> list[dict[str, str]]:
    contacts = []
    seen = set()
    records = sorted(profile.get("records", []), key=lambda row: clean(row.get("year")), reverse=True)
    for record in records:
        name = clean(record.get("mentor_name"))
        email = clean(record.get("mentor_email"))
        if not email or "@" not in email or len(email) > 80:
            continue
        if email.lower().startswith("s-"):
            continue
        if len(name) > 70:
            name = ""
        key = (name.lower(), email.lower())
        if key in seen:
            continue
        seen.add(key)
        contacts.append({"name": name, "email": email})
    return contacts[:8]


def student_list(profile: dict) -> list[dict[str, str]]:
    students = []
    seen = set()
    for student in sorted(profile.get("students", []), key=lambda row: clean(row.get("year")), reverse=True):
        name = clean(student.get("name"))
        year = clean(student.get("year"))
        if not name:
            continue
        key = (name.lower(), year)
        if key in seen:
            continue
        seen.add(key)
        students.append(
            {
                "name": name,
                "year": year,
                "category": clean(student.get("category")),
                "source": clean(student.get("source")),
                "page": clean(student.get("page")),
            }
        )
    return students


def build_cards(raw_profiles: list[dict]) -> list[dict]:
    cards = []
    for profile in raw_profiles:
        records = sorted(profile.get("records", []), key=lambda row: clean(row.get("year")), reverse=True)
        profile = {**profile, "records": records}
        descriptions = [clean(r.get("description")) for r in records if clean(r.get("description"))]
        uniques = [clean(r.get("unique_experiences")) for r in records if clean(r.get("unique_experiences"))]
        contacts = contact_list(profile)
        students = student_list(profile)
        themes = theme_for(profile)
        locations = [clean(location) for location in profile.get("locations", []) if clean(location)]
        enrichment = WEB_ENRICHMENT.get(profile["organization"], {})
        years = sorted(profile.get("years", []), reverse=True)
        tags = signal_tags(profile)
        fit_score = int(profile.get("score", 0))
        fit_score += min(10, max(0, profile.get("student_count", 0) - 1))
        if enrichment:
            fit_score += 8
        if contacts:
            fit_score += 6
        if any(year in {"2026", "2025"} for year in years):
            fit_score += 5
        fit_score = min(100, fit_score)
        cards.append(
            {
                "organization": clean(profile.get("organization")),
                "themes": themes,
                "categories": [clean(c) for c in profile.get("categories", [])[:8] if clean(c)],
                "locations": locations[:6],
                "locationGroup": location_group(locations),
                "years": years,
                "studentCount": profile.get("student_count", 0),
                "fitScore": fit_score,
                "catalogScore": profile.get("score", 0),
                "tags": tags,
                "contacts": contacts,
                "students": students,
                "summary": first_sentences(descriptions, 520) or "Catalog entry has limited description text; check the source PDF pages listed under past students.",
                "activities": first_sentences(uniques, 420),
                "web": enrichment,
                "ocrRecovered": any(r.get("ocr_recovered") for r in profile.get("records", [])),
                "searchText": "",
            }
        )
    for card in cards:
        card["searchText"] = " ".join(
            [
                card["organization"],
                " ".join(card["themes"]),
                " ".join(card["categories"]),
                " ".join(card["locations"]),
                " ".join(card["years"]),
                " ".join(tag for tag in card["tags"]),
                " ".join(contact["name"] + " " + contact["email"] for contact in card["contacts"]),
                " ".join(student["name"] for student in card["students"]),
                card["summary"],
                card["activities"],
                clean(card.get("web", {}).get("note")),
            ]
        ).lower()
    cards.sort(key=lambda item: (-item["fitScore"], -item["studentCount"], item["organization"].lower()))
    return cards


def build_markdown(cards: list[dict]) -> str:
    lines = [
        "# Senior Internship Profiles",
        "",
        "Generated from the 2021-2026 internship/job fair catalogs. OCR-recovered entries came from scanned PDFs; verify those fields against the original PDF before emailing.",
        "",
        f"Total profiles: {len(cards)}",
        f"Total past student placements represented: {sum(card['studentCount'] for card in cards)}",
        "",
        "## Quick Shortlist",
        "",
    ]
    for card in cards[:25]:
        contact = card["contacts"][0]["email"] if card["contacts"] else "no direct email found"
        lines.append(f"- {card['organization']} — {card['fitScore']}/100, {card['studentCount']} past placement(s), contact: {contact}")
    lines.extend(["", "## All Profiles", ""])
    for card in cards:
        lines.append(f"## {card['organization']}")
        lines.append("")
        lines.append(f"Fit score: {card['fitScore']}/100")
        lines.append(f"Best for: {', '.join(card['themes'])}")
        lines.append(f"Categories in catalogs: {', '.join(card['categories']) or 'unclear'}")
        lines.append(f"Location: {', '.join(card['locations']) or card['locationGroup']}")
        lines.append(f"Catalog years: {', '.join(card['years'])}")
        lines.append(f"Signals: {', '.join(card['tags']) or 'none'}")
        if card["contacts"]:
            lines.append("Contacts:")
            for contact in card["contacts"]:
                label = f"{contact['name']} — " if contact["name"] else ""
                lines.append(f"- {label}{contact['email']}")
        else:
            lines.append("Contacts: no direct mentor email found in parsed text")
        lines.append("")
        lines.append("What interns did:")
        lines.append(card["summary"])
        if card["activities"]:
            lines.append("")
            lines.append("Notable activities / experiences:")
            lines.append(card["activities"])
        if card.get("web"):
            lines.append("")
            lines.append("External research note:")
            lines.append(f"{card['web']['note']} ({card['web']['url']})")
        lines.append("")
        lines.append("People who went here before:")
        for student in card["students"]:
            source = f"{student['source']}"
            if student["page"]:
                source += f", page {student['page']}"
            lines.append(f"- {student['name']} ({student['year']}) — {student['category']} [{source}]")
        lines.append("")
        if card["ocrRecovered"]:
            lines.append("Note: Some data for this profile was recovered by OCR from scanned catalog pages; verify before sending.")
            lines.append("")
    return "\n".join(lines).strip() + "\n"


def build_html(cards: list[dict]) -> str:
    data_json = json.dumps(cards, ensure_ascii=False).replace("<", "\\u003c")
    themes = sorted({theme for card in cards for theme in card["themes"]})
    years = sorted({year for card in cards for year in card["years"]}, reverse=True)
    theme_options = "\n".join(f'<option value="{html.escape(theme)}">{html.escape(theme)}</option>' for theme in themes)
    year_options = "\n".join(f'<option value="{html.escape(year)}">{html.escape(year)}</option>' for year in years)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Senior Internship Finder</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #17212b;
      --muted: #607080;
      --line: #d8e0e8;
      --surface: #f6f8f8;
      --panel: #ffffff;
      --blue: #2456a6;
      --teal: #087f8c;
      --gold: #a66a00;
      --rose: #b33d4f;
      --green: #2d7043;
      --shadow: 0 8px 26px rgba(23, 33, 43, .08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--surface);
    }}
    header {{
      background: #fff;
      border-bottom: 1px solid var(--line);
      position: sticky;
      top: 0;
      z-index: 5;
    }}
    .wrap {{ max-width: 1180px; margin: 0 auto; padding: 18px; }}
    .topline {{ display: flex; align-items: end; justify-content: space-between; gap: 18px; flex-wrap: wrap; }}
    h1 {{ margin: 0; font-size: 24px; line-height: 1.1; letter-spacing: 0; }}
    .subtitle {{ margin-top: 6px; color: var(--muted); font-size: 13px; }}
    .stats {{ display: flex; gap: 10px; flex-wrap: wrap; }}
    .stat {{ border: 1px solid var(--line); background: #fbfcfc; border-radius: 8px; padding: 8px 10px; min-width: 92px; }}
    .stat strong {{ display: block; font-size: 18px; }}
    .stat span {{ color: var(--muted); font-size: 12px; }}
    .controls {{ display: grid; grid-template-columns: 2fr repeat(4, minmax(130px, 1fr)); gap: 10px; margin-top: 16px; }}
    input, select, button {{
      font: inherit;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      color: var(--ink);
      min-height: 40px;
    }}
    input, select {{ padding: 0 11px; width: 100%; }}
    button {{ padding: 0 12px; cursor: pointer; }}
    button.primary {{ background: var(--blue); border-color: var(--blue); color: #fff; }}
    button.ghost {{ background: #fff; }}
    .chips {{ display: flex; gap: 8px; overflow-x: auto; padding: 12px 0 2px; }}
    .chip {{ white-space: nowrap; border: 1px solid var(--line); background: #fff; border-radius: 999px; padding: 7px 11px; font-size: 13px; cursor: pointer; }}
    .chip.active {{ border-color: var(--teal); color: var(--teal); background: #eaf7f8; }}
    main .wrap {{ display: grid; grid-template-columns: 260px 1fr; gap: 18px; align-items: start; }}
    aside {{ position: sticky; top: 139px; border: 1px solid var(--line); background: #fff; border-radius: 8px; padding: 14px; box-shadow: var(--shadow); }}
    aside h2 {{ font-size: 14px; margin: 0 0 10px; }}
    .saved-list {{ display: grid; gap: 8px; }}
    .saved-item {{ border: 1px solid var(--line); border-radius: 8px; padding: 8px; background: #fbfcfc; font-size: 13px; }}
    .saved-item a {{ color: var(--blue); text-decoration: none; }}
    .resultbar {{ display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 10px; color: var(--muted); font-size: 13px; }}
    .grid {{ display: grid; gap: 12px; }}
    .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; box-shadow: var(--shadow); padding: 16px; }}
    .card-head {{ display: grid; grid-template-columns: 1fr auto; gap: 12px; }}
    .org {{ font-size: 20px; font-weight: 750; margin: 0; }}
    .score {{ width: 58px; height: 58px; border-radius: 8px; display: grid; place-items: center; background: #eef5ff; color: var(--blue); font-weight: 800; }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 7px; margin: 10px 0; }}
    .pill {{ font-size: 12px; line-height: 1; border-radius: 999px; padding: 6px 8px; background: #f1f4f6; color: #33404c; }}
    .pill.theme {{ background: #e8f4f5; color: var(--teal); }}
    .pill.warn {{ background: #fff5de; color: var(--gold); }}
    .pill.good {{ background: #eaf6ef; color: var(--green); }}
    .summary {{ margin: 10px 0 12px; color: #293540; line-height: 1.45; }}
    .row {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 10px; }}
    .mini {{ color: var(--muted); font-size: 13px; }}
    .contact {{ display: inline-flex; align-items: center; gap: 6px; border: 1px solid var(--line); border-radius: 8px; padding: 7px 9px; color: var(--blue); text-decoration: none; background: #fff; font-size: 13px; }}
    details {{ margin-top: 12px; border-top: 1px solid var(--line); padding-top: 10px; }}
    summary {{ cursor: pointer; font-weight: 700; }}
    .detail-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 12px; }}
    .detail-grid h3 {{ font-size: 13px; margin: 0 0 6px; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }}
    ul {{ margin: 0; padding-left: 18px; }}
    li {{ margin: 4px 0; }}
    .source-link {{ color: var(--blue); text-decoration: none; }}
    .empty {{ border: 1px dashed var(--line); border-radius: 8px; padding: 28px; text-align: center; color: var(--muted); background: #fff; }}
    .toast {{ position: fixed; right: 16px; bottom: 16px; background: var(--ink); color: #fff; border-radius: 8px; padding: 10px 12px; opacity: 0; transform: translateY(8px); transition: .18s ease; pointer-events: none; }}
    .toast.show {{ opacity: 1; transform: translateY(0); }}
    @media (max-width: 900px) {{
      .controls {{ grid-template-columns: 1fr 1fr; }}
      main .wrap {{ grid-template-columns: 1fr; }}
      aside {{ position: static; }}
    }}
    @media (max-width: 620px) {{
      .wrap {{ padding: 14px; }}
      .controls {{ grid-template-columns: 1fr; }}
      .card-head {{ grid-template-columns: 1fr; }}
      .score {{ width: auto; height: 42px; }}
      .detail-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="wrap">
      <div class="topline">
        <div>
          <h1>Senior Internship Finder</h1>
          <div class="subtitle">Catalog data from 2021-2026, recovered from searchable PDFs and OCR-scanned catalogs.</div>
        </div>
        <div class="stats">
          <div class="stat"><strong id="statProfiles">0</strong><span>profiles</span></div>
          <div class="stat"><strong id="statPlacements">0</strong><span>placements</span></div>
          <div class="stat"><strong id="statSaved">0</strong><span>saved</span></div>
        </div>
      </div>
      <div class="controls">
        <input id="q" type="search" placeholder="Search organization, mentor, student, field, location">
        <select id="theme"><option value="">All fields</option>{theme_options}</select>
        <select id="year"><option value="">All years</option>{year_options}</select>
        <select id="location"><option value="">All locations</option><option>Seattle</option><option>Eastside</option><option>Remote</option><option>Hybrid / flexible</option><option>Unclear</option></select>
        <select id="sort"><option value="fit">Sort by fit</option><option value="students">Most past students</option><option value="recent">Most recent</option><option value="alpha">A-Z</option></select>
      </div>
      <div class="chips" id="chips">
        <button class="chip" data-chip="direct email">Direct email</button>
        <button class="chip" data-chip="recent">Recent</button>
        <button class="chip" data-chip="repeat placement">Repeat placement</button>
        <button class="chip" data-chip="web-checked">Web-checked</button>
        <button class="chip" data-chip="academic mentor">Academic mentor</button>
        <button class="chip" data-chip="OCR recovered">OCR recovered</button>
      </div>
    </div>
  </header>
  <main>
    <div class="wrap">
      <aside>
        <h2>Saved</h2>
        <div class="saved-list" id="savedList"></div>
        <div class="row">
          <button class="ghost" id="copySaved">Copy saved</button>
          <button class="ghost" id="clearSaved">Clear</button>
        </div>
      </aside>
      <section>
        <div class="resultbar">
          <span id="resultCount"></span>
          <span id="activeFilters"></span>
        </div>
        <div class="grid" id="cards"></div>
      </section>
    </div>
  </main>
  <div class="toast" id="toast">Copied</div>
  <script id="profileData" type="application/json">{data_json}</script>
  <script>
    const data = JSON.parse(document.getElementById('profileData').textContent);
    const els = {{
      q: document.getElementById('q'),
      theme: document.getElementById('theme'),
      year: document.getElementById('year'),
      location: document.getElementById('location'),
      sort: document.getElementById('sort'),
      cards: document.getElementById('cards'),
      resultCount: document.getElementById('resultCount'),
      activeFilters: document.getElementById('activeFilters'),
      chips: document.getElementById('chips'),
      savedList: document.getElementById('savedList'),
      statProfiles: document.getElementById('statProfiles'),
      statPlacements: document.getElementById('statPlacements'),
      statSaved: document.getElementById('statSaved'),
      toast: document.getElementById('toast'),
      copySaved: document.getElementById('copySaved'),
      clearSaved: document.getElementById('clearSaved')
    }};
    let activeChips = new Set();
    let saved = new Set(JSON.parse(localStorage.getItem('internshipSaved') || '[]'));
    const esc = value => String(value || '').replace(/[&<>"']/g, ch => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}}[ch]));
    const mailto = (card, contact) => {{
      const subject = `Senior Internship Inquiry - ${{card.organization}}`;
      const alumni = card.students.slice(0, 4).map(s => `${{s.name}} (${{s.year}})`).join(', ');
      const body = `Hello ${{contact.name || ''}},%0D%0A%0D%0AI am interested in a senior internship with ${{card.organization}}. I saw past Interlake students connected with this opportunity${{alumni ? ': ' + alumni : ''}}.%0D%0A%0D%0AWould you be open to discussing whether there may be a placement available for the upcoming internship cycle?%0D%0A%0D%0AThank you,%0D%0A`;
      return `mailto:${{encodeURIComponent(contact.email)}}?subject=${{encodeURIComponent(subject)}}&body=${{body}}`;
    }};
    function showToast(text='Copied') {{
      els.toast.textContent = text;
      els.toast.classList.add('show');
      setTimeout(() => els.toast.classList.remove('show'), 1100);
    }}
    function saveState() {{
      localStorage.setItem('internshipSaved', JSON.stringify([...saved]));
      renderSaved();
    }}
    function cardText(card) {{
      const contacts = card.contacts.map(c => `${{c.name ? c.name + ' - ' : ''}}${{c.email}}`).join('; ');
      const students = card.students.map(s => `${{s.name}} (${{s.year}})`).join(', ');
      return `${{card.organization}}\\nScore: ${{card.fitScore}}/100\\nBest for: ${{card.themes.join(', ')}}\\nLocation: ${{card.locations.join(', ') || card.locationGroup}}\\nContact: ${{contacts || 'No direct email found'}}\\nWhat interns did: ${{card.summary}}\\nPast students: ${{students}}`;
    }}
    function renderSaved() {{
      els.statSaved.textContent = saved.size;
      const items = data.filter(card => saved.has(card.organization));
      if (!items.length) {{
        els.savedList.innerHTML = '<div class="mini">No saved profiles yet.</div>';
        return;
      }}
      els.savedList.innerHTML = items.map(card => `<div class="saved-item"><a href="#${{encodeURIComponent(card.organization)}}">${{esc(card.organization)}}</a><div class="mini">${{card.fitScore}}/100 · ${{card.studentCount}} placement(s)</div></div>`).join('');
    }}
    function filtered() {{
      const q = els.q.value.trim().toLowerCase();
      let rows = data.filter(card => {{
        if (q && !card.searchText.includes(q)) return false;
        if (els.theme.value && !card.themes.includes(els.theme.value)) return false;
        if (els.year.value && !card.years.includes(els.year.value)) return false;
        if (els.location.value && card.locationGroup !== els.location.value) return false;
        for (const chip of activeChips) if (!card.tags.includes(chip)) return false;
        return true;
      }});
      if (els.sort.value === 'students') rows.sort((a,b) => b.studentCount - a.studentCount || b.fitScore - a.fitScore || a.organization.localeCompare(b.organization));
      if (els.sort.value === 'recent') rows.sort((a,b) => Math.max(...b.years) - Math.max(...a.years) || b.fitScore - a.fitScore);
      if (els.sort.value === 'alpha') rows.sort((a,b) => a.organization.localeCompare(b.organization));
      if (els.sort.value === 'fit') rows.sort((a,b) => b.fitScore - a.fitScore || b.studentCount - a.studentCount || a.organization.localeCompare(b.organization));
      return rows;
    }}
    function render() {{
      const rows = filtered();
      els.statProfiles.textContent = data.length;
      els.statPlacements.textContent = data.reduce((sum, card) => sum + card.studentCount, 0);
      els.resultCount.textContent = `${{rows.length}} matching profile${{rows.length === 1 ? '' : 's'}}`;
      const filters = [els.theme.value, els.year.value, els.location.value, ...activeChips].filter(Boolean);
      els.activeFilters.textContent = filters.length ? filters.join(' · ') : 'No filters';
      if (!rows.length) {{
        els.cards.innerHTML = '<div class="empty">No matches.</div>';
        return;
      }}
      els.cards.innerHTML = rows.map(card => {{
        const savedClass = saved.has(card.organization) ? 'primary' : 'ghost';
        const contactButtons = card.contacts.length
          ? card.contacts.slice(0, 3).map(c => `<a class="contact" href="${{mailto(card, c)}}">${{esc(c.name || 'Email')}} · ${{esc(c.email)}}</a>`).join('')
          : '<span class="mini">No direct mentor email found in parsed text.</span>';
        const web = card.web && card.web.url ? `<p class="summary"><strong>External note:</strong> ${{esc(card.web.note)}} <a class="source-link" href="${{esc(card.web.url)}}" target="_blank" rel="noreferrer">${{esc(card.web.label || 'Source')}}</a></p>` : '';
        const warn = card.ocrRecovered ? '<span class="pill warn">verify OCR fields</span>' : '';
        return `<article class="card" id="${{encodeURIComponent(card.organization)}}">
          <div class="card-head">
            <div>
              <h2 class="org">${{esc(card.organization)}}</h2>
              <div class="meta">
                ${{card.themes.map(t => `<span class="pill theme">${{esc(t)}}</span>`).join('')}}
                <span class="pill">${{esc(card.locationGroup)}}</span>
                <span class="pill">${{card.studentCount}} past</span>
                <span class="pill">${{esc(card.years.join(', '))}}</span>
                ${{card.tags.includes('web-checked') ? '<span class="pill good">web-checked</span>' : ''}}
                ${{warn}}
              </div>
            </div>
            <div class="score" title="Fit score">${{card.fitScore}}</div>
          </div>
          <p class="summary">${{esc(card.summary)}}</p>
          <div class="row">${{contactButtons}}</div>
          <div class="row">
            <button class="${{savedClass}}" data-save="${{esc(card.organization)}}">${{saved.has(card.organization) ? 'Saved' : 'Save'}}</button>
            <button class="ghost" data-copy="${{esc(card.organization)}}">Copy profile</button>
          </div>
          <details>
            <summary>Profile details</summary>
            <div class="detail-grid">
              <div>
                <h3>Categories</h3>
                <p class="mini">${{esc(card.categories.join(', ') || 'unclear')}}</p>
                <h3>Locations</h3>
                <p class="mini">${{esc(card.locations.join(', ') || card.locationGroup)}}</p>
                ${{card.activities ? `<h3>Activities</h3><p class="mini">${{esc(card.activities)}}</p>` : ''}}
                ${{web}}
              </div>
              <div>
                <h3>Past students</h3>
                <ul>${{card.students.map(s => `<li>${{esc(s.name)}} (${{esc(s.year)}}) · ${{esc(s.category)}}${{s.page ? ` · p.${{esc(s.page)}}` : ''}}</li>`).join('')}}</ul>
              </div>
            </div>
          </details>
        </article>`;
      }}).join('');
    }}
    document.addEventListener('input', event => {{
      if ([els.q, els.theme, els.year, els.location, els.sort].includes(event.target)) render();
    }});
    els.chips.addEventListener('click', event => {{
      const button = event.target.closest('[data-chip]');
      if (!button) return;
      const chip = button.dataset.chip;
      if (activeChips.has(chip)) activeChips.delete(chip); else activeChips.add(chip);
      button.classList.toggle('active');
      render();
    }});
    document.addEventListener('click', event => {{
      const saveButton = event.target.closest('[data-save]');
      if (saveButton) {{
        const org = saveButton.dataset.save;
        if (saved.has(org)) saved.delete(org); else saved.add(org);
        saveState();
        render();
      }}
      const copyButton = event.target.closest('[data-copy]');
      if (copyButton) {{
        const card = data.find(item => item.organization === copyButton.dataset.copy);
        if (card) navigator.clipboard.writeText(cardText(card)).then(() => showToast());
      }}
    }});
    els.copySaved.addEventListener('click', () => {{
      const text = data.filter(card => saved.has(card.organization)).map(cardText).join('\\n\\n---\\n\\n');
      if (text) navigator.clipboard.writeText(text).then(() => showToast('Saved profiles copied'));
    }});
    els.clearSaved.addEventListener('click', () => {{
      saved.clear();
      saveState();
      render();
    }});
    renderSaved();
    render();
  </script>
</body>
</html>"""


def main() -> None:
    raw_profiles = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    cards = build_cards(raw_profiles)
    (ROOT / "senior_internship_finder.data.json").write_text(json.dumps(cards, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(build_markdown(cards), encoding="utf-8")
    OUT_HTML.write_text(build_html(cards), encoding="utf-8")
    print(f"profiles={len(cards)} placements={sum(card['studentCount'] for card in cards)}")
    print(OUT_HTML)
    print(OUT_MD)


if __name__ == "__main__":
    main()
