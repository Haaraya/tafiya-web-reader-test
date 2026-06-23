import argparse
import csv
import json
import os
import sys
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


EXISTING_WORKING_CODES = [
    "T4-NF-01",
    "T4-NF-02",
    "T4-F-03",
    "T4-F-04",
]

NEXT_SIX_SAFEST_CODES = [
    "T4-F-01",
    "T4-F-02",
    "T4-F-05",
    "T4-FT-01",
    "T3-NF-01",
    "T3-NF-02",
]

DEFAULT_TARGET_CODES = EXISTING_WORKING_CODES + NEXT_SIX_SAFEST_CODES

SKILL_FIELDS = [
    ("reading_strategy", "Reading Strategy", "eb_reading_strategy"),
    ("comprehension_skill", "Comprehension Skill", "eb_comprehension_skill"),
    ("phonological_awareness", "Phonological Awareness", "eb_phonological_awareness"),
    ("grammar_mechanics", "Grammar & Mechanics", "eb_grammar_mechanics"),
    ("word_work", "Word Work", "eb_word_work"),
    ("text_structure", "Text Structure", "eb_text_structure"),
]

BACK_COVER_META_FIELDS = [
    ("about_text", "back_about_text"),
    ("fp_level", "back_fp_level"),
    ("uk_book_band", "back_uk_book_band"),
]


def load_dotenv(path=".env"):
    env_path = Path(path)
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def die(message):
    print(f"\nERROR: {message}", file=sys.stderr)
    sys.exit(1)


def clean(value):
    return (value or "").strip()


def read_csv(path):
    p = Path(path)
    if not p.exists():
        die(f"Missing CSV: {p}")

    with p.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def index_by_code(rows, label):
    out = {}
    for row in rows:
        code = clean(row.get("book_code"))
        if not code:
            die(f"{label} has a row with no book_code.")
        if code in out:
            die(f"{label} has duplicate book_code: {code}")
        out[code] = row
    return out


def group_pages(rows):
    out = {}
    for row in rows:
        code = clean(row.get("book_code"))
        if code:
            out.setdefault(code, []).append(row)
    return out


def book_type_from_code(code):
    parts = code.split("-")
    if len(parts) < 3:
        return "unknown"

    marker = parts[1].upper()
    return {
        "C": "concept",
        "F": "fiction",
        "FT": "folktale",
        "NF": "non-fiction",
        "P": "poetry",
    }.get(marker, marker.lower())


def sorted_page_rows(rows):
    def page_number(row):
        page_num = clean(row.get("page_num"))
        if not page_num.startswith("P"):
            return 999999
        try:
            return int(page_num[1:])
        except ValueError:
            return 999999

    return sorted(rows, key=page_number)


def expected_image_paths(code, page_rows):
    paths = [f"books/{code}/{code}_FC.png"]

    for row in sorted_page_rows(page_rows):
        page_num = clean(row.get("page_num"))
        paths.append(f"books/{code}/{code}_{page_num}.png")

    return paths


def validate_csv_package(target_codes, cover_by_code, pages_by_code, back_by_code):
    validated = []

    for code in target_codes:
        if code not in cover_by_code:
            die(f"{code}: missing cover row.")
        if code not in pages_by_code:
            die(f"{code}: missing page rows.")
        if code not in back_by_code:
            die(f"{code}: missing back-cover CSV row.")

        if "-P-" in code:
            die(f"{code}: poetry is skipped for importer v2.")

        cover = cover_by_code[code]
        back = back_by_code[code]
        pages = sorted_page_rows(pages_by_code[code])

        page_nums = [clean(r.get("page_num")) for r in pages]
        if any(p == "POEM" for p in page_nums):
            die(f"{code}: has page_num=POEM. Poetry is skipped for now.")

        expected_nums = [f"P{i}" for i in range(1, len(pages) + 1)]
        if page_nums != expected_nums:
            die(f"{code}: page numbers are {page_nums}, expected {expected_nums}.")

        if len(pages) != 8:
            die(f"{code}: has {len(pages)} pages. Expected 8 for this batch.")

        cover_title = clean(cover.get("book_title"))
        back_title = clean(back.get("book_title"))
        page_titles = sorted({clean(r.get("book_title")) for r in pages})

        if len(page_titles) != 1:
            die(f"{code}: page rows contain multiple titles: {page_titles}")

        if cover_title != page_titles[0]:
            die(f"{code}: cover title does not match page title: {cover_title!r} vs {page_titles[0]!r}")

        if cover_title != back_title:
            die(f"{code}: cover title does not match back title: {cover_title!r} vs {back_title!r}")

        validated.append({
            "code": code,
            "title": cover_title,
            "level": clean(cover.get("level")),
            "tafiya_name": clean(cover.get("tafiya_name")),
            "book_type": book_type_from_code(code),
            "cover_path": f"books/{code}/{code}_FC.png",
            "pages": pages,
            "back": back,
            "expected_paths": expected_image_paths(code, pages),
        })

    return validated


class SupabaseClient:
    def __init__(self, url, service_key):
        self.url = url.rstrip("/")
        self.rest_url = f"{self.url}/rest/v1"
        self.service_key = service_key

    def headers(self, extra=None):
        h = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json",
        }
        if extra:
            h.update(extra)
        return h

    def request_json(self, method, url, body=None, headers=None):
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")

        req = Request(url, data=data, method=method, headers=self.headers(headers))

        try:
            with urlopen(req) as resp:
                raw = resp.read().decode("utf-8")
                if not raw:
                    return None
                return json.loads(raw)
        except HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            die(f"Supabase HTTP {e.code} for {method} {url}\n{detail}")
        except URLError as e:
            die(f"Could not reach Supabase: {e}")

    def get_rows(self, table, query):
        url = f"{self.rest_url}/{table}?{query}"
        return self.request_json("GET", url)

    def sample_columns(self, table, fallback):
        rows = self.get_rows(table, "select=*&limit=1")
        if rows and isinstance(rows, list) and rows:
            return set(rows[0].keys())
        return set(fallback)

    def upsert(self, table, rows, conflict_col):
        if not rows:
            return []

        url = f"{self.rest_url}/{table}?on_conflict={quote(conflict_col)}"
        return self.request_json(
            "POST",
            url,
            rows,
            headers={"Prefer": "resolution=merge-duplicates,return=representation"},
        )

    def insert(self, table, rows):
        if not rows:
            return []

        url = f"{self.rest_url}/{table}"
        return self.request_json(
            "POST",
            url,
            rows,
            headers={"Prefer": "return=minimal"},
        )

    def delete_by_book_ids(self, table, book_ids):
        if not book_ids:
            return

        joined = ",".join(book_ids)
        url = f"{self.rest_url}/{table}?book_id=in.({joined})"
        self.request_json(
            "DELETE",
            url,
            headers={"Prefer": "return=minimal"},
        )

    def list_storage_folder(self, bucket, folder):
        url = f"{self.url}/storage/v1/object/list/{quote(bucket)}"
        body = {
            "prefix": folder,
            "limit": 1000,
            "offset": 0,
            "sortBy": {"column": "name", "order": "asc"},
        }
        return self.request_json("POST", url, body)

    def storage_object_exists(self, bucket, path):
        quoted_path = quote(path, safe="/")
        url = f"{self.url}/storage/v1/object/{quote(bucket)}/{quoted_path}"

        req = Request(
            url,
            method="GET",
            headers=self.headers({"Range": "bytes=0-0"}),
        )

        try:
            with urlopen(req) as resp:
                return resp.status in (200, 206)
        except HTTPError as e:
            return e.code not in (400, 401, 403, 404)
        except URLError:
            return False


def validate_storage_paths(client, bucket, packages):
    missing = []

    for package in packages:
        code = package["code"]
        folder = f"books/{code}"

        objects = client.list_storage_folder(bucket, folder)
        found = set()

        for obj in objects or []:
            name = clean(obj.get("name"))
            if not name:
                continue

            if name.startswith(folder):
                found.add(name)
            else:
                found.add(f"{folder}/{name}")

        for path in package["expected_paths"]:
            if path not in found:
                if not client.storage_object_exists(bucket, path):
                    missing.append(path)

    if missing:
        print("\nMissing Supabase Storage objects:")
        for path in missing:
            print(f"  - {path}")
        die("Storage validation failed. Do not import until these paths exist.")

    total = sum(len(p["expected_paths"]) for p in packages)
    print(f"Storage validation passed for {total} image paths.")


def first_existing(columns, candidates):
    for col in candidates:
        if col in columns:
            return col
    return None


def only_known(row, columns):
    return {k: v for k, v in row.items() if k in columns}


def build_book_rows(packages, book_cols, status):
    code_col = first_existing(book_cols, ["code", "book_code"])
    title_col = first_existing(book_cols, ["title", "book_title"])

    if not code_col:
        die("books table needs a code or book_code column.")
    if not title_col:
        die("books table needs a title or book_title column.")

    rows = []

    for p in packages:
        row = {
            code_col: p["code"],
            title_col: p["title"],
        }

        optional_values = {
            "level": p["level"],
            "level_name": p["tafiya_name"],
            "tafiya_name": p["tafiya_name"],
            "status": status,
            "book_type": p["book_type"],
            "type": p["book_type"],
            "strand": p["book_type"],
            "cover_image_path": p["cover_path"],
            "front_cover_image_path": p["cover_path"],
            "cover_path": p["cover_path"],
            "image_path": p["cover_path"],
        }

        for col, value in optional_values.items():
            if col in book_cols:
                row[col] = value

        rows.append(row)

    return rows, code_col


def fetch_book_ids(client, codes, code_col):
    code_list = ",".join(codes)
    query = f"select=id,{code_col}&{code_col}=in.({code_list})"
    rows = client.get_rows("books", query)

    out = {}
    for row in rows or []:
        out[str(row[code_col])] = str(row["id"])

    missing = [c for c in codes if c not in out]
    if missing:
        die(f"Could not fetch book ids after upsert: {missing}")

    return out


def classify_text_length(text):
    words = [w for w in clean(text).split() if w]
    count = len(words)

    if count <= 10:
        return "short"
    if count <= 24:
        return "medium"
    return "long"


def build_page_rows(packages, page_cols, book_ids):
    rows = []

    page_number_col = first_existing(page_cols, ["page_number", "page_no", "page_num"])
    page_text_col = first_existing(page_cols, ["page_text", "text", "body"])
    image_path_col = first_existing(page_cols, ["image_path", "page_image_path"])

    if "book_id" not in page_cols:
        die("book_pages table needs a book_id column.")
    if not page_number_col:
        die("book_pages table needs page_number, page_no, or page_num.")
    if not page_text_col:
        die("book_pages table needs page_text, text, or body.")
    if not image_path_col:
        die("book_pages table needs image_path or page_image_path.")

    for p in packages:
        code = p["code"]
        book_id = book_ids[code]

        for row in sorted_page_rows(p["pages"]):
            page_num = clean(row.get("page_num"))
            number = int(page_num[1:])
            text = clean(row.get("page_text"))
            image_path = f"books/{code}/{code}_{page_num}.png"

            page_row = {
                "book_id": book_id,
                page_number_col: number,
                page_text_col: text,
                image_path_col: image_path,
            }

            if "length" in page_cols:
                page_row["length"] = classify_text_length(text)
            if "text_length" in page_cols:
                page_row["text_length"] = classify_text_length(text)
            if "page_type" in page_cols:
                page_row["page_type"] = "interior"

            rows.append(only_known(page_row, page_cols))

    return rows


def build_skill_rows(packages, skill_cols, book_ids):
    if "book_id" not in skill_cols:
        die("book_skills table needs a book_id column.")

    has_wide_skill_cols = any(key in skill_cols for key, _, _ in SKILL_FIELDS)

    if has_wide_skill_cols:
        rows = []

        for p in packages:
            row = {"book_id": book_ids[p["code"]]}

            for key, _, csv_col in SKILL_FIELDS:
                if key in skill_cols:
                    row[key] = clean(p["back"].get(csv_col))

            for db_col, csv_col in BACK_COVER_META_FIELDS:
                if db_col in skill_cols:
                    row[db_col] = clean(p["back"].get(csv_col))

            rows.append(only_known(row, skill_cols))

        return rows

    key_col = first_existing(skill_cols, ["skill_key", "skill_name", "skill_type", "field_name", "name"])
    value_col = first_existing(skill_cols, ["skill_value", "value", "field_value", "description"])
    label_col = first_existing(skill_cols, ["skill_label", "label", "display_name"])
    order_col = first_existing(skill_cols, ["sort_order", "display_order", "order_index", "position"])

    if not key_col or not value_col:
        die(
            "book_skills table needs either wide skill columns "
            "or a key/value shape like skill_key + skill_value."
        )

    rows = []

    combined = []
    for key, label, csv_col in SKILL_FIELDS:
        combined.append((key, label, csv_col))
    combined.extend([
        ("about_text", "About This Book", "back_about_text"),
        ("fp_level", "Fountas & Pinnell", "back_fp_level"),
        ("uk_book_band", "UK Book Band", "back_uk_book_band"),
    ])

    for p in packages:
        for idx, (key, label, csv_col) in enumerate(combined, start=1):
            row = {
                "book_id": book_ids[p["code"]],
                key_col: key,
                value_col: clean(p["back"].get(csv_col)),
            }

            if label_col:
                row[label_col] = label
            if order_col:
                row[order_col] = idx

            rows.append(only_known(row, skill_cols))

    return rows


def update_books_json(path, packages):
    p = Path(path)

    entries = []
    for package in packages:
        back = package["back"]
        entries.append({
            "code": package["code"],
            "title": package["title"],
            "level": package["level"],
            "tafiya_name": package["tafiya_name"],
            "book_type": package["book_type"],
            "status": "approved",
            "cover_image_path": package["cover_path"],
            "about_text": clean(back.get("back_about_text")),
            "fp_level": clean(back.get("back_fp_level")),
            "uk_book_band": clean(back.get("back_uk_book_band")),
        })

    if p.exists():
        data = json.loads(p.read_text(encoding="utf-8"))
    else:
        data = []

    def code_of(item):
        return item.get("code") or item.get("book_code")

    if isinstance(data, list):
        by_code = {code_of(item): item for item in data if isinstance(item, dict)}

        for entry in entries:
            old = by_code.get(entry["code"], {})
            old.update(entry)
            old.pop("back_cover_image_path", None)
            old.pop("back_image_path", None)
            old.pop("back_cover_path", None)
            by_code[entry["code"]] = old

        data = list(by_code.values())

    elif isinstance(data, dict) and isinstance(data.get("books"), list):
        by_code = {code_of(item): item for item in data["books"] if isinstance(item, dict)}

        for entry in entries:
            old = by_code.get(entry["code"], {})
            old.update(entry)
            old.pop("back_cover_image_path", None)
            old.pop("back_image_path", None)
            old.pop("back_cover_path", None)
            by_code[entry["code"]] = old

        data["books"] = list(by_code.values())

    elif isinstance(data, dict):
        for entry in entries:
            old = data.get(entry["code"], {})
            if not isinstance(old, dict):
                old = {}

            old.update(entry)
            old.pop("back_cover_image_path", None)
            old.pop("back_image_path", None)
            old.pop("back_cover_path", None)
            data[entry["code"]] = old

    else:
        die(f"{path} is not a JSON list or object.")

    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Updated {p}")


def chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def main():
    parser = argparse.ArgumentParser(description="Import Tafiya CSV books into Supabase.")
    parser.add_argument("--cover", default="import_sources/Tafiya_Cover_Merge.csv")
    parser.add_argument("--pages", default="import_sources/Tafiya_Pages_Merge.csv")
    parser.add_argument("--back", default="import_sources/Tafiya_BackCover_Merge.csv")
    parser.add_argument("--books-json", default="books.json")
    parser.add_argument("--book-codes", nargs="+", default=DEFAULT_TARGET_CODES)
    parser.add_argument("--bucket", default=None)
    parser.add_argument("--status", default="approved")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-storage-validation", action="store_true")
    args = parser.parse_args()

    load_dotenv()

    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("SERVICE_ROLE_KEY")
    )
    bucket = (
        args.bucket
        or os.environ.get("BOOK_ASSETS_BUCKET")
        or os.environ.get("SUPABASE_BUCKET")
        or "book-assets"
    )

    if not supabase_url:
        die("Missing SUPABASE_URL in .env.")
    if not service_key:
        die("Missing SUPABASE_SERVICE_ROLE_KEY in .env.")

    cover_rows = read_csv(args.cover)
    page_rows = read_csv(args.pages)
    back_rows = read_csv(args.back)

    cover_by_code = index_by_code(cover_rows, "cover CSV")
    pages_by_code = group_pages(page_rows)
    back_by_code = index_by_code(back_rows, "back-cover CSV")

    packages = validate_csv_package(
        args.book_codes,
        cover_by_code,
        pages_by_code,
        back_by_code,
    )

    print("\nImporter v2 target batch:")
    for p in packages:
        print(f"  - {p['code']} | {p['title']} | {p['level']} | {p['book_type']}")

    client = SupabaseClient(supabase_url, service_key)

    if not args.skip_storage_validation:
        validate_storage_paths(client, bucket, packages)

    if args.dry_run:
        print("\nDRY RUN PASSED. No database rows were changed.")
        return

    book_cols = client.sample_columns(
        "books",
        [
            "id",
            "book_code",
            "code",
            "title",
            "book_title",
            "level",
            "level_name",
            "tafiya_name",
            "status",
            "book_type",
            "cover_image_path",
        ],
    )
    page_cols = client.sample_columns(
        "book_pages",
        ["id", "book_id", "page_number", "page_text", "image_path", "length"],
    )
    skill_cols = client.sample_columns(
        "book_skills",
        [
            "id",
            "book_id",
            "reading_strategy",
            "comprehension_skill",
            "phonological_awareness",
            "grammar_mechanics",
            "word_work",
            "text_structure",
            "about_text",
            "fp_level",
            "uk_book_band",
            "website",
        ],
    )

    book_rows, code_col = build_book_rows(packages, book_cols, args.status)
    client.upsert("books", book_rows, code_col)
    print(f"Upserted {len(book_rows)} books.")

    book_ids = fetch_book_ids(client, [p["code"] for p in packages], code_col)

    client.delete_by_book_ids("book_pages", list(book_ids.values()))
    page_insert_rows = build_page_rows(packages, page_cols, book_ids)
    for group in chunked(page_insert_rows, 500):
        client.insert("book_pages", group)
    print(f"Replaced {len(page_insert_rows)} book_pages rows.")

    client.delete_by_book_ids("book_skills", list(book_ids.values()))
    skill_insert_rows = build_skill_rows(packages, skill_cols, book_ids)
    for group in chunked(skill_insert_rows, 500):
        client.insert("book_skills", group)
    print(f"Replaced {len(skill_insert_rows)} book_skills rows.")

    update_books_json(args.books_json, packages)

    print("\nDONE. Imported target batch to 10 books.")


if __name__ == "__main__":
    main()