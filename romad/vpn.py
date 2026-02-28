"""romad vpn — VPN health check and diagnostics."""

import re
import subprocess
import sys
import time

from .utils import C, colored, get_public_ip, get_ip_info, detect_vpn, print_banner


def ping_host(host, count=5, timeout=3):
    """Ping a host and return avg latency in ms, or None on failure."""
    try:
        out = subprocess.run(
            ["ping", "-c", str(count), "-W", str(timeout), host],
            capture_output=True, text=True, timeout=count * timeout + 5
        )
        # Parse avg from "round-trip min/avg/max/stddev = ..."
        match = re.search(r"[\d.]+/([\d.]+)/[\d.]+/[\d.]+", out.stdout)
        if match:
            return float(match.group(1))
    except Exception:
        pass
    return None


def check_wireguard_handshake():
    """Check WireGuard handshake freshness."""
    results = []
    try:
        wg_check = subprocess.run(
            ["which", "wg"], capture_output=True, text=True, timeout=3
        )
        if wg_check.returncode != 0:
            return results

        out = subprocess.run(
            ["wg", "show", "all", "latest-handshakes"],
            capture_output=True, text=True, timeout=5
        )
        if not out.stdout.strip():
            return results

        now = time.time()
        for line in out.stdout.strip().split("\n"):
            parts = line.split("\t")
            if len(parts) >= 3:
                iface, peer, timestamp = parts[0], parts[1], int(parts[2])
                if timestamp == 0:
                    results.append((iface, peer[:16] + "...", None, "never"))
                else:
                    age_sec = now - timestamp
                    if age_sec < 60:
                        age_str = f"{int(age_sec)}s ago"
                    elif age_sec < 3600:
                        age_str = f"{int(age_sec / 60)}m ago"
                    else:
                        age_str = f"{int(age_sec / 3600)}h ago"

                    if age_sec > 300:  # 5 min = stale
                        status = "stale"
                    elif age_sec > 180:  # 3 min = aging
                        status = "aging"
                    else:
                        status = "fresh"
                    results.append((iface, peer[:16] + "...", age_str, status))
    except Exception:
        pass
    return results


def check_ip_geolocation(expected_country=None):
    """Verify public IP geolocation matches expected VPN exit."""
    public_ip = get_public_ip()
    if not public_ip:
        return None, None, None

    info = get_ip_info(public_ip)
    city = info.get("city", "Unknown")
    region = info.get("region", "")
    country = info.get("country", "")
    org = info.get("org", "Unknown")
    location = ", ".join(filter(None, [city, region, country]))

    match = None
    if expected_country:
        match = country.upper() == expected_country.upper()

    return {
        "ip": public_ip,
        "location": location,
        "org": org,
        "country": country,
    }, match, expected_country


def run(expected_country=None, verbose=False):
    """Run VPN health check."""
    print_banner()
    print(colored("  ▸ VPN Health Check", C.BOLD))

    issues = 0

    # Step 1: VPN Detection
    print(colored("\n▸ VPN Status", C.BOLD))
    vpns = detect_vpn()
    if vpns:
        for vpn_type, detail in vpns:
            print(colored(f"  ✓ {vpn_type} detected: {detail}", C.GREEN))
    else:
        print(colored("  ✗ No VPN tunnel detected", C.RED))
        print(colored("  → Can't run health check without an active VPN.", C.YELLOW))
        print()
        return 1

    # Step 2: Tunnel Latency
    print(colored("\n▸ Tunnel Latency", C.BOLD))
    print(colored("  Testing latency...", C.DIM))

    # Test latency to common endpoints through the tunnel
    targets = [
        ("1.1.1.1", "Cloudflare"),
        ("8.8.8.8", "Google"),
        ("9.9.9.9", "Quad9"),
    ]

    latencies = []
    for host, name in targets:
        lat = ping_host(host, count=3)
        if lat is not None:
            latencies.append(lat)
            if lat < 50:
                color = C.GREEN
                status = "excellent"
            elif lat < 100:
                color = C.CYAN
                status = "good"
            elif lat < 200:
                color = C.YELLOW
                status = "fair"
            else:
                color = C.RED
                status = "poor"
                issues += 1
            print(f"  {name:12s} → {colored(f'{lat:.1f}ms', color)} ({status})")
        else:
            print(colored(f"  {name:12s} → unreachable", C.RED))
            issues += 1

    if latencies:
        avg = sum(latencies) / len(latencies)
        print(colored(f"\n  Average: {avg:.1f}ms", C.BOLD))

    # Step 3: WireGuard Handshake Check
    print(colored("\n▸ WireGuard Handshake", C.BOLD))
    handshakes = check_wireguard_handshake()
    if handshakes:
        for iface, peer, age, status in handshakes:
            if status == "fresh":
                print(colored(f"  ✓ {iface} peer {peer} — {age} (fresh)", C.GREEN))
            elif status == "aging":
                print(colored(f"  ⚠ {iface} peer {peer} — {age} (aging)", C.YELLOW))
            elif status == "stale":
                print(colored(f"  ✗ {iface} peer {peer} — {age} (stale)", C.RED))
                issues += 1
            elif status == "never":
                print(colored(f"  ✗ {iface} peer {peer} — no handshake yet", C.RED))
                issues += 1
    else:
        print(colored("  ℹ No WireGuard interfaces found (skipped)", C.DIM))

    # Step 4: IP Geolocation Verification
    print(colored("\n▸ IP Geolocation", C.BOLD))
    geo, geo_match, expected = check_ip_geolocation(expected_country)
    if geo:
        print(f"  IP: {colored(geo['ip'], C.CYAN)}")
        print(f"  Location: {geo['location']}")
        print(f"  Org: {geo['org']}")
        if expected:
            if geo_match:
                print(colored(f"  ✓ Appearing in {expected} as expected", C.GREEN))
            else:
                print(colored(f"  ✗ Expected {expected}, but appearing in {geo['country']}", C.RED))
                issues += 1
    else:
        print(colored("  ✗ Could not determine public IP", C.RED))
        issues += 1

    # Step 5: Connectivity Test
    print(colored("\n▸ Connectivity", C.BOLD))
    test_sites = [
        ("https://www.google.com", "Google"),
        ("https://www.cloudflare.com", "Cloudflare"),
        ("https://api.ipify.org", "ipify"),
    ]
    for url, name in test_sites:
        try:
            out = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code},%{time_total}", "-m", "5", url],
                capture_output=True, text=True, timeout=8
            )
            parts = out.stdout.strip().split(",")
            status_code = parts[0]
            time_total = float(parts[1]) if len(parts) > 1 else 0

            if status_code.startswith("2") or status_code.startswith("3"):
                print(colored(f"  ✓ {name:12s} — {status_code} ({time_total:.2f}s)", C.GREEN))
            else:
                print(colored(f"  ⚠ {name:12s} — HTTP {status_code} ({time_total:.2f}s)", C.YELLOW))
                issues += 1
        except Exception:
            print(colored(f"  ✗ {name:12s} — failed", C.RED))
            issues += 1

    # Verdict
    print(colored("\n▸ Verdict", C.BOLD))
    if issues == 0:
        print(colored("  ✓ VPN is healthy. All checks passed.", C.GREEN))
    elif issues <= 2:
        print(colored(f"  ⚠ VPN has {issues} minor issue(s). Review above.", C.YELLOW))
    else:
        print(colored(f"  ✗ VPN has {issues} issues. Needs attention.", C.RED))

    print()
    return 1 if issues > 2 else 0
