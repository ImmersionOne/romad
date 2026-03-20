"""romad portal — Captive portal detection and auto-open."""

import json as json_mod
import subprocess
import sys
import re

from .utils import C, colored


# Detection endpoints — these return known responses when internet is free
DETECTION_ENDPOINTS = [
    {
        "name": "Apple",
        "url": "http://captive.apple.com/hotspot-detect.html",
        "expect": "<HTML><HEAD><TITLE>Success</TITLE></HEAD><BODY>Success</BODY></HTML>",
    },
    {
        "name": "Google",
        "url": "http://connectivitycheck.goog/generate_204",
        "expect_code": 204,
    },
    {
        "name": "Microsoft",
        "url": "http://www.msftconnecttest.com/connecttest.txt",
        "expect": "Microsoft Connect Test",
    },
    {
        "name": "Firefox",
        "url": "http://detectportal.firefox.com/success.txt",
        "expect": "success",
    },
]


def _check_endpoint(ep, verbose=False):
    """Check a single detection endpoint. Returns dict with result."""
    try:
        cmd = [
            "curl", "-s", "-L",
            "-m", "10",
            "-w", "\n%{http_code}\n%{redirect_url}\n%{url_effective}",
            "-o", "-",
            ep["url"]
        ]
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        parts = out.stdout.rsplit("\n", 3)

        if len(parts) >= 4:
            body = parts[0]
            http_code = int(parts[1]) if parts[1].strip().isdigit() else 0
            redirect_url = parts[2].strip()
            effective_url = parts[3].strip()
        else:
            body = out.stdout
            http_code = 0
            redirect_url = ""
            effective_url = ""

        result = {
            "name": ep["name"],
            "url": ep["url"],
            "http_code": http_code,
            "redirect_url": redirect_url,
            "effective_url": effective_url,
            "captive": False,
            "portal_url": None,
        }

        # Check if we got the expected response
        if "expect" in ep:
            if ep["expect"].strip().lower() in body.strip().lower():
                result["status"] = "free"
            else:
                result["captive"] = True
                result["status"] = "captive"
                # Try to extract portal URL
                if redirect_url and redirect_url != ep["url"]:
                    result["portal_url"] = redirect_url
                elif effective_url and effective_url != ep["url"]:
                    result["portal_url"] = effective_url
                else:
                    # Look for redirect in body
                    match = re.search(r'(https?://[^\s"\'<>]+)', body)
                    if match:
                        result["portal_url"] = match.group(1)

        elif "expect_code" in ep:
            if http_code == ep["expect_code"]:
                result["status"] = "free"
            else:
                result["captive"] = True
                result["status"] = "captive"
                if redirect_url:
                    result["portal_url"] = redirect_url
                elif effective_url and effective_url != ep["url"]:
                    result["portal_url"] = effective_url

        return result

    except Exception as e:
        return {
            "name": ep["name"],
            "url": ep["url"],
            "status": "error",
            "error": str(e),
            "captive": False,
            "portal_url": None,
        }


def _get_network_info():
    """Get current network name and type."""
    info = {"ssid": None, "interface": None, "type": None}
    try:
        if sys.platform == "darwin":
            # Try networksetup for WiFi SSID
            out = subprocess.run(
                ["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-I"],
                capture_output=True, text=True, timeout=5
            )
            for line in out.stdout.splitlines():
                line = line.strip()
                if line.startswith("SSID:"):
                    info["ssid"] = line.split(":", 1)[1].strip()
                    info["type"] = "wifi"

            if not info["ssid"]:
                # Try system_profiler
                out2 = subprocess.run(
                    ["networksetup", "-getairportnetwork", "en0"],
                    capture_output=True, text=True, timeout=5
                )
                if "Current Wi-Fi Network:" in out2.stdout:
                    info["ssid"] = out2.stdout.split(":", 1)[1].strip()
                    info["type"] = "wifi"
        else:
            # Linux
            out = subprocess.run(
                ["iwgetid", "-r"], capture_output=True, text=True, timeout=5
            )
            if out.stdout.strip():
                info["ssid"] = out.stdout.strip()
                info["type"] = "wifi"

        if not info["type"]:
            info["type"] = "wired/other"

    except Exception:
        pass
    return info


def _open_portal(url):
    """Open the portal URL in the default browser."""
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", url], timeout=5)
        else:
            subprocess.run(["xdg-open", url], timeout=5)
        return True
    except Exception:
        return False


def run(verbose=False, json_output=False, auto_open=True):
    """Run captive portal detection."""
    results = {
        "network": {},
        "checks": [],
        "captive": False,
        "portal_url": None,
    }

    if not json_output:
        print(colored("\n  🌐 romad portal — captive portal detection", C.BOLD))
        print(colored("  ─────────────────────────────────────────", C.DIM))

    # Network info
    net_info = _get_network_info()
    results["network"] = net_info

    if not json_output:
        if net_info["ssid"]:
            print(f"\n  {C.DIM}├{C.RESET} Network   {colored(net_info['ssid'], C.CYAN)} ({net_info['type']})")
        else:
            print(f"\n  {C.DIM}├{C.RESET} Network   {colored(net_info.get('type', 'unknown'), C.CYAN)}")

    # Check each endpoint
    if not json_output:
        print(colored(f"\n  📡 Checking endpoints...", C.CYAN))

    captive_count = 0
    portal_url = None

    for ep in DETECTION_ENDPOINTS:
        result = _check_endpoint(ep, verbose)
        results["checks"].append(result)

        if result.get("captive"):
            captive_count += 1
            if result.get("portal_url") and not portal_url:
                portal_url = result["portal_url"]

        if not json_output:
            if result.get("status") == "free":
                print(f"  {C.DIM}├{C.RESET} {result['name']:<12} {colored('✓ free', C.GREEN)}")
            elif result.get("status") == "captive":
                url_info = f"  → {result['portal_url']}" if result.get("portal_url") else ""
                print(f"  {C.DIM}├{C.RESET} {result['name']:<12} {colored('✗ captive portal detected', C.RED)}{url_info}")
            else:
                err = f"  ({result.get('error', 'unknown')})" if verbose else ""
                print(f"  {C.DIM}├{C.RESET} {result['name']:<12} {colored('⚠ error', C.YELLOW)}{err}")

    # Verdict
    is_captive = captive_count >= 2  # majority vote
    results["captive"] = is_captive
    results["portal_url"] = portal_url

    if not json_output:
        print(colored(f"\n  ─────────────────────────────────────────", C.DIM))
        if is_captive:
            print(colored(f"  ⚠ CAPTIVE PORTAL DETECTED", C.RED + C.BOLD))
            if portal_url:
                print(f"  {C.DIM}└{C.RESET} Portal: {colored(portal_url, C.CYAN)}")
                if auto_open:
                    print(f"\n  {C.DIM}Opening portal in browser...{C.RESET}")
                    if _open_portal(portal_url):
                        print(colored(f"  ✓ Opened in browser", C.GREEN))
                    else:
                        print(colored(f"  ✗ Could not open browser", C.RED))
            else:
                print(f"  {C.DIM}└{C.RESET} Could not determine portal URL")
                print(f"  {C.DIM}  Try opening any HTTP site in your browser{C.RESET}")
        else:
            print(colored(f"  ✓ NO CAPTIVE PORTAL — internet is free", C.GREEN + C.BOLD))
        print()

    if json_output:
        print(json_mod.dumps(results, indent=2))

    return 1 if is_captive else 0
