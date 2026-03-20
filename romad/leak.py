"""romad leak — Full privacy leak check (DNS + WebRTC + IPv6)."""

import json as json_mod
import subprocess
import socket
import sys
import re

from .utils import C, colored, get_public_ip, get_ip_info, get_current_dns_servers, detect_vpn


def _check_ipv6_leak():
    """Check for IPv6 address leaks outside VPN tunnel."""
    results = {
        "has_ipv6": False,
        "ipv6_addresses": [],
        "leak": False,
    }

    try:
        # Check for global IPv6 addresses
        if sys.platform == "darwin":
            out = subprocess.run(
                ["/sbin/ifconfig"], capture_output=True, text=True, timeout=5
            )
        else:
            out = subprocess.run(
                ["ip", "-6", "addr", "show", "scope", "global"],
                capture_output=True, text=True, timeout=5
            )

        # Find global (non-link-local) IPv6 addresses
        for line in out.stdout.splitlines():
            line = line.strip()
            if "inet6" in line:
                parts = line.split()
                for p in parts:
                    if ":" in p and not p.startswith("fe80") and not p.startswith("::1"):
                        addr = p.split("/")[0].split("%")[0]
                        if addr and len(addr) > 4:
                            results["ipv6_addresses"].append(addr)

        results["has_ipv6"] = len(results["ipv6_addresses"]) > 0

        # Check if IPv6 reaches the internet (potential leak)
        if results["has_ipv6"]:
            try:
                out = subprocess.run(
                    ["curl", "-6", "-s", "-m", "5", "https://api64.ipify.org"],
                    capture_output=True, text=True, timeout=8
                )
                if out.stdout.strip() and ":" in out.stdout.strip():
                    results["public_ipv6"] = out.stdout.strip()
                    # If VPN is active but IPv6 goes out directly, that's a leak
                    vpns = detect_vpn()
                    if vpns:
                        results["leak"] = True
            except Exception:
                pass

    except Exception:
        pass

    return results


def _check_webrtc_candidates():
    """Check for WebRTC leak potential (system-level check).

    Note: Full WebRTC leak testing requires a browser. This checks
    if the system has local IPs that would be exposed via WebRTC.
    """
    results = {
        "local_ips": [],
        "risk": "unknown",
    }

    try:
        # Get all local IPs that could be exposed via WebRTC
        if sys.platform == "darwin":
            out = subprocess.run(
                ["/sbin/ifconfig"], capture_output=True, text=True, timeout=5
            )
        else:
            out = subprocess.run(
                ["ip", "addr", "show"], capture_output=True, text=True, timeout=5
            )

        for line in out.stdout.splitlines():
            line = line.strip()
            if "inet " in line:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == "inet":
                        addr = parts[i + 1].split("/")[0]
                        if addr != "127.0.0.1" and not addr.startswith("169.254"):
                            results["local_ips"].append(addr)

        # Determine risk level
        private_ranges = ["10.", "172.16.", "172.17.", "172.18.", "172.19.",
                         "172.20.", "172.21.", "172.22.", "172.23.", "172.24.",
                         "172.25.", "172.26.", "172.27.", "172.28.", "172.29.",
                         "172.30.", "172.31.", "192.168."]

        has_private = any(any(ip.startswith(r) for r in private_ranges)
                        for ip in results["local_ips"])
        has_public = any(not any(ip.startswith(r) for r in private_ranges)
                        for ip in results["local_ips"])

        if has_public:
            results["risk"] = "high"
        elif has_private:
            results["risk"] = "medium"
        else:
            results["risk"] = "low"

    except Exception:
        pass

    return results


def _check_dns_leak():
    """Enhanced DNS leak check."""
    results = {
        "system_dns": [],
        "leak": False,
        "leaking_servers": [],
    }

    dns_servers = get_current_dns_servers()
    results["system_dns"] = dns_servers

    # Get VPN status
    vpns = detect_vpn()
    ip = get_public_ip()
    ip_info = get_ip_info(ip) if ip else {}
    ip_country = ip_info.get("country", "")

    # Check if any DNS servers are outside the VPN country
    for server in dns_servers:
        dns_info = get_ip_info(server)
        if dns_info and dns_info.get("country"):
            dns_country = dns_info["country"]
            org = dns_info.get("org", "").lower()

            # Skip well-known public DNS
            if any(x in org for x in ["google", "cloudflare", "quad9", "opendns", "nextdns"]):
                continue

            # If on VPN and DNS is in a different country, potential leak
            if vpns and ip_country and dns_country != ip_country:
                results["leak"] = True
                results["leaking_servers"].append({
                    "server": server,
                    "country": dns_country,
                    "org": dns_info.get("org", ""),
                })

    return results


def _check_torrent_leak():
    """Check if torrent clients might leak real IP."""
    results = {"clients_running": [], "risk": "none"}

    clients = ["transmission", "qbittorrent", "deluge", "rtorrent", "aria2c"]
    for client in clients:
        try:
            out = subprocess.run(
                ["pgrep", "-x", client],
                capture_output=True, text=True, timeout=3
            )
            if out.stdout.strip():
                results["clients_running"].append(client)
        except Exception:
            pass

    if results["clients_running"]:
        results["risk"] = "high"

    return results


def run(verbose=False, json_output=False):
    """Run full privacy leak check."""
    results = {
        "ip": {},
        "vpn_active": False,
        "dns": {},
        "ipv6": {},
        "webrtc": {},
        "torrent": {},
        "leaks": [],
        "clean": True,
    }

    if not json_output:
        print(colored("\n  🔒 romad leak — full privacy leak check", C.BOLD))
        print(colored("  ─────────────────────────────────────────", C.DIM))

    # IP + VPN status
    ip = get_public_ip()
    ip_info = get_ip_info(ip) if ip else {}
    vpns = detect_vpn()
    results["ip"] = {"ip": ip, **ip_info}
    results["vpn_active"] = len(vpns) > 0

    if not json_output:
        print(colored(f"\n  🌐 Identity", C.CYAN))
        loc = f"{ip_info.get('city', '?')}, {ip_info.get('country', '?')}"
        print(f"  {C.DIM}├{C.RESET} IP        {colored(ip or 'unknown', C.CYAN)}")
        print(f"  {C.DIM}├{C.RESET} Location  {loc}")
        vpn_str = colored("active", C.GREEN) if vpns else colored("none detected", C.YELLOW)
        print(f"  {C.DIM}├{C.RESET} VPN       {vpn_str}")
        if vpns:
            for vtype, vname in vpns:
                print(f"  {C.DIM}│  {C.RESET}{C.DIM}{vtype}: {vname}{C.RESET}")

    # DNS leak check
    if not json_output:
        print(colored(f"\n  📡 DNS Leak Check", C.CYAN))
    dns_results = _check_dns_leak()
    results["dns"] = dns_results

    if not json_output:
        if dns_results["leak"]:
            print(f"  {C.DIM}├{C.RESET} {colored('✗ DNS LEAK DETECTED', C.RED)}")
            for s in dns_results["leaking_servers"]:
                print(f"  {C.DIM}│  {C.RESET}{C.RED}{s['server']} → {s['country']} ({s.get('org', '')}){C.RESET}")
            results["leaks"].append("dns")
        else:
            print(f"  {C.DIM}├{C.RESET} {colored('✓ No DNS leak detected', C.GREEN)}")
        print(f"  {C.DIM}├{C.RESET} System DNS: {C.DIM}{', '.join(dns_results['system_dns'][:3])}{C.RESET}")

    # IPv6 leak check
    if not json_output:
        print(colored(f"\n  🔗 IPv6 Leak Check", C.CYAN))
    ipv6_results = _check_ipv6_leak()
    results["ipv6"] = ipv6_results

    if not json_output:
        if ipv6_results.get("leak"):
            print(f"  {C.DIM}├{C.RESET} {colored('✗ IPv6 LEAK — traffic bypassing VPN', C.RED)}")
            if ipv6_results.get("public_ipv6"):
                print(f"  {C.DIM}│  {C.RESET}{C.RED}Public IPv6: {ipv6_results['public_ipv6']}{C.RESET}")
            results["leaks"].append("ipv6")
        elif ipv6_results.get("has_ipv6"):
            print(f"  {C.DIM}├{C.RESET} {colored('⚠ IPv6 present but not leaking externally', C.YELLOW)}")
            if verbose:
                for addr in ipv6_results["ipv6_addresses"][:3]:
                    print(f"  {C.DIM}│  {C.RESET}{C.DIM}{addr}{C.RESET}")
        else:
            print(f"  {C.DIM}├{C.RESET} {colored('✓ No IPv6 (no leak possible)', C.GREEN)}")

    # WebRTC check
    if not json_output:
        print(colored(f"\n  🎥 WebRTC Leak Risk", C.CYAN))
    webrtc_results = _check_webrtc_candidates()
    results["webrtc"] = webrtc_results

    if not json_output:
        risk = webrtc_results["risk"]
        if risk == "high":
            print(f"  {C.DIM}├{C.RESET} {colored('✗ HIGH RISK — public IPs exposed to WebRTC', C.RED)}")
            results["leaks"].append("webrtc")
        elif risk == "medium":
            print(f"  {C.DIM}├{C.RESET} {colored('⚠ MEDIUM — private IPs visible via WebRTC', C.YELLOW)}")
            print(f"  {C.DIM}│  {C.RESET}{C.DIM}Browsers can expose local IPs. Use a WebRTC blocker.{C.RESET}")
        else:
            print(f"  {C.DIM}├{C.RESET} {colored('✓ Low risk', C.GREEN)}")

        if verbose and webrtc_results["local_ips"]:
            for lip in webrtc_results["local_ips"]:
                print(f"  {C.DIM}│  {C.RESET}{C.DIM}{lip}{C.RESET}")

    # Torrent check
    if not json_output:
        print(colored(f"\n  📥 Torrent Client Check", C.CYAN))
    torrent_results = _check_torrent_leak()
    results["torrent"] = torrent_results

    if not json_output:
        if torrent_results["clients_running"]:
            clients = ", ".join(torrent_results["clients_running"])
            print(f"  {C.DIM}├{C.RESET} {colored(f'⚠ Running: {clients}', C.YELLOW)}")
            print(f"  {C.DIM}│  {C.RESET}{C.DIM}Torrent clients can leak real IP via DHT/trackers{C.RESET}")
        else:
            print(f"  {C.DIM}├{C.RESET} {colored('✓ No torrent clients detected', C.GREEN)}")

    # Verdict
    results["clean"] = len(results["leaks"]) == 0

    if not json_output:
        print(colored(f"\n  ─────────────────────────────────────────", C.DIM))
        if results["clean"]:
            print(colored(f"  ✓ CLEAN — no privacy leaks detected", C.GREEN + C.BOLD))
        else:
            leak_str = ", ".join(results["leaks"]).upper()
            print(colored(f"  ✗ LEAKS DETECTED: {leak_str}", C.RED + C.BOLD))
            print(colored(f"\n  💡 Fixes:", C.CYAN))
            if "dns" in results["leaks"]:
                print(f"  {C.DIM}├{C.RESET} Switch to VPN's DNS or use 1.1.1.1 / 8.8.8.8")
            if "ipv6" in results["leaks"]:
                print(f"  {C.DIM}├{C.RESET} Disable IPv6 or configure VPN to tunnel IPv6")
            if "webrtc" in results["leaks"]:
                print(f"  {C.DIM}├{C.RESET} Install a WebRTC blocker browser extension")
        print()

    if json_output:
        print(json_mod.dumps(results, indent=2))

    return 1 if results["leaks"] else 0
