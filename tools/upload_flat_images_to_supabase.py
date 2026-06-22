import argparse
import mimetypes
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


IMAGE_RE = re.compile(
    r"^(?P<book_code>[A-Z0-9]+-[A-Z]+-[0-9]+)_(?P<page>FC|BC|P[0-9]+)\.(?P<ext>png|jpg|jpeg|webp)$",
    re.IGNORECASE,
)


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


def upload_file(supabase_url, service_key, bucket, local_path, storage_path, dry_run=False):
    content_type = mimetypes.guess_type(local_path.name)[0] or "application/octet-stream"

    if dry_run:
        print(f"DRY RUN: {local_path.name} -> {bucket}/{storage_path}")
        return

    url = (
        f"{supabase_url.rstrip()}/storage/v1/object/"
        f"{quote(bucket)}/{quote(storage_path, safe='/')}"
    )

    data = local_path.read_bytes()

    req = Request(
        url,
        data=data,
        method="POST",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": content_type,
            "x-upsert": "true",
        },
    )

    try:
        with urlopen(req) as resp:
            if resp.status not in (200, 201):
                die(f"Unexpected upload status {resp.status} for {local_path.name}")
    except HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        die(f"Upload failed for {local_path.name}: HTTP {e.code}\n{detail}")
    except URLError as e:
        die(f"Could not reach Supabase while uploading {local_path.name}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Upload one flat folder of Tafiya images into Supabase Storage book folders."
    )
    parser.add_argument(
        "--source-folder",
        required=True,
        help="Local folder containing all image files in one flat folder.",
    )
    parser.add_argument(
        "--bucket",
        default=None,
        help="Supabase Storage bucket name. Defaults to BOOK_ASSETS_BUCKET or book-assets.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would upload without changing Supabase.",
    )
    args = parser.parse_args()

    load_dotenv()

    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("SERVICE_ROLE_KEY")
    )
    bucket = args.bucket or os.environ.get("BOOK_ASSETS_BUCKET") or "book-assets"

    if not supabase_url:
        die("Missing SUPABASE_URL in .env.")
    if not service_key:
        die("Missing SUPABASE_SERVICE_ROLE_KEY in .env.")

    source = Path(args.source_folder)

    if not source.exists():
        die(f"Source folder does not exist: {source}")
    if not source.is_dir():
        die(f"Source path is not a folder: {source}")

    files = sorted(
        p for p in source.iterdir()
        if p.is_file() and p.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]
    )

    if not files:
        die("No image files found in that folder.")

    matched = []
    skipped = []

    for file in files:
        match = IMAGE_RE.match(file.name)
        if not match:
            skipped.append(file.name)
            continue

        book_code = match.group("book_code").upper()
        page = match.group("page").upper()
        ext = match.group("ext").lower()

        normalized_filename = f"{book_code}_{page}.{ext}"
        storage_path = f"books/{book_code}/{normalized_filename}"

        matched.append((file, storage_path))

    print(f"\nFound {len(files)} image files.")
    print(f"Matched {len(matched)} Tafiya image filenames.")
    print(f"Skipped {len(skipped)} files.")

    if skipped:
        print("\nSkipped files because their names do not match BOOKCODE_PAGE.png:")
        for name in skipped[:30]:
            print(f"  - {name}")
        if len(skipped) > 30:
            print(f"  ... and {len(skipped) - 30} more")

    if not matched:
        die("Nothing matched. Check your filenames before uploading.")

    print("\nUpload plan:")
    for local_path, storage_path in matched[:20]:
        print(f"  {local_path.name} -> {bucket}/{storage_path}")
    if len(matched) > 20:
        print(f"  ... and {len(matched) - 20} more")

    for local_path, storage_path in matched:
        upload_file(
            supabase_url=supabase_url,
            service_key=service_key,
            bucket=bucket,
            local_path=local_path,
            storage_path=storage_path,
            dry_run=args.dry_run,
        )

    if args.dry_run:
        print("\nDRY RUN PASSED. No files were uploaded.")
    else:
        print(f"\nDONE. Uploaded {len(matched)} files to Supabase Storage.")


if __name__ == "__main__":
    main()