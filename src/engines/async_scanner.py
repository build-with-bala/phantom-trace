"""High-performance async HTTP engine with rate limiting."""

import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Any

import aiohttp
from fake_useragent import UserAgent

from src.models import SiteResult, CheckType


@dataclass
class RateLimiter:
    rate: float = 3.0
    _tokens: dict[str, float] = field(default_factory=dict)
    _timestamps: dict[str, float] = field(default_factory=dict)

    async def acquire(self, domain: str):
        now = time.monotonic()
        if domain not in self._timestamps:
            self._timestamps[domain] = now
            self._tokens[domain] = self.rate
            return
        elapsed = now - self._timestamps[domain]
        self._tokens[domain] = min(self.rate, self._tokens[domain] + elapsed * self.rate)
        self._timestamps[domain] = now
        if self._tokens[domain] < 1.0:
            await asyncio.sleep((1.0 - self._tokens[domain]) / self.rate)
            self._tokens[domain] = 0
        else:
            self._tokens[domain] -= 1.0


class AsyncScanner:
    def __init__(self, max_concurrent: int = 80, timeout: int = 15, retries: int = 2, proxy: str | None = None):
        self.max_concurrent = max_concurrent
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.retries = retries
        self.proxy = proxy
        self.rate_limiter = RateLimiter()
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self._ua = UserAgent()

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": self._ua.random,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "DNT": "1",
            "Connection": "keep-alive",
        }

    async def check_site(self, site_name: str, config: dict, username: str) -> SiteResult:
        url = config["url"].format(username)
        check_type = CheckType(config.get("check_type", "status_code"))
        result = SiteResult(site=site_name, url=url, category=config.get("category", "other"), username=username)

        async with self.semaphore:
            import tldextract
            domain = tldextract.extract(url).registered_domain
            await self.rate_limiter.acquire(domain)

            for attempt in range(self.retries + 1):
                try:
                    async with aiohttp.ClientSession(timeout=self.timeout) as session:
                        async with session.get(url, headers=self._headers(), proxy=self.proxy, allow_redirects=True, ssl=False) as resp:
                            body = await resp.text(errors="ignore")
                            if check_type == CheckType.STATUS_CODE:
                                result.found = resp.status in config.get("valid_codes", [200])
                            elif check_type == CheckType.RESPONSE_BODY:
                                valid = config.get("valid_pattern", "")
                                invalid = config.get("invalid_pattern", "")
                                if invalid and invalid in body:
                                    result.found = False
                                elif valid and valid in body:
                                    result.found = True
                            result.status_code = resp.status
                            break
                except asyncio.TimeoutError:
                    if attempt == self.retries:
                        result.error = "timeout"
                except aiohttp.ClientError as e:
                    if attempt == self.retries:
                        result.error = str(e)[:100]

                if attempt < self.retries:
                    await asyncio.sleep(random.uniform(0.5, 2.0))

        return result

    async def scan_all(self, username: str, sites: dict, callback=None) -> list[SiteResult]:
        tasks = [self.check_site(name, config, username) for name, config in sites.items()]
        results = []
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)
            if callback:
                callback(result)
        return results
