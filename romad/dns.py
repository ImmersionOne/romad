"""romad dns — DNS leak detection."""

import socket
import subprocess
import uuid

from .utils import C, colored, PUBLIC_DNS, get_public_ip, get_ip_info, get_current_dns_servers, resolve_with_server, detect_vpn, print_banner


def dns_leak_test_external():
    """Run external DNS leak tests to identify which servers handle your queries."""
    results = []

    print(colored("\n  Running external DNS leak test...", C.CYAN))

    # Akamai
    try:
        out = subprocess.run(
            ["dig", "whoami.akamai.net", "+short", "+time=3"],
            capture_output=True, text=True, timeout=8
        )
        ip = out.stdout.strip()
        if ip and not ip.startswith(";"):
            results.append(ip)
    except Exception:
        pass

    # Google
    try:
        out = subprocess.run(
            ["dig", "o-o.myaddr.l.google.com", "TXT", "@ns1.google.com", "+short", "+time=3"],
            capture_output=True, text=True, timeout=8
        )
        ip = out.stdout.strip().replace('"', '')
        if ip and not ip.startswith(";"):
            results.append(ip)
    except Exception:
        pass

    # OpenDNS
    try:
        out = subprocess.run(
            ["dig", "myip.opendns.com", "@resolver1.opendns.com", "+short", "+time=3"],
            capture_output=True, text=True, timeout=8
        )
        ip = out.stdout.strip()
        if ip and not ip.startswith(";"):
            results.append(ip)
    except Exception:
        pass

    return list(set(results))


def run(verbose=False, json_output=False):
    """Run the DNS leak detection test."""
    print_banner()
    print(colored("  ▸ DNS Leak Detection", C.BOLD))

    leaked = False

    # VPN Status
    print(colored("\n▸ VPN Status", C.BOLD))
    vpns = detect_vpn()
    if vpns:
        for vpn_type, detail in vpns:
            print(colored(f"  ✓ {vpn_type} detected: {detail}", C.GREEN))
    else:
        print(colored("  ✗ No VPN tunnel detected", C.RED))
        print(colored("  ⚠ All DNS queries are going through your ISP!", C.YELLOW))
        leaked = True

    # Public IP
    print(colored("\n▸ Public IP", C.BOLD))
    public_ip = get_public_ip()
    if public_ip:
        ip_info = get_ip_info(public_ip)
        org = ip_info.get("org", "Unknown")
        city = ip_info.get("city", "")
        region = ip_info.get("region", "")
        country = ip_info.get("country", "")
        location = ", ".join(filter(None, [city, region, country]))
        print(f"  IP: {colored(public_ip, C.CYAN)}")
        print(f"  Org: {org}")
        if location:
            print(f"  Location: {location}")
    else:
        print(colored("  ✗ Could not determine public IP", C.RED))

    # System DNS Servers
    print(colored("\n▸ System DNS Servers", C.BOLD))
    dns_servers = get_current_dns_servers()
    if dns_servers:
        for server in dns_servers:
            label = PUBLIC_DNS.get(server, "")
            if label:
                print(f"  • {server} ({label})")
            else:
                info = get_ip_info(server) if verbose else {}
                org = info.get("org", "")
                extra = f" ({org})" if org else ""
                print(f"  • {server}{extra}")
    else:
        print(colored("  ✗ Could not detect DNS servers", C.RED))

    # DNS Leak Test
    print(colored("\n▸ DNS Leak Test", C.BOLD))
    external_dns = dns_leak_test_external()

    if external_dns:
        print(colored("  DNS servers handling your queries:", C.DIM))
        for ip in external_dns:
            ip_clean = ip.split("/")[0].strip()
            if not ip_clean:
                continue
            info = get_ip_info(ip_clean)
            org = info.get("org", "Unknown")
            country = info.get("country", "")

            is_known_vpn_dns = False
            for dns_ip in PUBLIC_DNS:
                if ip_clean.startswith(dns_ip.rsplit(".", 1)[0]):
                    is_known_vpn_dns = True
                    break

            if vpns and not is_known_vpn_dns:
                print(colored(f"  ⚠ {ip_clean} — {org} [{country}]", C.YELLOW))
                leaked = True
            else:
                print(f"  • {ip_clean} — {org} [{country}]")

    # DNS Resolution Consistency
    print(colored("\n▸ DNS Resolution Consistency", C.BOLD))
    test_domain = "example.com"

    try:
        sys_result = socket.gethostbyname(test_domain)
        print(f"  System resolver → {sys_result}")
    except Exception:
        sys_result = None
        print(colored("  ✗ System resolver failed", C.RED))

    if dns_servers:
        for server in dns_servers[:2]:
            result = resolve_with_server(test_domain, server)
            if result:
                match = "✓" if result == sys_result else "≠"
                print(f"  {server} → {result} {match}")

    # Verdict
    print(colored("\n▸ Verdict", C.BOLD))
    if leaked:
        print(colored("  ⚠ POTENTIAL DNS LEAK DETECTED", C.RED))
        print(colored("  Your DNS queries may be visible to your ISP or a third party.", C.YELLOW))
        if not vpns:
            print(colored("  → Connect to your VPN first.", C.YELLOW))
        else:
            print(colored("  → Check your VPN's DNS settings.", C.YELLOW))
            print(colored("  → Ensure DNS is routed through the tunnel.", C.YELLOW))
    else:
        if vpns:
            print(colored("  ✓ No DNS leak detected. You look good.", C.GREEN))
        else:
            print(colored("  ℹ No VPN active. DNS is going through your default resolver.", C.YELLOW))

    print()
    return 1 if leaked else 0
