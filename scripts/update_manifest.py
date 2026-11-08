"""Refresh hashes of the assets stored in the repository."""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--date', default=date.today().isoformat(), help='Collection date, YYYY-MM-DD')
args = parser.parse_args()
files = []
for path in sorted((root/'assets').rglob('*')):
    if not path.is_file() or path.suffix in ('.css','.js'): continue
    raw = path.read_bytes()
    files.append({'path':path.relative_to(root).as_posix(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
(root/'data/file-manifest.json').write_text(json.dumps({'created':args.date,'files':files},indent=2),encoding='utf-8')
print(f'Recorded {len(files)} files, {sum(item["bytes"] for item in files):,} bytes')
