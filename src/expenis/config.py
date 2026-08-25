import os

from dotenv import find_dotenv, load_dotenv

DEV = False
if os.getenv("EXPENIS_ENV") != "production":
    DEV = True
    load_dotenv(find_dotenv(".env.dev"))

load_dotenv()

SECRET=os.getenv('secret')
COOKIE_DOMAIN=os.getenv('cookie_domain')
EXPIRATION_TIME_SECONDS=int(os.getenv('expiration_time_seconds'))
# Default 90 days. Must stay longer than access TTL, otherwise /api/refresh is
# already dead by the time the access token expires.
REFRESH_TIME_SECONDS=int(os.getenv('refresh_time_seconds', '7776000'))
ALPHAVANTAGE_KEY=os.getenv('alphavantage_key')