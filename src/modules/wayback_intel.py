"""Wayback Machine intelligence - historical profile and domain analysis."""

import aiohttp
from datetime import datetime


async def check_wayback_availability(url: str, session: aiohttp.ClientSession) -> dict:
    """Check if a URL has snapshots in the Wayback Machine."""
    result = {"url": url, "archived": False, "snapshots": 0, "first_seen": None, "last_seen": None}

    try:
        async with session.get(
            f"https://archive.org/wayback/available?url={url}",
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status == 200:
                data = await resp.json(content_type=None)
                snapshot = data.get("archived_snapshots", {}).get("closest", {})
                if snapshot.get("available"):
                    result["archived"] = True
                    result["snapshot_url"] = snapshot.get("url", "")
                    ts = snapshot.get("timestamp", "")
                    if ts:
                        result["last_seen"] = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"
    except Exception:
        pass

    return result


async def get_cdx_timeline(url: str, session: aiohttp.ClientSession, limit: int = 100) -> dict:
    """Query CDX API for full archival timeline of a URL.

    Returns all snapshots with timestamps, showing when a profile
    was first created, how it changed, and if it was deleted.
    """
    result = {
        "url": url,
        "total_snapshots": 0,
        "first_seen": None,
        "last_seen": None,
        "timeline": [],
        "status_history": [],
    }

    try:
        params = {
            "url": url,
            "output": "json",
            "fl": "timestamp,original,statuscode,digest,length",
            "collapse": "digest",  # Deduplicate identical snapshots
            "limit": str(limit),
        }

        async with session.get(
            "https://web.archive.org/cdx/search/cdx",
            params=params,
            timeout=aiohttp.ClientTimeout(total=20),
        ) as resp:
            if resp.status != 200:
                return result

            data = await resp.json(content_type=None)
            if not data or len(data) < 2:
                return result

            headers = data[0]
            rows = data[1:]

            result["total_snapshots"] = len(rows)

            for row in rows:
                entry = dict(zip(headers, row))
                ts = entry.get("timestamp", "")
                status = entry.get("statuscode", "")

                if ts:
                    formatted_date = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"
                    wayback_url = f"https://web.archive.org/web/{ts}/{entry.get('original', url)}"

                    result["timeline"].append({
                        "date": formatted_date,
                        "status": status,
                        "wayback_url": wayback_url,
                    })

                    if not result["first_seen"]:
                        result["first_seen"] = formatted_date
                    result["last_seen"] = formatted_date

                    result["status_history"].append(status)

    except Exception:
        pass

    return result


async def find_deleted_profiles(username: str, session: aiohttp.ClientSession) -> list[dict]:
    """Check Wayback Machine for profiles that no longer exist.

    If a profile was archived but now returns 404, the person
    likely deleted their account — which is itself intelligence.
    """
    platforms = [
        ("twitter", f"https://twitter.com/{username}"),
        ("instagram", f"https://www.instagram.com/{username}/"),
        ("github", f"https://github.com/{username}"),
        ("reddit", f"https://www.reddit.com/user/{username}"),
        ("medium", f"https://medium.com/@{username}"),
        ("devto", f"https://dev.to/{username}"),
        ("keybase", f"https://keybase.io/{username}"),
        ("tumblr", f"https://{username}.tumblr.com"),
    ]

    deleted = []

    for platform, url in platforms:
        timeline = await get_cdx_timeline(url, session, limit=5)
        if timeline["total_snapshots"] > 0:
            # Check if current URL returns 404
            try:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=10),
                    allow_redirects=True,
                    ssl=False,
                ) as resp:
                    if resp.status == 404:
                        deleted.append({
                            "platform": platform,
                            "url": url,
                            "first_seen": timeline["first_seen"],
                            "last_seen": timeline["last_seen"],
                            "total_snapshots": timeline["total_snapshots"],
                            "status": "deleted",
                        })
            except Exception:
                continue

    return deleted
