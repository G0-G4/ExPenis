from tuican import Application

from ..config import TOKEN
from .components import MainScreen, CategoriesMain, AccountMain
from ..core.models import db

async def post_init(application):
    await db.aconnect()

async def post_shutdown(application):
    await db.aclose()
    await db.close_pool()


def main():
    app = Application(TOKEN, {
        'start': MainScreen,
        'accounts': AccountMain,
        'categories': CategoriesMain
    }).post_init(post_init).post_shutdown(post_shutdown)
    app.run()


if __name__ == '__main__':
    main()
