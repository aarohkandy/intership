const state = {
  profiles: [],
  query: "",
  quick: "all",
  field: "",
  year: "",
  sort: "fit",
  hasEmail: false,
  recentOnly: false,
  repeatOnly: false,
  hideOcr: false,
  savedOnly: false,
  compactView: false,
  saved: new Set(JSON.parse(localStorage.getItem("internshipGuideSaved") || "[]"))
};

const el = {
  cards: document.querySelector("#cards"),
  template: document.querySelector("#cardTemplate"),
  search: document.querySelector("#searchInput"),
  settingsButton: document.querySelector("#settingsButton"),
  settingsPanel: document.querySelector("#settingsPanel"),
  field: document.querySelector("#fieldSelect"),
  year: document.querySelector("#yearSelect"),
  sort: document.querySelector("#sortSelect"),
  hasEmail: document.querySelector("#hasEmail"),
  recentOnly: document.querySelector("#recentOnly"),
  repeatOnly: document.querySelector("#repeatOnly"),
  hideOcr: document.querySelector("#hideOcr"),
  savedOnly: document.querySelector("#savedOnly"),
  compactView: document.querySelector("#compactView"),
  profileCount: document.querySelector("#profileCount"),
  resultSummary: document.querySelector("#resultSummary"),
  savedCount: document.querySelector("#savedCount"),
  savedList: document.querySelector("#savedList"),
  copySaved: document.querySelector("#copySaved"),
  clearSaved: document.querySelector("#clearSaved"),
  resetFilters: document.querySelector("#resetFilters"),
  toast: document.querySelector("#toast")
};

const sourceLabels = {
  "Internship_Catalogue_2026_in_rev.txt": "Internship Catalogue 2026",
  "Internship_Catalog_2025_final.txt": "Internship Catalog 2025",
  "Job_Fair_Catalog_June_2024.ocr.pages.json": "Job Fair Catalog June 2024 (scanned/OCR)",
  "Job_Fair_Catalog_June_2023.ocr.pages.json": "Job Fair Catalog June 2023 (scanned/OCR)",
  "Job_Fair_CAtalog_June_2022.ocr.pages.json": "Job Fair Catalog June 2022 (scanned/OCR)",
  "Job_Fair_Catalog_2021.txt": "Job Fair Catalog 2021"
};

const cleanText = value => String(value || "")
  .replaceAll("â€¢", "-")
  .replaceAll("â€™", "'")
  .replaceAll("â€œ", "\"")
  .replaceAll("â€", "\"")
  .replaceAll("â€“", "-")
  .replaceAll("Â·", "-")
  .replaceAll("·", "-")
  .replace(/\s+/g, " ")
  .trim();

const short = (text, limit = 240) => {
  const cleaned = cleanText(text);
  if (cleaned.length <= limit) return cleaned;
  return `${cleaned.slice(0, limit).replace(/\s+\S*$/, "")}...`;
};

const hasDirectEmail = profile => profile.contacts?.some(contact => contact.email);
const isRecent = profile => profile.years?.some(year => Number(year) >= 2025);
const isGoodEmail = email => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(email || "")) && !String(email || "").toLowerCase().startsWith("s-");
const isProbablyStudent = student => {
  const name = cleanText(student?.name);
  if (!name || name.length > 70 || name.includes("@")) return false;
  if (/mentor|category|company|location|email|internship/i.test(name)) return false;
  return true;
};

function normalizeProfile(profile) {
  const students = (profile.students || [])
    .filter(isProbablyStudent)
    .map(student => ({
      ...student,
      name: cleanText(student.name),
      category: cleanText(student.category),
      sourceLabel: sourceLabels[student.source] || cleanText(student.source),
      page: cleanText(student.page)
    }));

  const contacts = (profile.contacts || [])
    .filter(contact => isGoodEmail(contact.email))
    .map(contact => ({
      name: cleanText(contact.name).replace(/^n\/a$/i, ""),
      email: cleanText(contact.email)
    }));

  const sourceRefs = [];
  const seen = new Set();
  for (const student of students) {
    const key = `${student.sourceLabel}|${student.page}`;
    if (!seen.has(key)) {
      seen.add(key);
      sourceRefs.push({ label: student.sourceLabel, page: student.page, year: student.year });
    }
  }

  return {
    ...profile,
    organization: cleanText(profile.organization),
    parentOrganization: cleanText(profile.parentOrganization),
    profileFocus: cleanText(profile.profileFocus),
    summary: cleanText(profile.summary),
    activities: cleanText(profile.activities),
    categories: (profile.categories || []).map(cleanText).filter(Boolean),
    locations: (profile.locations || []).map(cleanText).filter(Boolean),
    contacts,
    students,
    sourceRefs,
    searchText: cleanText(profile.searchText).toLowerCase()
  };
}

function saveSaved() {
  localStorage.setItem("internshipGuideSaved", JSON.stringify([...state.saved]));
}

function showToast(message) {
  el.toast.textContent = message;
  el.toast.classList.add("is-visible");
  window.setTimeout(() => el.toast.classList.remove("is-visible"), 1300);
}

function setupOptions() {
  const fields = [...new Set(state.profiles.flatMap(profile => profile.themes || []))].sort();
  const years = [...new Set(state.profiles.flatMap(profile => profile.years || []))].sort((a, b) => Number(b) - Number(a));

  for (const field of fields) {
    const option = document.createElement("option");
    option.value = field;
    option.textContent = field;
    el.field.append(option);
  }

  for (const year of years) {
    const option = document.createElement("option");
    option.value = year;
    option.textContent = year;
    el.year.append(option);
  }
}

function matchQuick(profile) {
  if (state.quick === "all") return true;
  if (["Remote", "Eastside"].includes(state.quick)) return profile.locationGroup === state.quick;
  return profile.themes?.includes(state.quick);
}

function filteredProfiles() {
  const query = state.query.toLowerCase();
  const results = state.profiles.filter(profile => {
    if (query && !profile.searchText.includes(query)) return false;
    if (!matchQuick(profile)) return false;
    if (state.field && !profile.themes?.includes(state.field)) return false;
    if (state.year && !profile.years?.includes(state.year)) return false;
    if (state.hasEmail && !hasDirectEmail(profile)) return false;
    if (state.recentOnly && !isRecent(profile)) return false;
    if (state.repeatOnly && profile.studentCount < 2) return false;
    if (state.hideOcr && profile.ocrRecovered) return false;
    if (state.savedOnly && !state.saved.has(profile.organization)) return false;
    return true;
  });

  if (state.sort === "recent") {
    results.sort((a, b) => Math.max(...b.years.map(Number)) - Math.max(...a.years.map(Number)) || b.studentCount - a.studentCount);
  } else if (state.sort === "students") {
    results.sort((a, b) => b.studentCount - a.studentCount || a.organization.localeCompare(b.organization));
  } else if (state.sort === "name") {
    results.sort((a, b) => a.organization.localeCompare(b.organization));
  } else {
    results.sort((a, b) => b.fitScore - a.fitScore || b.studentCount - a.studentCount || a.organization.localeCompare(b.organization));
  }
  return results;
}

function contactHref(profile, contact) {
  const subject = `Senior internship question - ${profile.organization}`;
  const alumni = profile.students.slice(0, 4).map(student => `${student.name} (${student.year})`).join(", ");
  const body = [
    `Hello ${contact.name || ""},`,
    "",
    `I am interested in a senior internship with ${profile.organization}. I found this opportunity through past Interlake internship catalogs${alumni ? `, where students like ${alumni} were listed` : ""}.`,
    "",
    "Would you be open to sharing whether you may be taking interns for the upcoming school year?",
    "",
    "Thank you,"
  ].join("\n");
  return `mailto:${encodeURIComponent(contact.email)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}

function profileText(profile) {
  const contacts = profile.contacts?.length
    ? profile.contacts.map(contact => `${contact.name ? `${contact.name} - ` : ""}${contact.email}`).join("; ")
    : "No direct mentor email found";
  const students = profile.students.slice(0, 12).map(student => `${student.name} (${student.year})`).join(", ");
  const sources = profile.sourceRefs.slice(0, 12).map(ref => `${ref.label}${ref.page ? ` p.${ref.page}` : ""}`).join("; ");
  return [
    profile.organization,
    profile.parentOrganization && profile.parentOrganization !== profile.organization ? `Larger organization: ${profile.parentOrganization}` : "",
    profile.profileFocus ? `Mentor/lab focus: ${profile.profileFocus}` : "",
    `Catalog fields: ${(profile.themes || []).join(", ")}`,
    `Location: ${(profile.locations || []).join(", ") || profile.locationGroup}`,
    `Past placements: ${profile.studentCount} (${(profile.years || []).join(", ")})`,
    `Contacts: ${contacts}`,
    `What interns did: ${profile.summary}`,
    `Past students: ${students}`,
    profile.web?.url ? `Outside source: ${cleanText(profile.web.note)} (${profile.web.url})` : "",
    `Catalog sources: ${sources}`
  ].filter(Boolean).join("\n");
}

function renderSaved() {
  el.savedCount.textContent = state.saved.size;
  const savedProfiles = state.profiles.filter(profile => state.saved.has(profile.organization));
  el.savedList.innerHTML = "";

  if (!savedProfiles.length) {
    const empty = document.createElement("p");
    empty.className = "empty-note";
    empty.textContent = "Nothing saved yet.";
    el.savedList.append(empty);
    return;
  }

  for (const profile of savedProfiles) {
    const item = document.createElement("div");
    item.className = "saved-item";
    item.innerHTML = `<strong>${profile.organization}</strong><span>${profile.studentCount} past placement${profile.studentCount === 1 ? "" : "s"}</span>`;
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "Remove";
    remove.addEventListener("click", () => {
      state.saved.delete(profile.organization);
      saveSaved();
      render();
    });
    item.append(remove);
    el.savedList.append(item);
  }
}

function tag(text, kind = "") {
  const span = document.createElement("span");
  span.className = `tag ${kind}`.trim();
  span.textContent = text;
  return span;
}

function renderCard(profile) {
  const node = el.template.content.firstElementChild.cloneNode(true);
  node.dataset.org = profile.organization;
  const parentLabel = profile.parentOrganization && profile.parentOrganization !== profile.organization ? `${profile.parentOrganization} - ` : "";
  const focusLabel = profile.profileFocus ? `Mentor/lab: ${profile.profileFocus} - ` : "";
  node.querySelector(".card-kicker").textContent = `${parentLabel}${focusLabel}${profile.locationGroup} - ${profile.studentCount} past placement${profile.studentCount === 1 ? "" : "s"} - ${profile.years.join(", ")}`;
  node.querySelector("h3").textContent = profile.organization;
  node.querySelector(".summary").textContent = short(profile.summary, 420);
  node.querySelector(".activities").textContent = profile.activities ? short(profile.activities, 520) : "No extra activity notes were recovered. Check the past student list and source catalog if you need more detail.";

  const save = node.querySelector(".save-button");
  const isSaved = state.saved.has(profile.organization);
  save.textContent = isSaved ? "Saved" : "Save";
  save.classList.toggle("is-saved", isSaved);
  save.addEventListener("click", () => {
    if (state.saved.has(profile.organization)) state.saved.delete(profile.organization);
    else state.saved.add(profile.organization);
    saveSaved();
    render();
  });

  const tags = node.querySelector(".tags");
  for (const theme of profile.themes.slice(0, 3)) tags.append(tag(theme));
  if (profile.splitProfile) tags.append(tag("mentor/lab group", "good"));
  tags.append(tag("catalog sourced", "good"));
  if (hasDirectEmail(profile)) tags.append(tag("mentor email", "good"));
  if (isRecent(profile)) tags.append(tag("recent", "good"));
  if (profile.ocrRecovered) tags.append(tag("verify OCR", "warn"));
  if (profile.web?.url) tags.append(tag("outside source linked", "good"));

  const contacts = node.querySelector(".contact-row");
  const goodContacts = (profile.contacts || []).slice(0, 3);
  if (goodContacts.length) {
    for (const contact of goodContacts) {
      const link = document.createElement("a");
      link.className = "contact-link";
      link.href = contactHref(profile, contact);
      link.textContent = contact.name ? `${contact.name} - ${contact.email}` : contact.email;
      contacts.append(link);
    }
  } else {
    contacts.append(tag("No direct email in catalog", "warn"));
  }
  const copy = document.createElement("button");
  copy.className = "copy-link";
  copy.type = "button";
  copy.textContent = "Copy profile";
  copy.addEventListener("click", () => navigator.clipboard.writeText(profileText(profile)).then(() => showToast("Profile copied")));
  contacts.append(copy);

  const students = node.querySelector(".students");
  for (const student of profile.students.slice(0, 10)) {
    const li = document.createElement("li");
    li.textContent = `${student.name} (${student.year})${student.category ? ` - ${student.category}` : ""} - ${student.sourceLabel}${student.page ? `, p. ${student.page}` : ""}`;
    students.append(li);
  }

  const sourceBlock = node.querySelector(".source-block");
  const sourceHeading = document.createElement("h4");
  sourceHeading.textContent = "Sources";
  sourceBlock.append(sourceHeading);
  const sourceList = document.createElement("ul");
  sourceList.className = "sources";
  for (const ref of profile.sourceRefs.slice(0, 8)) {
    const li = document.createElement("li");
    li.textContent = `${ref.label}${ref.page ? `, p. ${ref.page}` : ""}`;
    sourceList.append(li);
  }
  if (profile.web?.url && profile.web?.verified) {
    const li = document.createElement("li");
    const link = document.createElement("a");
    link.href = profile.web.url;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = profile.web.label || "outside source";
    li.append("Outside source: ", link, ` - ${cleanText(profile.web.note)}`);
    sourceList.append(li);
  }
  if (profile.ocrRecovered) {
    const li = document.createElement("li");
    li.textContent = "Some entries came from scanned catalog pages using OCR. Use the listed catalog/page before sending important emails.";
    sourceList.append(li);
  }
  sourceBlock.append(sourceList);

  return node;
}

function render() {
  document.body.classList.toggle("compact", state.compactView);
  const results = filteredProfiles();
  el.profileCount.textContent = state.profiles.length;
  el.resultSummary.textContent = `${results.length} matching profile${results.length === 1 ? "" : "s"} - ${results.reduce((sum, profile) => sum + profile.studentCount, 0)} past placement examples`;
  el.cards.innerHTML = "";

  if (!results.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "No matches. Try clearing one setting or searching a broader word like research, law, health, remote, or Bellevue.";
    el.cards.append(empty);
  } else {
    for (const profile of results.slice(0, 80)) {
      el.cards.append(renderCard(profile));
    }
  }
  renderSaved();
}

function resetFilters() {
  state.query = "";
  state.quick = "all";
  state.field = "";
  state.year = "";
  state.sort = "fit";
  state.hasEmail = false;
  state.recentOnly = false;
  state.repeatOnly = false;
  state.hideOcr = false;
  state.savedOnly = false;
  el.search.value = "";
  el.field.value = "";
  el.year.value = "";
  el.sort.value = "fit";
  for (const input of [el.hasEmail, el.recentOnly, el.repeatOnly, el.hideOcr, el.savedOnly]) input.checked = false;
  document.querySelectorAll(".quick-filter").forEach(button => button.classList.toggle("is-active", button.dataset.filter === "all"));
  render();
}

function bindEvents() {
  el.search.addEventListener("input", event => {
    state.query = event.target.value;
    render();
  });
  el.settingsButton.addEventListener("click", () => {
    const isOpen = !el.settingsPanel.hidden;
    el.settingsPanel.hidden = isOpen;
    el.settingsButton.setAttribute("aria-expanded", String(!isOpen));
  });
  document.querySelectorAll(".quick-filter").forEach(button => {
    button.addEventListener("click", () => {
      state.quick = button.dataset.filter;
      document.querySelectorAll(".quick-filter").forEach(item => item.classList.toggle("is-active", item === button));
      render();
    });
  });
  el.field.addEventListener("change", event => {
    state.field = event.target.value;
    render();
  });
  el.year.addEventListener("change", event => {
    state.year = event.target.value;
    render();
  });
  el.sort.addEventListener("change", event => {
    state.sort = event.target.value;
    render();
  });
  for (const [key, input] of [
    ["hasEmail", el.hasEmail],
    ["recentOnly", el.recentOnly],
    ["repeatOnly", el.repeatOnly],
    ["hideOcr", el.hideOcr],
    ["savedOnly", el.savedOnly],
    ["compactView", el.compactView]
  ]) {
    input.addEventListener("change", event => {
      state[key] = event.target.checked;
      render();
    });
  }
  el.copySaved.addEventListener("click", () => {
    const savedProfiles = state.profiles.filter(profile => state.saved.has(profile.organization));
    if (!savedProfiles.length) return showToast("Nothing saved yet");
    navigator.clipboard.writeText(savedProfiles.map(profileText).join("\n\n---\n\n")).then(() => showToast("Shortlist copied"));
  });
  el.clearSaved.addEventListener("click", () => {
    state.saved.clear();
    saveSaved();
    render();
  });
  el.resetFilters.addEventListener("click", resetFilters);
}

async function init() {
  const response = await fetch("./profiles.json");
  if (!response.ok) throw new Error("Could not load internship profiles");
  state.profiles = (await response.json()).map(normalizeProfile);
  setupOptions();
  bindEvents();
  render();
}

init().catch(error => {
  el.cards.innerHTML = `<div class="empty">Something went wrong loading the guide: ${error.message}</div>`;
});
