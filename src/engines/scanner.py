"""Scanner engine with thread pool for concurrent checks."""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

from src.models import SiteResult, CheckType


def load_sites() -> dict:
    path = Path(__file__).parent.parent.parent / "data" / "sites.json"
    with open(path) as f:
        return json.load(f)


def check_site(site_name: str, config: dict, username: str, timeout: float = 10) -> SiteResult:
    url = config["url"].format(username)
    check_type = CheckType(config.get("check_type", "status_code"))
    result = SiteResult(site=site_name, url=url, category=config.get("category", "other"), username=username)

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        resp = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True)

        if check_type == CheckType.STATUS_CODE:
            result.found = resp.status_code in config.get("valid_codes", [200])
        elif check_type == CheckType.RESPONSE_BODY:
            pattern = config.get("valid_pattern", "")
            invalid = config.get("invalid_pattern", "")
            if invalid and invalid in resp.text:
                result.found = False
            elif pattern and pattern in resp.text:
                result.found = True

        result.status_code = resp.status_code
    except requests.RequestException as e:
        result.error = str(e)[:100]

    return result


def scan_username(username: str, max_workers: int = 30, timeout: float = 10) -> list[SiteResult]:
    sites = load_sites()
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(check_site, name, config, username, timeout): name
            for name, config in sites.items()
        }
        for future in as_completed(futures):
            results.append(future.result())

    return results
