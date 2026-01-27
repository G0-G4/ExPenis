import asyncio
import os

from dotenv import load_dotenv
from mypy.fixup import missing_alias
from tuican import Application

from bot.components.account_screen import AccountMain
from bot.components.daily_screen import MainScreen
from core.models import db

load_dotenv()
token = os.getenv("token")


async def post_init(application):
    await db.aconnect()


async def post_shutdown(application):
    await db.close()
    await db.close_pool()


def main():
    app = Application(token, {'start': MainScreen, 'accounts': AccountMain}).post_init(post_init).post_shutdown(post_shutdown)
    app.run()


if __name__ == '__main__':
    main()
