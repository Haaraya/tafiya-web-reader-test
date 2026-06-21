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

## Checkpoint 5 — books.json Homepage Catalog Working

Date: 2026-06-21

Status: Working

Confirmed:

- Root homepage works:
  - https://haaraya.github.io/tafiya-web-reader-test/

- Homepage now loads book cards from:
  - books.json

- books.json works at:
  - https://haaraya.github.io/tafiya-web-reader-test/books.json

- Current catalog books:
  - T4-NF-01 — How We Cook Jollof Rice
  - T4-NF-02 — The Keke Napep

- Homepage book buttons correctly open:
  - /reader/?book=T4-NF-01
  - /reader/?book=T4-NF-02

- Reader route still works:
  - https://haaraya.github.io/tafiya-web-reader-test/reader/?book=T4-NF-01
  - https://haaraya.github.io/tafiya-web-reader-test/reader/?book=T4-NF-02

- Homepage has a fallback book list if books.json fails.

Current clean structure:

root / = homepage  
books.json = homepage catalog  
/reader/ = book reader

Next planned step:

Add simple homepage library filtering by level/type only after more books exist.

## Checkpoint 6 — Library Skeleton with Coming Soon Books Working

Date: 2026-06-21

Status: Working

Confirmed:

- Root homepage works:
  - https://haaraya.github.io/tafiya-web-reader-test/

- Homepage loads catalog from:
  - books.json

- Catalog now contains 4 books:
  - T4-NF-01 — How We Cook Jollof Rice — available
  - T4-NF-02 — The Keke Napep — available
  - T4-F-03 — Amina Goes to the Farm — coming soon
  - T4-F-04 — Come to the River — coming soon

- Homepage correctly shows:
  - available books with “Read this book”
  - coming-soon books with “Coming soon”

- Coming-soon books do not open broken reader links.

- Reader route still works:
  - /reader/?book=T4-NF-01
  - /reader/?book=T4-NF-02

Next planned step:

Load T4-F-03 into Supabase and turn it from coming_soon to available after the reader link works.
