import os

from dotenv import load_dotenv


load_dotenv()

TOKEN = os.getenv("token")
SURPRISE_MESSAGE=os.getenv("surprise_message")

