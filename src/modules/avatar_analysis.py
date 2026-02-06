"""Avatar perceptual hashing for cross-platform identity correlation.

Downloads avatars from discovered profiles and computes hashes to
detect when the same person uses the same/similar avatar across platforms.
This is a strong identity correlation signal.
"""

import hashlib
import io
from dataclasses import dataclass

import aiohttp

try:
    from PIL import Image
    import imagehash
    HAS_IMAGEHASH = True
except ImportError:
    HAS_IMAGEHASH = False


@dataclass
class AvatarMatch:
    platform_a: str
    platform_b: str
    url_a: str
    url_b: str
    match_type: str  # "exact", "perceptual", "similar"
    similarity: float  # 0.0 - 1.0


async def download_avatar(url: str, session: aiohttp.ClientSession) -> bytes | None:
    """Download an avatar image."""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200 and resp.content_type and "image" in resp.content_type:
                return await resp.read()
    except Exception:
        pass
    return None


def compute_exact_hash(data: bytes) -> str:
    """SHA-256 hash for exact match detection."""
    return hashlib.sha256(data).hexdigest()


def compute_perceptual_hash(data: bytes) -> str | None:
    """Perceptual hash - detects similar images even after resize/recompression."""
    if not HAS_IMAGEHASH:
        return None
    try:
        img = Image.open(io.BytesIO(data))
        return str(imagehash.phash(img))
    except Exception:
        return None


def compute_average_hash(data: bytes) -> str | None:
    """Average hash - faster but less accurate than perceptual hash."""
    if not HAS_IMAGEHASH:
        return None
    try:
        img = Image.open(io.BytesIO(data))
        return str(imagehash.average_hash(img))
    except Exception:
        return None


async def analyze_avatars(
    avatar_urls: dict[str, str],
    session: aiohttp.ClientSession,
) -> dict:
    """Download and analyze all avatars for cross-platform matches.

    Args:
        avatar_urls: {platform_name: avatar_url}
        session: aiohttp session

    Returns:
        Analysis results with matches and hashes
    """
    import asyncio

    # Download all avatars
    downloads = {}
    for platform, url in avatar_urls.items():
        data = await download_avatar(url, session)
        if data:
            downloads[platform] = {
                "data": data,
                "url": url,
                "exact_hash": compute_exact_hash(data),
                "perceptual_hash": compute_perceptual_hash(data),
                "average_hash": compute_average_hash(data),
                "size": len(data),
            }

    # Find matches
    matches = []
    platforms = list(downloads.keys())

    for i in range(len(platforms)):
        for j in range(i + 1, len(platforms)):
            pa, pb = platforms[i], platforms[j]
            a, b = downloads[pa], downloads[pb]

            # Exact match (same file content)
            if a["exact_hash"] == b["exact_hash"]:
                matches.append(AvatarMatch(
                    platform_a=pa, platform_b=pb,
                    url_a=a["url"], url_b=b["url"],
                    match_type="exact", similarity=1.0,
                ))
                continue

            # Perceptual hash match (visually similar)
            if a["perceptual_hash"] and b["perceptual_hash"]:
                try:
                    hash_a = imagehash.hex_to_hash(a["perceptual_hash"])
                    hash_b = imagehash.hex_to_hash(b["perceptual_hash"])
                    distance = hash_a - hash_b  # Hamming distance
                    similarity = 1.0 - (distance / 64.0)  # 64-bit hash

                    if similarity > 0.85:
                        matches.append(AvatarMatch(
                            platform_a=pa, platform_b=pb,
                            url_a=a["url"], url_b=b["url"],
                            match_type="perceptual" if similarity > 0.95 else "similar",
                            similarity=similarity,
                        ))
                except Exception:
                    pass

    return {
        "total_avatars": len(downloads),
        "matches": [
            {
                "platforms": [m.platform_a, m.platform_b],
                "match_type": m.match_type,
                "similarity": f"{m.similarity:.0%}",
            }
            for m in matches
        ],
        "hashes": {
            platform: {
                "exact": info["exact_hash"][:16] + "...",
                "perceptual": info["perceptual_hash"],
                "size_bytes": info["size"],
            }
            for platform, info in downloads.items()
        },
        "same_person_evidence": len(matches) > 0,
    }
