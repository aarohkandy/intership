import { readFileSync, writeFileSync } from "node:fs";

const input = JSON.parse(readFileSync("profiles.json", "utf8"));

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

const isGoodEmail = email => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(email || "")) && !String(email || "").toLowerCase().startsWith("s-");

const isProbablyStudent = student => {
  const name = cleanText(student?.name);
  if (!name || name.length > 70 || name.includes("@")) return false;
  if (/mentor|category|company|location|email|internship/i.test(name)) return false;
  return true;
};

const publicProfiles = input.map(profile => {
  const students = (profile.students || [])
    .filter(isProbablyStudent)
    .map(student => ({
      name: cleanText(student.name),
      year: cleanText(student.year),
      category: cleanText(student.category),
      source: cleanText(student.source),
      page: cleanText(student.page)
    }));

  const contacts = (profile.contacts || [])
    .filter(contact => isGoodEmail(contact.email))
    .map(contact => ({
      name: cleanText(contact.name).replace(/^n\/a$/i, ""),
      email: cleanText(contact.email)
    }));

  const publicProfile = {
    organization: cleanText(profile.organization),
    themes: (profile.themes || []).map(cleanText).filter(Boolean),
    categories: (profile.categories || []).map(cleanText).filter(Boolean),
    locations: (profile.locations || []).map(cleanText).filter(Boolean),
    locationGroup: cleanText(profile.locationGroup),
    years: (profile.years || []).map(cleanText).filter(Boolean),
    studentCount: students.length,
    fitScore: Number(profile.fitScore || 0),
    contacts,
    students,
    summary: cleanText(profile.summary),
    activities: cleanText(profile.activities),
    web: profile.web?.url ? {
      url: cleanText(profile.web.url),
      label: cleanText(profile.web.label),
      note: cleanText(profile.web.note),
      verified: Boolean(profile.web.verified)
    } : {},
    ocrRecovered: Boolean(profile.ocrRecovered)
  };

  publicProfile.searchText = [
    publicProfile.organization,
    publicProfile.themes.join(" "),
    publicProfile.categories.join(" "),
    publicProfile.locations.join(" "),
    publicProfile.locationGroup,
    publicProfile.years.join(" "),
    publicProfile.contacts.map(contact => `${contact.name} ${contact.email}`).join(" "),
    publicProfile.students.map(student => `${student.name} ${student.category}`).join(" "),
    publicProfile.summary,
    publicProfile.activities,
    publicProfile.web.note || ""
  ].join(" ").toLowerCase();

  return publicProfile;
}).filter(profile => profile.organization && profile.students.length);

writeFileSync("profiles.json", `${JSON.stringify(publicProfiles, null, 2)}\n`, "utf8");

const placementCount = publicProfiles.reduce((sum, profile) => sum + profile.studentCount, 0);
console.log(`profiles=${publicProfiles.length} placements=${placementCount}`);
