# Tafiya Web Reader Renderer v1

This is a static prototype for rendering Tafiya books in the web app.

## What it does

- Reads one book JSON package.
- Renders cover, reading pages, and back-cover info.
- Uses locked logo zones.
- Uses image-first pages.
- Uses Andika/system fallback.
- Uses left-aligned reader text.
- Supports phone preview and wide preview.
- Uses text-length bands: short, medium, long.

## Run locally

Open `index.html` through a local server, not by double-clicking, because the browser may block JSON loading.

Example:

```bash
cd tafiya_web_reader_v1
python -m http.server 8000
```

Then open:

```text
http://localhost:8000
```

## Production note

This is not the final app. It is the reference renderer for turning the CSV/book package into web-reader components.
