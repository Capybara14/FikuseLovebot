import os
from dotenv import load_dotenv

load_dotenv()

EMOJI_TEMPLATE = "https://cdn.jsdelivr.net/npm/emoji-datasource-apple@15.0.1/img/apple/64/{code}.png"
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")
OWNER_ID = os.getenv("OWNER_ID")
IMGBB_KEY = os.getenv("IMGBB_KEY")
FILE_COMMANDS_PATH = "commands.json"
FILE_USERS_PATH = "users.json"
TIMEOUT = 600
LIMIT_OF_COMMANDS = 100