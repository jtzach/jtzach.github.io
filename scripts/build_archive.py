"""Build the dependency-free public archive from data/archive.json.

Run from any directory: python scripts/build_archive.py
The original homepage sections are retained; only generated blocks are refreshed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
from html import escape
import json
from pathlib import Path, PurePosixPath
import re
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def e(value):
    return escape(str(value or ""), quote=True)


def remote_url(value):
    value = str(value or "").strip()
    parsed = urlsplit(value)
    return value if parsed.scheme in {"http", "https"} and parsed.netloc else ""


def local_url(value, prefix="../"):
    value = str(value or "").replace("\\", "/")
    if not value or value.startswith("/") or any(char in value for char in ":?#%") or any(part in {"", ".", ".."} for part in value.split("/")):
        raise ValueError(f"Invalid local media path: {value!r}")
    return prefix + value


def media_paths(media):
    """Validate the saved file references; a split video remains one media item."""
    parts = media.get("parts")
    if parts is not None:
        if media_kind(media) != "video" or media.get("path") or not isinstance(parts, list) or not parts:
            raise ValueError("Split video media needs a nonempty parts list and no path.")
        if not all(isinstance(part, str) for part in parts) or len(parts) != len(set(parts)):
            raise ValueError("Video parts must be distinct and ordered.")
        if not re.fullmatch(r"[0-9a-f]{64}", str(media.get("sha256", ""))):
            raise ValueError("Split video media needs its full-file SHA-256.")
        if not isinstance(media.get("bytes"), int) or media["bytes"] <= 0:
            raise ValueError("Split video media needs a positive full-file byte count.")
        filename = str(media.get("original_filename", ""))
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.mp4", filename):
            raise ValueError("Invalid restored video filename.")
        for part in parts:
            local_url(part)
            path = (ROOT / part).resolve()
            if not str(part).startswith("assets/") or not path.is_relative_to(ROOT.resolve()) or not path.is_file():
                raise ValueError(f"Missing or unsafe video part: {part!r}")
        if sum((ROOT / part).stat().st_size for part in parts) != media["bytes"]:
            raise ValueError("Video part sizes do not match the complete file.")
        return parts
    if media.get("path"):
        local_url(media["path"])
        return [media["path"]]
    return []


def linkify(value):
    """Escape supplied text; make only ordinary HTTP(S) URLs interactive."""
    value = str(value or "")
    output = []
    offset = 0
    for match in re.finditer(r"https?://[^\s<>\"']+", value):
        url = match.group().rstrip(".,;!?)]}")
        if not remote_url(url):
            continue
        output.append(e(value[offset:match.start()]))
        output.append(f'<a href="{e(url)}" target="_blank" rel="noopener noreferrer">{e(url)}</a>')
        offset = match.start() + len(url)
    output.append(e(value[offset:]))
    return "".join(output)


def date_label(value):
    if not value:
        return "Date not recorded"
    value = str(value)
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").strftime("%d %b %Y").lstrip("0")
    except ValueError:
        return value


def media_kind(media):
    kind = str(media.get("type", "")).lower()
    suffix = Path(str(media.get("path", ""))).suffix.lower()
    if kind.startswith("image") or suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".avif"}:
        return "image"
    if kind.startswith("video") or suffix in {".mp4", ".webm", ".mov"}:
        return "video"
    if kind.startswith("audio") or suffix in {".mp3", ".m4a", ".ogg", ".wav"}:
        return "audio"
    if "pdf" in kind or suffix == ".pdf":
        return "pdf"
    return "file"


def notes_text(notes):
    return " ".join(str(note) for note in notes if note) if isinstance(notes, list) else str(notes or "")


def render_media(media, title):
    alt = e(media.get("alt") or media.get("title") or title)
    kind = media_kind(media)
    if kind == "video" and media.get("parts"):
        parts = media_paths(media)
        poster = f' poster="{e(local_url(media["poster"]))}"' if media.get("poster") else ""
        urls = e(json.dumps([local_url(part) for part in parts]))
        size = round(media["bytes"] / 1_000_000)
        filename = e(media["original_filename"])
        return f'<figure class="wide-media saved-video" data-video-parts="{urls}" data-video-bytes="{media["bytes"]}" data-video-sha256="{e(media["sha256"])}" data-video-filename="{filename}"><video{poster} controls preload="none" aria-label="{alt}"></video><button type="button" class="load-saved-video js-only">Load saved video ({size} MB)</button><p class="saved-video-status archive-note" role="status" aria-live="polite"></p><figcaption>{alt} <a class="saved-video-download" download="{filename}" hidden>Download video</a></figcaption><p class="archive-note"><a href="../scripts/VIDEO_RECOVERY.md">Video download help</a></p><noscript><p>The saved video can also be recovered without JavaScript using the download instructions above.</p></noscript></figure>'
    url = e(local_url(media["path"]))
    if kind == "image":
        return f'<figure><a href="{url}" target="_blank" rel="noopener"><img src="{url}" alt="{alt}" loading="lazy" decoding="async"></a><figcaption>{alt} · <a href="{url}" download>Download</a></figcaption></figure>'
    if kind == "video":
        poster = f' poster="{e(local_url(media["poster"]))}"' if media.get("poster") else ""
        return f'<figure class="wide-media"><video src="{url}"{poster} controls preload="none" aria-label="{alt}"></video><figcaption>{alt} · <a href="{url}" download>Download video</a></figcaption></figure>'
    if kind == "audio":
        return f'<figure class="wide-media"><audio src="{url}" controls preload="none" aria-label="{alt}"></audio><figcaption>{alt} · <a href="{url}" download>Download audio</a></figcaption></figure>'
    is_geogebra = Path(str(media.get("path", ""))).suffix.lower() == ".ggb"
    label = "Read saved PDF" if kind == "pdf" else "Download GeoGebra construction" if is_geogebra else "Open saved file"
    extra = " download" if is_geogebra else ' target="_blank" rel="noopener"'
    return f'<a class="file-link wide-media" href="{url}"{extra}>{label} ↗<br><span>{alt}</span></a>'


def render_entry(entry):
    title = str(entry.get("title") or "Untitled entry")
    entry_id = str(entry["id"])
    category = str(entry.get("category") or "Writing")
    text = str(entry.get("text") or "")
    summary = str(entry.get("summary") or "")
    if not summary and text:
        summary = re.sub(r"\s+", " ", text).strip()
        if len(summary) > 220:
            summary = summary[:217].rsplit(" ", 1)[0] + "…"
    media = [item for item in entry.get("media", []) if media_paths(item)]
    status = entry.get("status", "source-only")
    labels = {"full-text": "Text saved", "summary": "Summary saved", "source-only": "Source link", "archived": "Video & description saved"}
    text_kind = str(entry.get("text_kind") or "")
    if text and "abstract" in text_kind.lower():
        labels[status] = "Abstract saved"
    badges = [f'<span class="coverage-badge {"saved" if status == "full-text" else ""}">{e(labels.get(status, status))}</span>']
    kinds = Counter(media_kind(item) for item in media)
    for kind, count in kinds.items():
        noun = {"image": "image", "video": "video", "audio": "audio file", "pdf": "PDF", "file": "file"}[kind]
        badges.append(f'<span class="coverage-badge saved">{count} {noun}{"s" if count != 1 else ""} saved</span>')
    cover = next((item for item in media if media_kind(item) == "image"), None)
    if not cover:
        poster = next((item.get("poster") for item in media if item.get("poster")), None)
        if poster:
            cover = {"path": poster}
    cover_html = f'<a href="#{e(entry_id)}" tabindex="-1" aria-hidden="true"><img class="entry-cover" src="{e(local_url(cover["path"]))}" alt="" loading="lazy" decoding="async"></a>' if cover else ""
    source = remote_url(entry.get("source_url"))
    actions = f'<a href="{e(source)}" target="_blank" rel="noopener noreferrer">Original source ↗</a>' if source else ""
    actions += f'<a href="#{e(entry_id)}" aria-label="Link to {e(title)}">Link to this entry</a>'
    text_label = f'<p class="text-kind">{e(text_kind)}</p>' if text_kind and text else ""
    detail_content = text_label + (f'<div class="entry-text" dir="auto">{linkify(text)}</div>' if text else "")
    source_links = []
    for link in entry.get("source_links", []):
        url = remote_url(link.get("url"))
        if url:
            source_links.append(f'<li><a href="{e(url)}" target="_blank" rel="noopener noreferrer">{e(link.get("title") or url)}</a></li>')
    if source_links:
        detail_content += '<p class="archive-note">Links included with this entry</p><ul class="archive-note">' + "".join(source_links) + "</ul>"
    if media:
        detail_content += '<div class="entry-media">' + "".join(render_media(item, title) for item in media) + "</div>"
    detail_label = "Read saved text & view files" if text and media else "Read saved text" if text else "View saved files" if media else "Related links"
    details = f'<details class="entry-detail"><summary>{detail_label}</summary>{detail_content}</details>' if detail_content else ""
    note = notes_text(entry.get("notes"))
    if status == "source-only" and not media:
        note = " ".join(filter(None, ["This entry is a reference link; the original content and media have not been saved locally.", note]))
    note_html = f'<p class="entry-note"><strong>Coverage:</strong> {e(note)}</p>' if note else ""
    authors = entry.get("authors") or []
    if isinstance(authors, str):
        authors = [authors]
    author_names = [str(author.get("name") or "") if isinstance(author, dict) else str(author) for author in authors]
    author_names = [name for name in author_names if name]
    authors_html = f'<p class="entry-authors"><strong>{"Author" if len(author_names) == 1 else "Authors"}:</strong> {e(", ".join(author_names))}</p>' if author_names else ""
    license_info = entry.get("license")
    if isinstance(license_info, dict):
        license_info = " ".join(str(license_info[key]) for key in ["name", "url"] if license_info.get(key))
    license_html = f'<p class="entry-license"><strong>License / rights:</strong> {linkify(license_info)}</p>' if license_info else ""
    return f'''<article class="archive-entry" id="{e(entry_id)}" data-category="{e(category)}">
{cover_html}<div class="entry-inner"><div class="entry-meta"><span class="entry-category">{e(category)}</span><span>{e(date_label(entry.get("date")))}</span></div>
<h2><a href="#{e(entry_id)}">{e(title)}</a></h2>{authors_html}<p class="entry-summary" dir="auto">{e(summary)}</p>
<div class="entry-badges">{"".join(badges)}</div><div class="entry-actions">{actions}</div>{details}{note_html}{license_html}</div></article>'''


def render_project(project):
    title = e(project.get("title"))
    url = remote_url(project.get("url"))
    repo = remote_url(project.get("repository"))
    live = bool(project.get("live"))
    main_label = "Open project ↗" if live else "View repository ↗"
    actions = f'<a href="{e(url)}" target="_blank" rel="noopener noreferrer">{main_label}</a>' if url else ""
    if repo and repo != url:
        actions += f'<a href="{e(repo)}" target="_blank" rel="noopener noreferrer">Source code</a>'
    symbols = {"Aristotle Virtue Map": "◇", "Colourful Combinatorics": "∴", "IMC 2026 Puzzle Arena": "Σ", "VirtueMap Annotation Survey": "↗"}
    symbol = symbols.get(str(project.get("title")), "↗")
    return f'<article class="project-card"><div class="project-topline"><span class="project-kind">{"Live project" if live else "Code & research"}</span><span class="project-symbol" aria-hidden="true">{symbol}</span></div><h3>{title}</h3><p>{e(project.get("description"))}</p><div class="project-actions">{actions}</div></article>'


def replace_block(html, name, body, before):
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    block = f"{start}\n{body}\n{end}"
    if start in html and end in html:
        return re.sub(re.escape(start) + r".*?" + re.escape(end), lambda _: block, html, flags=re.S)
    if before not in html:
        raise ValueError(f"Cannot find homepage insertion point: {before}")
    return html.replace(before, block + "\n\n      " + before, 1)


def update_home(data, entries, media_count):
    path = ROOT / "index.html"
    html = path.read_text(encoding="utf-8")
    if 'href="assets/archive.css"' not in html:
        html = html.replace("</head>", '  <link rel="stylesheet" href="assets/archive.css">\n</head>')
    if 'src="assets/site-effects.js"' not in html:
        html = html.replace("</head>", '  <script src="assets/site-effects.js" defer></script>\n</head>')
    if 'class="skip-link"' not in html:
        html = html.replace("<body>", '<body>\n  <a class="skip-link" href="#main-content">Skip to content</a>')
        html = html.replace("<main>", '<main id="main-content">', 1)
    if 'href="#projects"' not in html:
        html = html.replace('<a class="pill" href="#about">About</a>', '<a class="pill" href="#about">About</a>\n        <a class="pill" href="#projects">Projects</a>\n        <a class="pill" href="archive/">Archive</a>')
    html = html.replace("PhD candidate • TUM • Munich", "Researcher & Lecturer • TUM • Munich")
    html = html.replace("PhD candidate at the Chair of Transportation Systems Engineering (TUM), collaborating with Huawei Munich Research Center.", "Researcher, lecturer and PhD candidate at the Chair of Transportation Systems Engineering, Technical University of Munich (TUM).")
    old_current = '<div class="role">Researcher (Fixed-term PhD Contract) — Huawei Munich Research Center</div>\n              <div class="meta">09/2024 – present</div>\n            </div>\n            <div class="meta">Trustworthy Technology & Engineering Lab • Identity & Access Management</div>'
    new_current = '<div class="role">Lecturer & Researcher — TUM</div>\n              <div class="meta">09/2026 – present</div>\n            </div>\n            <div class="meta">Chair of Transportation Systems Engineering • School of Engineering and Design</div>'
    html = html.replace(old_current, new_current)
    html = html.replace('<div class="role">Huawei Munich Research Center — Identity & Access Management</div>\n              <div class="meta">09/2024 – present</div>', '<div class="role">Huawei Munich Research Center — Identity & Access Management</div>\n              <div class="meta">09/2024 – 08/2026</div>')
    if '<div class="role">TUM — Lecturer & Researcher</div>' not in html:
        html = html.replace('<h2>Work experience</h2>', '<h2>Work experience</h2>\n          <div class="item"><div class="top"><div class="role">TUM — Lecturer & Researcher</div><div class="meta">09/2026 – present</div></div><ul class="bullets"><li>Chair of Transportation Systems Engineering, School of Engineering and Design</li></ul></div>')
    html = html.replace("GitHub Pages • single-file HTML", "GitHub Pages • Personal website & archive")
    projects = data.get("projects", [])
    launched = [project for project in projects if project.get("live")]
    code = [project for project in projects if not project.get("live")]
    project_html = f'''<section class="card section archive-home-section" id="projects" aria-labelledby="projects-heading">
<div class="section-heading"><div><p class="eyebrow">01 / Explore & interact</p><h2 id="projects-heading">Projects & experiments.</h2><p class="subtitle">Interactive work in mathematics, language models and human decision-making.</p></div><a class="section-link" href="https://github.com/jtzach" target="_blank" rel="noopener noreferrer">GitHub profile ↗</a></div>
<div class="project-grid launched-grid">{"".join(render_project(project) for project in launched)}</div>'''
    if code:
        project_html += f'<details class="entry-detail"><summary>Research code & other projects ({len(code)})</summary><div class="project-grid">{"".join(render_project(project) for project in code)}</div></details>'
    project_html += "</section>"
    html = replace_block(html, "PROJECTS", project_html, '<section class="card section" id="personal">')
    preview_entries = [entry for entry in entries if entry.get("status") == "full-text"][:3]
    if len(preview_entries) < 3:
        preview_entries += [entry for entry in entries if entry not in preview_entries][:3-len(preview_entries)]
    previews = []
    for entry in preview_entries:
        previews.append(f'<article class="preview-item"><span class="eyebrow">{e(entry.get("category"))}</span><h3><a href="archive/#{e(entry["id"])}">{e(entry.get("title"))}</a></h3><p>{e(date_label(entry.get("date")))}</p></article>')
    linkedin_count = sum(entry.get("category") == "LinkedIn" for entry in entries)
    archive_html = f'''<section class="card section archive-intro archive-home-section" id="archive" aria-labelledby="archive-heading">
<div class="section-heading"><div><p class="eyebrow">02 / Notes, milestones & discoveries</p><h2 id="archive-heading">The personal archive.</h2><p class="subtitle">Posts, writing, research and moments from across the web, collected here with locally saved files.</p></div><a class="section-link" href="archive/">Explore the archive →</a></div>
<div class="stat-row"><span><strong>{len(entries)}</strong>Entries collected</span><span><strong>{linkedin_count}</strong>LinkedIn posts</span><span><strong>{media_count}</strong>Files saved</span></div>
<div class="archive-preview">{"".join(previews)}</div>
<a class="btn" href="archive/">Browse posts & media →</a><p class="archive-note">Each entry identifies what is saved here and links to its original source. This collection includes publicly retrievable material; coverage and missing media are noted in the archive.</p></section>'''
    html = replace_block(html, "ARCHIVE", archive_html, '<section class="card section" id="personal">')
    path.write_text(html, encoding="utf-8", newline="\n")


def build(data_path):
    data = json.loads(data_path.read_text(encoding="utf-8-sig"))
    entries = data.get("entries", [])
    ids = [entry["id"] for entry in entries]
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", entry_id) for entry_id in ids):
        raise ValueError("Archive entry ids must be unique, URL-safe identifiers.")
    entries = sorted(entries, key=lambda entry: str(entry.get("date") or ""), reverse=True)
    all_media = [media for entry in entries for media in entry.get("media", []) if media_paths(media)]
    media_count = len({path for media in all_media for path in media_paths(media)})
    linkedin_count = sum(entry.get("category") == "LinkedIn" for entry in entries)
    categories = sorted({str(entry.get("category") or "Writing") for entry in entries})
    options = ''.join(f'<option value="{e(category)}">{e(category)}</option>' for category in categories)
    updated = date_label(data.get("updated"))
    coverage = notes_text(data.get("coverage")) or "This collection contains material retrievable from public sources. LinkedIn may hide older posts and additional carousel media; linked sources without a saved copy remain dependent on the original website. Coverage is recorded on each entry."
    page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Personal archive — Ioannis Tzachristas</title><meta name="description" content="Posts, writing, research and media by Ioannis Tzachristas, preserved with local files and original source references.">
<meta name="author" content="Ioannis Tzachristas"><link rel="stylesheet" href="../assets/archive.css"><script src="../assets/archive.js" defer></script><script src="../assets/site-effects.js" defer></script></head>
<body class="archive-page"><a class="skip-link" href="#archive-main">Skip to archive</a>
<header class="archive-header"><div class="archive-wrap"><a class="archive-home" href="../"><img src="../assets/img/image1.jpeg" alt="">Ioannis Tzachristas</a><nav aria-label="Primary"><a href="../">About</a><a href="../#projects">Projects</a><a href="./" aria-current="page">Archive</a><a href="../#research">Research</a><a href="../#contact">Contact</a></nav></div></header>
<main class="archive-wrap" id="archive-main"><div class="archive-masthead"><div><p class="eyebrow">A collection, kept close</p><h1>Personal archive.</h1><p class="archive-lead">Ideas, research and moments along the way.<br>Posts and writing from across the web, with saved copies you can read here.</p></div><div><div class="stat-row"><span><strong>{len(entries)}</strong>Entries</span><span><strong>{linkedin_count}</strong>LinkedIn posts</span><span><strong>{media_count}</strong>Local files</span></div><p class="archive-note">Collected through {e(updated)}</p></div></div>
<aside class="coverage-notice" aria-label="Archive coverage"><strong>What is preserved?</strong> {e(coverage)} Text and media marked as saved are stored with this website. Original-source links open the external publication.</aside>
<div class="archive-controls js-only" role="search" aria-label="Search archive"><div class="search-field"><label for="archive-search">Search posts, titles & saved text</label><input id="archive-search" type="search" placeholder="Try mathematics, piano, TUM…" autocomplete="off"></div><div class="filter-field"><label for="archive-category">Collection</label><select id="archive-category"><option value="">All collections</option>{options}</select></div><button type="button" id="clear-filters">Clear</button></div>
<noscript><p>All entries and saved content are available below. Enable JavaScript to search and filter the collection.</p></noscript>
<div class="result-line"><span id="result-count" aria-live="polite">{len(entries)} entries</span><span>Newest first · Undated entries at the end</span></div>
<div class="archive-entries">{"".join(render_entry(entry) for entry in entries)}</div><p class="no-results" id="no-results" hidden>No entries match this search. Try a different word or clear the filters.</p>
<footer class="archive-footer"><p>Ioannis Tzachristas · Personal archive</p><a href="../data/archive.json" download>Download the archive index (JSON)</a><a href="../data/coverage-gaps.json">Coverage &amp; known gaps</a><a href="../data/file-manifest.json">Saved file checksums</a><a href="../">Back to personal website ↑</a></footer></main></body></html>'''
    (ROOT / "archive").mkdir(exist_ok=True)
    (ROOT / "archive" / "index.html").write_text(page, encoding="utf-8", newline="\n")
    update_home(data, entries, media_count)
    print(f"Built archive: {len(entries)} entries, {linkedin_count} LinkedIn posts, {media_count} local files, {len(data.get('projects', []))} projects")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data" / "archive.json")
    args = parser.parse_args()
    build(args.data)
