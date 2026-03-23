import os

from dotenv import load_dotenv
from tuican import Application

from src.expenis.bot.components import AccountMain, CategoriesMain, MainScreen, CommandHandlerScreen
from src.expenis.core.models import db

load_dotenv()
token = os.getenv("token")


async def post_init(application):
    await db.aconnect()


async def post_shutdown(application):
    await db.close()
    await db.close_pool()


def main():
    app = Application(token, {
        'start': MainScreen,
        'mobile_token': CommandHandlerScreen,
        'accounts': AccountMain,
        'categories': CategoriesMain
    }).post_init(post_init).post_shutdown(post_shutdown)
    app.run()


if __name__ == '__main__':
    main()
