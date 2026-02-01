import os

from dotenv import find_dotenv, load_dotenv

DEV = False
if os.getenv("EXPENIS_ENV") != "production":
    DEV = True
    load_dotenv(find_dotenv(".env.dev"))

load_dotenv()

TOKEN = os.getenv("token")
SECRET=os.getenv('secret')
COOKIE_DOMAIN=os.getenv('cookie_domain')
EXPIRATION_TIME_SECONDS=int(os.getenv('expiration_time_seconds'))
BOT_NAME=os.getenv('bot_name')