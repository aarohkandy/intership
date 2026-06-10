import { readFileSync, writeFileSync } from "node:fs";

const RAW_ENTRIES_PATH = "internship_research/internship_entries.json";
const OUT_PATH = "profiles.json";
const COPYABLE_OUT_PATH = "internship_research/internship_profiles_copyable.md";

const SOURCE_LABELS = {
  "Internship_Catalogue_2026_in_rev.txt": "Internship Catalogue 2026",
  "Internship_Catalog_2025_final.txt": "Internship Catalog 2025",
  "Job_Fair_Catalog_June_2024.ocr.pages.json": "Job Fair Catalog June 2024 (scanned/OCR)",
  "Job_Fair_Catalog_June_2023.ocr.pages.json": "Job Fair Catalog June 2023 (scanned/OCR)",
  "Job_Fair_CAtalog_June_2022.ocr.pages.json": "Job Fair Catalog June 2022 (scanned/OCR)",
  "Job_Fair_Catalog_2021.txt": "Job Fair Catalog 2021"
};

const WEB_ENRICHMENT = {
  "Fred Hutchinson Cancer Center": {
    url: "https://www.fredhutch.org/en/about.html",
    label: "Fred Hutch About",
    note: "Official Fred Hutch pages describe a Seattle cancer research and care center with a long research history, global reach, thousands of employees, and Nobel Prize-winning scientific work.",
    verified: true
  },
  "UW Elementary Particle Experiment Group": {
    url: "https://phys.washington.edu/people/shih-chieh-hsu",
    label: "UW Physics: Shih-Chieh Hsu",
    note: "UW Physics profile for Shih-Chieh Hsu, whose listed work includes particle physics, ATLAS/LHC research, and machine-learning-related physics courses.",
    verified: true
  },
  "University of Washington": {
    url: "https://www.washington.edu/",
    label: "University of Washington",
    note: "Large public research university. Broad UW placements are split by the catalog mentor, lab, department, or source-backed contact group.",
    verified: true
  },
  "UW Medicine": {
    url: "https://www.uwmedicine.org/",
    label: "UW Medicine",
    note: "Academic medical system connected to University of Washington clinical and research departments. UW Medicine entries are split by lab or mentor when possible.",
    verified: true
  },
  "Institute for Systems Biology": {
    url: "https://isbscience.org/",
    label: "Institute for Systems Biology",
    note: "Seattle-based interdisciplinary research institute. Its official site emphasizes systems biology, software, genetics, microbial ecology, and health research.",
    verified: true
  },
  "Seattle Children's Research Institute": {
    url: "https://www.seattlechildrens.org/research/",
    label: "Seattle Children's Research",
    note: "Pediatric research institute with work across cancer therapies, genetics, neuroscience, immunology, infectious disease, and bioethics.",
    verified: true
  },
  "City of Bellevue Transportation Department": {
    url: "https://bellevuewa.gov/city-government/departments/transportation",
    label: "Bellevue Transportation",
    note: "Official city department page says it plans, designs, builds, operates, and maintains Bellevue's transportation system.",
    verified: true
  },
  "Kirkland Arts Center": {
    url: "https://kirklandartscenter.org/",
    label: "Kirkland Arts Center",
    note: "Community arts nonprofit in Kirkland with classes, gallery work, events, open studios, and arts experiences.",
    verified: true
  },
  "The Vera Project": {
    url: "https://theveraproject.org/",
    label: "The Vera Project",
    note: "All-ages Seattle nonprofit music and arts space with venue, screen print shop, recording studio, art gallery, and youth-driven programming.",
    verified: true
  },
  "World Affairs Council": {
    url: "https://www.world-affairs.org/",
    label: "World Affairs Council",
    note: "Nonpartisan Seattle nonprofit founded in 1951 that hosts programs around global understanding, civic dialogue, and international relationships.",
    verified: true
  },
  "Seattle Litigation Group": {
    url: "https://www.seattlelitigation.com/",
    label: "Seattle Litigation Group",
    note: "Seattle law firm focused on employment rights, civil litigation, professional license defense, and school mistreatment or injury matters.",
    verified: true
  },
  "Bellevue Arts Museum": {
    url: "https://www.bellevuearts.org/",
    label: "Bellevue Arts Museum",
    note: "Bellevue arts institution founded by volunteers in 1975 from the historic Pacific Northwest Arts & Crafts Fair.",
    verified: true
  }
};

const THEMES = [
  ["CS / AI / Data", ["computer", "software", "data", "machine learning", " ai ", "coding", "web", "python", "react", "cyber", "algorithm"]],
  ["Biomedical / Health", ["medical", "medicine", "health", "bio", "cancer", "clinical", "hospital", "neuro", "psych", "lab", "patient"]],
  ["Research", ["research", "study", "scientific", "experiment", "paper", "analysis", "publication", "literature review"]],
  ["Engineering / Physics", ["engineering", "physics", "aerospace", "mechanical", "electrical", "particle", "transportation", "construction", "device"]],
  ["Business / Marketing", ["business", "finance", "marketing", "operations", "real estate", "sales", "social media", "startup"]],
  ["Government / Law", ["government", "law", "legal", "policy", "public sector", "litigation", "city of", "court"]],
  ["Arts / Media / Music", ["art", "design", "music", "media", "video", "gallery", "museum", "creative", "film"]],
  ["Education / TA", ["school", "teaching", "teacher", "ta", "education", "classroom", "curriculum"]],
  ["Nonprofit / Community", ["non-profit", "nonprofit", "community", "volunteer", "council", "foundation"]],
  ["Environment", ["environment", "sustainability", "climate", "ecology", "waste", "energy", "conservation"]]
];

const BROAD_PARENTS = new Set([
  "Fred Hutchinson Cancer Center",
  "University of Washington",
  "UW Elementary Particle Experiment Group",
  "UW Medicine",
  "Institute for Systems Biology",
  "Seattle Children's Research Institute",
  "Interlake High School",
  "Bellevue School District",
  "City of Bellevue",
  "City of Bellevue Transportation Department"
]);

const MOJIBAKE = new Map([
  ["Ã¢â‚¬Â¢", "-"],
  ["Ã¢â‚¬â„¢", "'"],
  ["Ã¢â‚¬Å“", "\""],
  ["Ã¢â‚¬Â", "\""],
  ["Ã¢â‚¬â€œ", "-"],
  ["Ã¢â‚¬â€", "-"],
  ["Ã‚Â·", "-"],
  ["Â·", "-"],
  ["Ã‚", ""],
  ["â€™", "'"],
  ["â€œ", "\""],
  ["â€", "\""],
  ["•", "-"]
]);

const EMAIL_RE = /[\w.+%-]+@[\w.-]+\.[A-Za-z]{2,}/;

function trimChars(value) {
  return String(value || "").replace(/^[\s,.:;/-]+|[\s,.:;/-]+$/g, "");
}

function cleanText(value) {
  let text = String(value ?? "");
  for (const [bad, good] of MOJIBAKE.entries()) text = text.replaceAll(bad, good);
  return text.replace(/\s+/g, " ").trim();
}

function cutAtLabels(value) {
  let text = cleanText(value)
    .replace(/\bLIW\b/g, "UW")
    .replace(/\bIOW\b/g, "UW")
    .replace(/\bBand Intelligence\b/gi, "Bond Intelligence");
  const labelPattern = /\s+(?:Category|Company|Location|Internship description|Unique experiences|What surprised|My greatest|Mentor's name|Mentor's email|===== PAGE)\s*:?.*$/i;
  text = text.replace(labelPattern, "");
  return trimChars(text);
}

function simpleKey(value) {
  return cleanText(value)
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function titleish(value) {
  return cleanText(value)
    .replace(/\bDpt\.?\b/gi, "Department")
    .replace(/\bDept\.?\b/gi, "Department")
    .replace(/\bLIW\b/g, "UW")
    .replace(/\bIOW\b/g, "UW");
}

function extractEmail(...values) {
  for (const value of values) {
    const match = cleanText(value).match(EMAIL_RE);
    if (match) return match[0].replace(/[.;,]+$/, "");
  }
  return "";
}

function normalizeEmailForKey(email) {
  const raw = cleanText(email).toLowerCase();
  const match = raw.match(EMAIL_RE);
  if (!match) return "";
  let value = match[0].replace(/[.;,]+$/, "");
  const aliases = new Map([
    ["ashley-vauqhan@seattlechildrens.org", "ashley.vaughan@seattlechildrens.org"],
    ["edustch@svstemsbialagy.org", "edeutsch@systemsbiology.org"],
    ["eric.deutsch@isbscience.org", "edeutsch@systemsbiology.org"],
    ["msettv@fredhutch.org", "msetty@fredhutch.org"],
    ["staner@uw.edu", "stoner@uw.edu"],
    ["schsu@uwvedu", "schsu@uw.edu"],
    ["lenp@bsd405.org", "allenp@bsd405.org"],
    ["ajit@openexe.com", "ajit@openexa.com"],
    ["ajt@openexa.com", "ajit@openexa.com"],
    ["aiit@openexa.com", "ajit@openexa.com"],
    ["ejit@openexa.com", "ajit@openexa.com"],
    ["info@seattleljtigation.com", "info@seattlelitigation.com"],
    ["mac@sensariainc.com", "mac@sensoriainc.com"],
    ["kpepple@uwwedu", "kpepple@uw.edu"],
    ["sart@elap.orz", "sart@elap.org"]
  ]);
  return aliases.get(value) || value;
}

function isSuspiciousEmail(email) {
  const value = cleanText(email).toLowerCase();
  return /svstems|bialagy|vauqhan|openexe\.com|seattleljtigation|sensariainc|uwwedu|uwvedu|\.arg\b|\.orz\b|msettv@|staner@|^lenp@/.test(value);
}

function isGoodEmail(email) {
  const value = cleanText(email);
  if (!EMAIL_RE.test(value)) return false;
  if (value.toLowerCase().startsWith("s-")) return false;
  if (isSuspiciousEmail(value)) return false;
  return true;
}

function cleanMentorName(value) {
  let text = cleanText(value);
  text = text.replace(EMAIL_RE, "");
  text = text.replace(/\bMentor'?s?\s+\S+.*$/i, "");
  text = text.replace(/\bEm[a-z_!]*\s*:?.*$/i, "");
  text = text.replace(/\bCategory\b.*$/i, "");
  text = text.replace(/\btegory\b.*$/i, "");
  text = text.replace(/\bEmail\b\s*:.*$/i, "");
  text = text.replace(/^Contact\s+/i, "");
  text = text.replace(/\s*\([^)]{45,}\)\s*/g, " ");
  text = text.replace(/\btechnically\b.*$/i, "");
  text = text.replace(/\bDeustch\b/gi, "Deutsch");
  text = text.replace(/\bVayndarf\b/gi, "Vayndorf");
  text = text.replace(/\([^)]*$/g, "");
  text = trimChars(text.replace(/\s+/g, " "));
  if (!text || /^n\/?a\b/i.test(text) || /^none$/i.test(text)) return "";
  if (text.length > 78) return "";
  return text;
}

function mentorKey(name) {
  let value = cleanMentorName(name);
  value = value
    .replace(/\b(professor|prof\.?|dr\.?|phd|m\.d\.|md)\b/gi, "")
    .replace(/\blab manager\b/gi, "")
    .replace(/\s+/g, " ")
    .trim(" ,-/");
  value = value.replace(/\bM\.?\s*P\.?\s*\.?\s*Anantram\b/i, "MP Anantram");
  value = value.replace(/\bM\.?\s*P\.?\s*\.?\s*Anant\b/i, "MP Anantram");
  value = value.replace(/\bNicholas Buzinsky\b/i, "Nick Buzinsky");
  value = value.replace(/\bShih Chieh\b/i, "Shih-Chieh");
  return simpleKey(value);
}

function contactFromRecord(record) {
  const embeddedEmail = extractEmail(record.mentor_name);
  const listedEmail = extractEmail(record.mentor_email);
  const mentorSaysNoEmail = /\bemail\s*:?\s*n\/?a\b/i.test(cleanText(record.mentor_name));
  const email = embeddedEmail && (!listedEmail || isSuspiciousEmail(listedEmail) || cleanText(record.mentor_name).length > 70)
    ? embeddedEmail
    : mentorSaysNoEmail
      ? ""
      : listedEmail || embeddedEmail;
  const name = cleanMentorName(record.mentor_name);
  return {
    name,
    email: cleanText(email),
    emailKey: normalizeEmailForKey(email),
    nameKey: mentorKey(name)
  };
}

function canonicalContactKey(contact) {
  const aliases = new Map([
    ["schsu@uw.edu", "schsu@uw.edu"],
    ["shih chieh hsu", "schsu@uw.edu"],
    ["anan tmp@uw.edu", "anantmp@uw.edu"],
    ["anantmp@uw.edu", "anantmp@uw.edu"],
    ["mp anantram", "anantmp@uw.edu"],
    ["arindam@uw.edu", "arindam@uw.edu"],
    ["arindam das", "arindam@uw.edu"],
    ["gsmith@fredhutch.org", "gsmith@fredhutch.org"],
    ["gerry smith", "gsmith@fredhutch.org"],
    ["edeutsch@systemsbiology.org", "edeutsch@systemsbiology.org"],
    ["eric deutsch", "edeutsch@systemsbiology.org"],
    ["ashley.vaughan@seattlechildrens.org", "ashley.vaughan@seattlechildrens.org"],
    ["ashley vaughan", "ashley.vaughan@seattlechildrens.org"],
    ["jonathan.tang@seattlechildrens.org", "jonathan.tang@seattlechildrens.org"],
    ["jonathan tang", "jonathan.tang@seattlechildrens.org"],
    ["nbuzin@uw.edu", "nbuzin@uw.edu"],
    ["nick buzinsky", "nbuzin@uw.edu"],
    ["joeykey@uw.edu", "joeykey@uw.edu"],
    ["joey key", "joeykey@uw.edu"],
    ["brent lagesse", "lagesse@uw.edu"],
    ["lagesse@uw.edu", "lagesse@uw.edu"],
    ["elena vayndorf", "vayndorf@uw.edu"],
    ["vayndorf@uw.edu", "vayndorf@uw.edu"],
    ["evayndorf@gmail.com", "vayndorf@uw.edu"]
  ]);
  if (contact.emailKey && aliases.has(contact.emailKey)) return aliases.get(contact.emailKey);
  if (contact.nameKey && aliases.has(contact.nameKey)) return aliases.get(contact.nameKey);
  const emailKey = !cleanText(contact.email).toLowerCase().startsWith("s-") ? contact.emailKey : "";
  return emailKey || contact.nameKey;
}

function canonicalParentOrg(rawOrg) {
  const base = cutAtLabels(rawOrg);
  const simple = simpleKey(base);
  const exactAliases = new Map([
    ["openexa", "OpenEXA"],
    ["openexa inc", "OpenEXA"],
    ["open exa", "OpenEXA"],
    ["bond intelligence", "Bond Intelligence / OpenEXA"],
    ["bond intelligence us", "Bond Intelligence / OpenEXA"],
    ["xcmeet com", "XCMeet"],
    ["uw", "University of Washington"],
    ["prof hsu s internship group", "UW Elementary Particle Experiment Group"],
    ["uw elementary particle", "UW Elementary Particle Experiment Group"],
    ["epe ml group", "UW Elementary Particle Experiment Group"],
    ["uw epe ml group", "UW Elementary Particle Experiment Group"],
    ["uw epe ml research group", "UW Elementary Particle Experiment Group"],
    ["elementary particle experiment machine learning team epe ml", "UW Elementary Particle Experiment Group"],
    ["elementary particle experiment machine learning group", "UW Elementary Particle Experiment Group"],
    ["elementary particles experiment machine learning study group", "UW Elementary Particle Experiment Group"],
    ["uw physics department elementary particle experiment", "UW Elementary Particle Experiment Group"],
    ["university of washington elementary particle experiment", "UW Elementary Particle Experiment Group"],
    ["university of washington elementary particle experiment machine learning group", "UW Elementary Particle Experiment Group"],
    ["uw elementary particle experiment machine learning group", "UW Elementary Particle Experiment Group"],
    ["quantum devices lab", "University of Washington"],
    ["city of bellevue transportation", "City of Bellevue Transportation Department"],
    ["city of bellevue transportation department", "City of Bellevue Transportation Department"],
    ["li lab uw medicine", "UW Medicine"],
    ["uw medicine li lab", "UW Medicine"],
    ["neuropsychology and cognitive", "Neuropsychology and Cognitive Health"],
    ["neuropsychology and", "Neuropsychology and Cognitive Health"],
    ["fred hutch", "Fred Hutchinson Cancer Center"],
    ["fred hutch cancer center", "Fred Hutchinson Cancer Center"],
    ["fred hutch cancer centre", "Fred Hutchinson Cancer Center"],
    ["fred hutch cancer research center", "Fred Hutchinson Cancer Center"],
    ["fred hutch cancer research institute", "Fred Hutchinson Cancer Center"],
    ["fred hutchinson cancer center", "Fred Hutchinson Cancer Center"],
    ["fred hutchinson cancer research center", "Fred Hutchinson Cancer Center"],
    ["fred hutchinson cancer research institute", "Fred Hutchinson Cancer Center"],
    ["institute for systems biology isb", "Institute for Systems Biology"],
    ["institute for systems biology", "Institute for Systems Biology"],
    ["seattle children s research institute", "Seattle Children's Research Institute"],
    ["seattle children s hospital", "Seattle Children's"],
    ["interlake", "Interlake High School"],
    ["interlake high school", "Interlake High School"],
    ["bellevue school district bsd", "Bellevue School District"],
    ["bellevue school district", "Bellevue School District"],
    ["law office of jenny cochrane", "Law Office of Jenny Cochrane"],
    ["seattle litigation group", "Seattle Litigation Group"],
    ["seattle litigation group pllc", "Seattle Litigation Group"],
    ["robodub", "Robodub Inc."],
    ["robodub inc", "Robodub Inc."],
    ["kirkland arts center", "Kirkland Arts Center"],
    ["uw medicine", "UW Medicine"],
    ["university of washington medicine", "UW Medicine"]
  ]);
  if (exactAliases.has(simple)) return exactAliases.get(simple);
  if ((simple.includes("elementary particle") || /\bepe\b/.test(simple)) && (simple.includes("uw") || simple.includes("washington") || simple.includes("hsu") || simple.includes("ml"))) {
    return "UW Elementary Particle Experiment Group";
  }
  if (simple.includes("fred hutch")) return "Fred Hutchinson Cancer Center";
  if (simple.includes("systems biology")) return "Institute for Systems Biology";
  if (simple.includes("seattle children") && simple.includes("research")) return "Seattle Children's Research Institute";
  if (simple.includes("uw medicine") || simple.includes("university of washington medicine")) return "UW Medicine";
  if (simple.includes("city of bellevue") && simple.includes("transportation")) return "City of Bellevue Transportation Department";
  if (simple === "city of bellevue") return "City of Bellevue";
  if (simple.includes("bond intelligence")) return "Bond Intelligence / OpenEXA";
  if (simple.includes("openexa") || simple.includes("open exa")) return "OpenEXA";
  if (simple.includes("xcmeet")) return "XCMeet";
  if (simple.includes("sensors energy and automation lab")) return "University of Washington";
  if (simple.startsWith("uw ") || simple.includes("university of washington") || simple.includes("washington bothell")) return "University of Washington";
  if (simple.includes("interlake high school")) return "Interlake High School";
  return titleish(base);
}

function parentForRecord(record) {
  const parent = canonicalParentOrg(record.organization);
  const contact = contactFromRecord(record);
  const contactKey = canonicalContactKey(contact);
  if (parent === "University of Washington" && contactKey === "schsu@uw.edu") {
    return "UW Elementary Particle Experiment Group";
  }
  return parent;
}

function normalizeSpecificOrg(rawOrg, parent) {
  let label = titleish(cutAtLabels(rawOrg));
  const simple = simpleKey(label);
  if (!label) return parent;
  if (/fred hutch/i.test(label)) {
    label = label
      .replace(/Fred Hutch Cancer Centre/gi, "Fred Hutchinson Cancer Center")
      .replace(/Fred Hutch Cancer Center/gi, "Fred Hutchinson Cancer Center")
      .replace(/Fred Hutch Cancer Research (?:Center|Institute)/gi, "Fred Hutchinson Cancer Center")
      .replace(/Fred Hutchinson Cancer Research (?:Center|Institute)/gi, "Fred Hutchinson Cancer Center")
      .replace(/Bleakley Lab @ Fred Hutchinson Cancer Center/gi, "Bleakley Lab, Fred Hutchinson Cancer Center")
      .replace(/SCHARP, Fred Hutch/gi, "SCHARP at Fred Hutch")
      .replace(/The SCHARP Group at Fred Hutch/gi, "SCHARP at Fred Hutch");
  }
  if (simple === "university of washington" || simple === "uw medicine" || simple === "fred hutchinson cancer center") return parent;
  if (parent === "Institute for Systems Biology") label = label.replace(/Institute far Systems Biology/gi, "Institute for Systems Biology");
  if (parent === "UW Elementary Particle Experiment Group") {
    if (/\bepe\b/i.test(label)) label = label.replace(/^UW\s+EPE\s+ML(?:\s+Research)?\s+Group$/i, "UW Elementary Particle Experiment Machine Learning Group");
    if (/^EPE\s+ML\s+Group$/i.test(label)) label = "UW Elementary Particle Experiment Machine Learning Group";
  }
  if (simple.includes("university of washington lacation online")) return parent;
  if (label.length > 118) return parent;
  return label;
}

function specificityScore(label, parent) {
  const simple = simpleKey(label);
  if (!label || label === parent || simpleKey(parent) === simple) return -20;
  let score = 0;
  if (/\blab\b/i.test(label)) score += 18;
  if (/\b(group|department|division|center|centre|institute|school|clinic|studio|taskar|sch[a]?rp|cenpa|emit|kaeberlein)\b/i.test(label)) score += 10;
  if (/\bUW\b|University of Washington|Fred Hutch|Seattle Children's/i.test(label)) score += 3;
  if (label.length <= 80) score += 3;
  if (label.length > 100) score -= 5;
  return score;
}

function chooseSpecificOrg(records, parent) {
  const counts = new Map();
  for (const record of records) {
    const label = normalizeSpecificOrg(record.organization, parent);
    const key = simpleKey(label);
    if (!key) continue;
    if (!counts.has(key)) counts.set(key, { label, count: 0 });
    counts.get(key).count += 1;
  }
  const options = [...counts.values()].sort((a, b) => {
    const scoreDiff = specificityScore(b.label, parent) - specificityScore(a.label, parent);
    if (scoreDiff) return scoreDiff;
    if (b.count !== a.count) return b.count - a.count;
    return a.label.length - b.label.length;
  });
  return options[0]?.label || parent;
}

function shouldSplitParent(parent) {
  return BROAD_PARENTS.has(parent);
}

function groupKeyForEntry(record) {
  const parent = parentForRecord(record);
  if (!shouldSplitParent(parent)) return `${parent}|org`;
  const contact = contactFromRecord(record);
  const specific = normalizeSpecificOrg(record.organization, parent);
  let key = canonicalContactKey(contact);
  if (!key && parent === "UW Elementary Particle Experiment Group") key = "schsu@uw.edu";
  if (key) return `${parent}|mentor:${key}`;
  if (specificityScore(specific, parent) > 0) return `${parent}|specific:${simpleKey(specific)}`;
  return `${parent}|unlisted`;
}

function sortYears(years) {
  return [...years].sort((a, b) => Number(b) - Number(a));
}

function uniqueBy(values, keyFn) {
  const seen = new Set();
  const out = [];
  for (const value of values) {
    const key = keyFn(value);
    if (!key || seen.has(key)) continue;
    seen.add(key);
    out.push(value);
  }
  return out;
}

function firstSentences(values, limit = 520) {
  const pieces = [];
  const seen = new Set();
  for (const value of values) {
    const text = cleanText(value).replace(/^(?:internship description|unique experiences)\s*:?\s*/i, "");
    for (const rawSentence of text.split(/(?<=[.!?])\s+/)) {
      const sentence = cleanText(rawSentence).replace(/\s*[-:]\s*$/, "");
      const low = sentence.toLowerCase();
      if (sentence.length < 35) continue;
      if (/mentor'?s|category:|company:|what surprised/i.test(sentence)) continue;
      if (seen.has(low)) continue;
      seen.add(low);
      pieces.push(sentence.length > 230 ? `${sentence.slice(0, 230).replace(/\s+\S*$/, "")}...` : sentence);
      if (pieces.join(" ").length >= limit) return pieces.join(" ").slice(0, limit).replace(/\s+\S*$/, "") + "...";
    }
  }
  return pieces.join(" ").slice(0, limit);
}

function themeFor(profile) {
  const text = [
    profile.organization,
    profile.parentOrganization,
    profile.profileFocus,
    profile.categories.join(" "),
    profile.records.slice(0, 10).map(record => cleanText(record.description)).join(" ")
  ].join(" ").toLowerCase();
  const padded = ` ${text} `;
  const scored = [];
  for (const [label, words] of THEMES) {
    let score = 0;
    for (const word of words) {
      const token = word.trim();
      if (!token) continue;
      if (token.includes(" ")) {
        score += padded.split(token).length - 1;
      } else {
        score += (padded.match(new RegExp(`\\b${token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "g")) || []).length;
      }
    }
    if (score) scored.push([score, label]);
  }
  return scored.sort((a, b) => b[0] - a[0]).slice(0, 3).map(([, label]) => label);
}

function locationGroup(locations) {
  const text = locations.join(" ").toLowerCase();
  if (/remote|online|virtual/.test(text)) {
    if (/seattle|bellevue|kirkland|redmond|uw|washington/.test(text)) return "Hybrid / flexible";
    return "Remote";
  }
  if (/bellevue|redmond|kirkland|issaquah|bothell/.test(text)) return "Eastside";
  if (/seattle|uw|south lake union|washington/.test(text)) return "Seattle";
  return "Unclear";
}

function studentList(records) {
  const rows = records
    .map(record => ({
      name: cleanText(record.student_name),
      year: cleanText(record.year),
      category: cleanText(record.category),
      source: cleanText(record.source),
      page: cleanText(record.page)
    }))
    .filter(student => {
      if (!student.name || student.name.length > 70 || student.name.includes("@")) return false;
      return !/mentor|category|company|location|email|internship/i.test(student.name);
    })
    .sort((a, b) => Number(b.year) - Number(a.year) || a.name.localeCompare(b.name));
  return uniqueBy(rows, student => `${student.name.toLowerCase()}|${student.year}`);
}

function contactList(records) {
  const contacts = records
    .map(record => {
      const contact = contactFromRecord(record);
      return {
        name: contact.name,
        email: cleanText(contact.email),
        emailKey: contact.emailKey,
        year: Number(record.year) || 0,
        sourceBacked: true,
        good: isGoodEmail(contact.email)
      };
    })
    .filter(contact => contact.good);
  const byKey = new Map();
  for (const contact of contacts) {
    const key = contact.emailKey || contact.email.toLowerCase();
    const existing = byKey.get(key);
    if (!existing || contact.year > existing.year || (contact.name && !existing.name)) byKey.set(key, contact);
  }
  return [...byKey.values()]
    .sort((a, b) => b.year - a.year || a.email.localeCompare(b.email))
    .slice(0, 5)
    .map(({ name, email }) => ({ name: cleanText(name), email: cleanText(email) }));
}

function profileFocus(records) {
  const contacts = records.map(contactFromRecord);
  const names = contacts.map(contact => contact.name).filter(Boolean);
  const nameCounts = new Map();
  for (const name of names) {
    const key = mentorKey(name);
    if (!key) continue;
    const existing = nameCounts.get(key) || { name, count: 0 };
    existing.count += 1;
    if (name.length < existing.name.length) existing.name = name;
    nameCounts.set(key, existing);
  }
  const best = [...nameCounts.values()].sort((a, b) => b.count - a.count || a.name.length - b.name.length)[0];
  return best?.name || "";
}

function displayNameFor(records, parent) {
  const specific = chooseSpecificOrg(records, parent);
  const focus = profileFocus(records);
  let base = specific || parent;
  if (specific === parent && focus) base = `${parent} - ${focus}`;
  else if (focus && !simpleKey(specific).includes(simpleKey(focus))) base = `${specific} - ${focus}`;
  if (!focus && shouldSplitParent(parent) && specificityScore(specific, parent) <= 0) base = `${parent} - mentor not listed`;
  return cleanText(base);
}

function fitScore(profile) {
  let score = 0;
  score += Math.min(28, profile.studentCount * 5);
  score += Math.min(16, profile.years.length * 4);
  if (profile.contacts.length) score += 18;
  if (profile.web?.url) score += 7;
  if (profile.years.some(year => Number(year) >= 2025)) score += 8;
  if (profile.studentCount >= 2) score += 7;
  if (profile.themes.includes("Research") || profile.themes.includes("CS / AI / Data") || profile.themes.includes("Biomedical / Health")) score += 6;
  if (profile.parentOrganization !== profile.organization) score += 4;
  return Math.min(100, score);
}

function makeProfiles(entries) {
  const groups = new Map();
  for (const record of entries) {
    const parent = parentForRecord(record);
    const key = groupKeyForEntry(record);
    if (!groups.has(key)) groups.set(key, { parent, records: [] });
    groups.get(key).records.push(record);
  }

  const profiles = [];
  for (const { parent, records } of groups.values()) {
    const students = studentList(records);
    if (!students.length) continue;
    const categories = uniqueBy(
      records.map(record => cleanText(record.category)).filter(Boolean),
      value => simpleKey(value)
    ).slice(0, 8);
    const locations = uniqueBy(
      records.map(record => cutAtLabels(record.location)).filter(Boolean),
      value => simpleKey(value)
    ).filter(value => value.length <= 140).slice(0, 8);
    const years = sortYears(new Set(records.map(record => cleanText(record.year)).filter(Boolean)));
    const contacts = contactList(records);
    const organization = displayNameFor(records, parent);
    const profile = {
      organization,
      parentOrganization: parent,
      profileFocus: profileFocus(records),
      splitProfile: shouldSplitParent(parent),
      categories,
      locations,
      locationGroup: locationGroup(locations),
      years,
      studentCount: students.length,
      contacts,
      students,
      summary: firstSentences(records.map(record => record.description), 520) || "Catalog entry has limited description text; use the listed student examples and source catalog pages before emailing.",
      activities: firstSentences(records.map(record => record.unique_experiences), 430),
      web: WEB_ENRICHMENT[parent] || {},
      ocrRecovered: records.some(record => Boolean(record.ocr_recovered)),
      records
    };
    profile.themes = themeFor(profile);
    if (!profile.themes.length) profile.themes = ["Other"];
    profile.fitScore = fitScore(profile);
    profile.searchText = [
      profile.organization,
      profile.parentOrganization,
      profile.profileFocus,
      profile.themes.join(" "),
      profile.categories.join(" "),
      profile.locations.join(" "),
      profile.locationGroup,
      profile.years.join(" "),
      profile.contacts.map(contact => `${contact.name} ${contact.email}`).join(" "),
      profile.students.map(student => `${student.name} ${student.category}`).join(" "),
      profile.summary,
      profile.activities,
      profile.web.note || ""
    ].join(" ").toLowerCase();
    delete profile.records;
    profiles.push(profile);
  }

  const nameCounts = new Map();
  for (const profile of profiles) {
    const count = nameCounts.get(profile.organization) || 0;
    nameCounts.set(profile.organization, count + 1);
    if (count > 0) profile.organization = `${profile.organization} (${profile.years.join(", ")})`;
  }

  return profiles.sort((a, b) => b.fitScore - a.fitScore || b.studentCount - a.studentCount || a.organization.localeCompare(b.organization));
}

function sourceLabel(source) {
  return SOURCE_LABELS[source] || source || "catalog";
}

function buildMarkdown(profiles) {
  const lines = [
    "# Senior Internship Profiles",
    "",
    "Generated from the 2021-2026 internship/job fair catalogs. Broad institutions such as UW, Fred Hutch, ISB, and Seattle Children's are split by mentor, lab, or contact group when the catalog data supports it.",
    "",
    "Scanned 2022-2024 entries came from OCR and are marked in the website. Verify catalog page references before sending important emails.",
    "",
    `Total profiles: ${profiles.length}`,
    `Total past placement examples: ${profiles.reduce((sum, profile) => sum + profile.studentCount, 0)}`,
    "",
    "## Quick Shortlist",
    ""
  ];

  for (const profile of profiles.slice(0, 30)) {
    const contact = profile.contacts[0]?.email || "no direct email found";
    lines.push(`- ${profile.organization} - ${profile.studentCount} past placement(s), years ${profile.years.join(", ")}, contact: ${contact}`);
  }

  lines.push("", "## All Profiles", "");
  for (const profile of profiles) {
    lines.push(`## ${profile.organization}`);
    lines.push("");
    if (profile.parentOrganization && profile.parentOrganization !== profile.organization) lines.push(`Larger organization: ${profile.parentOrganization}`);
    if (profile.profileFocus) lines.push(`Mentor/lab focus: ${profile.profileFocus}`);
    lines.push(`Best for: ${profile.themes.join(", ")}`);
    lines.push(`Catalog categories: ${profile.categories.join(", ") || "unclear"}`);
    lines.push(`Location: ${profile.locations.join(", ") || profile.locationGroup}`);
    lines.push(`Catalog years: ${profile.years.join(", ")}`);
    lines.push(`Past placement examples: ${profile.studentCount}`);
    if (profile.contacts.length) {
      lines.push("Contacts:");
      for (const contact of profile.contacts) {
        lines.push(`- ${contact.name ? `${contact.name} - ` : ""}${contact.email}`);
      }
    } else {
      lines.push("Contacts: no direct mentor email found in parsed catalog text");
    }
    lines.push("");
    lines.push("What interns did:");
    lines.push(profile.summary);
    if (profile.activities) {
      lines.push("");
      lines.push("Notable activities:");
      lines.push(profile.activities);
    }
    if (profile.web?.url) {
      lines.push("");
      lines.push("Outside source:");
      lines.push(`${profile.web.note} (${profile.web.url})`);
    }
    lines.push("");
    lines.push("People who went here before:");
    for (const student of profile.students) {
      const source = `${sourceLabel(student.source)}${student.page ? `, p. ${student.page}` : ""}`;
      lines.push(`- ${student.name} (${student.year}) - ${student.category || "category unclear"} [${source}]`);
    }
    lines.push("");
  }

  return `${lines.join("\n").trim()}\n`;
}

const entries = JSON.parse(readFileSync(RAW_ENTRIES_PATH, "utf8"));
const profiles = makeProfiles(entries);
writeFileSync(OUT_PATH, `${JSON.stringify(profiles, null, 2)}\n`, "utf8");
writeFileSync(COPYABLE_OUT_PATH, buildMarkdown(profiles), "utf8");

const placementCount = profiles.reduce((sum, profile) => sum + profile.studentCount, 0);
console.log(`profiles=${profiles.length} placements=${placementCount}`);
for (const parent of ["Fred Hutchinson Cancer Center", "University of Washington", "UW Medicine", "Institute for Systems Biology", "Seattle Children's Research Institute"]) {
  const rows = profiles.filter(profile => profile.parentOrganization === parent);
  console.log(`${parent}: ${rows.length} profiles, ${rows.reduce((sum, row) => sum + row.studentCount, 0)} placements`);
}
