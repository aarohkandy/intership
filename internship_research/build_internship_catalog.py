from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent

SOURCES = [
    ("2021", ROOT / "Job_Fair_Catalog_2021.txt"),
    ("2025", ROOT / "Internship_Catalog_2025_final.txt"),
    ("2026", ROOT / "Internship_Catalogue_2026_in_rev.txt"),
]

OCR_SOURCES = [
    ("2022", ROOT / "Job_Fair_CAtalog_June_2022.ocr.pages.json"),
    ("2023", ROOT / "Job_Fair_Catalog_June_2023.ocr.pages.json"),
    ("2024", ROOT / "Job_Fair_Catalog_June_2024.ocr.pages.json"),
]


MOJIBAKE_REPLACEMENTS = {
    "â€™": "'",
    "â€œ": '"',
    "â€": '"',
    "â€˜": "'",
    "â€¢": "-",
    "â€“": "-",
    "â€”": "-",
    "â€¯": " ",
    "Â ": " ",
    "Â": "",
    "â€¦": "...",
    "ï¬": "fi",
    "ï¬‚": "fl",
    "’": "'",
    "‘": "'",
    "“": '"',
    "”": '"',
    "\u202f": " ",
    "\u00a0": " ",
}


FIELD_REPLACEMENTS = {
    "Mentor's Name": "Mentor's name",
    "Mentor's Email": "Mentor's email",
    "Mentor's Name :": "Mentor's name:",
    "Mentor's Email :": "Mentor's email:",
    "Mentor's  Name": "Mentor's name",
    "Mentor's  Email": "Mentor's email",
    "Internship Description": "Internship description",
    "Identify unique experiences": "Unique experiences",
    "Identify Unique Experiences": "Unique experiences",
    "What surprised you most?": "What surprised me the most:",
    "What surprised you most": "What surprised me the most:",
    "What is your greatest takeaway(s) from the internship experience?": "My greatest takeaways from the internship experience:",
    "What is your greatest takeaway(s) from the internship experience": "My greatest takeaways from the internship experience:",
    "What is your greatest takeaway": "My greatest takeaways from the internship experience:",
    "My greatest takeaways from the internship experience": "My greatest takeaways from the internship experience:",
}


EMAIL_RE = re.compile(r"[\w.+%-]+@[\w.-]+\.[A-Za-z]{2,}")
PAGE_RE = re.compile(r"===== PAGE (\d+) =====")


def clean_text(text: str) -> str:
    for bad, good in MOJIBAKE_REPLACEMENTS.items():
        text = text.replace(bad, good)
    # Repair common PDF line wraps inside email addresses and URL-ish domains.
    text = re.sub(r"([A-Za-z0-9._%+-]+@[\w.-]+)\.\s*\n\s*([A-Za-z]{2,})", r"\1.\2", text)
    text = re.sub(r"([A-Za-z0-9._%+-]+@)\s*\n\s*([\w.-]+\.[A-Za-z]{2,})", r"\1\2", text)
    text = re.sub(r"([A-Za-z0-9._%+-]+)\s*\n\s*(@[\w.-]+\.[A-Za-z]{2,})", r"\1\2", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    for bad, good in FIELD_REPLACEMENTS.items():
        text = text.replace(bad, good)
    return text


def normalize_space(value: str) -> str:
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\s+\n", "\n", value)
    value = re.sub(r"\n\s+", "\n", value)
    return value.strip()


def flatten(value: str) -> str:
    value = normalize_space(value)
    value = re.sub(r"\s*\n\s*", " ", value)
    return re.sub(r" {2,}", " ", value).strip(" -:\t\n")


def clean_scalar(value: str) -> str:
    value = flatten(value)
    value = re.sub(r"\bLIW\b", "UW", value)
    value = re.sub(r"\bIOW\b", "UW", value)
    value = re.sub(r"\bBand Intelligence\b", "Bond Intelligence", value, flags=re.I)
    for label in [
        " Category:",
        " Company:",
        " Location:",
        " Internship description:",
        " Unique experiences:",
        " What surprised",
        " My greatest",
        " Mentor's name:",
        " Mentor's email:",
        " ===== PAGE",
    ]:
        idx = value.find(label)
        if idx > 0:
            value = value[:idx]
    return value.strip(" -:\t\n")


def clean_email(value: str) -> str:
    value = clean_scalar(value)
    value = value.replace("gmaiL.com", "gmail.com").replace("gmaiI.com", "gmail.com")
    value = value.replace("hotmaiLcom", "hotmail.com").replace("gmaiLcom", "gmail.com")
    match = EMAIL_RE.search(value)
    if not match:
        return ""
    email = match.group(0).strip(" .;,")
    if email.lower() in {"n/a", "na"}:
        return ""
    return email


def normalize_ocr_line(value: str) -> str:
    value = clean_text(value)
    replacements = [
        (r"^(?:C?ategory|ategory|egory|ategoiy|ategoly)[\s.:;-]*", "Category: "),
        (r"^(?:C?ompany|ompany|mpany|ampany|ompäny|cornpany)[\s.:;-]*", "Company: "),
        (r"^(?:L?ocation|ocation)[\s.:;-]*", "Location: "),
        (r"^(?:I?nternship|nternship)\s+Description[\s.:;-]*", "Internship description: "),
        (r"^(?:I?dentify|dentify)\s+unique experiences[\s.:;-]*", "Unique experiences: "),
        (r"^(?:W?hat|hat)\s+surprised you most\??", "What surprised me the most:"),
        (r"^(?:W?hat|hat)\s+is your greatest takeaway(?:\\(s\\))?.*", "My greatest takeaways from the internship experience:"),
        (r"^(?:M?entor|entor)'?s?\s+Name\s*:", "Mentor's name:"),
        (r"^(?:M?entor|entor)s?\s+N[:a]?me\s*:", "Mentor's name:"),
        (r"^(?:M?entor|entor)'?s?\s+Email\s*:", "Mentor's email:"),
        (r"^(?:M?entor|entor)s?\s+Em[-:]?il\s*:", "Mentor's email:"),
        (r"^Email\s*[.:;-]+\s*", "Mentor's email: "),
    ]
    for pattern, replacement in replacements:
        value = re.sub(pattern, replacement, value, flags=re.I)
    return flatten(value)


def get_between(text: str, start_patterns: list[str], end_patterns: list[str]) -> str:
    start = None
    start_end = None
    for pat in start_patterns:
        m = re.search(pat, text, flags=re.I | re.S)
        if m and (start is None or m.start() < start):
            start = m.start()
            start_end = m.end()
    if start is None or start_end is None:
        return ""
    end = len(text)
    for pat in end_patterns:
        m = re.search(pat, text[start_end:], flags=re.I | re.S)
        if m:
            end = min(end, start_end + m.start())
    return flatten(text[start_end:end])


def current_page(prefix: str) -> int | None:
    matches = list(PAGE_RE.finditer(prefix))
    if not matches:
        return None
    return int(matches[-1].group(1))


def split_entries(text: str) -> list[tuple[str, int | None]]:
    # Each student profile ends at the mentor email line. Keep the previous
    # field block so the parser can look backward for student/org details.
    normalized = clean_text(text)
    markers = list(re.finditer(r"Mentor.?s\s*email\s*:\s*(.*?)(?=\n)", normalized, flags=re.I))
    entries: list[tuple[str, int | None]] = []
    prev_end = 0
    for marker in markers:
        end = marker.end()
        segment = normalized[prev_end:end]
        if "Category:" in segment and ("Company" in segment or "Company/Organization" in segment):
            entries.append((segment, current_page(normalized[: end])))
        prev_end = end
    return entries


def parse_entry(segment: str, year: str, source_name: str, page: int | None) -> dict[str, object] | None:
    lines = [flatten(line) for line in segment.splitlines()]
    lines = [line for line in lines if line and not line.startswith("=")]

    email_line_idx = None
    student_email = ""
    for idx, line in enumerate(lines):
        match = EMAIL_RE.search(line)
        if match:
            student_email = match.group(0)
            email_line_idx = idx
            break

    if email_line_idx is None:
        return None

    student_name = ""
    for idx in range(email_line_idx - 1, max(-1, email_line_idx - 8), -1):
        candidate = lines[idx]
        if (
            candidate
            and not candidate.lower().startswith(("page ", "contents", "category:", "company", "location"))
            and len(candidate) < 80
        ):
            student_name = candidate
            break

    category = clean_scalar(get_between(segment, [r"Category\s*:\s*"], [r"Company(?:/Organization)?\s*:"]))
    company = get_between(
        segment,
        [r"Company/Organization\s*:\s*", r"Company\s*:\s*"],
        [r"Location\s*:", r"Internship description\s*:"],
    )
    company = clean_scalar(company)
    location = get_between(
        segment,
        [r"Location\s*:\s*"],
        [r"Internship description\s*:", r"Unique experiences\s*:"],
    )
    location = clean_scalar(location)
    description = get_between(
        segment,
        [r"Internship description\s*:?\s*"],
        [r"Unique experiences\s*:?", r"What surprised me the most\s*:?", r"My greatest takeaways"],
    )
    unique = get_between(
        segment,
        [r"Unique experiences\s*:?\s*"],
        [r"What surprised me the most\s*:?", r"My greatest takeaways", r"Mentor's\s*name\s*:"],
    )
    surprised = get_between(
        segment,
        [r"What surprised me the most\s*:?\s*"],
        [r"My greatest takeaways", r"Mentor's\s*name\s*:"],
    )
    takeaways = get_between(
        segment,
        [r"My greatest takeaways from the internship experience\s*:?\s*"],
        [r"Mentor's\s*name\s*:"],
    )
    mentor_name = clean_scalar(get_between(segment, [r"Mentor.?s\s*name\s*:\s*"], [r"Mentor.?s\s*email\s*:"]))
    mentor_email_match = re.search(r"Mentor.?s\s*email\s*:\s*([^\n]+)", segment, flags=re.I)
    mentor_email = flatten(mentor_email_match.group(1)) if mentor_email_match else ""
    mentor_email = clean_email(mentor_email)

    if not company or company.lower() in {"n/a", "na"}:
        return None

    return {
        "year": year,
        "source": source_name,
        "page": page,
        "student_name": student_name,
        "student_email": clean_email(student_email),
        "category": category,
        "organization": company,
        "location": location,
        "description": description,
        "unique_experiences": unique,
        "surprised": surprised,
        "takeaways": takeaways,
        "mentor_name": mentor_name,
        "mentor_email": mentor_email,
    }


def looks_like_student_name(value: str) -> bool:
    value = flatten(value)
    if not value or len(value) > 45 or EMAIL_RE.search(value):
        return False
    lowered = value.lower()
    blocked = [
        "category",
        "company",
        "location",
        "internship",
        "mentor",
        "what ",
        "unique",
        "table of contents",
        "art, design",
        "business",
        "computer science",
        "government",
        "medical",
        "research",
    ]
    if any(lowered.startswith(word) for word in blocked):
        return False
    tokens = value.split()
    if not (2 <= len(tokens) <= 4):
        return False
    return sum(1 for token in tokens if token[:1].isupper()) >= 2


def student_candidates_from_ocr(lines: list[dict[str, object]]) -> list[dict[str, object]]:
    left_lines = []
    for raw in lines:
        text = flatten(str(raw.get("text", "")))
        if not text:
            continue
        if float(raw.get("right", 9999)) <= 455 or float(raw.get("left", 9999)) <= 430:
            left_lines.append({**raw, "text": text})
    left_lines.sort(key=lambda line: (float(line.get("top", 0)), float(line.get("left", 0))))

    candidates = []
    for idx, line in enumerate(left_lines):
        email_match = EMAIL_RE.search(str(line["text"]))
        if not email_match:
            continue
        email = email_match.group(0)
        name = ""
        name_top = float(line.get("top", 0))
        for prev in reversed(left_lines[max(0, idx - 5) : idx]):
            prev_text = str(prev["text"])
            distance = float(line.get("top", 0)) - float(prev.get("bottom", 0))
            if distance < 140 and looks_like_student_name(prev_text):
                name = prev_text
                name_top = float(prev.get("top", name_top))
                break
        candidates.append(
            {
                "name": name,
                "email": email,
                "top": name_top,
                "bottom": float(line.get("bottom", line.get("top", 0))),
                "center": (name_top + float(line.get("bottom", line.get("top", 0)))) / 2,
            }
        )
    return candidates


def parse_ocr_pages(year: str, path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    entries: list[dict[str, object]] = []
    for page in data.get("pages", []):
        page_number = int(page.get("page"))
        raw_lines = page.get("lines") or []
        lines = []
        for raw in raw_lines:
            text = normalize_ocr_line(str(raw.get("text", "")))
            if text:
                lines.append({**raw, "text": text})
        lines.sort(key=lambda line: (float(line.get("top", 0)), float(line.get("left", 0))))
        students = student_candidates_from_ocr(lines)
        content_lines = [line for line in lines if float(line.get("left", 0)) >= 430]
        start_indexes = [
            idx
            for idx, line in enumerate(content_lines)
            if re.match(r"Category\s*:", str(line.get("text", "")), flags=re.I)
        ]
        for offset, start_idx in enumerate(start_indexes):
            end_idx = start_indexes[offset + 1] if offset + 1 < len(start_indexes) else len(content_lines)
            segment_lines = content_lines[start_idx:end_idx]
            if not segment_lines:
                continue
            top = float(segment_lines[0].get("top", 0))
            bottom = max(float(line.get("bottom", 0)) for line in segment_lines)
            possible_students = [
                student for student in students if top - 80 <= float(student["center"]) <= bottom + 80
            ]
            if possible_students:
                student = min(
                    possible_students,
                    key=lambda item: abs(float(item["center"]) - ((top + bottom) / 2)),
                )
            elif students:
                student = min(students, key=lambda item: abs(float(item["center"]) - top))
            else:
                student = {"name": "", "email": ""}

            segment_text = "\n".join(str(line.get("text", "")) for line in segment_lines)
            synthetic = f"{student.get('name', '')}\n{student.get('email', '')}\n{segment_text}"
            parsed = parse_entry(synthetic, year, path.name, page_number)
            if parsed:
                parsed["ocr_recovered"] = True
                entries.append(parsed)
    return entries


def canonical_org(name: str) -> str:
    base = flatten(name)
    base = clean_scalar(base)
    simple = re.sub(r"[^a-z0-9]+", " ", base.lower()).strip()
    aliases = {
        "openexa": "OpenEXA",
        "openexa inc": "OpenEXA",
        "open exa": "OpenEXA",
        "bond intelligence": "Bond Intelligence / OpenEXA",
        "bond intelligence us": "Bond Intelligence / OpenEXA",
        "xcmeet com": "XCMeet",
        "prof hsu s internship group": "UW Elementary Particle Experiment Group",
        "uw elementary particle": "UW Elementary Particle Experiment Group",
        "university of washington": "University of Washington",
        "city of bellevue transportation": "City of Bellevue Transportation Department",
        "city of bellevue transportation department": "City of Bellevue Transportation Department",
        "sensors energy and automation lab university of washington dept of electrical and computer engineering": "UW Sensors, Energy, and Automation Lab",
        "sensors energy and automation lab university of washington department of electrical and computer engineering": "UW Sensors, Energy, and Automation Lab",
        "li lab uw medicine": "UW Medicine Li Lab",
        "neuropsychology and cognitive": "Neuropsychology and Cognitive Health",
        "neuropsychology and": "Neuropsychology and Cognitive Health",
        "fred hutch": "Fred Hutchinson Cancer Center",
        "fred hutch cancer center": "Fred Hutchinson Cancer Center",
        "fred hutchinson cancer center": "Fred Hutchinson Cancer Center",
        "fred hutchinson cancer research center": "Fred Hutchinson Cancer Center",
        "institute for systems biology isb": "Institute for Systems Biology",
        "institute for systems biology": "Institute for Systems Biology",
        "seattle children s research institute": "Seattle Children's Research Institute",
        "seattle children s hospital": "Seattle Children's",
        "interlake": "Interlake High School",
        "interlake high school": "Interlake High School",
        "bellevue school district bsd": "Bellevue School District",
        "law office of jenny cochrane": "Law Office of Jenny Cochrane",
        "seattle litigation group": "Seattle Litigation Group",
        "seattle litigation group pllc": "Seattle Litigation Group",
        "robodub": "Robodub Inc.",
        "robodub inc": "Robodub Inc.",
        "kirkland arts center": "Kirkland Arts Center",
        "uw medicine": "UW Medicine",
        "university of washington medicine": "UW Medicine",
    }
    if simple in aliases:
        return aliases[simple]
    if "openexa" in simple:
        return "OpenEXA"
    if "bond intelligence" in simple:
        return "Bond Intelligence / OpenEXA"
    if "xcmeet" in simple:
        return "XCMeet"
    if "city of bellevue" in simple and "transportation" in simple:
        return "City of Bellevue Transportation Department"
    if simple == "city of bellevue":
        return "City of Bellevue"
    if "fred hutch" in simple:
        return "Fred Hutchinson Cancer Center"
    if "systems biology" in simple:
        return "Institute for Systems Biology"
    if "seattle children" in simple and "research" in simple:
        return "Seattle Children's Research Institute"
    if simple.startswith("uw ") or simple.startswith("university of washington "):
        if "medicine" in simple:
            return "UW Medicine"
    if "sensors energy and automation lab" in simple:
        return "UW Sensors, Energy, and Automation Lab"
    if "elementary particle" in simple and ("uw" in simple or "washington" in simple or "hsu" in simple):
        return "UW Elementary Particle Experiment Group"
    return base


def score_profile(records: list[dict[str, object]]) -> int:
    emails = {r.get("mentor_email", "") for r in records if r.get("mentor_email")}
    years = {r.get("year", "") for r in records}
    categories = " ".join(str(r.get("category", "")) for r in records).lower()
    desc = " ".join(str(r.get("description", "")) for r in records).lower()
    score = 0
    score += min(25, len(records) * 4)
    score += min(15, len(years) * 5)
    if emails:
        score += 15
    if any(domain in " ".join(emails) for domain in [".edu", "uw.edu", "seattlechildrens.org", "systemsbiology.org", "fredhutch.org"]):
        score += 10
    if any(word in categories + " " + desc for word in ["research", "machine learning", "ai", "medicine", "engineering", "data", "physics"]):
        score += 10
    if len(records) >= 3:
        score += 10
    return min(100, score)


def build_profiles(entries: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for entry in entries:
        grouped[canonical_org(str(entry["organization"]))].append(entry)

    profiles = []
    for org, records in grouped.items():
        category_counts = Counter(flatten(str(r.get("category", ""))) for r in records if r.get("category"))
        location_counts = Counter(flatten(str(r.get("location", ""))) for r in records if r.get("location"))
        mentors = []
        seen_mentors = set()
        for r in records:
            mentor_name = flatten(str(r.get("mentor_name", "")))
            mentor_email = flatten(str(r.get("mentor_email", "")))
            key = (mentor_name.lower(), mentor_email.lower())
            if mentor_name or mentor_email:
                if key not in seen_mentors:
                    mentors.append({"name": mentor_name, "email": mentor_email})
                    seen_mentors.add(key)
        years = sorted({str(r["year"]) for r in records})
        profiles.append(
            {
                "organization": org,
                "categories": [name for name, _ in category_counts.most_common()],
                "locations": [name for name, _ in location_counts.most_common()],
                "mentors": mentors,
                "years": years,
                "student_count": len(records),
                "students": [
                    {
                        "name": r["student_name"],
                        "year": r["year"],
                        "category": r["category"],
                        "page": r["page"],
                        "source": r["source"],
                    }
                    for r in sorted(records, key=lambda row: (str(row["year"]), str(row["student_name"])))
                ],
                "records": records,
                "score": score_profile(records),
            }
        )
    profiles.sort(key=lambda p: (-int(p["score"]), -int(p["student_count"]), str(p["organization"]).lower()))
    return profiles


def write_outputs(entries: list[dict[str, object]], profiles: list[dict[str, object]]) -> None:
    (ROOT / "internship_entries.json").write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "internship_profiles.json").write_text(json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8")

    with (ROOT / "internship_entries.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "year",
                "student_name",
                "student_email",
                "category",
                "organization",
                "location",
                "mentor_name",
                "mentor_email",
                "source",
                "page",
            ],
        )
        writer.writeheader()
        for entry in entries:
            writer.writerow({field: entry.get(field, "") for field in writer.fieldnames})


def main() -> None:
    entries: list[dict[str, object]] = []
    for year, path in SOURCES:
        text = path.read_text(encoding="utf-8")
        for segment, page in split_entries(text):
            parsed = parse_entry(segment, year, path.name, page)
            if parsed:
                entries.append(parsed)
    for year, path in OCR_SOURCES:
        entries.extend(parse_ocr_pages(year, path))
    profiles = build_profiles(entries)
    write_outputs(entries, profiles)
    print(f"entries={len(entries)} profiles={len(profiles)}")
    for year in sorted({e['year'] for e in entries}):
        print(year, sum(1 for e in entries if e["year"] == year))
    print("top profiles:")
    for profile in profiles[:12]:
        print(f"- {profile['organization']}: {profile['student_count']} students, score {profile['score']}")


if __name__ == "__main__":
    main()
