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
