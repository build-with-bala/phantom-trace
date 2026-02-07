"""PGP keyserver lookup - find cryptographic identity proofs."""

import re
import aiohttp


KEYSERVERS = [
    "https://keys.openpgp.org",
    "https://keys.mailvelope.com",
]


async def lookup_by_email(email: str, session: aiohttp.ClientSession) -> dict:
    """Search PGP keyservers for keys associated with an email.

    PGP keys are strong identity evidence because they require
    email verification and are often used by security-conscious individuals.
    """
    result = {
        "email": email,
        "keys_found": [],
        "total_keys": 0,
    }

    # keys.openpgp.org - VKS API
    try:
        async with session.get(
            f"https://keys.openpgp.org/vks/v1/by-email/{email}",
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status == 200:
                key_data = await resp.text()
                if key_data and "BEGIN PGP" in key_data:
                    result["keys_found"].append({
                        "server": "keys.openpgp.org",
                        "has_key": True,
                        "key_preview": key_data[:200] + "...",
                    })
    except Exception:
        pass

    # Mailvelope keyserver
    try:
        async with session.get(
            f"https://keys.mailvelope.com/api/v1/key?email={email}",
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status == 200:
                data = await resp.json(content_type=None)
                if data:
                    result["keys_found"].append({
                        "server": "keys.mailvelope.com",
                        "has_key": True,
                        "key_id": data.get("keyId", ""),
                        "created": data.get("uploaded", {}).get("created", ""),
                    })
    except Exception:
        pass

    # Ubuntu keyserver (HKP protocol via web)
    try:
        async with session.get(
            f"https://keyserver.ubuntu.com/pks/lookup?search={email}&op=vindex&fingerprint=on&exact=on",
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status == 200:
                text = await resp.text()
                if "pub" in text and email.lower() in text.lower():
                    # Extract fingerprints
                    fingerprints = re.findall(r"([A-F0-9]{4}\s+){9}[A-F0-9]{4}", text)
                    uids = re.findall(r">(.*?)</a>", text)
                    uid_names = [u for u in uids if "@" in u or " " in u]

                    result["keys_found"].append({
                        "server": "keyserver.ubuntu.com",
                        "has_key": True,
                        "fingerprints": fingerprints[:3],
                        "uids": uid_names[:5],
                    })
    except Exception:
        pass

    result["total_keys"] = len(result["keys_found"])
    return result


async def lookup_by_username(username: str, session: aiohttp.ClientSession) -> dict:
    """Search keyservers for a username/name."""
    result = {"username": username, "keys_found": [], "total_keys": 0}

    try:
        async with session.get(
            f"https://keyserver.ubuntu.com/pks/lookup?search={username}&op=vindex&exact=off",
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status == 200:
                text = await resp.text()
                # Extract email addresses from results
                emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
                unique_emails = list(set(emails))[:10]

                if unique_emails:
                    result["keys_found"].append({
                        "server": "keyserver.ubuntu.com",
                        "associated_emails": unique_emails,
                    })
    except Exception:
        pass

    result["total_keys"] = len(result["keys_found"])
    return result
