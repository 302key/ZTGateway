#!/usr/bin/env python3
# trash_collector.py — Age-based file cleanup utility
#
# Design principles:
#   - Only sweeps known directories with explicit glob patterns (no blind rmtree)
#   - Never touches active files (blackboard state) or lock files
#   - Supports dry-run inspection and archive-instead-of-delete mode

import os
import time
import argparse
import fnmatch
import shutil

# ==========================================
# Configuration
# ==========================================
BASE_DIR = os.getenv("ZT_BASE_DIR", os.path.expanduser("~/tmp/ZT"))

# Sweep zones: (directory, glob pattern, TTL in days, prune matching dirs too)
SWEEP_ZONES = [
    (os.path.join(BASE_DIR, "blackboard"),               "*.md",            30, False),  # task drafts
    (os.path.join(BASE_DIR, "buffer_memory"),            "snapshot_*.json", 30, False),  # full-state snapshots
    (os.path.join(BASE_DIR, "buffer_memory"),            "*_suspend.json",  30, False),  # suspended-task remains
    (os.path.join(BASE_DIR, "router", "briefing_cache"), "*.md",            30, False),  # cached briefings
    (os.path.join(BASE_DIR, "orders", "completed"),      "*.json",          30, False),  # fulfilled orders
    (os.path.join(BASE_DIR, "router"),                   "*.log.*",          7, False),  # rotated log backups
    (os.path.join(os.path.expanduser("~/tmp")),          "temp_script_*.py", 1, False),  # actuator temp scripts
    (os.path.join(os.path.expanduser("~/tmp")),          "temp_venv_*",      1, True),   # leaked throwaway venvs
    # Expired drop payloads. Change this to your desired shared mount point.
    (os.path.join(BASE_DIR, "dead_drop_inbox"),          "*.py",            14, False),
]

# Files that must never be collected, regardless of age.
# Only exact filename matches are protected. Wildcards are disabled to prevent
# conflicts with sweep zones (e.g., *.py in dead_drop_inbox).
PROTECTED_NAMES = frozenset([
    "coffee.example.json",
    "coffee.example.json.lock",
    "character.example.json",
    "lmcache_config.yaml",
    "repo_manifest.example.json",
])

# ==========================================
# Helpers
# ==========================================

def age_of(path):
    """Age in seconds. Falls back to ctime, then to infinity (always collect)."""
    now = time.time()
    try:
        return now - os.path.getmtime(path)
    except OSError:
        try:
            return now - os.path.getctime(path)
        except OSError:
            return float("inf")

def is_protected(path):
    return os.path.basename(path) in PROTECTED_NAMES

def sweep(zone_dir, pattern, ttl_days, prune_dirs, archive_dir=None, dry_run=True):
    """Sweep one zone. Returns (collected_count, reclaimed_bytes)."""
    if not os.path.isdir(zone_dir):
        return (0, 0)

    cutoff = ttl_days * 86400
    collected = reclaimed = 0

    for root, dirs, files in os.walk(zone_dir, topdown=True):
        targets = [os.path.join(root, f) for f in fnmatch.filter(files, pattern)]
        if prune_dirs:
            targets += [os.path.join(root, d) for d in list(dirs)
                        if fnmatch.fnmatch(d, pattern)]

        for target in targets:
            if is_protected(target):
                continue
            if age_of(target) < cutoff:
                continue

            size = os.path.getsize(target) if os.path.isfile(target) else 0
            print(f"[DELETE] {target} ({size // 1024} KB, "
                  f"{age_of(target) // 86400:.0f} days old)")

            if dry_run:
                collected += 1
                reclaimed += size
                continue

            if archive_dir:
                os.makedirs(archive_dir, exist_ok=True)
                stamp = time.strftime("%Y%m%d_%H%M%S")
                dest = os.path.join(archive_dir,
                                    f"{stamp}_{os.path.basename(target)}")
                shutil.move(target, dest)  # quarantine, not incineration
            elif os.path.isdir(target):
                shutil.rmtree(target, ignore_errors=True)
            else:
                try:
                    os.remove(target)
                except OSError:
                    continue

            collected += 1
            reclaimed += size

        # Never descend into the archive directory itself.
        if archive_dir and os.path.commonpath(
                [os.path.abspath(root), os.path.abspath(archive_dir)]) \
                == os.path.abspath(archive_dir):
            dirs[:] = []

    return (collected, reclaimed)

def main():
    parser = argparse.ArgumentParser(
        description="Age-based cleanup for generated files (drafts, snapshots, orders, temp scripts)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would be collected without deleting")
    parser.add_argument("--archive", metavar="DIR",
                        help="Move files here instead of deleting (quarantine mode)")
    parser.add_argument("--ttl-days", type=int, default=None,
                        help="Override the per-zone TTL with a global value")
    args = parser.parse_args()

    if args.dry_run:
        mode = "DRY-RUN"
    elif args.archive:
        mode = f"ARCHIVE -> {args.archive}"
    else:
        mode = "DELETE"

    print(f"[GC] Sanitation online | mode: {mode}")

    total_count = total_bytes = 0
    for zone, pattern, default_ttl, prune_dirs in SWEEP_ZONES:
        ttl = args.ttl_days if args.ttl_days is not None else default_ttl
        count, size = sweep(zone, pattern, ttl, prune_dirs,
                            archive_dir=args.archive, dry_run=args.dry_run)
        total_count += count
        total_bytes += size

    verb = "identified" if args.dry_run else "collected"
    print(f"\n[OK] Done: {total_count} item(s), "
          f"{total_bytes // 1024 // 1024} MB {verb}.")

if __name__ == "__main__":
    main()
