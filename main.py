import os
import json
import logging
import threading
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, 
    Filters, ConversationHandler, CallbackQueryHandler, CallbackContext
)

# Import modules
import config
from keep_alive import start_server
from data_handler import ensure_directory_exists, load_json_file, save_json_file
from localization import preload_translations

# Import handlers
from bot_handlers import (
    start, language_selection, gender_selection, 
    region_selection, country_selection, cancel, forward_message
)
from admin_handlers import block_user, unblock_user, list_users, verify_payment_callback
from search_handlers import (
    start_partner_search, search_partner_language,
    search_partner_gender, search_partner_region, search_partner_country
)
from payment_handlers import (
    payment_verification_callback, handle_payment_proof, payment_command
)

# Import Flask app
from app import app

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ensure data directories exist
def setup_data_directories():
    """Setup necessary directories and files."""
    # Ensure data directory exists
    ensure_directory_exists(config.USER_DATA_FILE)
    ensure_directory_exists(config.PENDING_PAYMENTS_FILE)
    
    # Ensure locales directory exists
    ensure_directory_exists(os.path.join(config.LOCALES_DIR, "dummy.txt"))
    
    # Create initial regions_countries.json if it doesn't exist
    if not os.path.exists(config.REGIONS_COUNTRIES_FILE):
        regions_countries = {
            "Asia": [
                "Afghanistan", "Bahrain", "Bangladesh", "Bhutan", "Brunei", "Cambodia", "China", "India", 
                "Indonesia", "Iran", "Iraq", "Israel", "Japan", "Jordan", "Kazakhstan", "Kuwait", "Kyrgyzstan", 
                "Laos", "Lebanon", "Malaysia", "Maldives", "Mongolia", "Myanmar", "Nepal", "North Korea", 
                "Oman", "Pakistan", "Palestine State", "Philippines", "Qatar", "Saudi Arabia", "Singapore", 
                "South Korea", "Sri Lanka", "Syria", "Taiwan", "Tajikistan", "Thailand", "Timor-Leste", 
                "Turkey", "Turkmenistan", "United Arab Emirates", "Uzbekistan", "Vietnam", "Yemen"
            ],
            "Europe": [
                "Albania", "Andorra", "Armenia", "Austria", "Azerbaijan", "Belarus", "Belgium", 
                "Bosnia and Herzegovina", "Bulgaria", "Croatia", "Cyprus", "Czech Republic", "Denmark", 
                "Estonia", "Finland", "France", "Georgia", "Germany", "Greece", "Hungary", "Iceland", 
                "Ireland", "Italy", "Kosovo", "Latvia", "Liechtenstein", "Lithuania", "Luxembourg", "Malta", 
                "Moldova", "Monaco", "Montenegro", "Netherlands", "North Macedonia", "Norway", "Poland", 
                "Portugal", "Romania", "Russia", "San Marino", "Serbia", "Slovakia", "Slovenia", "Spain", 
                "Sweden", "Switzerland", "Ukraine", "United Kingdom", "Vatican City"
            ],
            "Africa": [
                "Algeria", "Angola", "Benin", "Botswana", "Burkina Faso", "Burundi", "Cabo Verde", 
                "Cameroon", "Central African Republic", "Chad", "Comoros", "Congo, Democratic Republic of the", 
                "Congo, Republic of the", "Cote d'Ivoire", "Djibouti", "Egypt", "Equatorial Guinea", 
                "Eritrea", "Eswatini", "Ethiopia", "Gabon", "Gambia", "Ghana", "Guinea", "Guinea-Bissau", 
                "Kenya", "Lesotho", "Liberia", "Libya", "Madagascar", "Malawi", "Mali", "Mauritania", 
                "Mauritius", "Morocco", "Mozambique", "Namibia", "Niger", "Nigeria", "Rwanda", 
                "Sao Tome and Principe", "Senegal", "Seychelles", "Sierra Leone", "Somalia", "South Africa", 
                "South Sudan", "Sudan", "Tanzania", "Togo", "Tunisia", "Uganda", "Zambia", "Zimbabwe"
            ],
            "North America": [
                "Antigua and Barbuda", "Bahamas", "Barbados", "Belize", "Canada", "Costa Rica", "Cuba", 
                "Dominica", "Dominican Republic", "El Salvador", "Grenada", "Guatemala", "Haiti", "Honduras", 
                "Jamaica", "Mexico", "Nicaragua", "Panama", "Saint Kitts and Nevis", "Saint Lucia", 
                "Saint Vincent and the Grenadines", "United States of America"
            ],
            "South America": [
                "Argentina", "Bolivia", "Brazil", "Chile", "Colombia", "Ecuador", "Guyana", "Paraguay", 
                "Peru", "Suriname", "Uruguay", "Venezuela"
            ],
            "Oceania": [
                "Australia", "Fiji", "Kiribati", "Marshall Islands", "Micronesia", "Nauru", "New Zealand", 
                "Palau", "Papua New Guinea", "Samoa", "Solomon Islands", "Tonga", "Tuvalu", "Vanuatu"
            ]
        }
        save_json_file(config.REGIONS_COUNTRIES_FILE, regions_countries)

    # Preload translation files
    for lang_code in ["en", "ar", "hi", "id"]:
        source_file = os.path.join("attached_assets", f"{lang_code}.json")
        target_file = os.path.join(config.LOCALES_DIR, f"{lang_code}.json")
        
        # Copy from attached assets if available and target doesn't exist
        if os.path.exists(source_file) and not os.path.exists(target_file):
            try:
                with open(source_file, "r", encoding="utf-8") as source:
                    translation_data = json.load(source)
                    save_json_file(target_file, translation_data)
                    logger.info(f"Copied translation file from {source_file} to {target_file}")
            except Exception as e:
                logger.error(f"Error copying translation file: {e}")

def main() -> None:
    """Start the bot."""
    logger.info("Starting bot...")
    
    # Setup data directories and initialize files
    setup_data_directories()
    
    # Create the Updater and pass it your bot's token
    updater = Updater(token=config.BOT_TOKEN)
    
    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher
    
    # Create profile conversation handler
    profile_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            config.SELECT_LANG: [MessageHandler(Filters.text & ~Filters.command, language_selection)],
            config.SELECT_GENDER: [MessageHandler(Filters.text & ~Filters.command, gender_selection)],
            config.SELECT_REGION: [MessageHandler(Filters.text & ~Filters.command, region_selection)],
            config.SELECT_COUNTRY_IN_REGION: [MessageHandler(Filters.text & ~Filters.command, country_selection)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="profile_conversation",
        persistent=False
    )
    
    # Create partner search conversation handler
    search_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("search", start_partner_search)],
        states={
            config.SEARCH_PARTNER_LANG: [MessageHandler(Filters.text & ~Filters.command, search_partner_language)],
            config.SEARCH_PARTNER_GENDER: [MessageHandler(Filters.text & ~Filters.command, search_partner_gender)],
            config.SEARCH_PARTNER_REGION: [MessageHandler(Filters.text & ~Filters.command, search_partner_region)],
            config.SEARCH_PARTNER_COUNTRY: [MessageHandler(Filters.text & ~Filters.command, search_partner_country)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="search_conversation",
        persistent=False
    )
    
    # Create payment verification conversation handler
    payment_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(payment_verification_callback, pattern="^verify_payment$")],
        states={
            config.PAYMENT_PROOF: [MessageHandler(Filters.all & ~Filters.command, handle_payment_proof)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="payment_conversation",
        persistent=False
    )
    
    # Add conversation handlers
    dispatcher.add_handler(profile_conv_handler)
    dispatcher.add_handler(search_conv_handler)
    dispatcher.add_handler(payment_conv_handler)
    
    # Add command handlers
    dispatcher.add_handler(CommandHandler("payment", payment_command))
    
    # Admin commands
    dispatcher.add_handler(CommandHandler("block", block_user))
    dispatcher.add_handler(CommandHandler("unblock", unblock_user))
    dispatcher.add_handler(CommandHandler("users", list_users))
    
    # Add callback query handler for admin payment verification
    dispatcher.add_handler(CallbackQueryHandler(verify_payment_callback, pattern="^(approve|reject)_payment_"))
    
    # Add handler for forwarding messages
    dispatcher.add_handler(MessageHandler(Filters.all & ~Filters.command, forward_message))
    
    # Start the Bot
    updater.start_polling()
    
    # Log that the bot has started
    logger.info("Bot started. Press Ctrl+C to stop.")
    
    # Keep the main thread running so the bot doesn't stop
    # We use threading event instead of just updater.idle() because we need to return control to Flask
    import threading
    stop_event = threading.Event()
    return stop_event  # Return the event so it can be used to stop the bot if needed

# Global variable to store the bot thread and stop event
bot_thread = None
bot_stop_event = None

def start_bot_in_thread():
    """Start the bot in a separate thread and ensure it stays running."""
    global bot_thread, bot_stop_event
    
    # If a bot thread is already running, do nothing
    if bot_thread and bot_thread.is_alive():
        logger.info("Bot is already running.")
        return
    
    # If we have a previous stop event, set it to stop any zombie threads
    if bot_stop_event:
        bot_stop_event.set()
    
    # Function to run in the thread
    def bot_worker():
        try:
            # Start the bot and get the stop event
            event = main()
            # Wait for the stop event to be set
            event.wait()
        except Exception as e:
            logger.error(f"Error in bot thread: {e}")
    
    # Create and start the thread
    bot_thread = threading.Thread(target=bot_worker, daemon=True)
    bot_thread.start()
    logger.info("Bot thread started")

# When this module is imported, automatically start the bot
start_bot_in_thread()

# Export app for the gunicorn server
from app import app