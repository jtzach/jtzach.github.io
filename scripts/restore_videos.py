"""Restore complete MP4s from saved parts, checking their original SHA-256.

Run: python scripts/restore_videos.py --output /path/to/recovered-videos
The archive index defaults to data/archive.json. Existing files are never replaced.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def digest_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_part(value, root):
    if not isinstance(value, str) or not value.startswith("assets/") or any(c in value for c in "\\:%?#"):
        raise ValueError(f"Unsafe video part: {value!r}")
    if any(part in {"", ".", ".."} for part in value.split("/")):
        raise ValueError(f"Unsafe video part: {value!r}")
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"Missing or unsafe video part: {value!r}")
    return path


def restore(media, destination, root=ROOT):
    filename = media.get("original_filename", "")
    expected_hash = media.get("sha256", "")
    expected_bytes = media.get("bytes")
    if not isinstance(filename, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.mp4", filename):
        raise ValueError("Invalid restored video filename.")
    if not re.fullmatch(r"[0-9a-f]{64}", str(expected_hash)) or not isinstance(expected_bytes, int) or expected_bytes <= 0:
        raise ValueError("Video record lacks a valid checksum or byte count.")
    parts = media.get("parts")
    if not isinstance(parts, list) or not parts or not all(isinstance(part, str) for part in parts) or len(parts) != len(set(parts)):
        raise ValueError("Video record needs distinct ordered parts.")
    paths = [safe_part(part, root) for part in parts]
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / filename
    if target.exists():
        if target.is_file() and target.stat().st_size == expected_bytes and digest_file(target) == expected_hash:
            print(f"Already verified: {target}")
            return target
        raise FileExistsError(f"Refusing to overwrite existing file: {target}")
    temporary = None
    try:
        digest = hashlib.sha256()
        length = 0
        with tempfile.NamedTemporaryFile(mode="wb", prefix=".restore-video-", suffix=".tmp", dir=destination, delete=False) as output:
            temporary = Path(output.name)
            for path in paths:
                with path.open("rb") as source:
                    for block in iter(lambda: source.read(1024 * 1024), b""):
                        output.write(block)
                        digest.update(block)
                        length += len(block)
            output.flush()
            os.fsync(output.fileno())
        if length != expected_bytes or digest.hexdigest() != expected_hash:
            raise ValueError(f"Integrity verification failed for {filename}; no complete file was published.")
        # Exclusive creation refuses an existing destination, including one
        # created after the earlier check. This works on cloud-backed folders
        # and filesystems that do not support hard links.
        with target.open("xb") as restored, temporary.open("rb") as source:
            shutil.copyfileobj(source, restored, length=1024 * 1024)
            restored.flush()
            os.fsync(restored.fileno())
        if target.stat().st_size != expected_bytes or digest_file(target) != expected_hash:
            raise ValueError(f"Restored file verification failed: {target}")
        print(f"Restored and verified: {target}")
        return target
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="Folder for complete restored MP4 files")
    parser.add_argument("--index", type=Path, default=ROOT / "data" / "archive.json")
    parser.add_argument("--id", help="Restore only this archive entry ID")
    args = parser.parse_args()
    data = json.loads(args.index.read_text(encoding="utf-8-sig"))
    entries = data["entries"]
    count = 0
    for entry in entries:
        if args.id and entry.get("id") != args.id:
            continue
        for media in entry.get("media", []):
            if media.get("type", "").startswith("video") and media.get("parts"):
                restore(media, args.output)
                count += 1
    if not count:
        raise SystemExit("No matching videos requiring restoration were found in the index.")


if __name__ == "__main__":
    main()
