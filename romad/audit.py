"""romad audit — Full security posture check before a work session."""

import subprocess
import sys
import time

from .utils import C, colored, detect_vpn, get_public_ip, get_ip_info, get_current_dns_servers, PUBLIC_DNS, print_banner
from .dns import dns_leak_test_external


def _check_vpn():
    """Check VPN status. Returns (pass, details)."""
    vpns = detect_vpn()
    if vpns:
        details = ", ".join(f"{t}: {d}" for t, d in vpns)
        return True, details
    return False, "No VPN tunnel detected"


def _check_dns_leak():
    """Check for DNS leaks. Returns (pass, details)."""
    vpns = detect_vpn()
    if not vpns:
        return None, "Skipped (no VPN)"

    external = dns_leak_test_external()
    leaks = []
    for ip in external:
        ip_clean = ip.split("/")[0].strip()
        if not ip_clean:
            continue
        is_known = any(ip_clean.startswith(d.rsplit(".", 1)[0]) for d in PUBLIC_DNS)
        if not is_known:
            info = get_ip_info(ip_clean)
            org = info.get("org", "Unknown")
            leaks.append(f"{ip_clean} ({org})")

    if leaks:
        return False, f"Leaking via: {', '.join(leaks)}"
    return True, "No leaks detected"


def _check_public_ip():
    """Check public IP and return info."""
    ip = get_public_ip()
    if not ip:
        return False, "Could not determine public IP"
    info = get_ip_info(ip)
    org = info.get("org", "Unknown")
    country = info.get("country", "")
    city = info.get("city", "")
    location = ", ".join(filter(None, [city, country]))
    return True, f"{ip} — {org} [{location}]"


def _check_dns_servers():
    """Check DNS server configuration."""
    servers = get_current_dns_servers()
    if not servers:
        return False, "No DNS servers found"

    known = []
    unknown = []
    for s in servers:
        if s in PUBLIC_DNS:
            known.append(f"{s} ({PUBLIC_DNS[s]})")
        else:
            unknown.append(s)

    if unknown and detect_vpn():
        return False, f"Unknown DNS servers: {', '.join(unknown)}"

    details = ", ".join(known[:3])
    if unknown:
        details += f" + {len(unknown)} other(s)"
    return True, details


def _check_firewall():
    """Check if macOS firewall is enabled."""
    if sys.platform != "darwin":
        return None, "Skipped (not macOS)"

    try:
        # socketfilterfw
        out = subprocess.run(
            ["/usr/libexec/ApplicationFirewall/socketfilterfw", "--getglobalstate"],
            capture_output=True, text=True, timeout=5
        )
        if "enabled" in out.stdout.lower():
            return True, "macOS firewall enabled"
        else:
            return False, "macOS firewall disabled"
    except Exception:
        return None, "Could not check firewall"


def _check_ssh_agent():
    """Check if SSH agent has keys loaded (potential exposure)."""
    try:
        out = subprocess.run(
            ["ssh-add", "-l"], capture_output=True, text=True, timeout=5
        )
        if out.returncode == 0 and out.stdout.strip():
            count = len(out.stdout.strip().split("\n"))
            return True, f"{count} key(s) loaded"
        elif "no identities" in out.stderr.lower() or out.returncode == 1:
            return True, "No keys loaded"
        return None, "Agent not running"
    except Exception:
        return None, "Could not check SSH agent"


def _check_connectivity():
    """Quick connectivity check through the tunnel."""
    try:
        out = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code},%{time_total}", "-m", "5",
             "https://www.google.com"],
            capture_output=True, text=True, timeout=8
        )
        parts = out.stdout.strip().split(",")
        code = parts[0]
        time_s = float(parts[1]) if len(parts) > 1 else 0
        if code.startswith("2") or code.startswith("3"):
            return True, f"OK ({time_s:.2f}s)"
        return False, f"HTTP {code}"
    except Exception:
        return False, "Connection failed"


def run(verbose=False):
    """Run full security posture audit."""
    print_banner()
    print(colored("  ▸ Security Posture Check", C.BOLD))

    checks = [
        ("VPN Status", _check_vpn),
        ("Public IP", _check_public_ip),
        ("DNS Servers", _check_dns_servers),
        ("DNS Leak Test", _check_dns_leak),
        ("Firewall", _check_firewall),
        ("SSH Agent", _check_ssh_agent),
        ("Connectivity", _check_connectivity),
    ]

    results = []
    passed = 0
    failed = 0
    skipped = 0

    print()
    for name, check_fn in checks:
        try:
            status, detail = check_fn()
        except Exception as e:
            status, detail = None, f"Error: {e}"

        results.append((name, status, detail))

        if status is True:
            icon = colored("✓", C.GREEN)
            passed += 1
        elif status is False:
            icon = colored("✗", C.RED)
            failed += 1
        else:
            icon = colored("–", C.DIM)
            skipped += 1

        print(f"  {icon} {name:18s} {detail}")

    # Verdict
    print(colored("\n▸ Verdict", C.BOLD))
    total = passed + failed
    if failed == 0:
        print(colored(f"  ✓ ALL CLEAR — {passed}/{total} checks passed. You're good to work.", C.GREEN))
    elif failed <= 2:
        print(colored(f"  ⚠ CAUTION — {failed} issue(s). Review before starting work.", C.YELLOW))
    else:
        print(colored(f"  ✗ NOT SAFE — {failed} issues detected. Fix before working.", C.RED))

    if skipped:
        print(colored(f"  ({skipped} check(s) skipped)", C.DIM))

    print()
    return 1 if failed > 2 else 0
