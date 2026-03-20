"""romad locate — Location consistency check.

Shows where you APPEAR to be (IP geolocation) vs where you ACTUALLY are
(system timezone), and flags mismatches that could reveal your real location.
"""

import json as json_mod
import subprocess
import time
import sys

from .utils import C, colored, get_public_ip, get_ip_info, get_current_dns_servers


# Timezone to approximate region mapping
TZ_REGIONS = {
    "America/New_York": ("US", "Eastern US"),
    "America/Chicago": ("US", "Central US"),
    "America/Denver": ("US", "Mountain US"),
    "America/Los_Angeles": ("US", "Western US"),
    "America/Anchorage": ("US", "Alaska"),
    "Pacific/Honolulu": ("US", "Hawaii"),
    "America/Toronto": ("CA", "Eastern Canada"),
    "America/Vancouver": ("CA", "Western Canada"),
    "Europe/London": ("GB", "United Kingdom"),
    "Europe/Berlin": ("DE", "Germany"),
    "Europe/Paris": ("FR", "France"),
    "Europe/Amsterdam": ("NL", "Netherlands"),
    "Europe/Zurich": ("CH", "Switzerland"),
    "Europe/Rome": ("IT", "Italy"),
    "Europe/Madrid": ("ES", "Spain"),
    "Europe/Lisbon": ("PT", "Portugal"),
    "Europe/Stockholm": ("SE", "Sweden"),
    "Europe/Oslo": ("NO", "Norway"),
    "Europe/Copenhagen": ("DK", "Denmark"),
    "Europe/Helsinki": ("FI", "Finland"),
    "Europe/Warsaw": ("PL", "Poland"),
    "Europe/Prague": ("CZ", "Czech Republic"),
    "Europe/Vienna": ("AT", "Austria"),
    "Europe/Dublin": ("IE", "Ireland"),
    "Europe/Bucharest": ("RO", "Romania"),
    "Europe/Athens": ("GR", "Greece"),
    "Europe/Istanbul": ("TR", "Turkey"),
    "Europe/Moscow": ("RU", "Russia"),
    "Asia/Tokyo": ("JP", "Japan"),
    "Asia/Seoul": ("KR", "South Korea"),
    "Asia/Shanghai": ("CN", "China"),
    "Asia/Hong_Kong": ("HK", "Hong Kong"),
    "Asia/Singapore": ("SG", "Singapore"),
    "Asia/Bangkok": ("TH", "Thailand"),
    "Asia/Jakarta": ("ID", "Indonesia"),
    "Asia/Kolkata": ("IN", "India"),
    "Asia/Dubai": ("AE", "UAE"),
    "Asia/Tel_Aviv": ("IL", "Israel"),
    "Australia/Sydney": ("AU", "Eastern Australia"),
    "Australia/Melbourne": ("AU", "Eastern Australia"),
    "Australia/Perth": ("AU", "Western Australia"),
    "Pacific/Auckland": ("NZ", "New Zealand"),
    "America/Sao_Paulo": ("BR", "Brazil"),
    "America/Mexico_City": ("MX", "Mexico"),
    "America/Bogota": ("CO", "Colombia"),
    "America/Lima": ("PE", "Peru"),
    "America/Santiago": ("CL", "Chile"),
    "America/Buenos_Aires": ("AR", "Argentina"),
    "Africa/Johannesburg": ("ZA", "South Africa"),
    "Africa/Lagos": ("NG", "Nigeria"),
    "Africa/Nairobi": ("KE", "Kenya"),
    "Africa/Cairo": ("EG", "Egypt"),
    "Africa/Casablanca": ("MA", "Morocco"),
}


def _get_system_timezone():
    """Get the system timezone."""
    try:
        if sys.platform == "darwin":
            out = subprocess.run(
                ["systemsetup", "-gettimezone"],
                capture_output=True, text=True, timeout=5
            )
            # "Time Zone: America/New_York"
            if "Time Zone:" in out.stdout:
                return out.stdout.split(":", 1)[1].strip()
        # Fallback: read /etc/localtime symlink
        import os
        link = os.readlink("/etc/localtime")
        # /var/db/timezone/zoneinfo/America/New_York → America/New_York
        if "zoneinfo/" in link:
            return link.split("zoneinfo/", 1)[1]
    except Exception:
        pass

    # Fallback: use Python
    try:
        return time.tzname[0]
    except Exception:
        return None


def _get_system_locale():
    """Get system locale/language settings."""
    try:
        out = subprocess.run(
            ["defaults", "read", "-g", "AppleLocale"],
            capture_output=True, text=True, timeout=5
        )
        return out.stdout.strip() if out.stdout.strip() else None
    except Exception:
        pass
    try:
        import locale
        return locale.getdefaultlocale()[0]
    except Exception:
        return None


def _get_system_language():
    """Get system language."""
    try:
        out = subprocess.run(
            ["defaults", "read", "-g", "AppleLanguages"],
            capture_output=True, text=True, timeout=5
        )
        # Parse plist array
        for line in out.stdout.splitlines():
            line = line.strip().strip(',').strip('"').strip("'")
            if line and not line.startswith("(") and not line.startswith(")"):
                return line
    except Exception:
        pass
    return None


def _check_dns_location():
    """Check where DNS servers are located."""
    dns_servers = get_current_dns_servers()
    dns_locations = []
    for server in dns_servers[:3]:  # Check first 3
        info = get_ip_info(server)
        if info and info.get("country"):
            dns_locations.append({
                "server": server,
                "country": info.get("country"),
                "city": info.get("city"),
                "org": info.get("org", ""),
            })
    return dns_locations


def run(verbose=False, json_output=False):
    """Run location consistency check."""
    results = {
        "ip": {},
        "system": {},
        "dns": [],
        "mismatches": [],
        "consistent": True,
    }

    if not json_output:
        print(colored("\n  📍 romad locate — location consistency check", C.BOLD))
        print(colored("  ─────────────────────────────────────────────", C.DIM))

    # 1. IP geolocation (where you APPEAR to be)
    if not json_output:
        print(colored(f"\n  🌐 IP Location (where you appear)", C.CYAN))

    ip = get_public_ip()
    if ip:
        ip_info = get_ip_info(ip)
        results["ip"] = {
            "ip": ip,
            "country": ip_info.get("country", "??"),
            "region": ip_info.get("region", ""),
            "city": ip_info.get("city", ""),
            "org": ip_info.get("org", ""),
            "timezone": ip_info.get("timezone", ""),
        }
        if not json_output:
            loc = f"{ip_info.get('city', '?')}, {ip_info.get('region', '?')}, {ip_info.get('country', '?')}"
            print(f"  {C.DIM}├{C.RESET} IP        {colored(ip, C.CYAN)}")
            print(f"  {C.DIM}├{C.RESET} Location  {colored(loc, C.GREEN)}")
            print(f"  {C.DIM}├{C.RESET} ISP/Org   {C.DIM}{ip_info.get('org', '?')}{C.RESET}")
            print(f"  {C.DIM}├{C.RESET} Timezone  {C.DIM}{ip_info.get('timezone', '?')}{C.RESET}")
    else:
        if not json_output:
            print(f"  {C.DIM}├{C.RESET} {colored('Could not determine public IP', C.RED)}")

    # 2. System settings (where you ACTUALLY are configured)
    if not json_output:
        print(colored(f"\n  💻 System Settings (your device config)", C.CYAN))

    sys_tz = _get_system_timezone()
    sys_locale = _get_system_locale()
    sys_lang = _get_system_language()

    results["system"] = {
        "timezone": sys_tz,
        "locale": sys_locale,
        "language": sys_lang,
    }

    tz_info = TZ_REGIONS.get(sys_tz, (None, None))
    sys_country = tz_info[0]
    sys_region = tz_info[1]

    if not json_output:
        print(f"  {C.DIM}├{C.RESET} Timezone  {colored(sys_tz or 'unknown', C.CYAN)}"
              f"  {C.DIM}({sys_region or 'unknown region'}){C.RESET}")
        print(f"  {C.DIM}├{C.RESET} Locale    {C.DIM}{sys_locale or 'unknown'}{C.RESET}")
        print(f"  {C.DIM}├{C.RESET} Language  {C.DIM}{sys_lang or 'unknown'}{C.RESET}")

    # 3. DNS location
    if not json_output:
        print(colored(f"\n  🔍 DNS Server Locations", C.CYAN))

    dns_locs = _check_dns_location()
    results["dns"] = dns_locs

    if not json_output:
        if dns_locs:
            for d in dns_locs:
                loc_str = f"{d.get('city', '?')}, {d['country']}"
                print(f"  {C.DIM}├{C.RESET} {d['server']:<16} {C.DIM}{loc_str} — {d.get('org', '')}{C.RESET}")
        else:
            print(f"  {C.DIM}├{C.RESET} {colored('No DNS location data', C.YELLOW)}")

    # 4. Consistency analysis
    mismatches = []

    ip_country = results["ip"].get("country", "")
    ip_tz = results["ip"].get("timezone", "")

    # IP country vs system timezone country
    if sys_country and ip_country and sys_country != ip_country:
        mismatches.append({
            "type": "country",
            "detail": f"IP says {ip_country}, timezone says {sys_country}",
            "severity": "high",
            "risk": "Your timezone reveals your real country differs from your VPN exit"
        })

    # IP timezone vs system timezone
    if ip_tz and sys_tz and ip_tz != sys_tz:
        mismatches.append({
            "type": "timezone",
            "detail": f"IP timezone: {ip_tz}, System timezone: {sys_tz}",
            "severity": "medium",
            "risk": "Timezone mismatch can reveal approximate real location"
        })

    # DNS country vs IP country
    for d in dns_locs:
        dns_country = d.get("country", "")
        if dns_country and ip_country and dns_country != ip_country:
            # Skip well-known public DNS (they're global)
            org = d.get("org", "").lower()
            if any(x in org for x in ["google", "cloudflare", "quad9", "opendns"]):
                continue
            mismatches.append({
                "type": "dns",
                "detail": f"DNS server {d['server']} is in {dns_country}, IP appears in {ip_country}",
                "severity": "medium",
                "risk": "DNS server location doesn't match your apparent location"
            })

    results["mismatches"] = mismatches
    results["consistent"] = len(mismatches) == 0

    # 5. Verdict
    if not json_output:
        print(colored(f"\n  ─────────────────────────────────────────────", C.DIM))
        if not mismatches:
            print(colored(f"  ✓ CONSISTENT — your location signals align", C.GREEN + C.BOLD))
        else:
            print(colored(f"  ⚠ MISMATCHES DETECTED ({len(mismatches)})", C.RED + C.BOLD))
            for m in mismatches:
                sev_color = C.RED if m["severity"] == "high" else C.YELLOW
                print(f"\n  {colored('●', sev_color)} {colored(m['type'].upper(), C.BOLD)}: {m['detail']}")
                print(f"    {C.DIM}Risk: {m['risk']}{C.RESET}")

            print(colored(f"\n  💡 Tips:", C.CYAN))
            print(f"  {C.DIM}├{C.RESET} Match your system timezone to your VPN exit location")
            print(f"  {C.DIM}├{C.RESET} Use public DNS (1.1.1.1, 8.8.8.8) to avoid DNS location leaks")
            print(f"  {C.DIM}└{C.RESET} Some browsers expose timezone via JavaScript")
        print()

    if json_output:
        print(json_mod.dumps(results, indent=2))

    return 1 if mismatches else 0
