#!/usr/bin/env python3
"""Manage local Flux auth users for temporary dashboard deployment."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_USERS_FILE = Path(os.environ.get("FLUX_USERS_FILE", str(ROOT / ".flux_users.json")))


def normalize_user_record(raw: object) -> dict | None:
    if isinstance(raw, str):
        return {
            "approved": True,
            "password_hash": raw,
            "must_change_password": False,
        }
    if isinstance(raw, dict):
        approved = bool(raw.get("approved", True))
        password_hash = raw.get("password_hash")
        if password_hash is None:
            password_hash = ""
        if not isinstance(password_hash, str):
            return None
        return {
            "approved": approved,
            "password_hash": password_hash,
            "must_change_password": bool(raw.get("must_change_password", False)),
        }
    return None


def load_users(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(parsed, dict):
        return {}

    users: dict[str, dict] = {}
    for username, raw in parsed.items():
        if not isinstance(username, str) or not username.strip():
            continue
        record = normalize_user_record(raw)
        if record is None:
            continue
        users[username] = record
    return users


def save_users(path: Path, users: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(users, indent=2, sort_keys=True), encoding="utf-8")


def cmd_list(args: argparse.Namespace) -> int:
    users = load_users(args.users_file)
    if not users:
        print("No users found.")
        return 0
    for username in sorted(users):
        rec = users[username]
        if not rec.get("approved", False):
            status = "not-approved"
        elif not rec.get("password_hash"):
            status = "approved-pending-signup"
        elif rec.get("must_change_password"):
            status = "must-change"
        else:
            status = "active"
        print(f"{username}\t{status}")
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    users = load_users(args.users_file)
    if args.username in users and not args.overwrite:
        print(f"User '{args.username}' already exists. Use --overwrite to replace.", file=sys.stderr)
        return 1

    users[args.username] = {
        "approved": True,
        "password_hash": "",
        "must_change_password": False,
    }
    save_users(args.users_file, users)
    print(f"Approved user '{args.username}' for first sign-up.")
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    users = load_users(args.users_file)
    if args.username in users and not args.overwrite:
        print(f"User '{args.username}' already exists. Use --overwrite to replace.", file=sys.stderr)
        return 1

    users[args.username] = {
        "approved": True,
        "password_hash": generate_password_hash(args.password),
        "must_change_password": args.force_change,
    }
    save_users(args.users_file, users)
    status = "must change password on first login" if args.force_change else "no forced change"
    print(f"Saved user '{args.username}' ({status}).")
    return 0


def cmd_set_password(args: argparse.Namespace) -> int:
    users = load_users(args.users_file)
    if args.username not in users:
        print(f"User '{args.username}' does not exist.", file=sys.stderr)
        return 1

    users[args.username]["password_hash"] = generate_password_hash(args.password)
    users[args.username]["approved"] = True
    users[args.username]["must_change_password"] = args.force_change
    save_users(args.users_file, users)
    status = "must change password on first login" if args.force_change else "no forced change"
    print(f"Updated password for '{args.username}' ({status}).")
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    users = load_users(args.users_file)
    if args.username not in users:
        print(f"User '{args.username}' does not exist.", file=sys.stderr)
        return 1

    del users[args.username]
    save_users(args.users_file, users)
    print(f"Deleted user '{args.username}'.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage Flux dashboard local users")
    parser.add_argument(
        "--users-file",
        type=Path,
        default=DEFAULT_USERS_FILE,
        help=f"Path to users JSON file (default: {DEFAULT_USERS_FILE})",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List users")
    p_list.set_defaults(func=cmd_list)

    p_approve = sub.add_parser("approve", help="Pre-approve user for first sign-up")
    p_approve.add_argument("username")
    p_approve.add_argument("--overwrite", action="store_true", help="Replace if user exists")
    p_approve.set_defaults(func=cmd_approve)

    p_add = sub.add_parser("add", help="Add user with password")
    p_add.add_argument("username")
    p_add.add_argument("--password", required=True)
    p_add.add_argument("--overwrite", action="store_true", help="Replace if user exists")
    p_add.add_argument(
        "--force-change",
        action="store_true",
        help="Force password change on first login",
    )
    p_add.set_defaults(func=cmd_add)

    p_set = sub.add_parser("set-password", help="Set an existing user's password")
    p_set.add_argument("username")
    p_set.add_argument("--password", required=True)
    p_set.add_argument(
        "--force-change",
        action="store_true",
        help="Force password change on next login",
    )
    p_set.set_defaults(func=cmd_set_password)

    p_del = sub.add_parser("delete", help="Delete user")
    p_del.add_argument("username")
    p_del.set_defaults(func=cmd_delete)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
