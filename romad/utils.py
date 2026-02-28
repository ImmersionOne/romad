"""Shared utilities for romad."""

import json
import subprocess
import sys


class C:
    """Terminal colors."""
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def print_banner():
    """Print the romad ASCII banner."""
    colors = [C.CYAN, C.BLUE, C.MAGENTA, C.RED, C.YELLOW, C.GREEN]
    lines = [
        r"                                  __  ",
        r"   _________  ____ ___  ____ ____/ /  ",
        r"  / ___/ __ \/ __ `__ \/ __ `/ __  /  ",
        r" / /  / /_/ / / / / / / /_/ / /_/ /   ",
        r"/_/   \____/_/ /_/ /_/\__,_/\__,_/    ",
        r"                                       ",
    ]
    print()
    for i, line in enumerate(lines):
        print(f"  {colors[i % len(colors)]}{line}{C.RESET}")
    print(f"  {C.DIM}v{_get_version()} — travel networking toolkit{C.RESET}")
    print()


def _get_version():
    try:
        from . import __version__
        return __version__
    except Exception:
        return "?"


def colored(text, color):
    return f"{color}{text}{C.RESET}"


# Well-known public DNS servers
PUBLIC_DNS = {
    "8.8.8.8": "Google DNS",
    "8.8.4.4": "Google DNS (secondary)",
    "1.1.1.1": "Cloudflare DNS",
    "1.0.0.1": "Cloudflare DNS (secondary)",
    "9.9.9.9": "Quad9 DNS",
    "208.67.222.222": "OpenDNS",
    "208.67.220.220": "OpenDNS (secondary)",
}


def get_public_ip():
    """Get the current public IP address."""
    services = [
        "https://api.ipify.org",
        "https://ifconfig.me/ip",
        "https://icanhazip.com",
    ]
    for url in services:
        try:
            out = subprocess.run(
                ["curl", "-s", "-m", "5", url],
                capture_output=True, text=True, timeout=8
            )
            ip = out.stdout.strip()
            if ip and len(ip) < 50:
                return ip
        except Exception:
            continue
    return None


def get_ip_info(ip):
    """Get geolocation info for an IP."""
    try:
        out = subprocess.run(
            ["curl", "-s", "-m", "5", f"https://ipinfo.io/{ip}/json"],
            capture_output=True, text=True, timeout=8
        )
        return json.loads(out.stdout)
    except Exception:
        return {}


def get_current_dns_servers():
    """Get the DNS servers currently configured on the system."""
    servers = []
    try:
        if sys.platform == "darwin":
            out = subprocess.run(
                ["/usr/sbin/scutil", "--dns"], capture_output=True, text=True, timeout=5
            )
            for line in out.stdout.splitlines():
                line = line.strip()
                if line.startswith("nameserver["):
                    ip = line.split(":", 1)[-1].strip()
                    if ip and ("." in ip or ":" in ip) and ip not in servers:
                        servers.append(ip)
        else:
            with open("/etc/resolv.conf") as f:
                for line in f:
                    if line.strip().startswith("nameserver"):
                        ip = line.strip().split()[1]
                        if ip not in servers:
                            servers.append(ip)
    except Exception as e:
        print(colored(f"  ⚠ Could not read system DNS: {e}", C.YELLOW))
    return servers


def resolve_with_server(domain, dns_server, timeout=5):
    """Resolve a domain using a specific DNS server via dig."""
    try:
        out = subprocess.run(
            ["dig", f"@{dns_server}", domain, "+short", "+time=3", "+tries=1"],
            capture_output=True, text=True, timeout=timeout
        )
        lines = [l.strip() for l in out.stdout.strip().split("\n") if l.strip() and not l.startswith(";")]
        return lines[0] if lines else None
    except Exception:
        return None


def detect_vpn():
    """Detect if a VPN tunnel is active."""
    vpns = []
    try:
        ifconfig_path = "/sbin/ifconfig" if sys.platform == "darwin" else "ifconfig"
        out = subprocess.run(
            [ifconfig_path], capture_output=True, text=True, timeout=5
        )
        interfaces = out.stdout

        # WireGuard
        wg_check = subprocess.run(
            ["which", "wg"], capture_output=True, text=True, timeout=3
        )
        if wg_check.returncode == 0:
            wg_show = subprocess.run(
                ["wg", "show"], capture_output=True, text=True, timeout=5
            )
            if wg_show.stdout.strip():
                for line in wg_show.stdout.strip().split("\n"):
                    if line.startswith("interface:"):
                        iface = line.split(":")[1].strip()
                        vpns.append(("WireGuard", iface))

        # OpenVPN
        ovpn_check = subprocess.run(
            ["pgrep", "-x", "openvpn"], capture_output=True, text=True, timeout=3
        )
        if ovpn_check.stdout.strip():
            vpns.append(("OpenVPN", f"PID {ovpn_check.stdout.strip()}"))

        # Generic tun/tap (not macOS utun)
        for line in interfaces.split("\n"):
            if "flags=" in line:
                iface_name = line.split(":")[0].strip()
                if iface_name.startswith(("tun", "tap")) and not iface_name.startswith("utun"):
                    if not any(iface_name in v[1] for v in vpns):
                        vpns.append(("VPN Tunnel", iface_name))

    except Exception as e:
        print(colored(f"  ⚠ VPN detection error: {e}", C.YELLOW))

    return vpns
