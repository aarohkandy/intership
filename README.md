# intership

Static senior internship guide built from Interlake internship/job fair catalogs.

The Vercel entry point is `index.html`, with no framework or build step required.

## Source Policy

- Internship names, contacts, locations, student names, categories, and descriptions come from the provided catalog PDFs.
- Scanned 2022-2024 catalog entries were recovered with OCR and are marked in the UI as `verify OCR`.
- Outside notes are shown only when a source link is attached.
- The public `profiles.json` is generated from raw placement rows and splits broad institutions into mentor/lab/contact groups when the catalog data supports it.
- Obvious OCR contact artifacts are not promoted as email buttons when a clean sourced contact is available, or when the source field says the email was `N/A`.

## Main Files

- `index.html` - Vercel/default static entry point.
- `styles.css` - site styling.
- `app.js` - search, filters, shortlist, copy, and source display.
- `profiles.json` - sanitized public internship profile data.
- `internship_research/internship_entries.json` - parsed placement rows used to rebuild public profiles.
- `internship_research/internship_profiles_copyable.md` - copy/paste profile catalog.
- `internship_research/internship_entries.csv` - raw parsed placement rows.
- `scripts/build_public_profiles.mjs` - regenerates public `profiles.json` from parsed catalog entries.
- `scripts/sanitize_profiles.mjs` - older sanitizer for already-built profile data.
