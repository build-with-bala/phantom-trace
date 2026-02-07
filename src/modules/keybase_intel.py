"""Keybase intelligence - cryptographically verified identity links.

Keybase is the holy grail for OSINT correlation because users
cryptographically PROVE they own their accounts on other platforms.
If someone has a Keybase profile, you get verified links to their
Twitter, GitHub, Reddit, HN, personal domains, and more.
"""

import aiohttp


async def lookup_keybase_user(username: str, session: aiohttp.ClientSession) -> dict:
    """Query Keybase API for verified identity proofs.

    Returns cryptographically verified account links - the strongest
    possible evidence that multiple accounts belong to the same person.
    """
    result = {
        "username": username,
        "exists": False,
        "full_name": None,
        "bio": None,
        "location": None,
        "verified_proofs": [],
        "devices": [],
        "stellar_address": None,
        "profile_url": f"https://keybase.io/{username}",
    }

    try:
        async with session.get(
            f"https://keybase.io/_/api/1.0/user/lookup.json?usernames={username}",
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                return result

            data = await resp.json(content_type=None)
            them = data.get("them", [])
            if not them:
                return result

            user = them[0]
            result["exists"] = True

            # Profile info
            profile = user.get("profile", {})
            result["full_name"] = profile.get("full_name")
            result["bio"] = profile.get("bio")
            result["location"] = profile.get("location")

            # Cryptographic proofs - the goldmine
            proofs_summary = user.get("proofs_summary", {})
            for proof in proofs_summary.get("all", []):
                proof_type = proof.get("proof_type")
                service_name = proof.get("nametag", "")
                service_url = proof.get("service_url", "")
                human_url = proof.get("human_url", "")
                state = proof.get("state", 0)

                # State 1 = verified
                verified = state == 1

                result["verified_proofs"].append({
                    "service": _proof_type_to_service(proof_type),
                    "username": service_name,
                    "url": human_url or service_url,
                    "verified": verified,
                    "proof_type": proof_type,
                })

            # Stellar address (cryptocurrency)
            stellar = user.get("stellar", {})
            if stellar.get("primary", {}).get("account_id"):
                result["stellar_address"] = stellar["primary"]["account_id"]

            # Device info
            devices = user.get("devices", {})
            for device_id, device in devices.items():
                result["devices"].append({
                    "name": device.get("name", ""),
                    "type": device.get("type", ""),
                    "status": device.get("status", 0),
                })

    except Exception:
        pass

    return result


def _proof_type_to_service(proof_type: int | str) -> str:
    """Map Keybase proof type to human-readable service name."""
    mapping = {
        1: "dns",
        2: "twitter",
        3: "github",
        4: "reddit",
        5: "coinbase",
        6: "hackernews",
        8: "generic_web",
        9: "facebook",
        1001: "generic_social",
    }
    if isinstance(proof_type, str):
        return proof_type
    return mapping.get(proof_type, f"unknown_{proof_type}")


async def search_keybase(query: str, session: aiohttp.ClientSession) -> list[dict]:
    """Search Keybase for users matching a query."""
    results = []

    try:
        async with session.get(
            f"https://keybase.io/_/api/1.0/user/autocomplete.json?q={query}",
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status == 200:
                data = await resp.json(content_type=None)
                completions = data.get("completions", [])

                for c in completions[:10]:
                    components = c.get("components", {})
                    username = components.get("username", {}).get("val", "")
                    full_name = components.get("full_name", {}).get("val", "")

                    if username:
                        results.append({
                            "username": username,
                            "full_name": full_name,
                            "score": c.get("total_score", 0),
                        })
    except Exception:
        pass

    return results
