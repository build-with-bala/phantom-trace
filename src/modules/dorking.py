"""Google dork generator for targeted OSINT queries.

Generates platform-specific search queries that reveal:
- Social profiles
- Leaked credentials and data
- Documents and files
- Code repository exposure
- Forum posts and comments
"""

import urllib.parse
from dataclasses import dataclass


@dataclass
class DorkQuery:
    category: str
    description: str
    query: str
    url: str  # Google search URL


def generate_dorks(
    username: str | None = None,
    email: str | None = None,
    real_name: str | None = None,
    domain: str | None = None,
    phone: str | None = None,
) -> list[DorkQuery]:
    """Generate targeted Google dork queries from known identifiers."""
    dorks = []
    target = username or email or real_name or ""

    if username:
        # Social profile discovery
        social_dorks = [
            ("Social Profiles", "LinkedIn profile", f'site:linkedin.com/in/ "{username}"'),
            ("Social Profiles", "Facebook profile", f'site:facebook.com "{username}"'),
            ("Social Profiles", "Twitter/X profile", f'site:twitter.com OR site:x.com "{username}"'),
            ("Social Profiles", "Instagram profile", f'site:instagram.com "{username}"'),
            ("Social Profiles", "TikTok profile", f'site:tiktok.com "@{username}"'),

            # Forum & community
            ("Forums", "Reddit posts", f'site:reddit.com/user/ "{username}"'),
            ("Forums", "Stack Overflow", f'site:stackoverflow.com "{username}"'),
            ("Forums", "Hacker News", f'site:news.ycombinator.com "{username}"'),
            ("Forums", "Medium articles", f'site:medium.com "@{username}"'),

            # Code exposure
            ("Code", "GitHub repositories", f'site:github.com "{username}"'),
            ("Code", "GitLab projects", f'site:gitlab.com "{username}"'),
            ("Code", "Pastebin dumps", f'site:pastebin.com "{username}"'),
            ("Code", "Gist snippets", f'site:gist.github.com "{username}"'),

            # Gaming
            ("Gaming", "Steam profile", f'site:steamcommunity.com "{username}"'),

            # Creative
            ("Creative", "DeviantArt", f'site:deviantart.com "{username}"'),
            ("Creative", "Behance portfolio", f'site:behance.net "{username}"'),
        ]
        for cat, desc, query in social_dorks:
            dorks.append(DorkQuery(cat, desc, query, _to_url(query)))

    if email:
        email_dorks = [
            ("Email Exposure", "Pastebin leaks", f'"{email}" site:pastebin.com'),
            ("Email Exposure", "GitHub exposure", f'"{email}" site:github.com'),
            ("Email Exposure", "PDF documents", f'"{email}" filetype:pdf'),
            ("Email Exposure", "Spreadsheets", f'"{email}" filetype:xlsx OR filetype:csv'),
            ("Email Exposure", "Trello boards", f'"{email}" site:trello.com'),
            ("Email Exposure", "Google Groups", f'"{email}" site:groups.google.com'),
            ("Email Exposure", "Public documents", f'"{email}" filetype:doc OR filetype:docx'),
            ("Email Exposure", "Config files", f'"{email}" filetype:env OR filetype:conf OR filetype:yml'),

            # Credential leaks
            ("Security", "Leaked credentials", f'"{email}" "password" OR "passwd" OR "credentials"'),
            ("Security", "Data breach mentions", f'"{email}" "breach" OR "leak" OR "dump"'),
        ]
        for cat, desc, query in email_dorks:
            dorks.append(DorkQuery(cat, desc, query, _to_url(query)))

    if real_name:
        name_dorks = [
            ("Identity", "LinkedIn profile", f'"{real_name}" site:linkedin.com'),
            ("Identity", "Resume/CV", f'"{real_name}" resume OR CV filetype:pdf'),
            ("Identity", "Academic papers", f'"{real_name}" site:scholar.google.com OR site:researchgate.net'),
            ("Identity", "Presentations", f'"{real_name}" site:slideshare.net OR site:speakerdeck.com'),
            ("Identity", "Conference talks", f'"{real_name}" site:youtube.com "talk" OR "conference" OR "presentation"'),
            ("Identity", "News mentions", f'"{real_name}" site:news.google.com'),
            ("Identity", "Court records", f'"{real_name}" site:courtlistener.com OR "court" OR "case"'),
        ]
        for cat, desc, query in name_dorks:
            dorks.append(DorkQuery(cat, desc, query, _to_url(query)))

    if domain:
        domain_dorks = [
            ("Infrastructure", "Subdomains", f'site:{domain} -www'),
            ("Infrastructure", "Admin panels", f'site:{domain} inurl:admin OR inurl:login OR inurl:dashboard'),
            ("Infrastructure", "Exposed files", f'site:{domain} filetype:pdf OR filetype:doc OR filetype:xls'),
            ("Infrastructure", "Directory listing", f'site:{domain} intitle:"index of"'),
            ("Infrastructure", "Config exposure", f'site:{domain} filetype:env OR filetype:conf OR filetype:yml'),
            ("Infrastructure", "Error pages", f'site:{domain} intext:"error" OR intext:"exception" OR intext:"stack trace"'),
            ("Infrastructure", "API endpoints", f'site:{domain} inurl:api OR inurl:v1 OR inurl:v2'),
        ]
        for cat, desc, query in domain_dorks:
            dorks.append(DorkQuery(cat, desc, query, _to_url(query)))

    if phone:
        phone_dorks = [
            ("Phone", "Public listings", f'"{phone}"'),
            ("Phone", "Social media", f'"{phone}" site:facebook.com OR site:linkedin.com'),
            ("Phone", "Business listings", f'"{phone}" site:yelp.com OR site:yellowpages.com'),
        ]
        for cat, desc, query in phone_dorks:
            dorks.append(DorkQuery(cat, desc, query, _to_url(query)))

    return dorks


def _to_url(query: str) -> str:
    """Convert a dork query to a Google search URL."""
    return f"https://www.google.com/search?q={urllib.parse.quote(query)}"


def format_dorks_markdown(dorks: list[DorkQuery]) -> str:
    """Format dorks as a clickable markdown document."""
    lines = ["# Generated Investigation Queries\n"]
    current_cat = ""

    for dork in dorks:
        if dork.category != current_cat:
            current_cat = dork.category
            lines.append(f"\n## {current_cat}\n")
        lines.append(f"- [{dork.description}]({dork.url})")
        lines.append(f"  `{dork.query}`\n")

    return "\n".join(lines)
