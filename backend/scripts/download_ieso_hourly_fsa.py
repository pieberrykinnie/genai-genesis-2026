from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import httpx

BASE_URL = "https://reports-public.ieso.ca/public/HourlyConsumptionByFSA/"
HREF_RE = re.compile(r'href="([^"]+)"', re.IGNORECASE)
MONTHLY_ZIP_RE = re.compile(
    r"^PUB_HourlyConsumptionByFSA_(?P<ym>\d{6})_v(?P<version>\d+)\.zip$",
    re.IGNORECASE,
)
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/zip,*/*",
}


@dataclass(frozen=True)
class MonthlyZip:
    ym: str
    version: int
    filename: str
    url: str


def _validate_ym(value: str, field_name: str) -> str:
    value = value.strip()
    if not re.fullmatch(r"\d{6}", value):
        raise ValueError(f"{field_name} must be YYYYMM, got {value!r}")
    month = int(value[4:6])
    if month < 1 or month > 12:
        raise ValueError(f"{field_name} has invalid month, got {value!r}")
    return value


def _fetch_index(url: str) -> str:
    with httpx.Client(timeout=45.0, follow_redirects=True, headers=DEFAULT_HEADERS) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def _parse_monthly_zips(index_html: str, base_url: str) -> list[MonthlyZip]:
    out: list[MonthlyZip] = []
    seen: set[str] = set()

    for href in HREF_RE.findall(index_html):
        filename = href.rsplit("/", 1)[-1]
        if filename in seen:
            continue
        seen.add(filename)

        match = MONTHLY_ZIP_RE.match(filename)
        if not match:
            continue

        ym = match.group("ym")
        version = int(match.group("version"))
        out.append(
            MonthlyZip(
                ym=ym,
                version=version,
                filename=filename,
                url=urljoin(base_url, filename),
            )
        )

    # Keep highest version per month.
    by_month: dict[str, list[MonthlyZip]] = defaultdict(list)
    for item in out:
        by_month[item.ym].append(item)

    selected = [max(items, key=lambda x: x.version) for items in by_month.values()]
    selected.sort(key=lambda x: x.ym)
    return selected


def _filter_months(
    items: list[MonthlyZip],
    from_ym: str | None,
    to_ym: str | None,
    latest_months: int | None,
) -> list[MonthlyZip]:
    filtered = items
    if from_ym:
        filtered = [x for x in filtered if x.ym >= from_ym]
    if to_ym:
        filtered = [x for x in filtered if x.ym <= to_ym]
    if latest_months is not None:
        if latest_months < 1:
            raise ValueError("--latest-months must be >= 1")
        filtered = filtered[-latest_months:]
    return filtered


def _sha256_bytes(blob: bytes) -> str:
    hasher = hashlib.sha256()
    hasher.update(blob)
    return hasher.hexdigest()


def _write_manifest_row(manifest_path: Path, row: dict) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def _download_file(url: str, out_path: Path) -> tuple[int, str]:
    with httpx.Client(timeout=120.0, follow_redirects=True, headers=DEFAULT_HEADERS) as client:
        response = client.get(url)
        response.raise_for_status()
        blob = response.content

    if not blob.startswith(b"PK"):
        raise ValueError("Downloaded content does not look like a ZIP file")

    out_path.write_bytes(blob)
    return len(blob), _sha256_bytes(blob)


def run(
    base_url: str,
    out_dir: Path,
    list_only: bool,
    from_ym: str | None,
    to_ym: str | None,
    latest_months: int | None,
    overwrite: bool,
    manifest: Path | None,
) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    index_html = _fetch_index(base_url)
    all_monthly = _parse_monthly_zips(index_html, base_url)
    if not all_monthly:
        raise RuntimeError("No monthly FSA ZIP files were found in the index.")

    target = _filter_months(all_monthly, from_ym=from_ym, to_ym=to_ym, latest_months=latest_months)
    if not target:
        raise RuntimeError("No files matched the provided month filters.")

    print(f"Found {len(all_monthly)} monthly files. Selected {len(target)} files.")
    print(f"Range: {target[0].ym} -> {target[-1].ym}")

    if list_only:
        for item in target:
            print(item.filename)
        return 0

    downloaded = 0
    skipped = 0
    failed = 0
    for item in target:
        out_path = out_dir / item.filename
        if out_path.exists() and not overwrite:
            print(f"SKIP {item.filename} (already exists)")
            skipped += 1
            continue

        try:
            size, checksum = _download_file(item.url, out_path)
            print(f"OK   {item.filename} ({size} bytes)")
            downloaded += 1
            status = "ok"
            fallback_used = False
        except Exception as exc:
            print(f"FAIL {item.filename}: {exc}")
            failed += 1
            status = f"error:{exc.__class__.__name__}"
            size = 0
            checksum = ""
            fallback_used = True

        if manifest is not None:
            _write_manifest_row(
                manifest,
                {
                    "source": "ieso",
                    "dataset": f"hourly_consumption_by_fsa_{item.ym}",
                    "url": item.url,
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "last_updated": datetime.now(timezone.utc).date().isoformat(),
                    "status": status,
                    "bytes": size,
                    "checksum_sha256": checksum,
                    "fallback_used": fallback_used,
                },
            )

    print(f"Done. downloaded={downloaded} skipped={skipped} failed={failed}")
    return 0 if failed == 0 else 2


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download monthly IESO HourlyConsumptionByFSA ZIPs directly from the public index."
    )
    parser.add_argument("--base-url", type=str, default=BASE_URL)
    parser.add_argument("--out-dir", type=Path, default=Path("./data/fsa_monthly"))
    parser.add_argument("--list-only", action="store_true")
    parser.add_argument("--from-ym", type=str, default=None, help="Filter start month in YYYYMM.")
    parser.add_argument("--to-ym", type=str, default=None, help="Filter end month in YYYYMM.")
    parser.add_argument(
        "--latest-months",
        type=int,
        default=None,
        help="Select only the latest N monthly files after applying date filters.",
    )
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("./data/ingestion_manifest.jsonl"),
        help="Manifest path.",
    )
    parser.add_argument("--no-manifest", action="store_true", help="Disable manifest logging.")
    args = parser.parse_args()

    if args.from_ym:
        args.from_ym = _validate_ym(args.from_ym, "--from-ym")
    if args.to_ym:
        args.to_ym = _validate_ym(args.to_ym, "--to-ym")
    if args.from_ym and args.to_ym and args.from_ym > args.to_ym:
        raise ValueError("--from-ym must be <= --to-ym")

    if args.no_manifest:
        args.manifest = None

    return args


def main() -> None:
    args = _parse_args()
    raise SystemExit(
        run(
            base_url=args.base_url,
            out_dir=args.out_dir,
            list_only=args.list_only,
            from_ym=args.from_ym,
            to_ym=args.to_ym,
            latest_months=args.latest_months,
            overwrite=args.overwrite,
            manifest=args.manifest,
        )
    )


if __name__ == "__main__":
    main()
