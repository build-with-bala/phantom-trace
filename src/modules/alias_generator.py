"""Generate probable username aliases from a known username."""

import re

LEET_MAP = {"a": ["4", "@"], "e": ["3"], "i": ["1", "!"], "o": ["0"], "s": ["5", "$"], "t": ["7"]}
SEPARATORS = ["", ".", "_", "-"]
SUFFIXES = ["", "1", "12", "123", "69", "420", "007", "x", "xx", "real", "official"]
PREFIXES = ["", "the", "its", "im", "real", "official", "not", "x", "mr", "ms"]


def _split_username(username: str) -> list[str]:
    for sep in [".", "_", "-"]:
        if sep in username:
            return [p for p in username.split(sep) if p]
    parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|\b)|[A-Z]+|\d+", username)
    if len(parts) > 1:
        return [p.lower() for p in parts]
    parts = re.findall(r"[a-zA-Z]+|\d+", username)
    return [p.lower() for p in parts] if len(parts) > 1 else [username]


def generate_aliases(username: str, max_results: int = 50) -> list[str]:
    aliases = set()
    base = username.lower().strip()
    aliases.update([base.upper(), base.capitalize()])

    parts = _split_username(base)
    if len(parts) > 1:
        for sep in SEPARATORS:
            aliases.add(sep.join(parts))
            aliases.add(sep.join(reversed(parts)))
        if len(parts) == 2:
            f, l = parts
            for sep in [".", "_", "-", ""]:
                aliases.update([f"{f[0]}{sep}{l}", f"{f}{sep}{l[0]}"])

    stripped = re.sub(r"\d+$", "", base)
    for suffix in SUFFIXES:
        aliases.update([f"{base}{suffix}", f"{stripped}{suffix}"])
    for prefix in PREFIXES:
        if prefix:
            aliases.update([f"{prefix}{base}", f"{prefix}_{base}"])

    for char, reps in LEET_MAP.items():
        if char in base:
            for rep in reps:
                aliases.add(base.replace(char, rep, 1))

    aliases.discard("")
    aliases.discard(base)
    return sorted(aliases, key=len)[:max_results]


def generate_from_real_name(first: str, last: str, birth_year: int | None = None) -> list[str]:
    f, l = first.lower().strip(), last.lower().strip()
    aliases = set()
    years = [str(birth_year), str(birth_year)[-2:]] if birth_year else []

    patterns = [f"{f}{l}", f"{l}{f}", f"{f}.{l}", f"{f}_{l}", f"{f}-{l}",
                f"{f[0]}{l}", f"{f}{l[0]}", f"{f[0]}.{l}", f"{l}.{f}", f"{l}{f[0]}"]
    for p in patterns:
        aliases.add(p)
        for y in years:
            aliases.add(f"{p}{y}")
    return sorted(aliases, key=len)
