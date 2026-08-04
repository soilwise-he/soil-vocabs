"""Test helper: download the CSV attached to a GitHub issue and log it.

GitHub rewrites an uploaded attachment into a markdown link pointing at
``https://github.com/user-attachments/files/<id>/<filename>`` (older issues use
``https://github.com/<owner>/<repo>/files/<id>/<filename>``). This script scans
the issue text for such links, downloads them, and prints what it found so we
can confirm the workflow wiring before adding any real validation.
"""

import argparse
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

URL_RE = re.compile(r"https?://[^\s)\]}<>\"']+")
ATTACHMENT_RE = re.compile(
    r"^https?://(?:www\.)?github\.com/(?:user-attachments/files/\d+/|[^/]+/[^/]+/files/\d+/)",
    re.IGNORECASE,
)

PREVIEW_ROWS = 20


def find_urls(text: str) -> list[str]:
    urls: list[str] = []
    for raw in URL_RE.findall(text or ""):
        url = raw.rstrip(".,;:")
        if url in urls:
            continue
        if ATTACHMENT_RE.match(url) or url.lower().endswith((".csv", ".tsv")):
            urls.append(url)
    return urls


def download(url: str, out_dir: Path) -> Path:
    request = urllib.request.Request(url, headers={"User-Agent": "soil-vocabs-ci"})
    with urllib.request.urlopen(request, timeout=60) as response:
        name = Path(urllib.parse.unquote(urllib.parse.urlparse(url).path)).name or "attachment.csv"
        target = out_dir / name
        target.write_bytes(response.read())
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body-file", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=Path("issue-attachments"))
    args = parser.parse_args()

    body = args.body_file.read_text(encoding="utf-8")
    urls = find_urls(body)
    print(f"Found {len(urls)} candidate attachment URL(s).")
    for url in urls:
        print(f"  {url}")

    if not urls:
        print("No CSV attachment found in the issue text.", file=sys.stderr)
        return 1

    args.out_dir.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    for url in urls:
        try:
            path = download(url, args.out_dir)
        except urllib.error.URLError as exc:
            print(f"Could not download {url}: {exc}", file=sys.stderr)
            continue

        downloaded += 1
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        lines = text.splitlines()
        print("-" * 70)
        print(f"File:  {path.name}")
        print(f"Bytes: {path.stat().st_size}")
        print(f"Lines: {len(lines)}")
        print(f"First {min(PREVIEW_ROWS, len(lines))} line(s):")
        for line in lines[:PREVIEW_ROWS]:
            print(f"  | {line}")
        if len(lines) > PREVIEW_ROWS:
            print(f"  ... {len(lines) - PREVIEW_ROWS} more line(s)")

    if not downloaded:
        print("None of the candidate URLs could be downloaded.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
