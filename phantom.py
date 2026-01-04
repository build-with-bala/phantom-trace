#!/usr/bin/env python3
"""Phantom Trace - OSINT People Search."""

import sys
from src.engines.scanner import scan_username

def main():
    if len(sys.argv) < 2:
        print("Usage: python phantom.py <username>")
        sys.exit(1)

    username = sys.argv[1]
    print(f"\n[*] Scanning for: {username}\n")

    results = scan_username(username)
    found = [r for r in results if r.found]
    errors = [r for r in results if r.error]

    for r in found:
        print(f"  [+] {r.site:<20} {r.url}")

    print(f"\n[*] Found on {len(found)}/{len(results)} sites")
    if errors:
        print(f"[!] {len(errors)} errors encountered")

if __name__ == "__main__":
    main()
