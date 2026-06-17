import re
from os import environ

# Bot Session Name
SESSION = environ.get('SESSION', 'TechVJBot')

# Your Telegram Account Api Id And Api Hash
API_ID = int(environ.get('API_ID', '33720317'))
API_HASH = environ.get('API_HASH', '145db99951f44490f134ac7446126630')

# Bot Token
BOT_TOKEN = environ.get('BOT_TOKEN', "")

# --- ADMIN SETUP (FIXED) ---
# Raw ID from environment
ADMIN_TXT = environ.get('ADMIN', '8692160077')

# 1. ADMIN: Ye purani files ke liye hai (Start.py etc.)
# Agar multiple IDs hain to ye pehli ID utha lega
try:
    ADMIN = int(ADMIN_TXT.split()[0])
except:
    ADMIN = 1865244712 # Fallback if error

# 2. ADMINS: Ye new Firebase plugin ke liye hai (List of IDs)
ADMINS = [int(x) for x in ADMIN_TXT.split()]
# ---------------------------

# Back Up Bot Token
BACKUP_BOT_TOKEN = environ.get('BACKUP_BOT_TOKEN', "")

# Log Channel
LOG_CHANNEL = int(environ.get('LOG_CHANNEL', '-1002869695930'))

# Mongodb Database
MONGODB_URI = environ.get("MONGODB_URI", "")

# Stream Url (Trailing slash removed for safety)
STREAM_URL = environ.get("STREAM_URL", "https://skillneaststream.onrender.com").rstrip("/")

# Permanent Link
LINK_URL = environ.get("LINK_URL", "https://skillneast.blogspot.com/p/s_7.html")

# Others
PORT = environ.get("PORT", "8080")
MULTI_CLIENT = False
SLEEP_THRESHOLD = int(environ.get('SLEEP_THRESHOLD', '60'))
PING_INTERVAL = int(environ.get("PING_INTERVAL", "1200"))

if 'DYNO' in environ:
    ON_HEROKU = True
else:
    ON_HEROKU = False
