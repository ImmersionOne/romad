"""romad — CLI entry point."""

import argparse
import sys

from . import __version__


def main():
    parser = argparse.ArgumentParser(
        prog="romad",
        description="romad — Travel networking toolkit for digital nomads",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  dns          Run DNS leak detection test
  vpn          Run VPN health check
  speed        Internet speed test
  status       Quick overview (dns + vpn combined)
  watch        Continuous VPN/DNS monitoring
  audit        Full security posture check
  sync         Cross-machine note sync via GitHub

Examples:
  romad dns                  Check for DNS leaks
  romad vpn --expect US      Verify VPN exit is in US
  romad speed                Run internet speed test
  romad speed --quick        Fast speed test (smaller payloads)
  romad speed --json         JSON output
  romad status               Full status check
  romad watch                Monitor VPN/DNS continuously
  romad watch -i 30          Check every 30 seconds
  romad audit                Pre-work security posture check
  romad sync init            Initialize sync repo
  romad sync push            Push notes to GitHub
  romad sync pull            Pull notes from GitHub
        """,
    )

    parser.add_argument(
        "--version", action="version", version=f"romad {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # dns subcommand
    dns_parser = subparsers.add_parser("dns", help="DNS leak detection")
    dns_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    dns_parser.add_argument("--json", action="store_true", help="JSON output")

    # speed subcommand
    speed_parser = subparsers.add_parser("speed", help="Internet speed test")
    speed_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    speed_parser.add_argument("--json", action="store_true", help="JSON output")
    speed_parser.add_argument("--quick", action="store_true", help="Quick test (smaller payloads)")

    # vpn subcommand
    vpn_parser = subparsers.add_parser("vpn", help="VPN health check")
    vpn_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    vpn_parser.add_argument(
        "--expect", metavar="COUNTRY",
        help="Expected exit country code (e.g. US, DE, JP)"
    )

    # status subcommand
    status_parser = subparsers.add_parser("status", help="Full status check (dns + vpn)")
    status_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    status_parser.add_argument(
        "--expect", metavar="COUNTRY",
        help="Expected exit country code"
    )

    # watch subcommand
    watch_parser = subparsers.add_parser("watch", help="Continuous VPN/DNS monitoring")
    watch_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    watch_parser.add_argument(
        "-i", "--interval", type=int, default=60,
        help="Check interval in seconds (default: 60)"
    )

    # audit subcommand
    audit_parser = subparsers.add_parser("audit", help="Full security posture check")
    audit_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    # sync subcommand
    sync_parser = subparsers.add_parser("sync", help="Cross-machine note sync")
    sync_sub = sync_parser.add_subparsers(dest="sync_command", help="Sync command")

    sync_sub.add_parser("init", help="Initialize sync repo")
    sync_sub.add_parser("status", help="Show sync status")
    sync_sub.add_parser("push", help="Push notes to remote")
    sync_sub.add_parser("pull", help="Pull notes from remote")
    sync_sub.add_parser("ls", help="List synced files")

    remote_parser = sync_sub.add_parser("remote", help="Set remote URL")
    remote_parser.add_argument("url", help="GitHub repo URL")

    add_parser = sync_sub.add_parser("add", help="Add a file to sync")
    add_parser.add_argument("file", help="File path to add")

    args = parser.parse_args()

    if not args.command:
        from .utils import print_banner
        print_banner()
        parser.print_help()
        sys.exit(0)

    if args.command == "speed":
        from .speed import run
        sys.exit(run(verbose=args.verbose, json_output=args.json, quick=args.quick))

    elif args.command == "dns":
        from .dns import run
        sys.exit(run(verbose=args.verbose, json_output=args.json))

    elif args.command == "vpn":
        from .vpn import run
        sys.exit(run(expected_country=args.expect, verbose=args.verbose))

    elif args.command == "status":
        from .dns import run as dns_run
        from .vpn import run as vpn_run
        dns_code = dns_run(verbose=args.verbose)
        vpn_code = vpn_run(expected_country=getattr(args, "expect", None), verbose=args.verbose)
        sys.exit(max(dns_code, vpn_code))

    elif args.command == "watch":
        from .watch import run
        sys.exit(run(interval=args.interval, verbose=args.verbose))

    elif args.command == "audit":
        from .audit import run
        sys.exit(run(verbose=args.verbose))

    elif args.command == "sync":
        from . import sync as sync_mod
        sc = args.sync_command

        if not sc or sc == "status":
            sys.exit(sync_mod.status())
        elif sc == "init":
            sys.exit(sync_mod.init())
        elif sc == "remote":
            sys.exit(sync_mod.remote(args.url))
        elif sc == "push":
            sys.exit(sync_mod.push())
        elif sc == "pull":
            sys.exit(sync_mod.pull())
        elif sc == "ls":
            sys.exit(sync_mod.ls())
        elif sc == "add":
            sys.exit(sync_mod.add_note(args.file))
        else:
            sync_parser.print_help()
            sys.exit(0)


if __name__ == "__main__":
    main()
