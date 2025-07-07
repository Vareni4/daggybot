import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# JWT settings
JWT_SECRET = "your-secret-key"  # Change this to a secure secret key
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = 15  # minutes

# Read bot token from file
BOT_TOKEN_PATH = os.path.join(os.path.dirname(__file__), 'secrets', 'bot_token.txt')
with open(BOT_TOKEN_PATH, 'r') as f:
    BOT_TOKEN = f.read().strip()

# Authorized users
AUTHORIZED_USERS = {128772612}  # Replace with your authorized user IDs 

# Admin users
ADMIN_USERS = {128772612}  # Replace with your authorized user IDs 