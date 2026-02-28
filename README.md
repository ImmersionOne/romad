# romad 🌍

**Travel networking toolkit for digital nomads.**

DNS leak detection, VPN health checks, and network security tools for people who work from everywhere.

## Install

```bash
pip install -e .
```

## Usage

```bash
# DNS leak detection
romad dns
romad dns -v              # verbose (lookup DNS server owners)

# VPN health check
romad vpn
romad vpn --expect US     # verify VPN exit is in expected country

# Full status (dns + vpn combined)
romad status
romad status --expect JP
```

## Features

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
- IP geolocation verification (are you appearing where you should?)
- Connectivity tests through the tunnel

### `romad status` — Full Check
Runs both `dns` and `vpn` checks in sequence.

## Requirements

- Python 3.8+
- `dig` (macOS built-in, `dnsutils` on Linux)
- `curl`
- `ping`

## Roadmap

- [ ] `romad sync` — Encrypted note sync between machines
- [ ] `romad speed` — Speed test from current location
- [ ] `romad portal` — Captive portal detection
- [ ] `romad scan` — Port scan your own setup
- [ ] `--json` output for all commands
- [ ] `--watch` continuous monitoring mode
- [ ] Travel profile presets

## License

MIT
