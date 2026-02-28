"""romad sync — Encrypted cross-machine note sync via GitHub."""

import json
import os
import subprocess
import sys
import time

from .utils import C, colored, print_banner

DEFAULT_REPO_NAME = "romad-sync"
SYNC_DIR_NAME = ".romad-sync"


def _get_sync_dir():
    return os.path.join(os.path.expanduser("~"), SYNC_DIR_NAME)


def _get_config_path():
    return os.path.join(_get_sync_dir(), ".sync-config.json")


def _load_config():
    cfg_path = _get_config_path()
    if os.path.exists(cfg_path):
        with open(cfg_path) as f:
            return json.load(f)
    return {}


def _save_config(cfg):
    cfg_path = _get_config_path()
    os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
    with open(cfg_path, "w") as f:
        json.dump(cfg, f, indent=2)


def _run_git(args, cwd=None, check=True):
    """Run a git command and return output."""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True, text=True, timeout=30,
        cwd=cwd or _get_sync_dir()
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result


def _ensure_repo(remote_url=None):
    """Ensure the sync directory and git repo exist."""
    sync_dir = _get_sync_dir()

    if not os.path.isdir(sync_dir):
        os.makedirs(sync_dir, exist_ok=True)

    git_dir = os.path.join(sync_dir, ".git")
    if not os.path.isdir(git_dir):
        if remote_url:
            print(colored("  Cloning remote repo...", C.CYAN))
            subprocess.run(
                ["git", "clone", remote_url, sync_dir],
                check=True, timeout=30
            )
        else:
            print(colored("  Initializing new sync repo...", C.CYAN))
            _run_git(["init"], cwd=sync_dir)
            # Create initial commit
            readme = os.path.join(sync_dir, "README.md")
            with open(readme, "w") as f:
                f.write("# romad-sync\n\nEncrypted cross-machine notes synced by romad.\n")
            _run_git(["add", "."])
            _run_git(["commit", "-m", "Initial commit"])


def init(remote_url=None):
    """Initialize the sync repo."""
    print_banner()
    print(colored("  ▸ Sync Init", C.BOLD))

    sync_dir = _get_sync_dir()

    if os.path.isdir(os.path.join(sync_dir, ".git")):
        print(colored(f"\n  ✓ Sync repo already exists at {sync_dir}", C.GREEN))
        cfg = _load_config()
        if cfg.get("remote"):
            print(f"  Remote: {cfg['remote']}")
        return 0

    _ensure_repo(remote_url)

    cfg = {"remote": remote_url or "", "created": time.strftime("%Y-%m-%dT%H:%M:%SZ")}
    _save_config(cfg)

    if remote_url:
        print(colored(f"\n  ✓ Sync repo cloned to {sync_dir}", C.GREEN))
    else:
        print(colored(f"\n  ✓ Sync repo created at {sync_dir}", C.GREEN))
        print(colored("  → Add a remote: romad sync remote <github-url>", C.YELLOW))

    print()
    return 0


def remote(url):
    """Set the remote URL for the sync repo."""
    sync_dir = _get_sync_dir()
    if not os.path.isdir(os.path.join(sync_dir, ".git")):
        print(colored("  ✗ No sync repo. Run 'romad sync init' first.", C.RED))
        return 1

    # Check if origin exists
    result = _run_git(["remote"], check=False)
    if "origin" in result.stdout:
        _run_git(["remote", "set-url", "origin", url])
    else:
        _run_git(["remote", "add", "origin", url])

    cfg = _load_config()
    cfg["remote"] = url
    _save_config(cfg)

    print(colored(f"  ✓ Remote set to {url}", C.GREEN))
    return 0


def push(message=None):
    """Stage, commit, and push all changes."""
    print(colored("\n▸ Pushing notes...", C.BOLD))

    sync_dir = _get_sync_dir()
    if not os.path.isdir(os.path.join(sync_dir, ".git")):
        print(colored("  ✗ No sync repo. Run 'romad sync init' first.", C.RED))
        return 1

    # Check for changes
    status = _run_git(["status", "--porcelain"])
    if not status.stdout.strip():
        print(colored("  ℹ Nothing to push — working tree clean.", C.DIM))
        return 0

    # Stage and commit
    _run_git(["add", "."])
    commit_msg = message or f"sync {time.strftime('%Y-%m-%d %H:%M')}"
    _run_git(["commit", "-m", commit_msg])

    # Push if remote exists
    result = _run_git(["remote"], check=False)
    if "origin" in result.stdout:
        print(colored("  Pushing to origin...", C.CYAN))
        push_result = _run_git(["push", "-u", "origin", "HEAD"], check=False)
        if push_result.returncode != 0:
            print(colored(f"  ⚠ Push failed: {push_result.stderr.strip()}", C.YELLOW))
            print(colored("  Changes are committed locally.", C.DIM))
            return 1
        print(colored("  ✓ Pushed successfully.", C.GREEN))
    else:
        print(colored("  ✓ Committed locally (no remote configured).", C.GREEN))
        print(colored("  → Add remote: romad sync remote <url>", C.YELLOW))

    print()
    return 0


def pull():
    """Pull latest from remote."""
    print(colored("\n▸ Pulling notes...", C.BOLD))

    sync_dir = _get_sync_dir()
    if not os.path.isdir(os.path.join(sync_dir, ".git")):
        print(colored("  ✗ No sync repo. Run 'romad sync init' first.", C.RED))
        return 1

    result = _run_git(["remote"], check=False)
    if "origin" not in result.stdout:
        print(colored("  ✗ No remote configured. Run 'romad sync remote <url>'.", C.RED))
        return 1

    pull_result = _run_git(["pull", "--rebase", "origin", "HEAD"], check=False)
    if pull_result.returncode != 0:
        print(colored(f"  ⚠ Pull failed: {pull_result.stderr.strip()}", C.YELLOW))
        return 1

    print(colored("  ✓ Pulled latest.", C.GREEN))
    print()
    return 0


def add_note(filepath):
    """Copy a file into the sync directory."""
    sync_dir = _get_sync_dir()
    if not os.path.isdir(os.path.join(sync_dir, ".git")):
        print(colored("  ✗ No sync repo. Run 'romad sync init' first.", C.RED))
        return 1

    if not os.path.exists(filepath):
        print(colored(f"  ✗ File not found: {filepath}", C.RED))
        return 1

    import shutil
    dest = os.path.join(sync_dir, os.path.basename(filepath))
    shutil.copy2(filepath, dest)
    print(colored(f"  ✓ Added {os.path.basename(filepath)} to sync folder.", C.GREEN))
    return 0


def ls():
    """List files in the sync directory."""
    sync_dir = _get_sync_dir()
    if not os.path.isdir(sync_dir):
        print(colored("  ✗ No sync repo. Run 'romad sync init' first.", C.RED))
        return 1

    print(colored("\n▸ Synced files:", C.BOLD))
    files = [f for f in os.listdir(sync_dir) if not f.startswith(".")]
    if not files:
        print(colored("  (empty)", C.DIM))
    else:
        for f in sorted(files):
            fpath = os.path.join(sync_dir, f)
            size = os.path.getsize(fpath)
            if size < 1024:
                size_str = f"{size}B"
            else:
                size_str = f"{size // 1024}KB"
            print(f"  • {f} ({size_str})")

    print()
    return 0


def status():
    """Show sync status."""
    print_banner()
    print(colored("  ▸ Sync Status", C.BOLD))

    sync_dir = _get_sync_dir()

    if not os.path.isdir(os.path.join(sync_dir, ".git")):
        print(colored("\n  ✗ Not initialized. Run 'romad sync init'.", C.RED))
        print()
        return 1

    cfg = _load_config()

    print(colored("\n▸ Repo", C.BOLD))
    print(f"  Path: {sync_dir}")
    print(f"  Remote: {cfg.get('remote') or '(none)'}")

    # File count
    files = [f for f in os.listdir(sync_dir) if not f.startswith(".")]
    print(f"  Files: {len(files)}")

    # Git status
    git_status = _run_git(["status", "--porcelain"], check=False)
    changes = len([l for l in git_status.stdout.strip().split("\n") if l.strip()])
    if changes:
        print(colored(f"  Uncommitted changes: {changes}", C.YELLOW))
    else:
        print(colored("  Working tree clean", C.GREEN))

    # Last commit
    log = _run_git(["log", "--oneline", "-1"], check=False)
    if log.stdout.strip():
        print(f"  Last commit: {log.stdout.strip()}")

    print()
    return 0
