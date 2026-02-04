"""Gravatar deep intelligence - mine linked accounts, photos, and verified profiles."""

import hashlib
import aiohttp


async def get_gravatar_profile(email: str, session: aiohttp.ClientSession) -> dict:
    """Fetch full Gravatar JSON profile - a goldmine of linked accounts.

    Most people don't realize their Gravatar profile exposes:
    - Their real name
    - Their self-reported accounts (Flickr, Twitter, WordPress, etc.)
    - Their photos
    - Their verified URLs
    - Their location
    """
    email_hash = hashlib.md5(email.lower().strip().encode()).hexdigest()
    result = {
        "email_hash": email_hash,
        "exists": False,
        "name": None,
        "display_name": None,
        "location": None,
        "about": None,
        "avatar_url": None,
        "profile_url": None,
        "linked_accounts": [],
        "verified_urls": [],
        "photos": [],
    }

    # Check avatar existence
    try:
        async with session.get(f"https://gravatar.com/avatar/{email_hash}?d=404") as resp:
            if resp.status == 200:
                result["avatar_url"] = f"https://gravatar.com/avatar/{email_hash}?s=400"
                result["exists"] = True
            else:
                return result
    except Exception:
        return result

    # Fetch the full JSON profile (the real goldmine)
    try:
        async with session.get(f"https://gravatar.com/{email_hash}.json") as resp:
            if resp.status != 200:
                return result

            data = await resp.json()
            entries = data.get("entry", [])
            if not entries:
                return result

            entry = entries[0]

            result["display_name"] = entry.get("displayName")
            result["profile_url"] = entry.get("profileUrl")
            result["about"] = entry.get("aboutMe")
            result["location"] = entry.get("currentLocation")
            result["hash"] = entry.get("hash")

            # Real name
            name_obj = entry.get("name", {})
            if name_obj:
                parts = []
                if name_obj.get("givenName"):
                    parts.append(name_obj["givenName"])
                if name_obj.get("familyName"):
                    parts.append(name_obj["familyName"])
                if parts:
                    result["name"] = " ".join(parts)

            # Linked accounts - people link their social profiles here
            for account in entry.get("accounts", []):
                result["linked_accounts"].append({
                    "service": account.get("shortname", account.get("domain", "unknown")),
                    "username": account.get("username", ""),
                    "display": account.get("display", ""),
                    "url": account.get("url", ""),
                    "verified": account.get("verified", False),
                })

            # Verified URLs
            for url_obj in entry.get("urls", []):
                result["verified_urls"].append({
                    "title": url_obj.get("title", ""),
                    "url": url_obj.get("value", ""),
                })

            # Photos
            for photo in entry.get("photos", []):
                result["photos"].append({
                    "url": photo.get("value", ""),
                    "type": photo.get("type", ""),
                })

    except Exception:
        pass

    return result


async def gravatar_reverse_lookup(email_hash: str, session: aiohttp.ClientSession) -> dict | None:
    """Try to get profile from a known hash (useful when you have hash but not email)."""
    try:
        async with session.get(f"https://gravatar.com/{email_hash}.json") as resp:
            if resp.status == 200:
                data = await resp.json()
                entries = data.get("entry", [])
                if entries:
                    return entries[0]
    except Exception:
        pass
    return None
