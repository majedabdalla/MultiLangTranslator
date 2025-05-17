import logging
import json
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext, CallbackQueryHandler

# Load configuration
BOT_TOKEN = os.environ.get("BOT_TOKEN") or "8199168632:AAECMyWkDmLJdryMhwRNYvAPRvq5DNyBuio"
ADMIN_ID = int(os.environ.get("ADMIN_ID") or 1341868920)
TARGET_GROUP_ID = int(os.environ.get("TARGET_GROUP_ID") or -1002586522122)
PAYEER_ACCOUNT = os.environ.get("PAYEER_ACCOUNT") or "p1060900640"
BITCOIN_ADDRESS = os.environ.get("BITCOIN_ADDRESS") or "14qaZcSda7az1i9FFXp92vgpj9gj4wrK8z"

SUPPORTED_LANGUAGES = {
    "en": "English",
    "ar": "العربية",
    "hi": "हिन्दी",
    "id": "Bahasa Indonesia"
}
DEFAULT_LANGUAGE = "en"
USER_DATA_FILE = "/home/ubuntu/MultiChatBot/data/user_data.json"
PENDING_PAYMENTS_FILE = "/home/ubuntu/MultiChatBot/data/pending_payments.json"
REGIONS_COUNTRIES_FILE = "/home/ubuntu/MultiChatBot/data/regions_countries.json"
LOCALES_DIR = "/home/ubuntu/MultiChatBot/locales"

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states for profile creation
SELECT_LANG, SELECT_GENDER, SELECT_REGION, SELECT_COUNTRY_IN_REGION = range(4)

# Conversation states for partner search
SEARCH_PARTNER_LANG, SEARCH_PARTNER_GENDER, SEARCH_PARTNER_COUNTRY = range(4, 7)

# --- Localization Cache ---
loaded_translations = {}

def load_translation_file(lang_code):
    if lang_code in loaded_translations:
        return loaded_translations[lang_code]
    try:
        file_path = os.path.join(LOCALES_DIR, f"{lang_code}.json")
        with open(file_path, "r", encoding="utf-8") as f:
            translations = json.load(f)
            loaded_translations[lang_code] = translations
            return translations
    except FileNotFoundError:
        logger.warning(f"Translation file for {lang_code} not found at {file_path}. Falling back to English.")
        if lang_code != DEFAULT_LANGUAGE:
            return load_translation_file(DEFAULT_LANGUAGE)
        return {}
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from translation file: {file_path}")
        if lang_code != DEFAULT_LANGUAGE:
            return load_translation_file(DEFAULT_LANGUAGE)
        return {}

for lang_code_initial in SUPPORTED_LANGUAGES.keys():
    load_translation_file(lang_code_initial)

# --- Data Handling Functions ---
def load_user_data():
    try:
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_user_data(data):
    with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_regions_countries():
    try:
        with open(REGIONS_COUNTRIES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Regions and countries file not found at {REGIONS_COUNTRIES_FILE}")
        return {}

def load_pending_payments():
    try:
        with open(PENDING_PAYMENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_pending_payments(data):
    with open(PENDING_PAYMENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

regions_countries_data = load_regions_countries()

# --- Helper Functions (Localization) ---
def get_text(user_id, key, lang_code=None, **kwargs):
    user_data_loaded = load_user_data()
    effective_lang = lang_code or user_data_loaded.get(str(user_id), {}).get("language", DEFAULT_LANGUAGE)
    translations = loaded_translations.get(effective_lang)
    if not translations and effective_lang != DEFAULT_LANGUAGE:
        translations = loaded_translations.get(DEFAULT_LANGUAGE)
    if not translations:
        return f"ERR_NO_TRANSLATIONS_FOR_{effective_lang.upper()}_{key}"
    message = translations.get(key, f"Missing translation for: {key} in {effective_lang}")
    if kwargs:
        try:
            message = message.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing placeholder {e} in translation key '{key}' for language '{effective_lang}'. Original message: '{message}'")
    return message

# --- Payment and Premium Feature Functions ---
def is_premium_user(user_id):
    """Check if a user has premium status."""
    user_data = load_user_data()
    return user_data.get(str(user_id), {}).get("premium", False)

async def show_payment_info(update: Update, context: CallbackContext) -> None:
    """Show payment information to the user."""
    user_id = str(update.effective_user.id)
    
    # Check if user already has premium
    if is_premium_user(user_id):
        await update.message.reply_text(get_text(user_id, "feature_already_activated"))
        return
    
    # Show payment options
    payment_text = get_text(user_id, "payment_prompt", 
                           payeer_account=PAYEER_ACCOUNT, 
                           bitcoin_address=BITCOIN_ADDRESS)
    
    # Create inline keyboard for payment verification
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, "payment_verify_button"), callback_data="verify_payment")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(payment_text, reply_markup=reply_markup)

async def payment_verification_callback(update: Update, context: CallbackContext) -> None:
    """Handle payment verification button click."""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    
    # Ask user to send payment proof
    await query.edit_message_text(get_text(user_id, "payment_send_proof"))
    
    # Set user state to wait for payment proof
    context.user_data["awaiting_payment_proof"] = True

async def handle_payment_proof(update: Update, context: CallbackContext) -> None:
    """Process payment proof sent by user."""
    user = update.effective_user
    user_id = str(user.id)
    
    # Only process if we're awaiting payment proof from this user
    if not context.user_data.get("awaiting_payment_proof"):
        return
    
    # Reset the awaiting flag
    context.user_data["awaiting_payment_proof"] = False
    
    # Add to pending payments list
    pending_payments = load_pending_payments()
    pending_payments.append({
        "user_id": user_id,
        "name": user.full_name,
        "username": user.username,
        "timestamp": update.message.date.isoformat(),
        "message_id": update.message.message_id,
        "chat_id": update.message.chat_id,
        "status": "pending"
    })
    save_pending_payments(pending_payments)
    
    # Notify admin about new payment verification request
    try:
        admin_notification = f"New payment verification request from user {user.full_name} (ID: {user_id})"
        if user.username:
            admin_notification += f" @{user.username}"
        
        # Create inline keyboard for admin to approve/reject
        keyboard = [
            [
                InlineKeyboardButton("Approve", callback_data=f"approve_payment_{user_id}"),
                InlineKeyboardButton("Reject", callback_data=f"reject_payment_{user_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_notification, reply_markup=reply_markup)
        
        # Forward the actual payment proof to admin
        await context.bot.forward_message(chat_id=ADMIN_ID, 
                                         from_chat_id=update.message.chat_id, 
                                         message_id=update.message.message_id)
    except Exception as e:
        logger.error(f"Error notifying admin about payment: {e}")
    
    # Notify user that payment is being processed
    await update.message.reply_text(get_text(user_id, "payment_received_pending_verification"))

async def admin_payment_callback(update: Update, context: CallbackContext) -> None:
    """Handle admin's approval or rejection of payment."""
    query = update.callback_query
    await query.answer()
    
    # Only allow admin to use these callbacks
    if query.from_user.id != ADMIN_ID:
        return
    
    # Parse callback data
    data = query.data
    action, user_id = data.split("_")[0], data.split("_")[2]
    
    user_data = load_user_data()
    
    if user_id not in user_data:
        await query.edit_message_text(get_text(ADMIN_ID, "admin_error_user_not_found", user_id=user_id))
        return
    
    if action == "approve":
        # Update user's premium status
        user_data[user_id]["premium"] = True
        save_user_data(user_data)
        
        # Update pending payment status
        pending_payments = load_pending_payments()
        for payment in pending_payments:
            if payment["user_id"] == user_id and payment["status"] == "pending":
                payment["status"] = "approved"
        save_pending_payments(pending_payments)
        
        # Notify admin
        await query.edit_message_text(get_text(ADMIN_ID, "admin_payment_verified", user_id=user_id))
        
        # Notify user
        try:
            await context.bot.send_message(chat_id=int(user_id), 
                                          text=get_text(user_id, "feature_activated"))
        except Exception as e:
            logger.error(f"Error notifying user about payment approval: {e}")
    
    elif action == "reject":
        # Update pending payment status
        pending_payments = load_pending_payments()
        for payment in pending_payments:
            if payment["user_id"] == user_id and payment["status"] == "pending":
                payment["status"] = "rejected"
        save_pending_payments(pending_payments)
        
        # Notify admin
        await query.edit_message_text(f"Payment from user {user_id} has been rejected.")
        
        # Notify user
        try:
            await context.bot.send_message(chat_id=int(user_id), 
                                          text=get_text(user_id, "payment_rejected"))
        except Exception as e:
            logger.error(f"Error notifying user about payment rejection: {e}")

# --- Partner Search Functions ---
async def start_partner_search(update: Update, context: CallbackContext) -> int:
    """Start the partner search process."""
    user_id = str(update.effective_user.id)
    
    # Check if user has a complete profile
    user_data = load_user_data()
    if user_id not in user_data or not user_data[user_id].get("profile_complete", False):
        await update.message.reply_text(get_text(user_id, "profile_incomplete"))
        return ConversationHandler.END
    
    # Check if user has premium status
    if not is_premium_user(user_id):
        # Show payment information
        await show_payment_info(update, context)
        return ConversationHandler.END
    
    # Start the search process
    lang_keyboard = [[KeyboardButton(name)] for name in SUPPORTED_LANGUAGES.values()]
    await update.message.reply_text(
        get_text(user_id, "search_partner_prompt_language"),
        reply_markup=ReplyKeyboardMarkup(lang_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return SEARCH_PARTNER_LANG

async def search_partner_language(update: Update, context: CallbackContext) -> int:
    """Handle language selection for partner search."""
    user_input_lang_name = update.message.text
    user_id = str(update.effective_user.id)
    
    selected_lang_code = None
    for code, name in SUPPORTED_LANGUAGES.items():
        if name == user_input_lang_name:
            selected_lang_code = code
            break
    
    if not selected_lang_code:
        lang_keyboard = [[KeyboardButton(name)] for name in SUPPORTED_LANGUAGES.values()]
        await update.message.reply_text(
            get_text(user_id, "invalid_language"),
            reply_markup=ReplyKeyboardMarkup(lang_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return SEARCH_PARTNER_LANG
    
    # Store the selected language for search
    context.user_data["partner_search"] = {"language": selected_lang_code}
    
    # Ask for gender preference
    gender_options = [get_text(user_id, "male"), get_text(user_id, "female"), get_text(user_id, "other"), get_text(user_id, "any_gender")]
    gender_keyboard = [[KeyboardButton(text)] for text in gender_options]
    await update.message.reply_text(
        get_text(user_id, "search_partner_prompt_gender"),
        reply_markup=ReplyKeyboardMarkup(gender_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return SEARCH_PARTNER_GENDER

async def search_partner_gender(update: Update, context: CallbackContext) -> int:
    """Handle gender selection for partner search."""
    selected_gender_text = update.message.text
    user_id = str(update.effective_user.id)
    
    # Map localized gender to canonical value
    gender_map = {
        get_text(user_id, "male"): "male",
        get_text(user_id, "female"): "female",
        get_text(user_id, "other"): "other",
        get_text(user_id, "any_gender"): "any"
    }
    
    gender = gender_map.get(selected_gender_text)
    if not gender:
        gender_options = [get_text(user_id, "male"), get_text(user_id, "female"), get_text(user_id, "other"), get_text(user_id, "any_gender")]
        gender_keyboard = [[KeyboardButton(text)] for text in gender_options]
        await update.message.reply_text(
            get_text(user_id, "invalid_gender"),
            reply_markup=ReplyKeyboardMarkup(gender_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return SEARCH_PARTNER_GENDER
    
    # Store the selected gender for search
    context.user_data["partner_search"]["gender"] = gender
    
    # Ask for country preference
    # For simplicity, we'll use regions first, then countries
    region_names = list(regions_countries_data.keys())
    region_names.append(get_text(user_id, "any_country"))  # Add "Any country" option
    region_keyboard = [[KeyboardButton(region_name)] for region_name in region_names]
    await update.message.reply_text(
        get_text(user_id, "search_partner_prompt_country"),
        reply_markup=ReplyKeyboardMarkup(region_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return SEARCH_PARTNER_COUNTRY

async def search_partner_country(update: Update, context: CallbackContext) -> int:
    """Handle country selection for partner search."""
    selected_country = update.message.text
    user_id = str(update.effective_user.id)
    
    # Check if "Any country" was selected
    if selected_country == get_text(user_id, "any_country"):
        context.user_data["partner_search"]["country"] = "any"
    else:
        # Store the selected country for search
        context.user_data["partner_search"]["country"] = selected_country
    
    # Perform the search
    await perform_partner_search(update, context)
    return ConversationHandler.END

async def perform_partner_search(update: Update, context: CallbackContext) -> None:
    """Search for partners based on criteria and show results."""
    user_id = str(update.effective_user.id)
    search_criteria = context.user_data.get("partner_search", {})
    
    # Load all user data
    all_users = load_user_data()
    
    # Filter users based on search criteria
    matching_users = []
    for potential_partner_id, potential_partner_data in all_users.items():
        # Skip the user themselves
        if potential_partner_id == user_id:
            continue
        
        # Skip users without complete profiles
        if not potential_partner_data.get("profile_complete", False):
         
(Content truncated due to size limit. Use line ranges to read in chunks)