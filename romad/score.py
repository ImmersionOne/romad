"""romad score — Nomad readiness score.

Runs all checks and produces a single readiness score:
speed + latency + VPN + DNS + leaks = green/yellow/red
"""

import json as json_mod
import sys
import time

from .utils import C, colored, get_public_ip, get_ip_info, detect_vpn, get_current_dns_servers


def _score_speed():
    """Run a quick speed test and score it."""
    from .speed import _download_test, _ping, DOWNLOAD_URLS, PING_HOSTS

    # Quick download test (10MB only)
    url, expected, label = DOWNLOAD_URLS[0]
    mbps, _, _ = _download_test(url, expected, label)

    # Quick ping
    ping_ms = None
    result = _ping(PING_HOSTS[0][0], count=3)
    if result:
        ping_ms = result[0]

    download_score = 0
    if mbps:
        if mbps >= 50:
            download_score = 100
        elif mbps >= 25:
            download_score = 80
        elif mbps >= 10:
            download_score = 60
        elif mbps >= 5:
            download_score = 40
        else:
            download_score = 20

    ping_score = 0
    if ping_ms:
        if ping_ms < 20:
            ping_score = 100
        elif ping_ms < 50:
            ping_score = 80
        elif ping_ms < 100:
            ping_score = 60
        elif ping_ms < 200:
            ping_score = 40
        else:
            ping_score = 20

    return {
        "download_mbps": round(mbps, 1) if mbps else None,
        "ping_ms": round(ping_ms, 1) if ping_ms else None,
        "download_score": download_score,
        "ping_score": ping_score,
        "combined": int((download_score * 0.7 + ping_score * 0.3)) if mbps else 0,
    }


def _score_vpn():
    """Score VPN status."""
    vpns = detect_vpn()
    ip = get_public_ip()
    ip_info = get_ip_info(ip) if ip else {}

    has_vpn = len(vpns) > 0

    return {
        "active": has_vpn,
        "ip": ip,
        "country": ip_info.get("country", "??"),
        "city": ip_info.get("city", ""),
        "org": ip_info.get("org", ""),
        "score": 100 if has_vpn else 30,
    }


def _score_dns():
    """Score DNS configuration."""
    from .utils import PUBLIC_DNS
    dns_servers = get_current_dns_servers()

    # Check if using known secure DNS
    secure_dns = ["1.1.1.1", "1.0.0.1", "8.8.8.8", "8.8.4.4", "9.9.9.9"]
    using_secure = any(s in secure_dns for s in dns_servers)

    # Check for ISP DNS (potential leak)
    has_isp_dns = False
    for server in dns_servers:
        if server not in PUBLIC_DNS:
            info = get_ip_info(server)
            org = (info.get("org", "") if info else "").lower()
            if not any(x in org for x in ["google", "cloudflare", "quad9", "opendns", "nextdns"]):
                has_isp_dns = True

    score = 100
    if not using_secure:
        score -= 30
    if has_isp_dns:
        score -= 40

    return {
        "servers": dns_servers,
        "using_secure_dns": using_secure,
        "has_isp_dns": has_isp_dns,
        "score": max(score, 0),
    }


def _score_privacy():
    """Score privacy posture."""
    from .leak import _check_ipv6_leak, _check_webrtc_candidates, _check_torrent_leak

    ipv6 = _check_ipv6_leak()
    webrtc = _check_webrtc_candidates()
    torrent = _check_torrent_leak()

    score = 100
    issues = []

    if ipv6.get("leak"):
        score -= 30
        issues.append("IPv6 leak")
    if webrtc.get("risk") == "high":
        score -= 25
        issues.append("WebRTC high risk")
    elif webrtc.get("risk") == "medium":
        score -= 10
    if torrent.get("clients_running"):
        score -= 15
        issues.append(f"Torrent client running: {', '.join(torrent['clients_running'])}")

    return {
        "ipv6_leak": ipv6.get("leak", False),
        "webrtc_risk": webrtc.get("risk", "unknown"),
        "torrent_risk": torrent.get("risk", "none"),
        "issues": issues,
        "score": max(score, 0),
    }


def _grade(score):
    """Convert score to letter grade."""
    if score >= 90:
        return "A", C.GREEN
    elif score >= 75:
        return "B", C.GREEN
    elif score >= 60:
        return "C", C.YELLOW
    elif score >= 40:
        return "D", C.RED
    else:
        return "F", C.RED


def _score_bar(score, width=20):
    """Visual score bar."""
    filled = int(score / 100 * width)
    bar = "█" * filled + "░" * (width - filled)
    if score >= 75:
        color = C.GREEN
    elif score >= 50:
        color = C.YELLOW
    else:
        color = C.RED
    return f"{color}{bar}{C.RESET} {score}/100"


def run(verbose=False, json_output=False):
    """Run nomad readiness score."""
    if not json_output:
        print(colored("\n  🏆 romad score — nomad readiness", C.BOLD))
        print(colored("  ─────────────────────────────────", C.DIM))
        print(colored(f"\n  Running checks...\n", C.DIM))

    # Run all checks
    if not json_output:
        sys.stdout.write(f"  {C.DIM}├{C.RESET} Speed test...     ")
        sys.stdout.flush()
    speed = _score_speed()
    if not json_output:
        dl = f"{speed['download_mbps']} Mbps" if speed['download_mbps'] else "failed"
        pg = f"{speed['ping_ms']}ms" if speed['ping_ms'] else "n/a"
        print(f"{dl} ↓  {pg} ping")

    if not json_output:
        sys.stdout.write(f"  {C.DIM}├{C.RESET} VPN check...      ")
        sys.stdout.flush()
    vpn = _score_vpn()
    if not json_output:
        status = colored("active", C.GREEN) if vpn["active"] else colored("none", C.RED)
        print(f"{status}  {vpn['city']}, {vpn['country']}")

    if not json_output:
        sys.stdout.write(f"  {C.DIM}├{C.RESET} DNS check...      ")
        sys.stdout.flush()
    dns = _score_dns()
    if not json_output:
        sec = colored("secure", C.GREEN) if dns["using_secure_dns"] else colored("insecure", C.YELLOW)
        print(f"{sec}")

    if not json_output:
        sys.stdout.write(f"  {C.DIM}├{C.RESET} Privacy check...  ")
        sys.stdout.flush()
    privacy = _score_privacy()
    if not json_output:
        if privacy["issues"]:
            print(colored(f"{len(privacy['issues'])} issue(s)", C.YELLOW))
        else:
            print(colored("clean", C.GREEN))

    # Calculate overall score (weighted)
    weights = {
        "speed": 0.20,
        "vpn": 0.30,
        "dns": 0.20,
        "privacy": 0.30,
    }

    overall = int(
        speed["combined"] * weights["speed"] +
        vpn["score"] * weights["vpn"] +
        dns["score"] * weights["dns"] +
        privacy["score"] * weights["privacy"]
    )

    grade, grade_color = _grade(overall)

    results = {
        "speed": speed,
        "vpn": vpn,
        "dns": dns,
        "privacy": privacy,
        "overall": {
            "score": overall,
            "grade": grade,
        }
    }

    if json_output:
        print(json_mod.dumps(results, indent=2))
    else:
        print(colored(f"\n  ─────────────────────────────────", C.DIM))
        print(colored(f"  Scorecard", C.BOLD))
        print(f"  {C.DIM}├{C.RESET} Speed     {_score_bar(speed['combined'])}")
        print(f"  {C.DIM}├{C.RESET} VPN       {_score_bar(vpn['score'])}")
        print(f"  {C.DIM}├{C.RESET} DNS       {_score_bar(dns['score'])}")
        print(f"  {C.DIM}├{C.RESET} Privacy   {_score_bar(privacy['score'])}")
        print(colored(f"  ─────────────────────────────────", C.DIM))
        print(f"  {C.DIM}└{C.RESET} Overall   {_score_bar(overall)}  {grade_color}{C.BOLD}{grade}{C.RESET}")

        if overall < 75:
            print(colored(f"\n  💡 Improve your score:", C.CYAN))
            if not vpn["active"]:
                print(f"  {C.DIM}├{C.RESET} Connect to a VPN (+30 pts)")
            if not dns["using_secure_dns"]:
                print(f"  {C.DIM}├{C.RESET} Switch to secure DNS (1.1.1.1 or 8.8.8.8) (+20 pts)")
            if speed["combined"] < 60:
                print(f"  {C.DIM}├{C.RESET} Find a faster connection (+20 pts)")
            for issue in privacy["issues"]:
                print(f"  {C.DIM}├{C.RESET} Fix: {issue}")
        print()

    return 0
