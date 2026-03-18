"""romad speed — Internet speed test (zero dependencies)."""

import json as json_mod
import time
import subprocess
import sys
import threading

from .utils import C, colored


# Cloudflare speed test endpoints (reliable, global CDN)
DOWNLOAD_URLS = [
    ("https://speed.cloudflare.com/__down?bytes=10000000", 10_000_000, "10MB"),
    ("https://speed.cloudflare.com/__down?bytes=25000000", 25_000_000, "25MB"),
    ("https://speed.cloudflare.com/__down?bytes=50000000", 50_000_000, "50MB"),
]

UPLOAD_URL = "https://speed.cloudflare.com/__up"

PING_HOSTS = [
    ("1.1.1.1", "Cloudflare"),
    ("8.8.8.8", "Google"),
    ("speed.cloudflare.com", "Cloudflare CDN"),
]


def _ping(host, count=5):
    """Ping a host and return (avg_ms, min_ms, max_ms, jitter_ms) or None."""
    try:
        out = subprocess.run(
            ["ping", "-c", str(count), "-W", "3", host],
            capture_output=True, text=True, timeout=count * 4
        )
        for line in out.stdout.splitlines():
            # macOS/Linux: round-trip min/avg/max/stddev = 1.234/5.678/9.012/1.234 ms
            if "min/avg/max" in line:
                parts = line.split("=")[-1].strip().split("/")
                mn, avg, mx, jitter = [float(x.replace("ms", "").strip()) for x in parts[:4]]
                return avg, mn, mx, jitter
    except Exception:
        pass
    return None


def _download_test(url, expected_bytes, label, verbose=False):
    """Download a file and return speed in Mbps."""
    try:
        start = time.monotonic()
        out = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{size_download} %{time_total}",
             "-m", "30", url],
            capture_output=True, text=True, timeout=35
        )
        elapsed = time.monotonic() - start
        parts = out.stdout.strip().split()
        if len(parts) >= 2:
            downloaded = float(parts[0])
            curl_time = float(parts[1])
            if curl_time > 0 and downloaded > 0:
                mbps = (downloaded * 8) / (curl_time * 1_000_000)
                return mbps, downloaded, curl_time
    except Exception as e:
        if verbose:
            print(colored(f"  ⚠ Download test failed ({label}): {e}", C.YELLOW))
    return None, 0, 0


def _upload_test(size_bytes=2_000_000, verbose=False):
    """Upload random data and return speed in Mbps."""
    try:
        # Generate random-ish data via /dev/urandom
        start = time.monotonic()
        out = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{size_upload} %{time_total}",
             "-X", "POST", "--data-binary", f"@/dev/urandom",
             "-H", "Content-Type: application/octet-stream",
             "-m", "30", "--limit-rate", "0",
             f"--max-filesize", str(size_bytes),
             UPLOAD_URL],
            capture_output=True, text=True, timeout=35,
            input=None
        )
        # Alternative: use dd to pipe exact bytes
        proc = subprocess.run(
            f'dd if=/dev/urandom bs={size_bytes} count=1 2>/dev/null | '
            f'curl -s -o /dev/null -w "%{{size_upload}} %{{time_total}}" '
            f'-X POST --data-binary @- '
            f'-H "Content-Type: application/octet-stream" '
            f'-m 30 {UPLOAD_URL}',
            shell=True, capture_output=True, text=True, timeout=35
        )
        parts = proc.stdout.strip().split()
        if len(parts) >= 2:
            uploaded = float(parts[0])
            curl_time = float(parts[1])
            if curl_time > 0 and uploaded > 0:
                mbps = (uploaded * 8) / (curl_time * 1_000_000)
                return mbps, uploaded, curl_time
    except Exception as e:
        if verbose:
            print(colored(f"  ⚠ Upload test failed: {e}", C.YELLOW))
    return None, 0, 0


def _progress_char():
    """Simple progress indicator characters."""
    chars = "▏▎▍▌▋▊▉█"
    return chars


def _format_speed(mbps):
    """Format speed nicely."""
    if mbps is None:
        return "failed"
    if mbps >= 1000:
        return f"{mbps / 1000:.2f} Gbps"
    elif mbps >= 100:
        return f"{mbps:.0f} Mbps"
    elif mbps >= 10:
        return f"{mbps:.1f} Mbps"
    else:
        return f"{mbps:.2f} Mbps"


def _speed_bar(mbps, max_mbps=500, width=20):
    """Create a visual speed bar."""
    if mbps is None:
        return colored("  ✗ failed", C.RED)
    ratio = min(mbps / max_mbps, 1.0)
    filled = int(ratio * width)
    bar = "█" * filled + "░" * (width - filled)

    if mbps >= 100:
        color = C.GREEN
    elif mbps >= 25:
        color = C.YELLOW
    else:
        color = C.RED

    return f"{color}{bar}{C.RESET} {_format_speed(mbps)}"


def run(verbose=False, json_output=False, quick=False):
    """Run the speed test."""
    results = {
        "ping": {},
        "download": {},
        "upload": {},
    }

    if not json_output:
        print(colored("\n  ⚡ romad speed test", C.BOLD))
        print(colored("  ─────────────────────────────────", C.DIM))

    # --- Ping ---
    if not json_output:
        print(colored("\n  📡 Latency", C.CYAN))

    for host, name in PING_HOSTS:
        result = _ping(host, count=5 if not quick else 3)
        if result:
            avg, mn, mx, jitter = result
            results["ping"][name] = {
                "host": host,
                "avg_ms": round(avg, 2),
                "min_ms": round(mn, 2),
                "max_ms": round(mx, 2),
                "jitter_ms": round(jitter, 2),
            }
            if not json_output:
                color = C.GREEN if avg < 20 else C.YELLOW if avg < 50 else C.RED
                print(f"  {C.DIM}├{C.RESET} {name:<16} {color}{avg:.1f}ms{C.RESET}"
                      f"  {C.DIM}(min {mn:.1f} / max {mx:.1f} / jitter {jitter:.1f}){C.RESET}")
        else:
            results["ping"][name] = None
            if not json_output:
                print(f"  {C.DIM}├{C.RESET} {name:<16} {colored('timeout', C.RED)}")

    # --- Download ---
    if not json_output:
        print(colored("\n  ⬇ Download", C.CYAN))

    # Use progressive sizes — start small, go bigger if fast
    best_download = None
    for url, expected, label in DOWNLOAD_URLS:
        if not json_output:
            sys.stdout.write(f"  {C.DIM}├{C.RESET} {label:<8} ")
            sys.stdout.flush()

        mbps, downloaded, elapsed = _download_test(url, expected, label, verbose)

        if mbps is not None:
            results["download"][label] = {
                "mbps": round(mbps, 2),
                "bytes": downloaded,
                "seconds": round(elapsed, 2),
            }
            best_download = max(best_download or 0, mbps)

            if not json_output:
                print(_speed_bar(mbps))

            # Skip larger tests if connection is slow
            if quick or (mbps < 10 and label == "10MB"):
                break
        else:
            results["download"][label] = None
            if not json_output:
                print(colored("failed", C.RED))
            break

    # --- Upload ---
    if not json_output:
        print(colored("\n  ⬆ Upload", C.CYAN))
        sys.stdout.write(f"  {C.DIM}├{C.RESET} 2MB     ")
        sys.stdout.flush()

    upload_mbps, uploaded, elapsed = _upload_test(2_000_000, verbose)
    if upload_mbps is not None:
        results["upload"]["2MB"] = {
            "mbps": round(upload_mbps, 2),
            "bytes": uploaded,
            "seconds": round(elapsed, 2),
        }
        if not json_output:
            print(_speed_bar(upload_mbps))

        # Try larger upload if fast
        if upload_mbps > 20 and not quick:
            if not json_output:
                sys.stdout.write(f"  {C.DIM}├{C.RESET} 10MB    ")
                sys.stdout.flush()
            upload_mbps2, uploaded2, elapsed2 = _upload_test(10_000_000, verbose)
            if upload_mbps2:
                results["upload"]["10MB"] = {
                    "mbps": round(upload_mbps2, 2),
                    "bytes": uploaded2,
                    "seconds": round(elapsed2, 2),
                }
                if not json_output:
                    print(_speed_bar(upload_mbps2))
    else:
        results["upload"]["2MB"] = None
        if not json_output:
            print(colored("failed", C.RED))

    # --- Summary ---
    best_ping = None
    for name, data in results["ping"].items():
        if data and (best_ping is None or data["avg_ms"] < best_ping):
            best_ping = data["avg_ms"]

    best_up = None
    for label, data in results["upload"].items():
        if data and (best_up is None or data["mbps"] > best_up):
            best_up = data["mbps"]

    results["summary"] = {
        "download_mbps": round(best_download, 2) if best_download else None,
        "upload_mbps": round(best_up, 2) if best_up else None,
        "ping_ms": round(best_ping, 2) if best_ping else None,
    }

    if json_output:
        print(json_mod.dumps(results, indent=2))
    else:
        print(colored("\n  ─────────────────────────────────", C.DIM))
        print(colored("  Summary", C.BOLD))
        dl = _format_speed(best_download) if best_download else "n/a"
        ul = _format_speed(best_up) if best_up else "n/a"
        pg = f"{best_ping:.1f}ms" if best_ping else "n/a"
        print(f"  {C.DIM}├{C.RESET} Download  {colored(dl, C.GREEN if best_download and best_download >= 50 else C.YELLOW)}")
        print(f"  {C.DIM}├{C.RESET} Upload    {colored(ul, C.GREEN if best_up and best_up >= 20 else C.YELLOW)}")
        print(f"  {C.DIM}└{C.RESET} Ping      {colored(pg, C.GREEN if best_ping and best_ping < 20 else C.YELLOW)}")
        print()

    return 0
