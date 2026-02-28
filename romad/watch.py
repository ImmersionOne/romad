"""romad watch — Continuous VPN/DNS monitoring daemon."""

import signal
import sys
import time

from .utils import C, colored, detect_vpn, get_public_ip, get_ip_info, get_current_dns_servers, print_banner
from .dns import dns_leak_test_external


_running = True


def _handle_signal(signum, frame):
    global _running
    _running = False
    print(colored("\n\n  ⏹ Watch stopped.", C.YELLOW))


def _check_cycle(last_ip=None, verbose=False):
    """Run one check cycle. Returns (exit_code, current_ip)."""
    issues = []
    now = time.strftime("%H:%M:%S")

    # VPN check
    vpns = detect_vpn()
    if not vpns:
        issues.append("No VPN detected")

    # Public IP check
    current_ip = get_public_ip()
    ip_changed = last_ip is not None and current_ip != last_ip

    if ip_changed:
        issues.append(f"IP changed: {last_ip} → {current_ip}")

    # DNS leak check
    external_dns = dns_leak_test_external()
    dns_servers = get_current_dns_servers()

    # Simple leak heuristic: if external DNS resolvers don't match system DNS
    if vpns and external_dns:
        from .utils import PUBLIC_DNS
        for ip in external_dns:
            ip_clean = ip.split("/")[0].strip()
            if not ip_clean:
                continue
            is_known = False
            for dns_ip in PUBLIC_DNS:
                if ip_clean.startswith(dns_ip.rsplit(".", 1)[0]):
                    is_known = True
                    break
            if not is_known:
                info = get_ip_info(ip_clean)
                org = info.get("org", "Unknown")
                issues.append(f"DNS leak via {ip_clean} ({org})")

    # Output
    if issues:
        print(colored(f"\n  [{now}] ⚠ ALERT — {len(issues)} issue(s):", C.RED))
        for issue in issues:
            print(colored(f"    • {issue}", C.YELLOW))
    else:
        vpn_names = ", ".join(f"{t}:{d}" for t, d in vpns) if vpns else "none"
        ip_display = current_ip or "unknown"
        print(colored(f"  [{now}] ✓ All clear — VPN: {vpn_names} | IP: {ip_display}", C.GREEN))

    return (1 if issues else 0), current_ip


def run(interval=60, verbose=False):
    """Run continuous watch loop."""
    print_banner()
    print(colored("  ▸ Live Monitor", C.BOLD))
    print(colored(f"\n  Checking every {interval}s. Ctrl+C to stop.\n", C.DIM))

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    last_ip = None
    alert_count = 0

    while _running:
        code, last_ip = _check_cycle(last_ip, verbose=verbose)
        if code > 0:
            alert_count += 1

        # Wait for next cycle
        waited = 0
        while _running and waited < interval:
            time.sleep(1)
            waited += 1

    print(colored(f"\n  Session summary: {alert_count} alert(s) fired.\n", C.BOLD))
    return 1 if alert_count > 0 else 0
