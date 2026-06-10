# intership

Static senior internship guide built from Interlake internship/job fair catalogs.

The Vercel entry point is `index.html`, with no framework or build step required.

## Source Policy

- Internship names, contacts, locations, student names, categories, and descriptions come from the provided catalog PDFs.
- Scanned 2022-2024 catalog entries were recovered with OCR and are marked in the UI as `verify OCR`.
- Outside notes are shown only when a source link is attached.
- The public `profiles.json` is sanitized to remove obvious OCR label artifacts before display.

## Main Files

- `index.html` - Vercel/default static entry point.
- `styles.css` - site styling.
- `app.js` - search, filters, shortlist, copy, and source display.
- `profiles.json` - sanitized public internship profile data.
- `internship_research/internship_profiles_copyable.md` - copy/paste profile catalog.
- `internship_research/internship_entries.csv` - raw parsed placement rows.
- `scripts/sanitize_profiles.mjs` - regenerates sanitized `profiles.json`.
