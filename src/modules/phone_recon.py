"""Phone number OSINT module."""

import re
import aiohttp

COUNTRY_CODES = {
    "+1": "US/CA", "+44": "UK", "+91": "IN", "+61": "AU", "+49": "DE",
    "+33": "FR", "+81": "JP", "+86": "CN", "+971": "UAE", "+65": "SG",
}


def normalize_phone(number: str) -> str:
    cleaned = re.sub(r"[^\d+]", "", number)
    if not cleaned.startswith("+"):
        if len(cleaned) == 10:
            cleaned = "+1" + cleaned
        elif len(cleaned) == 11 and cleaned.startswith("1"):
            cleaned = "+" + cleaned
    return cleaned


def detect_country(number: str) -> str | None:
    n = normalize_phone(number)
    for code, country in sorted(COUNTRY_CODES.items(), key=lambda x: -len(x[0])):
        if n.startswith(code):
            return country
    return None


async def check_phone(number: str, session: aiohttp.ClientSession) -> dict:
    normalized = normalize_phone(number)
    result = {"number": normalized, "country": detect_country(normalized), "services": []}

    try:
        async with session.get(f"https://wa.me/{normalized.lstrip('+')}", allow_redirects=False) as resp:
            if resp.status in [200, 301, 302]:
                loc = resp.headers.get("Location", "")
                if "send" in loc or resp.status == 200:
                    result["services"].append("whatsapp")
    except Exception:
        pass

    return result
