"""Check credentials against known breach databases."""

import hashlib
import aiohttp


async def check_hibp(email: str, session: aiohttp.ClientSession) -> dict:
    result = {"email": email, "breached": False, "breach_count": 0, "breaches": []}
    try:
        async with session.get(
            f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}",
            headers={"User-Agent": "PhantomTrace-OSINT", "Accept": "application/json"},
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                result["breached"] = True
                result["breach_count"] = len(data)
                result["breaches"] = [{"name": b["Name"], "date": b.get("BreachDate", "")} for b in data]
    except Exception:
        result["error"] = "HIBP API unavailable"
    return result


async def check_password_pwned(password: str, session: aiohttp.ClientSession) -> dict:
    sha1 = hashlib.sha1(password.encode()).hexdigest().upper()
    prefix, suffix = sha1[:5], sha1[5:]
    result = {"pwned": False, "count": 0}
    try:
        async with session.get(f"https://api.pwnedpasswords.com/range/{prefix}") as resp:
            if resp.status == 200:
                for line in (await resp.text()).splitlines():
                    h, c = line.split(":")
                    if h == suffix:
                        result.update({"pwned": True, "count": int(c)})
                        break
    except Exception:
        pass
    return result
