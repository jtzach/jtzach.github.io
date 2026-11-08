"""Save publicly retrievable media for the curated personal archive.

Input is a JSON list of records with images/videos and source URLs. The output
retains failures explicitly; a source URL alone is never counted as a backup.
"""
import argparse
import base64
import concurrent.futures
import hashlib
import json
import mimetypes
from pathlib import Path
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 95 * 1024 * 1024  # Keep individual assets below GitHub's hard file limit.


def download(job):
    url, folder = job
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ('https', 'http', 'data'):
        return url, {'error': 'Unsupported source URL scheme'}
    key = hashlib.sha256(url.encode()).hexdigest()[:20]
    cache = ROOT / 'data' / 'download-cache.json'
    old = CACHE.get(url)
    if old and (ROOT / old['path']).is_file():
        payload = (ROOT / old['path']).read_bytes()
        if hashlib.sha256(payload).hexdigest() == old['sha256']:
            return url, old
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Personal content archive)'})
        with urllib.request.urlopen(request, timeout=45) as response:
            mime = response.headers.get_content_type()
            if not (mime.startswith(('image/', 'video/', 'audio/')) or mime == 'application/pdf'):
                raise ValueError(f'Expected media; received {mime}')
            if int(response.headers.get('Content-Length', '0')) > LIMIT:
                raise ValueError('File exceeds the per-file archive limit')
            payload = response.read(LIMIT + 1)
            if len(payload) > LIMIT:
                raise ValueError('File exceeds the per-file archive limit')
            if not payload:
                raise ValueError('Empty response')
        ext = {'image/jpeg': '.jpg', 'image/png': '.png', 'image/gif': '.gif',
               'image/webp': '.webp', 'video/mp4': '.mp4', 'application/pdf': '.pdf'}.get(mime)
        ext = ext or mimetypes.guess_extension(mime) or '.bin'
        path = Path('assets') / 'archive' / folder / (key + ext)
        (ROOT / path).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / path).write_bytes(payload)
        return url, {'path': path.as_posix(), 'type': mime, 'bytes': len(payload),
                     'sha256': hashlib.sha256(payload).hexdigest(), 'source_url': url,
                     'retrieved': '2026-11-08'}
    except Exception as error:
        return url, {'error': str(error), 'source_url': url}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input')
    parser.add_argument('output')
    args = parser.parse_args()
    records = json.loads(Path(args.input).read_text(encoding='utf-8'))
    cache_path = ROOT / 'data' / 'download-cache.json'
    cache_path.parent.mkdir(exist_ok=True)
    CACHE = json.loads(cache_path.read_text(encoding='utf-8')) if cache_path.exists() else {}
    jobs = {}
    for record in records:
        for kind in ['images', 'videos']:
            items = record.get(kind, [])
            if isinstance(items, dict): items = [items]
            for item in items:
                url = item if isinstance(item, str) else item.get('contentUrl', item.get('url', ''))
                if url: jobs[url] = record.get('category', 'media').lower()
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for url, result in pool.map(download, jobs.items()):
            results[url] = result
            if 'path' in result: CACHE[url] = result
            print(json.dumps({'saved': len(results), 'total': len(jobs), 'bytes': result.get('bytes'), 'error': result.get('error')}), flush=True)
            cache_path.write_text(json.dumps(CACHE, ensure_ascii=False, indent=2), encoding='utf-8')
    for record in records:
        media = list(record.get('media', []))
        missing = []
        for kind in ['images', 'videos']:
            items = record.get(kind, [])
            if isinstance(items, dict): items = [items]
            for number, item in enumerate(items, 1):
                url = item if isinstance(item, str) else item.get('contentUrl', item.get('url', ''))
                if not url: continue
                saved = results[url]
                if 'path' in saved:
                    media.append(dict(saved, alt=f"{record['title']} — {kind[:-1]} {number}"))
                else: missing.append(saved)
        record['media'] = list({item['path']: item for item in media}.values())
        record['missing_media'] = missing
    Path(args.output).write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
