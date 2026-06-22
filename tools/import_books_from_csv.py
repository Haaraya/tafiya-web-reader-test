from __future__ import annotations

import csv
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests


# ============================================================
# Haaraya / Tafiya Importer v1
#
# Run from repo root:
#   python tools/import_books_from_csv.py
#
# This version:
# - imports ONLY the four working test books
# - does NOT upload images
# - validates that images already exist in Supabase Storage
# - upserts books
# - deletes/reinserts book_pages
# - deletes/reinserts book_skills
# - regenerates/updates books.json
# ============================================================


REPO_ROOT = Path(__file__).resolve().parents[1]

SOURCE_DIR = REPO_ROOT / "import_sources"
COVER_CSV = SOURCE_DIR / "Tafiya_Cover_Merge.csv"
PAGES_CSV = SOURCE_DIR / "Tafiya_Pages_Merge.csv"
BACK_COVER_CSV = SOURCE_DIR / "Tafiya_BackCover_Merge.csv"

BOOKS_JSON = REPO_ROOT / "books.json"

STORAGE_BUCKET = "book-assets"

BOOK_CODES_TO_IMPORT = [
    "T4-NF-01",
    "T4-NF-02",
    "T4-F-03",
    "T4-F-04",
]

EXPECTED_PAGE_COUNTS = {
    "T4-NF-01": 8,
    "T4-NF-02": 8,
    "T4-F-03": 8,
    "T4-F-04": 8,
}

TOPIC_OVERRIDES = {
    "T4-NF-01": "Food",
    "T4-NF-02": "Transport",
}

DEFAULT_LAYOUT = "image_top_text_bottom"
DEFAULT_TEXT_BAND = "bottom"


def die(message: str) -> None:
    print(f"\nERROR: {message}")
    sys.exit(1)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_env_file() -> None:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        die(f"Missing CSV file: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def clean_text(value) -> str:
    if value is None:
        return ""
    return str(value).replace("\ufeff", "").strip()


def count_words(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9’']+", clean_text(text)))


def page_number_from_label(page_label: str) -> int:
    label = clean_text(page_label).upper()
    match = re.fullmatch(r"P(\d+)", label)
    if not match:
        raise ValueError(f"Bad page_num value: {page_label!r}")
    return int(match.group(1))


def derive_book_type(book_code: str) -> str:
    if "-NF-" in book_code:
        return "Non-Fiction"
    if "-FT-" in book_code:
        return "Folktale"
    if "-C-" in book_code:
        return "Concept"
    if "-P-" in book_code:
        return "Poetry"
    if "-F-" in book_code:
        return "Fiction"
    return "Tafiya"


def storage_path_for_cover(book_code: str) -> str:
    return f"books/{book_code}/{book_code}_FC.png"


def storage_path_for_page(book_code: str, page_number: int) -> str:
    return f"books/{book_code}/{book_code}_P{page_number}.png"


class SupabaseClient:
    def __init__(self, url: str, service_role_key: str):
        self.url = url.rstrip("/")
        self.key = service_role_key

        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def request(self, method: str, path: str, *, params=None, json_body=None, prefer=None):
        headers = dict(self.headers)
        if prefer:
            headers["Prefer"] = prefer

        endpoint = f"{self.url}{path}"
        response = requests.request(
            method,
            endpoint,
            headers=headers,
            params=params,
            json=json_body,
            timeout=60,
        )

        if not response.ok:
            detail = response.text[:2000]
            raise RuntimeError(
                f"{method} {endpoint} failed: {response.status_code} {response.reason}\n{detail}"
            )

        if response.text.strip():
            return response.json()

        return None

    def storage_object_exists(self, object_path: str) -> bool:
        public_url = (
            f"{self.url}/storage/v1/object/public/"
            f"{STORAGE_BUCKET}/{quote(object_path, safe='/')}"
        )

        response = requests.head(public_url, timeout=30)

        if response.status_code in (200, 206):
            return True

        # Some storage/CDN layers do not answer HEAD properly.
        response = requests.get(
            public_url,
            headers={"Range": "bytes=0-0"},
            timeout=30,
        )

        return response.status_code in (200, 206)

    def get_book_by_code(self, book_code: str) -> dict | None:
        rows = self.request(
            "GET",
            "/rest/v1/books",
            params={
                "book_code": f"eq.{book_code}",
                "select": "*",
                "limit": "1",
            },
        )
        return rows[0] if rows else None

    def upsert_book(self, payload: dict) -> dict:
        existing = self.get_book_by_code(payload["book_code"])

        if existing:
            updated = dict(payload)
            updated["updated_at"] = now_iso()

            rows = self.request(
                "PATCH",
                "/rest/v1/books",
                params={
                    "book_code": f"eq.{payload['book_code']}",
                    "select": "*",
                },
                json_body=updated,
                prefer="return=representation",
            )
            return rows[0]

        created = dict(payload)
        stamp = now_iso()
        created["created_at"] = stamp
        created["updated_at"] = stamp

        rows = self.request(
            "POST",
            "/rest/v1/books",
            params={"select": "*"},
            json_body=created,
            prefer="return=representation",
        )
        return rows[0]

    def replace_pages(self, book_id: str, pages: list[dict]) -> None:
        self.request(
            "DELETE",
            "/rest/v1/book_pages",
            params={"book_id": f"eq.{book_id}"},
            prefer="return=minimal",
        )

        if pages:
            self.request(
                "POST",
                "/rest/v1/book_pages",
                json_body=pages,
                prefer="return=minimal",
            )

    def replace_skills(self, book_id: str, skills: dict) -> None:
        self.request(
            "DELETE",
            "/rest/v1/book_skills",
            params={"book_id": f"eq.{book_id}"},
            prefer="return=minimal",
        )

        self.request(
            "POST",
            "/rest/v1/book_skills",
            json_body=skills,
            prefer="return=minimal",
        )


def build_source_maps():
    cover_rows = read_csv(COVER_CSV)
    page_rows = read_csv(PAGES_CSV)
    back_rows = read_csv(BACK_COVER_CSV)

    covers_by_code = {}
    for row in cover_rows:
        code = clean_text(row.get("book_code"))
        if code:
            covers_by_code[code] = row

    pages_by_code = {}
    for row in page_rows:
        code = clean_text(row.get("book_code"))
        if code:
            pages_by_code.setdefault(code, []).append(row)

    backs_by_code = {}
    for row in back_rows:
        code = clean_text(row.get("book_code"))
        if code:
            backs_by_code[code] = row

    return covers_by_code, pages_by_code, backs_by_code


def validate_sources(covers_by_code, pages_by_code, backs_by_code, client: SupabaseClient):
    errors = []

    for code in BOOK_CODES_TO_IMPORT:
        if code not in covers_by_code:
            errors.append(f"{code}: missing cover row")
            continue

        if code not in pages_by_code:
            errors.append(f"{code}: missing page rows")
            continue

        if code not in backs_by_code:
            errors.append(f"{code}: missing back-cover/skills row")
            continue

        pages = pages_by_code[code]

        page_numbers = []
        for row in pages:
            try:
                page_no = page_number_from_label(row.get("page_num", ""))
                page_numbers.append(page_no)
            except ValueError as exc:
                errors.append(f"{code}: {exc}")

            if not clean_text(row.get("page_text")):
                errors.append(f"{code}: blank page_text on {row.get('page_num')}")

        page_numbers_sorted = sorted(page_numbers)
        expected_sequence = list(range(1, len(page_numbers_sorted) + 1))

        if page_numbers_sorted != expected_sequence:
            errors.append(
                f"{code}: page numbers are not consecutive. "
                f"Found {page_numbers_sorted}, expected {expected_sequence}"
            )

        expected_count = EXPECTED_PAGE_COUNTS.get(code)
        if expected_count and len(page_numbers_sorted) != expected_count:
            errors.append(
                f"{code}: expected {expected_count} pages, found {len(page_numbers_sorted)}"
            )

        cover_title = clean_text(covers_by_code[code].get("book_title"))
        back_title = clean_text(backs_by_code[code].get("book_title"))

        if cover_title and back_title and cover_title != back_title:
            print(f"WARNING: {code} title mismatch: cover={cover_title!r}, back={back_title!r}")

        cover_path = storage_path_for_cover(code)
        if not client.storage_object_exists(cover_path):
            errors.append(f"{code}: missing Supabase cover image: {cover_path}")

        for page_no in page_numbers_sorted:
            image_path = storage_path_for_page(code, page_no)
            if not client.storage_object_exists(image_path):
                errors.append(f"{code}: missing Supabase page image: {image_path}")

    if errors:
        print("\nVALIDATION FAILED")
        for error in errors:
            print(f"- {error}")
        sys.exit(1)

    print("Validation passed.")


def build_book_payload(code: str, cover_row: dict) -> dict:
    book_type = derive_book_type(code)
    topic = TOPIC_OVERRIDES.get(code)

    return {
        "book_code": code,
        "title": clean_text(cover_row.get("book_title")),
        "strand": "Tafiya",
        "level": clean_text(cover_row.get("level")),
        "tafiya_name": clean_text(cover_row.get("tafiya_name")),
        "book_type": book_type,
        "theme": None,
        "topic": topic,
        "cover_image_path": storage_path_for_cover(code),
        "status": "approved",
    }


def build_page_payloads(code: str, book_id: str, page_rows: list[dict]) -> list[dict]:
    stamp = now_iso()
    cleaned = []

    for row in page_rows:
        page_no = page_number_from_label(row.get("page_num", ""))
        page_text = clean_text(row.get("page_text"))

        cleaned.append(
            {
                "book_id": book_id,
                "page_number": page_no,
                "page_text": page_text,
                "image_path": storage_path_for_page(code, page_no),
                "layout": DEFAULT_LAYOUT,
                "text_band": DEFAULT_TEXT_BAND,
                "word_count": count_words(page_text),
                "created_at": stamp,
                "updated_at": stamp,
            }
        )

    return sorted(cleaned, key=lambda r: r["page_number"])


def build_skills_payload(code: str, book_id: str, back_row: dict, pages: list[dict]) -> dict:
    stamp = now_iso()

    return {
        "book_id": book_id,
        "reading_strategy": clean_text(back_row.get("eb_reading_strategy")),
        "comprehension_skill": clean_text(back_row.get("eb_comprehension_skill")),
        "phonological_awareness": clean_text(back_row.get("eb_phonological_awareness")),
        "grammar_mechanics": clean_text(back_row.get("eb_grammar_mechanics")),
        "word_work": clean_text(back_row.get("eb_word_work")),
        "text_structure": clean_text(back_row.get("eb_text_structure")),
        "topic": TOPIC_OVERRIDES.get(code),
        "key_vocabulary": None,
        "total_word_count": sum(int(p.get("word_count") or 0) for p in pages),
        "about_text": clean_text(back_row.get("back_about_text")),
        "fp_level": clean_text(back_row.get("back_fp_level")),
        "uk_book_band": clean_text(back_row.get("back_uk_book_band")),
        "website": "haarayaeducation.org",
        "created_at": stamp,
        "updated_at": stamp,
    }


def load_existing_catalog() -> list[dict]:
    if not BOOKS_JSON.exists():
        return []

    try:
        return json.loads(BOOKS_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        die(f"books.json is not valid JSON: {BOOKS_JSON}")


def update_books_json(imported_catalog_rows: list[dict]) -> None:
    existing = load_existing_catalog()
    by_code = {
        clean_text(item.get("book_code")): dict(item)
        for item in existing
        if clean_text(item.get("book_code"))
    }

    for row in imported_catalog_rows:
        code = row["book_code"]
        old = by_code.get(code, {})

        merged = dict(old)
        merged.update(row)

        by_code[code] = merged

    catalog = list(by_code.values())
    catalog.sort(key=lambda item: int(item.get("sort_order") or 999999))

    BOOKS_JSON.write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    load_env_file()

    supabase_url = os.environ.get("SUPABASE_URL", "").strip()
    service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()

    if not supabase_url:
        die("Missing SUPABASE_URL in .env")

    if not service_role_key:
        die("Missing SUPABASE_SERVICE_ROLE_KEY in .env")

    if service_role_key.startswith("sb_publishable_"):
        die("You pasted the publishable key. This importer needs the service role key.")

    client = SupabaseClient(supabase_url, service_role_key)

    covers_by_code, pages_by_code, backs_by_code = build_source_maps()

    print("Validating CSV rows and Supabase image paths...")
    validate_sources(covers_by_code, pages_by_code, backs_by_code, client)

    imported_catalog_rows = []

    print("\nImporting books...")
    for index, code in enumerate(BOOK_CODES_TO_IMPORT, start=1):
        cover_row = covers_by_code[code]
        back_row = backs_by_code[code]
        page_rows = pages_by_code[code]

        book_payload = build_book_payload(code, cover_row)
        book = client.upsert_book(book_payload)
        book_id = book["id"]

        pages = build_page_payloads(code, book_id, page_rows)
        skills = build_skills_payload(code, book_id, back_row, pages)

        client.replace_pages(book_id, pages)
        client.replace_skills(book_id, skills)

        imported_catalog_rows.append(
            {
                "book_code": code,
                "title": book_payload["title"],
                "level_label": book_payload["level"],
                "strand": book_payload["strand"],
                "book_type": book_payload["book_type"],
                "short_description": clean_text(back_row.get("back_about_text")),
                "featured": True,
                "status": "available",
                "sort_order": index,
                "reader_url": f"reader/?book={code}",
            }
        )

        print(f"- {code}: imported {len(pages)} pages")

    update_books_json(imported_catalog_rows)

    print("\nDONE")
    print(f"Imported books: {len(BOOK_CODES_TO_IMPORT)}")
    print(f"Updated: {BOOKS_JSON}")


if __name__ == "__main__":
    main()
