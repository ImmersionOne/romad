"""romad compare — Save and compare locations over time.

Saves speed/latency/VPN results per location so you can compare
cafes, coworking spots, hotels, airports, etc.
"""

import json as json_mod
import os
import sys
import time
from datetime import datetime

from .utils import C, colored, get_public_ip, get_ip_info
from .speed import _download_test, _ping, DOWNLOAD_URLS, PING_HOSTS


DATA_DIR = os.path.expanduser("~/.romad")
HISTORY_FILE = os.path.join(DATA_DIR, "locations.json")


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _load_history():
    _ensure_data_dir()
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return {"locations": []}


# Use the json module directly
import json


def _save_history(data):
    _ensure_data_dir()
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _run_quick_test():
    """Run a quick speed + ping test."""
    # Download (10MB)
    url, expected, label = DOWNLOAD_URLS[0]
    mbps, _, _ = _download_test(url, expected, label)

    # Ping
    ping_ms = None
    result = _ping(PING_HOSTS[0][0], count=3)
    if result:
        ping_ms = result[0]

    # IP info
    ip = get_public_ip()
    ip_info = get_ip_info(ip) if ip else {}

    return {
        "download_mbps": round(mbps, 1) if mbps else None,
        "ping_ms": round(ping_ms, 1) if ping_ms else None,
        "ip": ip,
        "country": ip_info.get("country", ""),
        "city": ip_info.get("city", ""),
        "org": ip_info.get("org", ""),
    }


def save(name, verbose=False, json_output=False):
    """Save current location with a name."""
    if not json_output:
        print(colored(f"\n  📍 Saving location: {name}", C.BOLD))
        print(colored("  ─────────────────────────────────", C.DIM))
        print(colored(f"  Running tests...\n", C.DIM))

    test = _run_quick_test()

    entry = {
        "name": name,
        "timestamp": datetime.now().isoformat(),
        "download_mbps": test["download_mbps"],
        "ping_ms": test["ping_ms"],
        "ip": test["ip"],
        "country": test["country"],
        "city": test["city"],
        "org": test["org"],
    }

    history = _load_history()
    history["locations"].append(entry)
    _save_history(history)

    if json_output:
        print(json_mod.dumps(entry, indent=2))
    else:
        dl = f"{test['download_mbps']} Mbps" if test['download_mbps'] else "failed"
        pg = f"{test['ping_ms']}ms" if test['ping_ms'] else "n/a"
        print(f"  {C.DIM}├{C.RESET} Download  {colored(dl, C.CYAN)}")
        print(f"  {C.DIM}├{C.RESET} Ping      {colored(pg, C.CYAN)}")
        print(f"  {C.DIM}├{C.RESET} Location  {test['city']}, {test['country']}")
        print(f"  {C.DIM}├{C.RESET} ISP       {C.DIM}{test['org']}{C.RESET}")
        print(f"\n  {colored('✓ Saved!', C.GREEN)} ({len(history['locations'])} total entries)")
        print()

    return 0


def show(json_output=False):
    """Show comparison of all saved locations."""
    history = _load_history()
    locations = history.get("locations", [])

    if not locations:
        if json_output:
            print(json_mod.dumps({"locations": []}, indent=2))
        else:
            print(colored("\n  No saved locations yet.", C.YELLOW))
            hint = colored('romad compare save "Coffee Shop Name"', C.CYAN)
            print(f"  Save one with: {hint}")
            print()
        return 0

    if json_output:
        print(json_mod.dumps(history, indent=2))
        return 0

    print(colored(f"\n  📊 romad compare — location comparison", C.BOLD))
    print(colored("  ─────────────────────────────────────────────────────────────────", C.DIM))

    # Group by name, show best result per location
    by_name = {}
    for loc in locations:
        name = loc["name"]
        if name not in by_name:
            by_name[name] = []
        by_name[name].append(loc)

    # Sort by best download speed
    sorted_locs = sorted(
        by_name.items(),
        key=lambda x: max((e.get("download_mbps") or 0) for e in x[1]),
        reverse=True
    )

    # Find max speed for bar scaling
    max_speed = max(
        (e.get("download_mbps") or 0)
        for locs in by_name.values()
        for e in locs
    ) or 100

    print(f"\n  {'Location':<25} {'Best ↓':<12} {'Best Ping':<12} {'Tests':<7} {'Last Tested'}")
    print(colored(f"  {'─' * 75}", C.DIM))

    for name, entries in sorted_locs:
        best_dl = max((e.get("download_mbps") or 0) for e in entries)
        best_ping = min((e.get("ping_ms") or 999) for e in entries)
        last = entries[-1]
        last_date = last.get("timestamp", "")[:10]

        # Speed bar
        bar_width = 15
        ratio = best_dl / max_speed if max_speed > 0 else 0
        filled = int(ratio * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)

        if best_dl >= 50:
            dl_color = C.GREEN
        elif best_dl >= 10:
            dl_color = C.YELLOW
        else:
            dl_color = C.RED

        if best_ping < 30:
            pg_color = C.GREEN
        elif best_ping < 100:
            pg_color = C.YELLOW
        else:
            pg_color = C.RED

        dl_str = f"{best_dl:.1f} Mbps" if best_dl else "n/a"
        pg_str = f"{best_ping:.0f}ms" if best_ping < 999 else "n/a"

        print(f"  {name:<25} {dl_color}{dl_str:<12}{C.RESET} {pg_color}{pg_str:<12}{C.RESET} {len(entries):<7} {C.DIM}{last_date}{C.RESET}")
        print(f"  {C.DIM}{'':>25} {dl_color}{bar}{C.RESET}{C.RESET}")

    # Winner
    if len(sorted_locs) > 1:
        winner = sorted_locs[0][0]
        print(colored(f"\n  🏆 Best spot: {winner}", C.GREEN + C.BOLD))

    print()
    return 0


def clear(json_output=False):
    """Clear all saved locations."""
    _save_history({"locations": []})
    if json_output:
        print(json_mod.dumps({"cleared": True}))
    else:
        print(colored("  ✓ All saved locations cleared.", C.GREEN))
        print()
    return 0


def run(action="show", name=None, verbose=False, json_output=False):
    """Entry point for compare command."""
    if action == "save":
        if not name:
            print(colored("  Error: provide a location name", C.RED))
            print(f"  Usage: romad compare save \"Coffee Shop\"")
            return 1
        return save(name, verbose, json_output)
    elif action == "clear":
        return clear(json_output)
    else:
        return show(json_output)
