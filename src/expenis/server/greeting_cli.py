import argparse
import asyncio
import sys
from datetime import UTC, date, datetime

from peewee import PeeweeException

from ..core.errors import NotFoundException
from ..core.models import db
from ..core.service.personal_greeting_service import (
    assign_greetings,
    delete_greetings,
    inspect_greeting,
    select_greeting_recipients,
    validate_greeting,
)


def _date(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError
        return parsed
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use a valid YYYY-MM-DD date.") from exc


def greeting_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage personal greetings on this server.")
    actions = parser.add_subparsers(dest="action", required=True)
    for action in ("set", "show", "delete"):
        command = actions.add_parser(action)
        target = command.add_mutually_exclusive_group(required=True)
        target.add_argument("--user-id", type=int)
        target.add_argument("--username")
        target.add_argument("--all", action="store_true", dest="all_users")
        if action == "set":
            command.add_argument("--text", required=True)
            command.add_argument("--expires-on", type=_date, help="Inclusive date in Europe/Moscow")
    return parser


async def run_greeting_command(args: argparse.Namespace) -> None:
    if args.action == "set":
        validate_greeting(args.text, args.expires_on)
    users = await select_greeting_recipients(
        user_id=args.user_id, username=args.username, all_users=args.all_users,
    )
    if args.action == "show":
        for user in users:
            greeting = await inspect_greeting(user.id)
            print(f"User: {user.id} ({user.username or 'no username'})")
            if greeting is None:
                print("No greeting.")
                continue
            expired = greeting.expires_at is not None and greeting.expires_at <= datetime.now(UTC)
            print(f"Assignment: {greeting.assignment_id}")
            print(f"Expires at (UTC): {greeting.expires_at or 'never'}")
            print(f"Dismissed at (UTC): {greeting.dismissed_at or 'not dismissed'}")
            print(f"Expired: {expired}")
            print(f"Active: {not expired and greeting.dismissed_at is None}")
            print(greeting.text)
        if not users:
            print("Recipients: 0")
        return

    print(f"Recipients: {len(users)}")
    if not users:
        return
    if args.all_users:
        try:
            answer = input(f"{args.action} greetings for ALL {len(users)} recipients? [y/N] ")
        except (EOFError, OSError):
            answer = ""
        if answer.strip().lower() not in ("y", "yes"):
            print("Cancelled. No greetings changed.")
            return
    user_ids = [user.id for user in users]
    if args.action == "set":
        await assign_greetings(user_ids, args.text, args.expires_on)
    else:
        await delete_greetings(user_ids)
    print(f"Done: {len(users)} recipients.")


async def _run(args: argparse.Namespace) -> None:
    try:
        async with db:
            await run_greeting_command(args)
    finally:
        await db.close_pool()


def greeting_main(argv: list[str]) -> None:
    args = greeting_parser().parse_args(argv)
    try:
        asyncio.run(_run(args))
    except (ValueError, NotFoundException, PeeweeException) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
