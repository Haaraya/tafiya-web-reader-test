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
