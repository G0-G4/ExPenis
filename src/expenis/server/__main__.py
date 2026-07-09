import argparse
import asyncio
import sys
from datetime import timedelta

import uvicorn

from ..config import DEV
from ..core.logging_config import setup_logging
from ..core.models import User, db
from .application import auth


async def _generate_token(username: str, days: int) -> None:
    """Generate a long-lived access + refresh token for an existing user.

    The user must already exist (created via the app or other means).
    If the username is not found, the command will exit with an error.
    """
    await db.aconnect()
    try:
        user = await db.run(lambda: User.get_or_none(User.username == username))
        if user is None:
            print(f"Error: User with username '{username}' not found.", file=sys.stderr)
            print("The user must already exist in the database.", file=sys.stderr)
            print("Create the account first using the web/app interface (register or Telegram login).", file=sys.stderr)
            sys.exit(1)

        uid = str(user.id)
        access_token = auth.create_access_token(
            uid=uid,
            expiry=timedelta(days=days),
        )
        refresh_token = auth.create_refresh_token(
            uid=uid,
            expiry=timedelta(days=days),
        )

        print(f"User: {username} (id={user.id})")
        print(f"\nAccess token (valid for {days} days):")
        print(access_token)
        print(f"\nRefresh token (valid for {days} days):")
        print(refresh_token)
        print("\nUse in requests:")
        print(f'  Authorization: Bearer {access_token}')
        print("\n(You can also use the refresh token to obtain new access tokens via /api/refresh)")
    finally:
        await db.aclose()
        try:
            await db.close_pool()
        except Exception:
            pass


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "token":
        parser = argparse.ArgumentParser(
            description="Generate a long-lived JWT token for LLM agents or automation."
        )
        parser.add_argument(
            "--username",
            required=True,
            help="Username of an *existing* user (the user must already be registered)",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=365,
            help="Token lifetime in days (default: 365)",
        )
        args = parser.parse_args(sys.argv[2:])
        asyncio.run(_generate_token(args.username, args.days))
        return

    # Normal server run
    log_config = setup_logging()
    options = {"host": "0.0.0.0", "port": 8000, "log_config": log_config}
    if DEV:
        options["reload"] = True
        options["reload_excludes"] = ["logs/"]
    uvicorn.run("src.expenis.server.application:app", **options)


if __name__ == "__main__":
    main()