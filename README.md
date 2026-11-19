# CFA Level I · Study Notes

A GitHub Pages site of chapter study packs. `index.html` lists the chapters, and every chapter page has a navigation bar (All chapters, previous, next).

## Layout

```
index.html                  generated chapter list (do not edit between the markers)
chapters.json               the one list of chapters: edit this to add or rename chapters
tools/build_site.py         writes the chapter list and the navigation bars
chapter-1/
  chapter-1-content.json    study content (source)
  index.html                built study page
```

## Adding a chapter

1. Build the study pack for the chapter into `chapter-N/index.html`, using the cfa-study-pack skill (`scripts/build_html.py`) on `chapter-N/chapter-N-content.json`.
2. Add an entry to `chapters.json`:
   ```json
   { "number": 2, "title": "Time Value of Money", "description": "One line.", "folder": "chapter-2", "content": "chapter-2/chapter-2-content.json" }
   ```
   For a chapter that is planned but not built, use `"folder": null` and `"content": null`. It shows on the index as "Not built yet" and is skipped by the navigation.
3. Run the wiring script from the repo root:
   ```bash
   python3 tools/build_site.py
   ```
4. Commit and push. GitHub Pages republishes the site.

Run `tools/build_site.py` again whenever you rebuild a chapter page, because a rebuild replaces the navigation bar.

## Publishing

GitHub Pages serves the `main` branch from the root folder: Settings → Pages → Deploy from a branch → `main` / `(root)`.
