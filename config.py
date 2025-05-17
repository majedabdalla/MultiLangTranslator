import os

# Bot configuration
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8199168632:AAECMyWkDmLJdryMhwRNYvAPRvq5DNyBuio")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "1341868920"))
TARGET_GROUP_ID = int(os.environ.get("TARGET_GROUP_ID", "-1002586522122"))

# Payment Details
PAYEER_ACCOUNT = os.environ.get("PAYEER_ACCOUNT", "p1060900640")
BITCOIN_ADDRESS = os.environ.get("BITCOIN_ADDRESS", "14qaZcSda7az1i9FFXp92vgpj9gj4wrK8z")

# Supported Languages
SUPPORTED_LANGUAGES = {
    "en": "English",
    "ar": "العربية",
    "hi": "हिन्दी",
    "id": "Bahasa Indonesia"
}

# Default language for new users
DEFAULT_LANGUAGE = "en"

# File paths
USER_DATA_FILE = "data/user_data.json"
PENDING_PAYMENTS_FILE = "data/pending_payments.json"
REGIONS_COUNTRIES_FILE = "data/regions_countries.json"
LOCALES_DIR = "locales"

# Conversation states
# Profile creation
SELECT_LANG = 0
SELECT_GENDER = 1
SELECT_REGION = 2
SELECT_COUNTRY_IN_REGION = 3

# Partner search
SEARCH_PARTNER_LANG = 4
SEARCH_PARTNER_GENDER = 5
SEARCH_PARTNER_REGION = 6
SEARCH_PARTNER_COUNTRY = 7

# Payment verification
PAYMENT_PROOF = 8

# Flask settings
PORT = int(os.environ.get("PORT", 5000))
SESSION_SECRET = os.environ.get("SESSION_SECRET", "multichatbot_secret_key")
