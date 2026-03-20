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
  portal       Captive portal detection
  locate       Location consistency check
  leak         Full privacy leak check (DNS + IPv6 + WebRTC)
  score        Nomad readiness score
  compare      Save & compare locations over time
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
  romad portal               Detect captive portals
  romad locate               Check location consistency
  romad leak                 Full privacy leak check
  romad score                Get your nomad readiness score
  romad compare              Compare saved locations
  romad compare save "Cafe"  Save current location
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

    # portal subcommand
    portal_parser = subparsers.add_parser("portal", help="Captive portal detection")
    portal_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    portal_parser.add_argument("--json", action="store_true", help="JSON output")
    portal_parser.add_argument("--no-open", action="store_true", help="Don't auto-open portal in browser")

    # locate subcommand
    locate_parser = subparsers.add_parser("locate", help="Location consistency check")
    locate_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    locate_parser.add_argument("--json", action="store_true", help="JSON output")

    # leak subcommand
    leak_parser = subparsers.add_parser("leak", help="Full privacy leak check")
    leak_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    leak_parser.add_argument("--json", action="store_true", help="JSON output")

    # score subcommand
    score_parser = subparsers.add_parser("score", help="Nomad readiness score")
    score_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    score_parser.add_argument("--json", action="store_true", help="JSON output")

    # compare subcommand
    compare_parser = subparsers.add_parser("compare", help="Save & compare locations")
    compare_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    compare_parser.add_argument("--json", action="store_true", help="JSON output")
    compare_sub = compare_parser.add_subparsers(dest="compare_command", help="Compare command")
    compare_save = compare_sub.add_parser("save", help="Save current location")
    compare_save.add_argument("name", help="Location name (e.g. 'WeWork SoHo')")
    compare_sub.add_parser("show", help="Show comparison (default)")
    compare_sub.add_parser("clear", help="Clear all saved locations")

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

    if args.command == "portal":
        from .portal import run
        sys.exit(run(verbose=args.verbose, json_output=args.json, auto_open=not args.no_open))

    elif args.command == "locate":
        from .locate import run
        sys.exit(run(verbose=args.verbose, json_output=args.json))

    elif args.command == "leak":
        from .leak import run
        sys.exit(run(verbose=args.verbose, json_output=args.json))

    elif args.command == "score":
        from .score import run
        sys.exit(run(verbose=args.verbose, json_output=args.json))

    elif args.command == "compare":
        from .compare import run
        action = args.compare_command or "show"
        name = getattr(args, "name", None)
        sys.exit(run(action=action, name=name, verbose=args.verbose, json_output=args.json))

    elif args.command == "speed":
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
