# Haaraya / Tafiya Build Checkpoints

## Checkpoint 1 — Homepage + Reader Route Working

Date: 2026-06-21

Status: Working

Confirmed:

* Root homepage works:

  * https://haaraya.github.io/tafiya-web-reader-test/

* Reader route works:

  * https://haaraya.github.io/tafiya-web-reader-test/reader/?book=T4-NF-01
  * https://haaraya.github.io/tafiya-web-reader-test/reader/?book=T4-NF-02

* Supabase fetch works.

* Reader uses book codes in the URL, not numeric IDs.

* Current working books:

  * T4-NF-01 — How We Cook Jollof Rice
  * T4-NF-02 — The Keke Napep

Current structure:

root / = homepage
/reader/ = book reader

Do not start yet:

* user accounts
* school dashboards
* payments
* subscriptions
* assessments
* reports
* offline downloads

Next planned step:

Polish the homepage so it feels more like the Haaraya website prototype while keeping only the two working books for now.

## Checkpoint 2 — Homepage Polish v2 Working

Date: 2026-06-21

Status: Working

Confirmed:

- Root homepage now uses stronger Haaraya-style branding.
- Homepage opens at:
  - https://haaraya.github.io/tafiya-web-reader-test/

- Reader still works at:
  - https://haaraya.github.io/tafiya-web-reader-test/reader/?book=T4-NF-01
  - https://haaraya.github.io/tafiya-web-reader-test/reader/?book=T4-NF-02

- Homepage book buttons correctly open the /reader/ route.
- Supabase book loading still works.
- Current reader files inside /reader/ remain untouched.

Next planned step:

Clean up the repo gently and decide whether to remove the old root reader.css and reader.js files after confirming nothing depends on them.

## Checkpoint 3 — Repo Cleanup Working

Date: 2026-06-21

Status: Working

Confirmed:

* Old root reader files were removed:

  * old-root-reader.css
  * old-root-reader.js

* Root homepage still works:

  * https://haaraya.github.io/tafiya-web-reader-test/

* Reader route still works:

  * https://haaraya.github.io/tafiya-web-reader-test/reader/?book=T4-NF-01
  * https://haaraya.github.io/tafiya-web-reader-test/reader/?book=T4-NF-02

* Final clean structure is now:

root / = homepage
/reader/ = book reader

Current working files:

* index.html
* reader/index.html
* reader/reader.css
* reader/reader.js
* CHECKPOINTS.md

Next planned step:

Connect the homepage/library area more cleanly to the future Haaraya website structure while keeping the reader stable.

## Checkpoint 4 — Data-Driven Homepage Library Working

Date: 2026-06-21

Status: Working

Confirmed:

- Root homepage still works:
  - https://haaraya.github.io/tafiya-web-reader-test/

- Homepage book cards are now rendered from one BOOKS list inside root index.html.

- Current homepage books:
  - T4-NF-01 — How We Cook Jollof Rice
  - T4-NF-02 — The Keke Napep

- Book card buttons correctly open:
  - /reader/?book=T4-NF-01
  - /reader/?book=T4-NF-02

- Reader route still works:
  - https://haaraya.github.io/tafiya-web-reader-test/reader/?book=T4-NF-01
  - https://haaraya.github.io/tafiya-web-reader-test/reader/?book=T4-NF-02

- Supabase reader loading still works.

Current clean structure:

root / = homepage  
/reader/ = book reader

Next planned step:

Move the homepage book list out of index.html into a small catalog file later, or connect the homepage library to Supabase when the catalog fields are stable.

