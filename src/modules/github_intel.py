"""GitHub deep intelligence - extract commit emails, repos, activity patterns."""

import re
from datetime import datetime
from collections import Counter
from typing import Any

import aiohttp


async def extract_commit_emails(username: str, session: aiohttp.ClientSession) -> list[dict]:
    """Extract real email addresses from public commit history.

    Most developers unknowingly expose their personal email via git config.
    The GitHub Events API exposes commit author emails for PushEvents.
    """
    emails = []
    seen = set()

    try:
        # Method 1: Public events API (up to 300 events, 10 pages of 30)
        for page in range(1, 4):
            async with session.get(
                f"https://api.github.com/users/{username}/events/public?per_page=100&page={page}",
                headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "PhantomTrace-OSINT"},
            ) as resp:
                if resp.status != 200:
                    break
                events = await resp.json()
                if not events:
                    break

                for event in events:
                    if event.get("type") != "PushEvent":
                        continue
                    payload = event.get("payload", {})
                    for commit in payload.get("commits", []):
                        author = commit.get("author", {})
                        email = author.get("email", "")
                        name = author.get("name", "")

                        if not email or email in seen:
                            continue
                        # Skip noreply emails
                        if "noreply" in email or "@users.noreply.github.com" in email:
                            continue
                        seen.add(email)
                        emails.append({
                            "email": email,
                            "name": name,
                            "source": "git_commit",
                            "repo": event.get("repo", {}).get("name", ""),
                            "timestamp": event.get("created_at", ""),
                        })

        # Method 2: Check patch files for author email
        async with session.get(
            f"https://api.github.com/users/{username}/repos?sort=updated&per_page=5",
            headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "PhantomTrace-OSINT"},
        ) as resp:
            if resp.status == 200:
                repos = await resp.json()
                for repo in repos[:3]:
                    repo_name = repo.get("full_name", "")
                    if not repo_name:
                        continue
                    # Get latest commit as patch
                    async with session.get(
                        f"https://api.github.com/repos/{repo_name}/commits?per_page=5",
                        headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "PhantomTrace-OSINT"},
                    ) as cresp:
                        if cresp.status == 200:
                            commits = await cresp.json()
                            for c in commits:
                                for key in ["author", "commit"]:
                                    obj = c.get(key, {})
                                    if isinstance(obj, dict):
                                        # Direct author object or nested commit.author
                                        if "email" in obj:
                                            em = obj["email"]
                                        elif "author" in obj and isinstance(obj["author"], dict):
                                            em = obj["author"].get("email", "")
                                        else:
                                            continue
                                        if em and em not in seen and "noreply" not in em:
                                            seen.add(em)
                                            emails.append({
                                                "email": em,
                                                "name": obj.get("name", obj.get("author", {}).get("name", "")),
                                                "source": "commit_api",
                                                "repo": repo_name,
                                            })
    except Exception:
        pass

    return emails


async def get_github_profile(username: str, session: aiohttp.ClientSession) -> dict[str, Any]:
    """Get comprehensive GitHub profile data."""
    result = {"exists": False}

    try:
        async with session.get(
            f"https://api.github.com/users/{username}",
            headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "PhantomTrace-OSINT"},
        ) as resp:
            if resp.status != 200:
                return result

            data = await resp.json()
            result.update({
                "exists": True,
                "login": data.get("login"),
                "name": data.get("name"),
                "bio": data.get("bio"),
                "company": data.get("company"),
                "blog": data.get("blog"),
                "location": data.get("location"),
                "email": data.get("email"),  # Public email if set
                "avatar_url": data.get("avatar_url"),
                "created_at": data.get("created_at"),
                "public_repos": data.get("public_repos", 0),
                "public_gists": data.get("public_gists", 0),
                "followers": data.get("followers", 0),
                "following": data.get("following", 0),
                "hireable": data.get("hireable"),
                "twitter_username": data.get("twitter_username"),
            })

            # Get organizations
            async with session.get(
                f"https://api.github.com/users/{username}/orgs",
                headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "PhantomTrace-OSINT"},
            ) as org_resp:
                if org_resp.status == 200:
                    orgs = await org_resp.json()
                    result["organizations"] = [o.get("login") for o in orgs]

            # Get top languages from repos
            async with session.get(
                f"https://api.github.com/users/{username}/repos?sort=updated&per_page=20",
                headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "PhantomTrace-OSINT"},
            ) as repo_resp:
                if repo_resp.status == 200:
                    repos = await repo_resp.json()
                    langs = Counter(r.get("language") for r in repos if r.get("language"))
                    result["top_languages"] = [lang for lang, _ in langs.most_common(5)]
                    result["repos"] = [
                        {"name": r["name"], "description": r.get("description", ""), "stars": r.get("stargazers_count", 0), "language": r.get("language")}
                        for r in sorted(repos, key=lambda x: x.get("stargazers_count", 0), reverse=True)[:5]
                    ]

    except Exception:
        pass

    return result


async def get_activity_pattern(username: str, session: aiohttp.ClientSession) -> dict:
    """Analyze activity patterns to determine timezone and habits."""
    hours = []
    days = []

    try:
        async with session.get(
            f"https://api.github.com/users/{username}/events/public?per_page=100",
            headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "PhantomTrace-OSINT"},
        ) as resp:
            if resp.status == 200:
                events = await resp.json()
                for event in events:
                    ts = event.get("created_at", "")
                    if ts:
                        try:
                            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                            hours.append(dt.hour)
                            days.append(dt.strftime("%A"))
                        except ValueError:
                            continue
    except Exception:
        pass

    if not hours:
        return {"pattern": "insufficient_data"}

    hour_counts = Counter(hours)
    day_counts = Counter(days)
    peak_hour = hour_counts.most_common(1)[0][0]
    peak_day = day_counts.most_common(1)[0][0]

    # Estimate timezone from peak activity
    # If peak hour (UTC) is around 14-18, they're likely UTC-5 to UTC-8 (Americas daytime)
    # If peak hour (UTC) is around 7-12, they're likely UTC+5 to UTC+9 (Asia daytime)
    if 14 <= peak_hour <= 22:
        tz_guess = "Americas (UTC-5 to UTC-8)"
    elif 7 <= peak_hour <= 14:
        tz_guess = "Asia/Oceania (UTC+5 to UTC+10)"
    elif 8 <= peak_hour <= 18:
        tz_guess = "Europe/Africa (UTC+0 to UTC+3)"
    else:
        tz_guess = "Uncertain"

    return {
        "peak_hour_utc": peak_hour,
        "peak_day": peak_day,
        "timezone_estimate": tz_guess,
        "total_events_analyzed": len(hours),
        "hour_distribution": dict(hour_counts.most_common(5)),
    }
