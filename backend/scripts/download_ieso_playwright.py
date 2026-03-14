from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import (
    APIRequestContext,
    BrowserContext,
    Error as PlaywrightError,
    TimeoutError,
    sync_playwright,
)

IESO_PUBLIC_BASE_URL = "https://reports-public.ieso.ca/public/Demand"


def _save_csv_from_request(
    request_context: APIRequestContext, url: str, out_path: Path, timeout_ms: int
) -> bool:
    try:
        api_response = request_context.get(url, timeout=timeout_ms)
        ctype = (api_response.headers or {}).get("content-type", "").lower()
        blob = api_response.body()
        head = blob[:1024].lower()
        if api_response.ok and ("text/csv" in ctype or (b"," in head and b"date" in head)):
            out_path.write_bytes(blob)
            return True
    except PlaywrightError:
        pass
    return False


def _save_csv_from_page(context: BrowserContext, url: str, out_path: Path, timeout_ms: int) -> bool:
    page = context.new_page()
    try:
        # Prefer download flow first for reports-public CSV endpoints.
        try:
            with page.expect_download(timeout=timeout_ms) as download_info:
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            download_info.value.save_as(str(out_path))
            return True
        except TimeoutError:
            pass
        except PlaywrightError as exc:
            if "Download is starting" not in str(exc):
                raise

        response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_load_state("networkidle", timeout=timeout_ms)

        ctype = ""
        if response is not None:
            ctype = (response.headers or {}).get("content-type", "")

        # Case 1: direct CSV response.
        if "text/csv" in ctype or page.url.lower().endswith(".csv"):
            text = page.content()
            if "<html" in text.lower():
                text = page.inner_text("body")
            if "date" in text.lower() and "," in text:
                out_path.write_text(text, encoding="utf-8")
                return True

        # Case 2: interstitial page with JS auto-submit form; submit it explicitly.
        if page.locator("form").count() > 0:
            with page.expect_navigation(wait_until="networkidle", timeout=timeout_ms):
                page.evaluate("() => document.forms[0].submit()")

            text = page.content()
            if "<html" in text.lower():
                text = page.inner_text("body")
            if "date" in text.lower() and "," in text:
                out_path.write_text(text, encoding="utf-8")
                return True

        return False
    finally:
        page.close()


def run(start_year: int, end_year: int, out_dir: Path, headless: bool, timeout_ms: int, base_url: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    base_url = base_url.rstrip("/")

    with sync_playwright() as p:
        request_context = p.request.new_context()
        browser = None
        context = None

        ok = 0
        for year in range(start_year, end_year + 1):
            url = f"{base_url}/PUB_Demand_{year}.csv"
            out_path = out_dir / f"PUB_Demand_{year}.csv"
            print(f"Fetching {year}: {url}")

            success = _save_csv_from_request(request_context, url, out_path, timeout_ms)
            if not success:
                if context is None:
                    browser = p.chromium.launch(headless=headless)
                    context = browser.new_context(accept_downloads=True)
                success = _save_csv_from_page(context, url, out_path, timeout_ms)

            if success:
                print(f"  OK -> {out_path}")
                ok += 1
            else:
                print(f"  FAILED -> {year}")

        request_context.dispose()
        if context is not None:
            context.close()
        if browser is not None:
            browser.close()

    print(f"Completed. Downloaded {ok}/{(end_year - start_year + 1)} files.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download IESO demand CSVs via Playwright browser automation.")
    parser.add_argument("--start-year", type=int, default=2020)
    parser.add_argument("--end-year", type=int, default=2025)
    parser.add_argument("--out-dir", type=Path, default=Path("./data"))
    parser.add_argument("--headless", action="store_true", default=False)
    parser.add_argument("--timeout-ms", type=int, default=45000)
    parser.add_argument("--base-url", type=str, default=IESO_PUBLIC_BASE_URL)
    args = parser.parse_args()

    run(
        start_year=args.start_year,
        end_year=args.end_year,
        out_dir=args.out_dir,
        headless=args.headless,
        timeout_ms=args.timeout_ms,
        base_url=args.base_url,
    )


if __name__ == "__main__":
    main()
