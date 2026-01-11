"""Email-based reconnaissance module."""

import hashlib
import re

import aiohttp

from src.models import PersonProfile


async def check_email(email: str, session: aiohttp.ClientSession) -> dict:
    result = {"email": email, "valid": False, "services": [], "gravatar": None, "provider": ""}

    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        return result

    result["valid"] = True
    result["provider"] = email.split("@")[1]

    # Gravatar
    email_hash = hashlib.md5(email.lower().strip().encode()).hexdigest()
    try:
        async with session.get(f"https://gravatar.com/avatar/{email_hash}?d=404") as resp:
            if resp.status == 200:
                result["gravatar"] = f"https://gravatar.com/avatar/{email_hash}"
                result["services"].append("gravatar")
    except Exception:
        pass

    # GitHub
    try:
        async with session.get(
            f"https://api.github.com/search/users?q={email}+in:email",
            headers={"Accept": "application/vnd.github.v3+json"},
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("total_count", 0) > 0:
                    result["services"].append("github")
    except Exception:
        pass

    return result


def generate_email_permutations(first: str, last: str, domain: str | None = None) -> list[str]:
    f, l = first.lower(), last.lower()
    domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "protonmail.com"]
    if domain:
        domains.insert(0, domain)
    patterns = [f"{f}{l}", f"{f}.{l}", f"{f}_{l}", f"{l}{f}", f"{f[0]}{l}", f"{f}{l[0]}"]
    return [f"{p}@{d}" for p in patterns for d in domains]
