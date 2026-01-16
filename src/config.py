"""Configuration loader."""

import yaml
from pathlib import Path
from dataclasses import dataclass


@dataclass
class Config:
    max_concurrent: int = 80
    request_timeout: int = 15
    retries: int = 2
    rate_limit: float = 3.0
    proxy_enabled: bool = False
    tor: bool = False
    tor_port: int = 9050
    default_format: str = "all"

    @classmethod
    def load(cls, path: str | None = None) -> "Config":
        config_path = Path(path) if path else Path(__file__).parent.parent / "config" / "settings.yaml"
        if not config_path.exists():
            return cls()

        with open(config_path) as f:
            data = yaml.safe_load(f)

        general = data.get("general", {})
        proxy = data.get("proxy", {})
        output = data.get("output", {})

        return cls(
            max_concurrent=general.get("max_concurrent", 80),
            request_timeout=general.get("request_timeout", 15),
            retries=general.get("retries", 2),
            rate_limit=general.get("rate_limit_per_domain", 3.0),
            proxy_enabled=proxy.get("enabled", False),
            tor=proxy.get("tor", False),
            tor_port=proxy.get("tor_port", 9050),
            default_format=output.get("default_format", "all"),
        )

    @property
    def proxy_url(self) -> str | None:
        if self.tor:
            return f"socks5://127.0.0.1:{self.tor_port}"
        return None
