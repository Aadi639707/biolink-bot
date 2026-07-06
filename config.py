import os
from dotenv import load_dotenv
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
# Owner IDs - only these users can use owner-level commands
OWNER_IDS = [2099312325, 8682893578]
DEVELOPER_USERNAME = "rushdeveloper"
CHANNEL_INVITE = "https://t.me/rushbots"
# Number of warnings before mute
MAX_WARNINGS = 3
