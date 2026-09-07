"""Download the public monthly inputs used by FairQueue 2.0.

The script discovers links from NHS England archive pages rather than relying on
hard-coded media URLs. It keeps raw files out of version control and writes a
small, tracked provenance manifest with source URLs and SHA-256 digests.

Coverage: April 2022 through June 2026 (inclusive).
"""
from __future__ import annotations

import argparse
import hashlib
import html
import shutil
import sys
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
from utils import RAW, ROOT, period_from_text  # noqa: E402

START = pd.Period("2022-04", freq="M")
END = pd.Period("2026-06", freq="M")
USER_AGENT = "FairQueue/2.0 (+https://github.com/tollyboy88/fairqueue-simulator)"

RTT_PAGES = [
    "https://www.england.nhs.uk/statistics/statistical-work-areas/"
    f"rtt-waiting-times/rtt-data-{year}/"
    for year in ("2022-23", "2023-24", "2024-25", "2025-26", "2026-27")
]
DM01_PAGES = [
    "https://www.england.nhs.uk/statistics/statistical-work-areas/"
    "diagnostics-waiting-times-and-activity/monthly-diagnostics-waiting-times-and-activity/"
    f"monthly-diagnostics-data-{year}/"
    for year in ("2022-23", "2023-24", "2024-25", "2025-26", "2026-27")
]
WLMDS_GEOGRAPHY_URL = (
    "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/03/"
    "WLMDS-Demographics-Geography-to-22-February-2026-v1.csv"
)
WLMDS_SNAPSHOT_DATE = pd.Timestamp("2026-02-22")
WLMDS_AVAILABLE_DATE = pd.Timestamp("2026-03-12")


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.links.append((html.unescape(" ".join(self._text)), self._href))
            self._href = None
            self._text = []


@dataclass(frozen=True)
class Source:
    dataset: str
    month: pd.Period
    url: str


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read().decode("utf-8", errors="replace")


def discover(page: str, dataset: str) -> list[Source]:
    parser = LinkParser()
    parser.feed(fetch_text(page))
    found: dict[pd.Period, Source] = {}
    for text, href in parser.links:
        joined = f"{text} {href}"
        low = joined.lower()
        if not href.lower().endswith(".zip"):
            continue
        if dataset == "rtt" and "full-csv-data-file" not in low:
            continue
        if dataset == "dm01" and ("full-extract" not in low or "cdc" in low):
            continue
        # Media filenames are more reliable than occasionally mistyped link text.
        year, month = period_from_text(href)
        if not (year and month):
            year, month = period_from_text(text)
        if not (year and month):
            continue
        period = pd.Period(f"{year}-{month:02d}", freq="M")
        if START <= period <= END:
            found[period] = Source(dataset, period, href)
    return list(found.values())


def existing_file(dataset: str, month: pd.Period) -> Path | None:
    folder = "rtt" if dataset == "rtt" else "diagnostics"
    roots = [RAW / folder, RAW / f"{dataset}_longitudinal"]
    token_a = month.strftime("%b%y").lower()
    token_b = month.strftime("%B-%Y").lower()
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.zip"):
            low = path.name.lower()
            if dataset == "rtt" and "full-csv" not in low:
                continue
            if dataset == "dm01" and ("full-extract" not in low or "cdc" in low):
                continue
            if token_a in low or token_b in low or str(month) in low:
                return path
    return None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(source: Source, force: bool = False) -> Path:
    present = None if force else existing_file(source.dataset, source.month)
    if present is not None:
        print(f"reuse {source.dataset:4s} {source.month}: {present.name}")
        return present
    folder = RAW / f"{source.dataset}_longitudinal"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{source.dataset}_{source.month}.zip"
    partial = target.with_suffix(".part")
    print(f"download {source.dataset:4s} {source.month}: {source.url}")
    request = urllib.request.Request(source.url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response, partial.open("wb") as output:
        shutil.copyfileobj(response, output)
    partial.replace(target)
    return target


def download_wlmds_geography(force: bool = False) -> Path:
    folder = RAW / "wlmds" / "WLMDS"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / Path(WLMDS_GEOGRAPHY_URL).name
    if target.exists() and not force:
        print(f"reuse wlmds {WLMDS_SNAPSHOT_DATE.date()}: {target.name}")
        return target
    partial = target.with_suffix(".part")
    print(f"download wlmds {WLMDS_SNAPSHOT_DATE.date()}: {WLMDS_GEOGRAPHY_URL}")
    request = urllib.request.Request(WLMDS_GEOGRAPHY_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response, partial.open("wb") as output:
        shutil.copyfileobj(response, output)
    partial.replace(target)
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="redownload files already present")
    args = parser.parse_args()

    sources = []
    for page in RTT_PAGES:
        sources.extend(discover(page, "rtt"))
    for page in DM01_PAGES:
        sources.extend(discover(page, "dm01"))
    selected = {(source.dataset, str(source.month)): source for source in sources}
    expected = {
        (dataset, str(month))
        for dataset in ("rtt", "dm01")
        for month in pd.period_range(START, END, freq="M")
    }
    missing_links = sorted(expected - set(selected))
    if missing_links:
        raise RuntimeError(f"Archive pages did not expose expected links: {missing_links}")

    rows = []
    retrieved = datetime.now(timezone.utc).isoformat()
    for key in sorted(selected):
        source = selected[key]
        path = download(source, force=args.force)
        rows.append({
            "dataset": source.dataset,
            "month": str(source.month),
            "source_url": source.url,
            "local_path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "retrieved_utc": retrieved,
            "available_date": "",
        })
    wlmds_path = download_wlmds_geography(force=args.force)
    rows.append({
        "dataset": "wlmds_geography",
        "month": str(WLMDS_SNAPSHOT_DATE.to_period("M")),
        "source_url": WLMDS_GEOGRAPHY_URL,
        "local_path": wlmds_path.relative_to(ROOT).as_posix(),
        "bytes": wlmds_path.stat().st_size,
        "sha256": sha256(wlmds_path),
        "retrieved_utc": retrieved,
        "available_date": WLMDS_AVAILABLE_DATE.date().isoformat(),
    })
    manifest = ROOT / "data" / "source_manifest.csv"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).sort_values(["dataset", "month"]).to_csv(manifest, index=False)
    print(f"Wrote {manifest} with {len(rows)} dated sources")


if __name__ == "__main__":
    main()
