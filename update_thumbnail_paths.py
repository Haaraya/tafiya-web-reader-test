import json
from pathlib import Path

books_json = Path("books.json")
thumb_dir = Path("thumbnails/covers")

data = json.loads(books_json.read_text(encoding="utf-8"))
books = data.get("books", data) if isinstance(data, dict) else data

thumbs = list(thumb_dir.glob("*_fc.jpg"))

missing = []

for book in books:
    code = (book.get("book_code") or book.get("code") or "").strip()
    matches = [p for p in thumbs if p.name.startswith(code + "_")]

    if len(matches) == 1:
        book["thumbnail_image_path"] = "thumbnails/covers/" + matches[0].name
    elif len(matches) == 0:
        missing.append(code)
    else:
        print(f"Multiple thumbnails for {code}:")
        for p in matches:
            print("  " + p.name)

books_json.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

if missing:
    print("Missing thumbnails:")
    for code in missing:
        print("  " + code)
else:
    print("All books matched to thumbnails.")
