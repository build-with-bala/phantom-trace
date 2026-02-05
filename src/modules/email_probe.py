"""Holehe-style email registration probing.

Checks if an email is registered on various services by exploiting
password reset and signup validation endpoints.

Each service has its own endpoint, headers, and response patterns.
This is the most powerful OSINT technique for email → service mapping.
"""

import aiohttp
import json
from dataclasses import dataclass


@dataclass
class ProbeResult:
    service: str
    registered: bool
    method: str  # "password_reset", "signup_check", "api"
    extra: dict | None = None
    error: str | None = None


async def _probe_spotify(email: str, session: aiohttp.ClientSession) -> ProbeResult:
    """Spotify - signup validation endpoint."""
    try:
        async with session.get(
            f"https://spclient.wg.spotify.com/signup/public/v1/account?validate=1&email={email}",
            headers={"User-Agent": "Mozilla/5.0"},
        ) as resp:
            if resp.status == 200:
                data = await resp.json(content_type=None)
                status = data.get("status", 0)
                # status 20 = email exists, status 1 = available
                return ProbeResult("spotify", status == 20, "signup_check")
    except Exception as e:
        return ProbeResult("spotify", False, "signup_check", error=str(e)[:50])
    return ProbeResult("spotify", False, "signup_check")


async def _probe_pinterest(email: str, session: aiohttp.ClientSession) -> ProbeResult:
    """Pinterest - email exists resource."""
    try:
        data_param = json.dumps({"options": {"email": email}})
        async with session.get(
            f"https://www.pinterest.com/resource/EmailExistsResource/get/?data={data_param}",
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
        ) as resp:
            if resp.status == 200:
                data = await resp.json(content_type=None)
                exists = data.get("resource_response", {}).get("data", False)
                return ProbeResult("pinterest", bool(exists), "api")
    except Exception as e:
        return ProbeResult("pinterest", False, "api", error=str(e)[:50])
    return ProbeResult("pinterest", False, "api")


async def _probe_twitter(email: str, session: aiohttp.ClientSession) -> ProbeResult:
    """Twitter/X - email availability check."""
    try:
        async with session.get(
            f"https://api.twitter.com/i/users/email_available.json?email={email}",
            headers={"User-Agent": "Mozilla/5.0"},
        ) as resp:
            if resp.status == 200:
                data = await resp.json(content_type=None)
                # taken=true means registered
                return ProbeResult("twitter", data.get("taken", False), "api")
    except Exception as e:
        return ProbeResult("twitter", False, "api", error=str(e)[:50])
    return ProbeResult("twitter", False, "api")


async def _probe_instagram(email: str, session: aiohttp.ClientSession) -> ProbeResult:
    """Instagram - signup attempt endpoint."""
    try:
        async with session.post(
            "https://www.instagram.com/accounts/web_create_ajax/attempt/",
            data={"email": email},
            headers={
                "User-Agent": "Mozilla/5.0",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://www.instagram.com/accounts/emailsignup/",
            },
        ) as resp:
            if resp.status == 200:
                data = await resp.json(content_type=None)
                errors = data.get("errors", {})
                email_taken = "email" in errors
                return ProbeResult("instagram", email_taken, "signup_check")
    except Exception as e:
        return ProbeResult("instagram", False, "signup_check", error=str(e)[:50])
    return ProbeResult("instagram", False, "signup_check")


async def _probe_adobe(email: str, session: aiohttp.ClientSession) -> ProbeResult:
    """Adobe - account check endpoint."""
    try:
        async with session.post(
            "https://auth.services.adobe.com/signin/v2/users/accounts",
            json={"username": email},
            headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"},
        ) as resp:
            # 200 with user data = exists, 404 = doesn't exist
            return ProbeResult("adobe", resp.status == 200, "api")
    except Exception as e:
        return ProbeResult("adobe", False, "api", error=str(e)[:50])


async def _probe_wordpress(email: str, session: aiohttp.ClientSession) -> ProbeResult:
    """WordPress.com - email check."""
    try:
        async with session.get(
            f"https://public-api.wordpress.com/rest/v1.1/users/{email}/auth-options",
            headers={"User-Agent": "Mozilla/5.0"},
        ) as resp:
            if resp.status == 200:
                data = await resp.json(content_type=None)
                return ProbeResult("wordpress", "email_verified" in data, "api",
                                   extra={"passwordless": data.get("passwordless", False)})
    except Exception as e:
        return ProbeResult("wordpress", False, "api", error=str(e)[:50])
    return ProbeResult("wordpress", False, "api")


async def _probe_github(email: str, session: aiohttp.ClientSession) -> ProbeResult:
    """GitHub - search for users by email."""
    try:
        async with session.get(
            f"https://api.github.com/search/users?q={email}+in:email",
            headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "PhantomTrace"},
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                count = data.get("total_count", 0)
                users = data.get("items", [])
                extra = {"username": users[0]["login"]} if users else None
                return ProbeResult("github", count > 0, "api", extra=extra)
    except Exception as e:
        return ProbeResult("github", False, "api", error=str(e)[:50])
    return ProbeResult("github", False, "api")


async def _probe_discord(email: str, session: aiohttp.ClientSession) -> ProbeResult:
    """Discord - register endpoint probing."""
    try:
        async with session.post(
            "https://discord.com/api/v9/auth/register",
            json={"email": email, "username": "phantomtrace_check", "password": "Pt#Ch3ck!", "date_of_birth": "1990-01-01"},
            headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"},
        ) as resp:
            if resp.status == 400:
                data = await resp.json(content_type=None)
                errors = data.get("errors", {})
                # If email field has error about already registered
                email_errors = errors.get("email", {}).get("_errors", [])
                registered = any("already" in e.get("message", "").lower() for e in email_errors)
                return ProbeResult("discord", registered, "signup_check")
    except Exception as e:
        return ProbeResult("discord", False, "signup_check", error=str(e)[:50])
    return ProbeResult("discord", False, "signup_check")


async def _probe_tumblr(email: str, session: aiohttp.ClientSession) -> ProbeResult:
    """Tumblr - email check via signup flow."""
    try:
        async with session.post(
            "https://www.tumblr.com/svc/account/register",
            data={"action": "signup_account", "email": email, "password": "dummycheck123!"},
            headers={"User-Agent": "Mozilla/5.0"},
        ) as resp:
            text = await resp.text()
            registered = "already" in text.lower() or "taken" in text.lower()
            return ProbeResult("tumblr", registered, "signup_check")
    except Exception as e:
        return ProbeResult("tumblr", False, "signup_check", error=str(e)[:50])


async def _probe_duolingo(email: str, session: aiohttp.ClientSession) -> ProbeResult:
    """Duolingo - signup validation."""
    try:
        async with session.post(
            "https://www.duolingo.com/2017-06-30/users",
            json={"email": email, "password": "dummycheck", "age": 25},
            headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"},
        ) as resp:
            if resp.status == 400:
                data = await resp.json(content_type=None)
                return ProbeResult("duolingo", data.get("errorId") == "EMAIL_TAKEN", "signup_check")
    except Exception as e:
        return ProbeResult("duolingo", False, "signup_check", error=str(e)[:50])
    return ProbeResult("duolingo", False, "signup_check")


# Registry of all probes
PROBES = {
    "spotify": _probe_spotify,
    "pinterest": _probe_pinterest,
    "twitter": _probe_twitter,
    "instagram": _probe_instagram,
    "adobe": _probe_adobe,
    "wordpress": _probe_wordpress,
    "github": _probe_github,
    "discord": _probe_discord,
    "tumblr": _probe_tumblr,
    "duolingo": _probe_duolingo,
}


async def probe_all_services(email: str, session: aiohttp.ClientSession | None = None) -> list[ProbeResult]:
    """Run all service probes for an email address.

    This is the killer OSINT feature: give it an email,
    get back every service the person is registered on.
    """
    import asyncio

    own_session = session is None
    if own_session:
        session = aiohttp.ClientSession()

    try:
        tasks = [probe_fn(email, session) for probe_fn in PROBES.values()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        return [r for r in results if isinstance(r, ProbeResult)]
    finally:
        if own_session:
            await session.close()
