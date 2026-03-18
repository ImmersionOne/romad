# romad 🌍

**Travel networking toolkit for digital nomads.**

DNS leak detection, VPN health checks, speed tests, and network security tools for people who work from everywhere.

## Install

### Homebrew (macOS)

```bash
brew tap ImmersionOne/romad
brew install romad
```

### pip

```bash
pip install -e .
```

## Usage

```bash
# Internet speed test
romad speed
romad speed --quick        # faster test, smaller payloads
romad speed --json         # JSON output

# DNS leak detection
romad dns
romad dns -v               # verbose
romad dns --json           # JSON output

# VPN health check
romad vpn
romad vpn --expect US      # verify VPN exit is in expected country

# Full status (dns + vpn combined)
romad status
romad status --expect JP

# Continuous monitoring
romad watch
romad watch -i 30          # check every 30 seconds

# Security posture audit
romad audit
```

## Features

### `romad speed` — Internet Speed Test
- Download speed (progressive: 10MB → 25MB → 50MB)
- Upload speed test
- Latency & jitter to Cloudflare, Google, Quad9
- Visual speed bars + summary
- Zero dependencies — uses Cloudflare's speed test CDN

### `romad dns` — DNS Leak Detection
- Detects active VPN tunnels (WireGuard, OpenVPN)
- Shows public IP + geolocation
- Lists system DNS servers
- Runs external DNS leak tests (Akamai, Google, OpenDNS)
- DNS resolution consistency check
- Clear pass/fail verdict

### `romad vpn` — VPN Health Check
- VPN tunnel detection
- Tunnel latency testing (Cloudflare, Google, Quad9)
- WireGuard handshake freshness monitoring
- IP geolocation verification
- Connectivity tests through the tunnel

### `romad status` — Full Check
Runs both `dns` and `vpn` checks in sequence.

### `romad watch` — Continuous Monitoring
Monitors VPN/DNS status on an interval.

### `romad audit` — Security Posture Check
Full security audit of your network setup.

## Requirements

- Python 3.8+
- `curl` (macOS/Linux built-in)
- `dig` (macOS built-in, `dnsutils` on Linux)
- `ping`

## Roadmap

- [x] `romad speed` — Speed test from current location
- [x] `--json` output for commands
- [x] `--watch` continuous monitoring mode
- [ ] `romad sync` — Encrypted note sync between machines
- [ ] `romad portal` — Captive portal detection
- [ ] `romad scan` — Port scan your own setup
- [ ] Travel profile presets

## License

MIT
