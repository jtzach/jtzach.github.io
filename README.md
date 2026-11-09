# Ioannis Tzachristas — personal website and archive

[Personal website](https://jtzach.github.io/) · [Archive](https://jtzach.github.io/archive/)

This static GitHub Pages site brings together my profile, projects, writing and research, with locally saved copies of retrievable media. The collection assembled on 8 November 2026 includes 11 LinkedIn posts, all 75 entries exposed by my two public blog feeds, one ATRIUM article, 13 research PDFs, six videos and 10 summaries of recognition and external coverage. The project section links to two live projects and seven code repositories.

This is a public-source collection, not a verified export of every LinkedIn post or every mention on the web. [Known coverage gaps](data/coverage-gaps.json) include additional indexed LinkedIn posts, old embedded resources and the school portfolio. Each [archive entry](data/archive.json) distinguishes saved text, summaries, local media and source-only references.

## Maintain and preview

Python 3 is sufficient; the site has no build dependencies.

1. Edit `data/archive.json`. Add entries with a unique `id`, `title`, `category`, `source_url`, a verified `date` when available, `text`, `status` and `media`. Preserve author credits, source links and coverage notes. The statuses are `full-text`, `archived`, `summary` and `source-only`; media records use paths relative to the site root.
2. Place saved images, PDFs, videos or other files under `assets/` and reference them in the entry's `media` array. Keep the source URL and retrieval metadata. An external link alone is not a backup.
3. Run from this directory:

   ```sh
   python scripts/update_manifest.py
   python scripts/build_archive.py
   python scripts/check_archive.py
   python -m http.server 8000
   ```

4. Open `http://localhost:8000/` and `http://localhost:8000/archive/`. Check the changed entries, local files, search and mobile layout before committing the data, assets and generated HTML together.

The generator rebuilds `archive/index.html` and the marked project/archive sections of `index.html`; edit other homepage sections directly. It does not fetch new posts or media. There is no scheduled automatic synchronization.

## Preservation and attribution

Files referenced locally remain available with the repository even if their original hosts disappear. The six saved YouTube videos are 360p or 720p delivery copies with audio, not original camera or master files. SlideShare slides are saved as rendered images, not editable presentation decks. A recovered GeoGebra construction is stored as a `.ggb` file. Some unavailable embeds remain source links with coverage notes.

My published text is retained with its original quotations and credits. Research records preserve coauthors and available license information. Outside press and institutional pages are represented by factual summaries and attribution; their complete articles and photographs are not republished. No blanket reuse license is implied for third-party material.

Original blog markup is also retained as inert data in [blog-original-markup.json](data/blog-original-markup.json). Two larger videos are stored in lossless parts and assembled by the archive player. [Video recovery instructions](scripts/VIDEO_RECOVERY.md) explain how to reconstruct complete MP4s offline.

[The file manifest](data/file-manifest.json) records saved asset paths, byte sizes and SHA-256 checksums. Refresh it when adding or replacing files; the HTML build does not regenerate it. Keep source files and additional independent backups when available.
