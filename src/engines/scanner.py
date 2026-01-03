"""Basic synchronous scanner - initial implementation."""

import json
import requests
from pathlib import Path

from src.models import SiteResult, CheckType


def load_sites() -> dict:
    path = Path(__file__).parent.parent.parent / "data" / "sites.json"
    with open(path) as f:
        return json.load(f)


def check_site(site_name: str, config: dict, username: str) -> SiteResult:
    url = config["url"].format(username)
    check_type = CheckType(config.get("check_type", "status_code"))
    result = SiteResult(site=site_name, url=url, category=config.get("category", "other"), username=username)

    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True)

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


def scan_username(username: str) -> list[SiteResult]:
    sites = load_sites()
    results = []
    for name, config in sites.items():
        result = check_site(name, config, username)
        results.append(result)
    return results
