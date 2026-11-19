#!/usr/bin/env python3
"""Wire the site's navigation from chapters.json.

Run after adding or rebuilding a chapter:

    python3 tools/build_site.py

It does two things, both driven by chapters.json:

1. Writes the chapter list into index.html, between the
   <!-- chapters:start --> and <!-- chapters:end --> markers.
2. Writes a navigation bar (All chapters / previous / next) into each built
   chapter page, between the <!-- site-nav:start --> and <!-- site-nav:end -->
   markers. The bar is inserted right after <body> and replaced on every run.

Chapter pages themselves are built with the cfa-study-pack skill
(scripts/build_html.py). This script never touches chapter content.

Exits non-zero if the manifest points at a page that does not exist.
"""
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "chapters.json"
INDEX = ROOT / "index.html"

LIST_START, LIST_END = "<!-- chapters:start -->", "<!-- chapters:end -->"
NAV_START, NAV_END = "<!-- site-nav:start -->", "<!-- site-nav:end -->"

NAV_CSS = """<style>
.site-nav{max-width:1000px;margin:0 auto;padding:12px 16px 0;display:flex;align-items:center;gap:8px;font-size:.9rem}
.site-nav a{color:var(--accent);text-decoration:none;border:1px solid var(--border);background:var(--card);border-radius:999px;padding:6px 12px;white-space:nowrap}
.site-nav a:hover,.site-nav a:focus-visible{border-color:var(--accent);outline:none}
.site-nav .here{flex:1;text-align:center;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
.site-nav .gap{flex:1}
</style>"""


def load_manifest():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    chapters = data["chapters"]
    errors, warnings = [], []

    folders = [c["folder"] for c in chapters if c.get("folder")]
    if len(set(folders)) != len(folders):
        errors.append("chapters.json: two chapters share the same folder")
    numbers = [c["number"] for c in chapters]
    if len(set(numbers)) != len(numbers):
        errors.append("chapters.json: two chapters share the same number")

    for c in chapters:
        label = f"Chapter {c.get('number', '?')}"
        for key in ("number", "title", "description"):
            if c.get(key) in (None, ""):
                errors.append(f"{label}: missing '{key}'")
        if c.get("folder") and not (ROOT / c["folder"] / "index.html").exists():
            errors.append(f"{label}: {c['folder']}/index.html does not exist (build it first)")

    # Warn about built chapter pages that are not registered in the manifest.
    registered = set(folders)
    for page in sorted(ROOT.glob("chapter-*/index.html")):
        if page.parent.name not in registered:
            warnings.append(f"{page.parent.name}/index.html exists but is not in chapters.json")

    return data, chapters, errors, warnings


def stats_for(chapter):
    """Counts from the content JSON, if the chapter has one."""
    if not chapter.get("content"):
        return None
    content = json.loads((ROOT / chapter["content"]).read_text(encoding="utf-8"))
    return (
        f"{len(content.get('los', []))} learning outcomes · "
        f"{len(content.get('concepts', []))} concepts · "
        f"{len(content.get('questions', []))} questions"
    )


def render_index_list(chapters):
    items = []
    for c in chapters:
        num = html.escape(f"Chapter {c['number']}")
        title = html.escape(c["title"])
        desc = html.escape(c["description"])
        if c.get("folder"):
            stats = html.escape(stats_for(c) or "")
            items.append(
                f'    <li>\n'
                f'      <a class="card" href="{html.escape(c["folder"])}/">\n'
                f'        <span class="chapter-num">{num}</span>\n'
                f'        <span class="chapter-title">{title}</span>\n'
                f'        <span class="chapter-desc">{desc}</span>\n'
                f'        <span class="chapter-stats">{stats}</span>\n'
                f'      </a>\n'
                f'    </li>'
            )
        else:
            items.append(
                f'    <li>\n'
                f'      <div class="card soon" aria-disabled="true">\n'
                f'        <span class="chapter-num">{num}</span>\n'
                f'        <span class="chapter-title">{title}</span>\n'
                f'        <span class="chapter-desc">{desc}</span>\n'
                f'        <span class="chapter-stats">Not built yet</span>\n'
                f'      </div>\n'
                f'    </li>'
            )
    return "\n".join(items)


def write_index(chapters, site):
    text = INDEX.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(LIST_START) + r".*?" + re.escape(LIST_END), re.S)
    if not pattern.search(text):
        raise SystemExit("index.html is missing the chapters:start/end markers")
    block = f"{LIST_START}\n{render_index_list(chapters)}\n    {LIST_END}"
    text = pattern.sub(lambda _: block, text)
    text = re.sub(r"<title>.*?</title>", f"<title>{html.escape(site['site_title'])}</title>", text, count=1)
    text = re.sub(r'(<p class="intro">).*?(</p>)',
                  lambda m: m.group(1) + html.escape(site["site_intro"]) + m.group(2), text, count=1, flags=re.S)
    INDEX.write_text(text, encoding="utf-8")


def nav_block(chapters, current, built):
    """Navigation for one chapter page. `built` is the list of chapters with pages, in order."""
    pos = built.index(current)
    prev_c = built[pos - 1] if pos > 0 else None
    next_c = built[pos + 1] if pos < len(built) - 1 else None

    def link(c, label):
        return (f'<a href="../{html.escape(c["folder"])}/" title="{html.escape(c["title"])}">'
                f'{html.escape(label)}</a>')

    prev_html = link(prev_c, f"‹ Chapter {prev_c['number']}") if prev_c else '<span class="gap"></span>'
    next_html = link(next_c, f"Chapter {next_c['number']} ›") if next_c else '<span class="gap"></span>'
    here = html.escape(f"Chapter {current['number']} · {current['title']}")

    return (
        f"{NAV_START}\n{NAV_CSS}\n"
        f'<nav class="site-nav" aria-label="Chapter navigation">\n'
        f'  <a href="../">All chapters</a>\n'
        f"  {prev_html}\n"
        f'  <span class="here">{here}</span>\n'
        f"  {next_html}\n"
        f"</nav>\n{NAV_END}"
    )


def write_chapter_nav(chapters):
    built = [c for c in chapters if c.get("folder")]
    for c in built:
        page = ROOT / c["folder"] / "index.html"
        text = page.read_text(encoding="utf-8")
        block = nav_block(c, c, built)
        block_pattern = re.compile(re.escape(NAV_START) + r".*?" + re.escape(NAV_END), re.S)
        if block_pattern.search(text):
            text = block_pattern.sub(lambda _: block, text, count=1)
        else:
            body = re.search(r"<body[^>]*>", text)
            if not body:
                raise SystemExit(f"{page}: no <body> tag found")
            text = text[:body.end()] + "\n" + block + "\n" + text[body.end():]
        page.write_text(text, encoding="utf-8")


def main():
    data, chapters, errors, warnings = load_manifest()
    for w in warnings:
        print(f"warning: {w}")
    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    write_index(chapters, data)
    write_chapter_nav(chapters)

    built = [c for c in chapters if c.get("folder")]
    print(f"index.html: {len(chapters)} chapters listed ({len(built)} built, "
          f"{len(chapters) - len(built)} not built yet)")
    for c in built:
        print(f"  {c['folder']}/index.html: navigation updated")


if __name__ == "__main__":
    main()
