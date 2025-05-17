import logging
from typing import Dict, Any, List
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import CallbackContext, ConversationHandler

import config
from data_handler import (
    get_user_data, update_user_data, is_user_blocked, 
    get_all_regions, get_countries_in_region, is_country_in_region
)
from localization import get_text

# Initialize logger
logger = logging.getLogger(__name__)

def start(update: Update, context: CallbackContext) -> int:
    """Start command handler to begin user profile creation conversation."""
    user = update.effective_user
    user_id = str(user.id)
    
    # Check if user is blocked
    if is_user_blocked(user_id):
        return ConversationHandler.END
    
    # Get existing user data if any
    user_data = get_user_data(user_id)
    
    # Save basic user info
    update_user_data(user_id, {
        "name": user.full_name,
        "username": user.username
    })
    
    # Check if user already has a complete profile
    if user_data.get("profile_complete", False):
        # Welcome back message
        update.message.reply_text(
            get_text(user_id, "welcome_existing_user", name=user.first_name)
        )
        return ConversationHandler.END
    
    # Welcome new user message
    language_keyboard = []
    for code, name in config.SUPPORTED_LANGUAGES.items():
        language_keyboard.append([KeyboardButton(name)])
    
    update.message.reply_text(
        get_text(user_id, "welcome_new_user", lang_code=config.DEFAULT_LANGUAGE),
        reply_markup=ReplyKeyboardMarkup(language_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    
    return config.SELECT_LANG

def language_selection(update: Update, context: CallbackContext) -> int:
    """Handle language selection during profile creation."""
    user = update.effective_user
    user_id = str(user.id)
    language_name = update.message.text
    
    # Find the language code for the selected language name
    selected_lang = None
    for code, name in config.SUPPORTED_LANGUAGES.items():
        if name == language_name:
            selected_lang = code
            break
    
    # If invalid language, ask again
    if not selected_lang:
        language_keyboard = []
        for code, name in config.SUPPORTED_LANGUAGES.items():
            language_keyboard.append([KeyboardButton(name)])
        
        update.message.reply_text(
            get_text(user_id, "invalid_language", lang_code=config.DEFAULT_LANGUAGE),
            reply_markup=ReplyKeyboardMarkup(language_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return config.SELECT_LANG
    
    # Update user's language preference
    update_user_data(user_id, {"language": selected_lang})
    
    # Ask for gender
    gender_options = [get_text(user_id, "male"), get_text(user_id, "female"), get_text(user_id, "other")]
    gender_keyboard = [[KeyboardButton(text)] for text in gender_options]
    
    update.message.reply_text(
        get_text(user_id, "choose_gender"),
        reply_markup=ReplyKeyboardMarkup(gender_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    
    return config.SELECT_GENDER

def gender_selection(update: Update, context: CallbackContext) -> int:
    """Handle gender selection during profile creation."""
    user = update.effective_user
    user_id = str(user.id)
    gender_text = update.message.text
    
    # Map gender text to standardized values
    gender_mapping = {
        get_text(user_id, "male"): "male",
        get_text(user_id, "female"): "female",
        get_text(user_id, "other"): "other"
    }
    
    selected_gender = gender_mapping.get(gender_text)
    
    # If invalid gender, ask again
    if not selected_gender:
        gender_options = [get_text(user_id, "male"), get_text(user_id, "female"), get_text(user_id, "other")]
        gender_keyboard = [[KeyboardButton(text)] for text in gender_options]
        
        update.message.reply_text(
            get_text(user_id, "invalid_gender"),
            reply_markup=ReplyKeyboardMarkup(gender_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return config.SELECT_GENDER
    
    # Update user's gender
    update_user_data(user_id, {"gender": selected_gender})
    
    # Ask for region
    regions = get_all_regions()
    region_keyboard = [[KeyboardButton(region)] for region in regions]
    
    update.message.reply_text(
        get_text(user_id, "choose_region"),
        reply_markup=ReplyKeyboardMarkup(region_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    
    return config.SELECT_REGION

def region_selection(update: Update, context: CallbackContext) -> int:
    """Handle region selection during profile creation."""
    user = update.effective_user
    user_id = str(user.id)
    selected_region = update.message.text
    
    # Check if the region is valid
    regions = get_all_regions()
    if selected_region not in regions:
        region_keyboard = [[KeyboardButton(region)] for region in regions]
        
        update.message.reply_text(
            get_text(user_id, "invalid_region"),
            reply_markup=ReplyKeyboardMarkup(region_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return config.SELECT_REGION
    
    # Store the selected region temporarily
    context.user_data["selected_region"] = selected_region
    
    # Get countries in the selected region
    countries = get_countries_in_region(selected_region)
    
    # Split countries into chunks of 4 for better display
    country_keyboard = [countries[i:i+2] for i in range(0, len(countries), 2)]
    country_markup = ReplyKeyboardMarkup(
        [[KeyboardButton(country) for country in row] for row in country_keyboard], 
        one_time_keyboard=True, 
        resize_keyboard=True
    )
    
    update.message.reply_text(
        get_text(user_id, "choose_country_in_region", region=selected_region),
        reply_markup=country_markup
    )
    
    return config.SELECT_COUNTRY_IN_REGION

def country_selection(update: Update, context: CallbackContext) -> int:
    """Handle country selection during profile creation."""
    user = update.effective_user
    user_id = str(user.id)
    selected_country = update.message.text
    selected_region = context.user_data.get("selected_region")
    
    # Check if the country is in the selected region
    if not is_country_in_region(selected_country, selected_region):
        countries = get_countries_in_region(selected_region)
        
        # Split countries into chunks of 4 for better display
        country_keyboard = [countries[i:i+2] for i in range(0, len(countries), 2)]
        country_markup = ReplyKeyboardMarkup(
            [[KeyboardButton(country) for country in row] for row in country_keyboard], 
            one_time_keyboard=True, 
            resize_keyboard=True
        )
        
        update.message.reply_text(
            get_text(user_id, "country_not_found_in_region"),
            reply_markup=country_markup
        )
        return config.SELECT_COUNTRY_IN_REGION
    
    # Update user's country
    update_user_data(user_id, {
        "country": selected_country,
        "region": selected_region,
        "profile_complete": True
    })
    
    # Profile complete message
    update.message.reply_text(
        get_text(user_id, "profile_complete"),
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext) -> int:
    """Cancel the conversation."""
    user_id = str(update.effective_user.id)
    
    update.message.reply_text(
        get_text(user_id, "cancel_profile"),
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ConversationHandler.END

def forward_message(update: Update, context: CallbackContext) -> None:
    """Forward user messages to the target group."""
    # Skip command messages
    if update.message and update.message.text and update.message.text.startswith('/'):
        return
    
    user = update.effective_user
    user_id = str(user.id)
    
    # Check if user is blocked
    if is_user_blocked(user_id):
        return
    
    # Get user data for info
    user_data = get_user_data(user_id)
    
    try:
        # Prepare admin info header
        admin_info = get_text(
            "admin", 
            "forward_message_admin_info",
            user_name=user.full_name,
            user_id=user.id
        )
        
        # Send admin info message to group
        context.bot.send_message(
            chat_id=config.TARGET_GROUP_ID,
            text=f"{admin_info}\n"
                 f"Language: {user_data.get('language', 'Unknown')}\n"
                 f"Gender: {user_data.get('gender', 'Unknown')}\n"
                 f"Country: {user_data.get('country', 'Unknown')}"
        )
        
        # Forward the actual message
        update.message.forward(chat_id=config.TARGET_GROUP_ID)
        
    except Exception as e:
        logger.error(f"Error forwarding message: {e}")
