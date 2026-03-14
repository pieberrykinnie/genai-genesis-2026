from __future__ import annotations

import argparse
import sys
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
}

STATCAN_PID_BY_DATASET: dict[str, str] = {
    "census_profile_98-10-0001-01": "98100001",
    "water_use_38-10-0250-01": "38100250",
}

DEFAULT_DATASETS = [
    {
        "source": "ieso",
        "dataset": "pub_demand_{year}",
        "url": "https://reports.ieso.ca/public/Demand/PUB_Demand_{year}.csv",
        "years": [2020, 2021, 2022, 2023, 2024, 2025],
    },
    {
        "source": "statcan",
        "dataset": "census_profile_98-10-0001-01",
        "urls": [
            "https://www150.statcan.gc.ca/t1/tbl1/en/dtbl/downloadTbl/csvDownload/98-10-0001-01.zip",
            "https://www150.statcan.gc.ca/n1/tbl/csv/98-10-0001-01-eng.zip",
        ],
    },
    {
        "source": "statcan",
        "dataset": "water_use_38-10-0250-01",
        "urls": [
            "https://www150.statcan.gc.ca/t1/tbl1/en/dtbl/downloadTbl/csvDownload/38-10-0250-01.zip",
            "https://www150.statcan.gc.ca/n1/tbl/csv/38-10-0250-01-eng.zip",
        ],
    },
    {
        "source": "aafc",
        "dataset": "drought_monitor_ogc",
        "url": "https://agriculture.canada.ca/imagery-images/rest/services/canadian_drought_monitor/ImageServer?f=pjson",
    },
    {
        "source": "cer",
        "dataset": "hfed_api_guide",
        "url": "https://www.canadaenergyregulator.ca/en/data-analysis/canada-energy-future/canadian-centre-energy-information/canadian-centre-energy-information-open-data-user-guide.html",
    },
    {
        "source": "eccc",
        "dataset": "aqhi_feed_listing",
        "url": "https://dd.weather.gc.ca/air_quality/aqhi/observation/realtime/json/",
    },
]


def _sha256_bytes(blob: bytes) -> str:
    hasher = hashlib.sha256()
    hasher.update(blob)
    return hasher.hexdigest()


def _download(url: str, timeout: float = 20.0) -> bytes:
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=DEFAULT_HEADERS) as client:
        r = client.get(url)
        r.raise_for_status()
        blob = r.content

    head = blob[:512].lower().lstrip()
    if head.startswith(b"<html") or b"<html" in head:
        raise ValueError("UnexpectedHTMLResponse")
    return blob


def _resolve_statcan_download_url(dataset: str, timeout: float = 20.0) -> str | None:
    pid = STATCAN_PID_BY_DATASET.get(dataset)
    if not pid:
        return None

    endpoint = f"https://www150.statcan.gc.ca/t1/wds/rest/getFullTableDownloadCSV/{pid}/en"
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=DEFAULT_HEADERS) as client:
            r = client.get(endpoint)
            r.raise_for_status()
            payload = r.json()
        if isinstance(payload, dict) and payload.get("status") == "SUCCESS":
            out = payload.get("object")
            if isinstance(out, str) and out:
                return out
    except Exception:
        return None
    return None


def _write_manifest_row(path: Path, row: dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def _filename_from_url(url: str, default_name: str) -> str:
    parsed = urlparse(url)
    name = Path(parsed.path).name
    if not name:
        return default_name
    return name


def _try_urls(urls: list[str]) -> tuple[str, bytes]:
    last_error: Exception | None = None
    for candidate in urls:
        try:
            return candidate, _download(candidate)
        except Exception as exc:
            last_error = exc
    if last_error is None:
        raise RuntimeError("No URLs to try")
    raise last_error


def _error_status(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return f"HTTPStatusError:{code}"
    return exc.__class__.__name__


def run(data_dir: Path, manifest_path: Path, *, strict: bool = False) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    failures: list[dict[str, str]] = []

    for entry in DEFAULT_DATASETS:
        years = entry.get("years")
        if years:
            for year in years:
                url = str(entry["url"]).format(year=year)
                dataset = str(entry["dataset"]).format(year=year)
                out_name = _filename_from_url(url, f"{entry['source']}_{dataset}.bin")
                out_path = data_dir / out_name
                try:
                    blob = _download(url)
                    out_path.write_bytes(blob)
                    status = "ok"
                    checksum = _sha256_bytes(blob)
                    size = len(blob)
                    fallback_used = False
                except Exception as exc:
                    status = f"error: {_error_status(exc)}"
                    checksum = ""
                    size = 0
                    fallback_used = True
                    failures.append({"dataset": dataset, "url": url, "error": status})
                    if strict:
                        _write_manifest_row(
                            manifest_path,
                            {
                                "source": entry["source"],
                                "dataset": dataset,
                                "url": url,
                                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                                "last_updated": datetime.now(timezone.utc).date().isoformat(),
                                "status": status,
                                "bytes": 0,
                                "checksum_sha256": "",
                                "fallback_used": True,
                            },
                        )
                        raise RuntimeError(
                            f"--strict: aborting on first failure: {dataset} ({url}): {status}"
                        ) from exc

                _write_manifest_row(
                    manifest_path,
                    {
                        "source": entry["source"],
                        "dataset": dataset,
                        "url": url,
                        "retrieved_at": datetime.now(timezone.utc).isoformat(),
                        "last_updated": datetime.now(timezone.utc).date().isoformat(),
                        "status": status,
                        "bytes": size,
                        "checksum_sha256": checksum,
                        "fallback_used": fallback_used,
                    },
                )
            continue

        candidate_urls = entry.get("urls") or [str(entry["url"])]
        if entry.get("source") == "statcan":
            resolved = _resolve_statcan_download_url(str(entry["dataset"]))
            if resolved:
                candidate_urls = [resolved, *candidate_urls]
        out_name = _filename_from_url(str(candidate_urls[0]), f"{entry['source']}_{entry['dataset']}.bin")
        out_path = data_dir / out_name
        try:
            used_url, blob = _try_urls(candidate_urls)
            out_path.write_bytes(blob)
            status = "ok"
            checksum = _sha256_bytes(blob)
            size = len(blob)
            fallback_used = used_url != candidate_urls[0]
        except Exception as exc:
            used_url = candidate_urls[0]
            status = f"error: {_error_status(exc)}"
            checksum = ""
            size = 0
            fallback_used = True

        if fallback_used:
            failures.append({"dataset": str(entry["dataset"]), "url": used_url, "error": status})
            if strict:
                _write_manifest_row(
                    manifest_path,
                    {
                        "source": entry["source"],
                        "dataset": entry["dataset"],
                        "url": used_url,
                        "retrieved_at": datetime.now(timezone.utc).isoformat(),
                        "last_updated": datetime.now(timezone.utc).date().isoformat(),
                        "status": status,
                        "bytes": 0,
                        "checksum_sha256": "",
                        "fallback_used": True,
                    },
                )
                raise RuntimeError(
                    f"--strict: aborting on first failure: {entry['dataset']} ({used_url}): {status}"
                )

        _write_manifest_row(
            manifest_path,
            {
                "source": entry["source"],
                "dataset": entry["dataset"],
                "url": used_url,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "last_updated": datetime.now(timezone.utc).date().isoformat(),
                "status": status,
                "bytes": size,
                "checksum_sha256": checksum,
                "fallback_used": fallback_used,
            },
        )

    if failures:
        print(f"\nERROR: {len(failures)} download(s) failed:", file=sys.stderr)
        for f in failures:
            print(f"  - {f['dataset']}: {f['error']} ({f['url']})", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download source datasets and write a manifest log.")
    parser.add_argument("--data-dir", type=Path, default=Path("./data"))
    parser.add_argument("--manifest", type=Path, default=Path("./data/ingestion_manifest.jsonl"))
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Abort immediately on the first download failure.",
    )
    args = parser.parse_args()
    run(args.data_dir, args.manifest, strict=args.strict)
    print(f"Manifest written to {args.manifest}")


if __name__ == "__main__":
    main()
