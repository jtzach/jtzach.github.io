"""Check preservation, local dependencies and archive file integrity before publishing."""
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links, self.resources = [], [], []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if attrs.get('id'): self.ids.append(attrs['id'])
        if attrs.get('href'): self.links.append(attrs['href'])
        if tag in ('img', 'script', 'video', 'audio', 'source', 'iframe'):
            for name in ('src', 'poster'):
                if attrs.get(name): self.resources.append(attrs[name])
        if tag == 'link' and attrs.get('rel') == 'stylesheet':
            self.resources.append(attrs['href'])


def check():
    data = json.loads((ROOT / 'data/archive.json').read_text(encoding='utf-8'))
    pages = {}
    for relative in ('index.html', 'archive/index.html'):
        page = Page()
        page.feed((ROOT / relative).read_text(encoding='utf-8'))
        assert len(page.ids) == len(set(page.ids)), f'Duplicate IDs in {relative}'
        pages[relative] = page
    for relative, page in pages.items():
        base = (ROOT / relative).parent
        for url in page.resources:
            assert not urlsplit(url).scheme and not url.startswith('//'), f'External dependency: {url}'
        for url in page.links + page.resources:
            parsed = urlsplit(url)
            if parsed.scheme or parsed.netloc: continue
            target = (base / unquote(parsed.path)).resolve() if parsed.path else ROOT / relative
            assert target.is_relative_to(ROOT), f'Path leaves site: {url}'
            if target.is_dir(): target = target / 'index.html'
            assert target.exists(), f'Missing local file: {relative}: {url}'
            key = target.relative_to(ROOT).as_posix()
            if parsed.fragment and key in pages:
                assert unquote(parsed.fragment) in pages[key].ids, f'Missing anchor: {url}'
    manifest = json.loads((ROOT / 'data/file-manifest.json').read_text(encoding='utf-8'))['files']
    total = 0
    for item in manifest:
        raw = (ROOT / item['path']).read_bytes()
        assert len(raw) == item['bytes']
        assert hashlib.sha256(raw).hexdigest() == item['sha256'], f'Hash mismatch: {item["path"]}'
        assert len(raw) < 100 * 1024 * 1024, f'GitHub file limit: {item["path"]}'
        total += len(raw)
    assert total < 1024 ** 3, 'GitHub Pages size limit'
    for entry in data['entries']:
        assert entry['id'] in pages['archive/index.html'].ids
        for media in entry.get('media', []):
            paths = media.get('parts') or ([media['path']] if media.get('path') else [])
            payload_hash = hashlib.sha256()
            length = 0
            for path in paths:
                if isinstance(path, dict): path = path.get('path')
                assert (ROOT / path).is_file(), f'Missing media: {path}'
                raw = (ROOT / path).read_bytes()
                payload_hash.update(raw)
                length += len(raw)
            if paths and media.get('sha256'):
                assert payload_hash.hexdigest() == media['sha256'], f'Media integrity: {entry["id"]}'
            if paths and media.get('bytes'):
                assert length == media['bytes'], f'Media size: {entry["id"]}'
    original = Page()
    original.feed(subprocess.check_output(['git','show','68c64a54fec67e713131200f26a146c6dd29c5f2:index.html'],cwd=ROOT).decode())
    assert set(original.ids).issubset(pages['index.html'].ids), 'An original homepage section was removed'
    assert set(original.links).issubset(pages['index.html'].links), 'An original homepage link was removed'
    home = (ROOT/'index.html').read_text(encoding='utf-8')
    for project in data['projects']:
        assert project['url'] in home, f'Project missing: {project["title"]}'
    print(json.dumps({'result':'passed','entries':len(data['entries']),'preserved_original_sections':len(original.ids),
                      'projects':len(data['projects']),'manifest_files':len(manifest),'asset_bytes':total}))


if __name__ == '__main__': check()
