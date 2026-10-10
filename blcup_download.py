#!/usr/bin/env python3
"""Download every MP3 listed on a BLCUP (blcup.com) mobile resource series page.

Usage:
    python blcup_download.py "http://www.blcup.com/MobileResSeries?rid=<id>" [-o DIR] [-j 8] [--full-names]

By default each file is saved under its track number only (e.g. 1-01-01-01.mp3).
Files already downloaded with the correct size are skipped, so the script can be
re-run safely to resume an interrupted download.
"""

import argparse
import html
import re
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE = "http://www.blcup.com"
ITEM_RE = re.compile(
    r'href="/MobileResource\?rid=([0-9a-fA-F-]+)"[^>]*>([^<]+)<span class="badge">mp3</span>'
)
CODE_RE = re.compile(r"(\d+(?:-\d+)+)\s*$")
INVALID_CHARS = re.compile(r'[\\/:*?"<>|]')


def fetch(url, method="GET"):
    req = urllib.request.Request(url, method=method, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=60)


def list_tracks(series_url):
    with fetch(series_url) as resp:
        page = resp.read().decode("utf-8", errors="replace")
    tracks = []
    for rid, title in ITEM_RE.findall(page):
        title = html.unescape(title).strip()
        tracks.append((rid, title))
    return tracks


def target_name(title, full_names):
    if not full_names:
        m = CODE_RE.search(title)
        if m:
            return m.group(1) + ".mp3"
    return INVALID_CHARS.sub("_", title) + ".mp3"


def download(rid, dest, retries=3):
    url = f"{BASE}/Common/DownRes?doi={urllib.parse.quote(rid)}"
    part = dest.with_name(dest.name + ".part")
    last_err = None
    for _ in range(retries):
        try:
            with fetch(url) as resp:
                expected = int(resp.headers.get("Content-Length") or 0)
                if dest.exists() and expected and dest.stat().st_size == expected:
                    return "skipped"
                with open(part, "wb") as f:
                    while chunk := resp.read(64 * 1024):
                        f.write(chunk)
            if expected and part.stat().st_size != expected:
                raise IOError(f"incomplete: {part.stat().st_size}/{expected} bytes")
            part.replace(dest)
            return "downloaded"
        except Exception as e:  # retry on any network/IO error
            last_err = e
    part.unlink(missing_ok=True)
    raise RuntimeError(last_err)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", help="MobileResSeries page URL")
    ap.add_argument("-o", "--output", default=".", help="output directory (default: current)")
    ap.add_argument("-j", "--jobs", type=int, default=8, help="parallel downloads (default: 8)")
    ap.add_argument("--full-names", action="store_true", help="keep the full title as the filename")
    args = ap.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    tracks = list_tracks(args.url)
    if not tracks:
        sys.exit("No MP3 tracks found on that page.")
    print(f"Found {len(tracks)} tracks.")

    names = [target_name(t, args.full_names) for _, t in tracks]
    if len(set(names)) != len(names):
        sys.exit("Track numbers are not unique on this page; rerun with --full-names.")

    failed = 0
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(download, rid, out / name): name for (rid, _), name in zip(tracks, names)}
        for i, fut in enumerate(as_completed(futures), 1):
            name = futures[fut]
            try:
                status = fut.result()
                print(f"[{i}/{len(tracks)}] {status}: {name}")
            except Exception as e:
                failed += 1
                print(f"[{i}/{len(tracks)}] FAILED: {name} ({e})", file=sys.stderr)

    print(f"Done. {len(tracks) - failed} ok, {failed} failed.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
