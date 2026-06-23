#!/usr/bin/env python3
"""
Safe Haaraya/Tafiya CSV importer.

What it does:
- Reads Tafiya_Cover_Merge.csv, Tafiya_Pages_Merge.csv, Tafiya_BackCover_Merge.csv
- Skips poetry books
- Requires exactly FC + P1-P8 images
- Requires exactly P1-P8 page rows
- Skips books with bad/missing metadata
- Upserts safe books into Supabase
- Replaces old pages/skills for each imported book
- Updates books.json for the library

Run dry first:
python tools/import_books_from_csv.py --dry-run --image-root "C:\\path\\to\\generated-images"

Then real import:
python tools/import_books_from_csv.py --image-root "C:\\path\\to\\generated-images"
"""

import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import requests


DEFAULT_COVER_CSV = "import_sources/Tafiya_Cover_Merge.csv"
DEFAULT_PAGES_CSV = "import_sources/Tafiya_Pages_Merge.csv"
DEFAULT_BACK_CSV = "import_sources/Tafiya_BackCover_Merge.csv"
DEFAULT_BOOKS_JSON = "books.json"
DEFAULT_BUCKET = "book-assets"

BOOK_TYPE_LABELS = {
    "F": "Fiction",
    "NF": "Non-Fiction",
    "FT": "Folktale",
    "C": "Concept",
    "P": "Poetry",
}

EXPECTED_PAGE_LABELS = [f"P{i}" for i in range(1, 9)]
EXPECTED_IMAGE_SUFFIXES = ["FC"] + EXPECTED_PAGE_LABELS
IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp"]


def load_dotenv(path=".env"):
    env_path = Path(path)
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


def clean(value):
    return (value or "").strip()


def read_csv_rows(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def parse_book_code(code):
    """
    Expected examples:
    T4-NF-01
    T4-F-03
    T1-C-02
    T4-FT-01
    T4-P-01
    """
    code = clean(code)
    match = re.match(r"^T(\d+)-([A-Z]+)-(\d+)$", code)
    if not match:
        return None

    return {
        "level": int(match.group(1)),
        "type_code": match.group(2),
        "sequence": int(match.group(3)),
    }


def natural_book_sort_key(code):
    parsed = parse_book_code(code)
    if not parsed:
        return (999, "ZZZ", 999, code)

    type_order = {
        "C": 1,
        "F": 2,
        "FT": 3,
        "NF": 4,
        "P": 9,
    }

    return (
        parsed["level"],
        type_order.get(parsed["type_code"], 99),
        parsed["sequence"],
        code,
    )


def is_poetry_book(code, page_rows):
    parsed = parse_book_code(code)
    if parsed and parsed["type_code"] == "P":
        return True

    for row in page_rows:
        if clean(row.get("page_num")).upper() == "POEM":
            return True

    return False


def page_label_to_number(label):
    label = clean(label).upper()
    match = re.match(r"^P(\d+)$", label)
    if not match:
        return None
    return int(match.group(1))


def word_count(text):
    return len(re.findall(r"\b[\w'-]+\b", clean(text)))


def text_band_for(text):
    count = word_count(text)
    if count <= 10:
        return "short"
    if count <= 28:
        return "medium"
    return "long"


def storage_path(book_code, suffix):
    return f"books/{book_code}/{book_code}_{suffix}.png"


def find_case_insensitive_file(path):
    path = Path(path)

    if path.exists():
        return path

    parent = path.parent
    if not parent.exists():
        return None

    wanted = path.name.lower()
    for child in parent.iterdir():
        if child.name.lower() == wanted:
            return child

    return None


def image_candidates(image_root, csv_image_path, book_code, suffix):
    candidates = []

    names = [f"{book_code}_{suffix}{ext}" for ext in IMAGE_EXTENSIONS]

    if suffix == "FC":
        names += [f"{book_code}_COVER{ext}" for ext in IMAGE_EXTENSIONS]

    if image_root:
        root = Path(image_root)
        for name in names:
            candidates.append(root / name)

    raw_path = clean(csv_image_path)
    if raw_path:
        raw = Path(raw_path)
        candidates.append(raw)

        for name in names:
            candidates.append(raw.with_name(name))

    return candidates


def find_image(image_root, csv_image_path, book_code, suffix):
    for candidate in image_candidates(image_root, csv_image_path, book_code, suffix):
        found = find_case_insensitive_file(candidate)
        if found:
            return found
    return None


def index_single(rows, key_name):
    indexed = {}
    duplicates = defaultdict(list)

    for row in rows:
        key = clean(row.get(key_name))
        if not key:
            continue

        if key in indexed:
            duplicates[key].append(row)
        else:
            indexed[key] = row

    return indexed, duplicates


def required_back_fields_missing(back_row):
    fields = [
        "back_fp_level",
        "back_uk_book_band",
        "back_about_text",
        "eb_reading_strategy",
        "eb_comprehension_skill",
        "eb_phonological_awareness",
        "eb_grammar_mechanics",
        "eb_word_work",
        "eb_text_structure",
    ]

    return [field for field in fields if not clean(back_row.get(field))]


def validate_book(code, cover_row, page_rows, back_row, image_root):
    reasons = []

    parsed = parse_book_code(code)
    if not parsed:
        reasons.append("bad book_code format")
        return None, reasons

    if parsed["type_code"] not in BOOK_TYPE_LABELS:
        reasons.append(f"unknown book type: {parsed['type_code']}")

    if is_poetry_book(code, page_rows):
        reasons.append("poetry book skipped")

    if not back_row:
        reasons.append("missing back-cover row")

    if not page_rows:
        reasons.append("missing page rows")

    if reasons:
        return None, reasons

    cover_title = clean(cover_row.get("book_title"))
    back_title = clean(back_row.get("book_title"))
    page_titles = {clean(row.get("book_title")) for row in page_rows if clean(row.get("book_title"))}

    all_titles = {cover_title, back_title, *page_titles}
    all_titles.discard("")

    if len(all_titles) > 1:
        reasons.append(f"title mismatch across CSVs: {sorted(all_titles)}")

    if not cover_title:
        reasons.append("missing title")

    level_text = clean(cover_row.get("level"))
    level_match = re.search(r"\d+", level_text)
    if not level_match:
        reasons.append(f"bad level value: {level_text}")

    tafiya_name = clean(cover_row.get("tafiya_name"))
    if not tafiya_name:
        reasons.append("missing tafiya_name")

    page_map = defaultdict(list)
    for row in page_rows:
        label = clean(row.get("page_num")).upper()
        page_map[label].append(row)

    actual_labels = set(page_map.keys())
    expected_labels = set(EXPECTED_PAGE_LABELS)

    if actual_labels != expected_labels:
        missing = sorted(expected_labels - actual_labels)
        extra = sorted(actual_labels - expected_labels)
        parts = []
        if missing:
            parts.append(f"missing pages {missing}")
        if extra:
            parts.append(f"unexpected pages {extra}")
        reasons.append("; ".join(parts))

    duplicates = [label for label, rows in page_map.items() if len(rows) > 1]
    if duplicates:
        reasons.append(f"duplicate page rows: {sorted(duplicates)}")

    empty_text_pages = []
    for label in EXPECTED_PAGE_LABELS:
        rows = page_map.get(label, [])
        if rows and not clean(rows[0].get("page_text")):
            empty_text_pages.append(label)

    if empty_text_pages:
        reasons.append(f"empty page text: {empty_text_pages}")

    missing_back_fields = required_back_fields_missing(back_row)
    if missing_back_fields:
        reasons.append(f"missing back-cover fields: {missing_back_fields}")

    missing_images = []

    cover_csv_path = cover_row.get("image_path")
    if not find_image(image_root, cover_csv_path, code, "FC"):
        missing_images.append("FC")

    for label in EXPECTED_PAGE_LABELS:
        rows = page_map.get(label, [])
        csv_path = rows[0].get("image_path") if rows else ""
        if not find_image(image_root, csv_path, code, label):
            missing_images.append(label)

    if missing_images:
        reasons.append(f"missing images: {missing_images}")

    if reasons:
        return None, reasons

    sorted_pages = []
    for label in EXPECTED_PAGE_LABELS:
        row = page_map[label][0]
        sorted_pages.append(
            {
                "page_number": page_label_to_number(label),
                "page_text": clean(row.get("page_text")),
                "image_path": storage_path(code, label),
                "layout": "image_top_text_bottom",
                "text_band": text_band_for(row.get("page_text")),
                "word_count": word_count(row.get("page_text")),
            }
        )

    book_type = BOOK_TYPE_LABELS[parsed["type_code"]]
    level_number = int(level_match.group(0))
    total_words = sum(page["word_count"] for page in sorted_pages)

    book = {
        "book_code": code,
        "title": cover_title,
        "strand": "Tafiya",
        "level": level_number,
        "tafiya_name": tafiya_name,
        "book_type": book_type,
        "theme": "",
        "topic": "",
        "cover_image_path": storage_path(code, "FC"),
        "status": "published",
    }

    skills = {
        "about_text": clean(back_row.get("back_about_text")),
        "fp_level": clean(back_row.get("back_fp_level")),
        "uk_book_band": clean(back_row.get("back_uk_book_band")),
        "reading_strategy": clean(back_row.get("eb_reading_strategy")),
        "comprehension_skill": clean(back_row.get("eb_comprehension_skill")),
        "phonological_awareness": clean(back_row.get("eb_phonological_awareness")),
        "grammar_mechanics": clean(back_row.get("eb_grammar_mechanics")),
        "word_work": clean(back_row.get("eb_word_work")),
        "text_structure": clean(back_row.get("eb_text_structure")),
        "topic": "",
        "key_vocabulary": "",
        "total_word_count": total_words,
        "website": "",
    }

    prepared = {
        "book": book,
        "pages": sorted_pages,
        "skills": skills,
    }

    return prepared, []


class SupabaseClient:
    def __init__(self, url, service_key):
        self.url = url.rstrip("/")
        self.service_key = service_key
        self.headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
        }

    def request(self, method, path, json_body=None, prefer=None, expected=(200, 201, 204)):
        headers = dict(self.headers)
        if prefer:
            headers["Prefer"] = prefer

        response = requests.request(
            method,
            f"{self.url}{path}",
            headers=headers,
            json=json_body,
            timeout=60,
        )

        if response.status_code not in expected:
            raise RuntimeError(
                f"Supabase {method} {path} failed: "
                f"{response.status_code} {response.text}"
            )

        if response.status_code == 204 or not response.text:
            return None

        return response.json()

    def upsert_book(self, book):
        data = self.request(
            "POST",
            "/rest/v1/books?on_conflict=book_code",
            json_body=book,
            prefer="resolution=merge-duplicates,return=representation",
            expected=(200, 201),
        )

        if not data:
            raise RuntimeError(f"No book returned after upsert: {book['book_code']}")

        return data[0]["id"]

    def delete_existing_book_children(self, book_id):
        self.request(
            "DELETE",
            f"/rest/v1/book_pages?book_id=eq.{book_id}",
            prefer="return=minimal",
            expected=(200, 204),
        )

        self.request(
            "DELETE",
            f"/rest/v1/book_skills?book_id=eq.{book_id}",
            prefer="return=minimal",
            expected=(200, 204),
        )

    def insert_pages(self, book_id, pages):
        payload = []
        for page in pages:
            row = dict(page)
            row["book_id"] = book_id
            payload.append(row)

        self.request(
            "POST",
            "/rest/v1/book_pages",
            json_body=payload,
            prefer="return=minimal",
            expected=(200, 201),
        )

    def insert_skills(self, book_id, skills):
        payload = dict(skills)
        payload["book_id"] = book_id

        self.request(
            "POST",
            "/rest/v1/book_skills",
            json_body=payload,
            prefer="return=minimal",
            expected=(200, 201),
        )

    def import_book(self, prepared):
        book_id = self.upsert_book(prepared["book"])
        self.delete_existing_book_children(book_id)
        self.insert_pages(book_id, prepared["pages"])
        self.insert_skills(book_id, prepared["skills"])
        return book_id


def build_books_json_payload(imported_books, existing_payload):
    library_books = []

    for book in imported_books:
        code = book["book_code"]
        library_books.append(
            {
                "book_code": code,
                "code": code,
                "title": book["title"],
                "level": book["level"],
                "tafiya_name": book["tafiya_name"],
                "level_name": book["tafiya_name"],
                "book_type": book["book_type"],
                "cover_image_path": book["cover_image_path"],
                "href": f"reader/index.html?book={code}",
                "reader_url": f"reader/index.html?book={code}",
            }
        )

    if isinstance(existing_payload, dict):
        existing_payload["books"] = library_books
        return existing_payload

    return library_books


def write_books_json(path, imported_books):
    path = Path(path)

    existing_payload = None
    if path.exists():
        try:
            existing_payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing_payload = None

    payload = build_books_json_payload(imported_books, existing_payload)

    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def print_skip_report(skipped):
    if not skipped:
        print("Skipped: 0")
        return

    print(f"Skipped: {len(skipped)}")
    for item in skipped:
        code = item["book_code"]
        reasons = "; ".join(item["reasons"])
        print(f"  - {code}: {reasons}")


def parse_only(value):
    if not value:
        return None

    return {
        clean(part)
        for part in re.split(r"[,\s]+", value)
        if clean(part)
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cover-csv", default=DEFAULT_COVER_CSV)
    parser.add_argument("--pages-csv", default=DEFAULT_PAGES_CSV)
    parser.add_argument("--back-csv", default=DEFAULT_BACK_CSV)
    parser.add_argument("--books-json", default=DEFAULT_BOOKS_JSON)
    parser.add_argument("--image-root", default="")
    parser.add_argument("--bucket", default=DEFAULT_BUCKET)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-books-json", action="store_true")
    parser.add_argument("--only", default="", help="Comma/space-separated book codes")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--keep-going", action="store_true")
    args = parser.parse_args()

    load_dotenv()

    cover_rows = read_csv_rows(args.cover_csv)
    page_rows = read_csv_rows(args.pages_csv)
    back_rows = read_csv_rows(args.back_csv)

    cover_by_code, cover_dupes = index_single(cover_rows, "book_code")
    back_by_code, back_dupes = index_single(back_rows, "book_code")

    pages_by_code = defaultdict(list)
    for row in page_rows:
        code = clean(row.get("book_code"))
        if code:
            pages_by_code[code].append(row)

    only_codes = parse_only(args.only)

    prepared_books = []
    skipped = []

    for code in sorted(cover_by_code.keys(), key=natural_book_sort_key):
        if only_codes and code not in only_codes:
            continue

        reasons = []

        if code in cover_dupes:
            reasons.append("duplicate cover rows")

        if code in back_dupes:
            reasons.append("duplicate back-cover rows")

        prepared, validation_reasons = validate_book(
            code=code,
            cover_row=cover_by_code[code],
            page_rows=pages_by_code.get(code, []),
            back_row=back_by_code.get(code),
            image_root=args.image_root,
        )

        reasons.extend(validation_reasons)

        if reasons:
            skipped.append(
                {
                    "book_code": code,
                    "reasons": reasons,
                }
            )
            continue

        prepared_books.append(prepared)

        if args.limit and len(prepared_books) >= args.limit:
            break

    print("")
    print("SAFE IMPORT CHECK")
    print("-----------------")
    print(f"Cover rows: {len(cover_rows)}")
    print(f"Unique cover books: {len(cover_by_code)}")
    print(f"Prepared safe books: {len(prepared_books)}")
    print_skip_report(skipped)
    print("")

    if prepared_books:
        print("Safe books:")
        for item in prepared_books:
            book = item["book"]
            print(f"  - {book['book_code']} | {book['title']} | Level {book['level']} | {book['book_type']}")
        print("")

    if args.dry_run:
        print("Dry run only. Supabase was not changed.")
        return

    if not prepared_books:
        print("No safe books to import. Stopping.")
        sys.exit(1)

    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SECRET_KEY")
        or os.environ.get("SUPABASE_SERVICE_KEY")
    )

    if not supabase_url or not service_key:
        raise RuntimeError(
            "Missing Supabase credentials. Add SUPABASE_URL and "
            "SUPABASE_SERVICE_ROLE_KEY to .env."
        )

    client = SupabaseClient(supabase_url, service_key)

    imported_books = []

    print("IMPORTING TO SUPABASE")
    print("---------------------")

    for item in prepared_books:
        book = item["book"]
        code = book["book_code"]

        try:
            book_id = client.import_book(item)
            imported_books.append(book)
            print(f"Imported {code}: {book['title']} ({book_id})")
        except Exception as exc:
            print(f"FAILED {code}: {exc}")

            if not args.keep_going:
                print("Stopping because --keep-going was not used.")
                sys.exit(1)

    if imported_books and not args.no_books_json:
        write_books_json(args.books_json, imported_books)
        print("")
        print(f"Updated {args.books_json} with {len(imported_books)} imported books.")

    print("")
    print(f"Done. Imported {len(imported_books)} safe books.")


if __name__ == "__main__":
    main()