"""Certificate transparency + WHOIS/RDAP chain for domain intelligence."""

import re
import socket
from datetime import datetime

import aiohttp


async def query_crtsh(domain: str, session: aiohttp.ClientSession) -> list[dict]:
    """Query crt.sh certificate transparency logs.

    If a target owns a domain, this reveals:
    - All subdomains ever issued certificates
    - Certificate timeline (when they started using the domain)
    - Email addresses in certificate SANs
    - Other domains on shared certificates
    """
    results = []

    try:
        async with session.get(
            f"https://crt.sh/?q={domain}&output=json",
            timeout=aiohttp.ClientTimeout(total=20),
        ) as resp:
            if resp.status != 200:
                return results

            data = await resp.json(content_type=None)

            seen_names = set()
            for cert in data:
                name_value = cert.get("name_value", "")
                issuer = cert.get("issuer_name", "")
                not_before = cert.get("not_before", "")
                not_after = cert.get("not_after", "")

                # Split multi-line name values (SANs)
                for name in name_value.split("\n"):
                    name = name.strip().lower()
                    if name and name not in seen_names:
                        seen_names.add(name)
                        results.append({
                            "domain": name,
                            "issuer": issuer,
                            "not_before": not_before,
                            "not_after": not_after,
                            "is_wildcard": name.startswith("*."),
                        })

    except Exception:
        pass

    # Sort by discovery date
    results.sort(key=lambda x: x.get("not_before", ""), reverse=True)
    return results[:50]  # Cap results


async def query_rdap(domain: str, session: aiohttp.ClientSession) -> dict:
    """Query RDAP (modern WHOIS replacement) for domain registration info.

    Returns structured JSON with registrant info, nameservers, dates.
    """
    result = {
        "domain": domain,
        "registered": False,
        "registrant": None,
        "registrar": None,
        "created": None,
        "expires": None,
        "nameservers": [],
        "status": [],
    }

    try:
        async with session.get(
            f"https://rdap.org/domain/{domain}",
            headers={"Accept": "application/rdap+json"},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status != 200:
                return result

            data = await resp.json(content_type=None)
            result["registered"] = True

            # Events (creation, expiration, last update)
            for event in data.get("events", []):
                action = event.get("eventAction", "")
                date = event.get("eventDate", "")
                if action == "registration":
                    result["created"] = date
                elif action == "expiration":
                    result["expires"] = date

            # Nameservers
            for ns in data.get("nameservers", []):
                result["nameservers"].append(ns.get("ldhName", ""))

            # Status
            result["status"] = data.get("status", [])

            # Entities (registrant, registrar, etc.)
            for entity in data.get("entities", []):
                roles = entity.get("roles", [])
                vcard = entity.get("vcardArray", [None, []])

                if "registrar" in roles:
                    # Extract registrar name from vCard
                    if len(vcard) > 1:
                        for field in vcard[1]:
                            if field[0] == "fn":
                                result["registrar"] = field[3]
                                break

                if "registrant" in roles:
                    registrant = {}
                    if len(vcard) > 1:
                        for field in vcard[1]:
                            if field[0] == "fn":
                                registrant["name"] = field[3]
                            elif field[0] == "adr":
                                registrant["address"] = field[3] if isinstance(field[3], str) else str(field[3])
                            elif field[0] == "email":
                                registrant["email"] = field[3]
                            elif field[0] == "tel":
                                registrant["phone"] = field[3]
                    if registrant:
                        result["registrant"] = registrant

    except Exception:
        pass

    return result


def resolve_domain(domain: str) -> dict:
    """DNS resolution for a domain."""
    result = {"domain": domain, "ips": [], "error": None}
    try:
        infos = socket.getaddrinfo(domain, None, socket.AF_INET)
        result["ips"] = list(set(info[4][0] for info in infos))
    except socket.gaierror as e:
        result["error"] = str(e)
    return result


async def domain_intel_chain(domain: str, session: aiohttp.ClientSession) -> dict:
    """Full domain intelligence chain: DNS → crt.sh → RDAP."""
    dns = resolve_domain(domain)
    certs = await query_crtsh(domain, session)
    rdap = await query_rdap(domain, session)

    # Extract unique subdomains from certs
    subdomains = set()
    for cert in certs:
        d = cert["domain"]
        if d != domain and not d.startswith("*."):
            subdomains.add(d)

    return {
        "domain": domain,
        "dns": dns,
        "certificates": certs[:20],
        "subdomains": sorted(subdomains),
        "rdap": rdap,
        "total_certs_found": len(certs),
    }
