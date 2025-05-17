import logging
from typing import Dict, Any, List
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler

import config
from data_handler import (
    get_user_data, has_complete_profile, is_premium_user,
    get_all_regions, get_countries_in_region, find_matching_users
)
from localization import get_text
from payment_handlers import show_payment_info

# Initialize logger
logger = logging.getLogger(__name__)

def start_partner_search(update: Update, context: CallbackContext) -> int:
    """Start the partner search process."""
    user = update.effective_user
    user_id = str(user.id)
    
    # Check if user has a complete profile
    if not has_complete_profile(user_id):
        update.message.reply_text(get_text(user_id, "profile_incomplete"))
        return ConversationHandler.END
    
    # Check if user has premium status
    if not is_premium_user(user_id):
        # Show payment information
        show_payment_info(update, context)
        return ConversationHandler.END
    
    # Start the search process - first ask for language preference
    lang_keyboard = []
    for code, name in config.SUPPORTED_LANGUAGES.items():
        lang_keyboard.append([KeyboardButton(name)])
    
    # Add "Any Language" option
    lang_keyboard.append([KeyboardButton("Any Language")])
    
    update.message.reply_text(
        get_text(user_id, "search_partner_prompt_language"),
        reply_markup=ReplyKeyboardMarkup(lang_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    
    return config.SEARCH_PARTNER_LANG

def search_partner_language(update: Update, context: CallbackContext) -> int:
    """Handle language selection for partner search."""
    user = update.effective_user
    user_id = str(user.id)
    language_name = update.message.text
    
    # Initialize search criteria if not yet created
    if "search_criteria" not in context.user_data:
        context.user_data["search_criteria"] = {"user_id": user_id}
    
    # Handle "Any Language" selection
    if language_name == "Any Language":
        context.user_data["search_criteria"]["language"] = "any"
    else:
        # Find the language code for the selected language name
        selected_lang = None
        for code, name in config.SUPPORTED_LANGUAGES.items():
            if name == language_name:
                selected_lang = code
                break
        
        # If invalid language, ask again
        if not selected_lang:
            lang_keyboard = []
            for code, name in config.SUPPORTED_LANGUAGES.items():
                lang_keyboard.append([KeyboardButton(name)])
            
            # Add "Any Language" option
            lang_keyboard.append([KeyboardButton("Any Language")])
            
            update.message.reply_text(
                get_text(user_id, "invalid_language"),
                reply_markup=ReplyKeyboardMarkup(lang_keyboard, one_time_keyboard=True, resize_keyboard=True)
            )
            return config.SEARCH_PARTNER_LANG
        
        # Store the selected language in search criteria
        context.user_data["search_criteria"]["language"] = selected_lang
    
    # Next, ask for gender preference
    gender_options = [
        get_text(user_id, "male"), 
        get_text(user_id, "female"), 
        get_text(user_id, "other"),
        get_text(user_id, "any_gender")
    ]
    gender_keyboard = [[KeyboardButton(text)] for text in gender_options]
    
    update.message.reply_text(
        get_text(user_id, "search_partner_prompt_gender"),
        reply_markup=ReplyKeyboardMarkup(gender_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    
    return config.SEARCH_PARTNER_GENDER

def search_partner_gender(update: Update, context: CallbackContext) -> int:
    """Handle gender selection for partner search."""
    user = update.effective_user
    user_id = str(user.id)
    selected_gender = update.message.text
    
    # Map selected gender text to internal representation
    gender_mapping = {
        get_text(user_id, "male"): "male",
        get_text(user_id, "female"): "female",
        get_text(user_id, "other"): "other",
        get_text(user_id, "any_gender"): "any"
    }
    
    # If invalid gender, ask again
    if selected_gender not in gender_mapping:
        gender_options = [
            get_text(user_id, "male"), 
            get_text(user_id, "female"), 
            get_text(user_id, "other"),
            get_text(user_id, "any_gender")
        ]
        gender_keyboard = [[KeyboardButton(text)] for text in gender_options]
        
        update.message.reply_text(
            get_text(user_id, "invalid_gender"),
            reply_markup=ReplyKeyboardMarkup(gender_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return config.SEARCH_PARTNER_GENDER
    
    # Store the selected gender in search criteria
    context.user_data["search_criteria"]["gender"] = gender_mapping[selected_gender]
    
    # Next, ask for region preference
    regions = get_all_regions()
    region_keyboard = [[KeyboardButton(region)] for region in regions]
    
    # Add "Any Region" option
    region_keyboard.append([KeyboardButton(get_text(user_id, "any_region"))])
    
    update.message.reply_text(
        get_text(user_id, "search_partner_prompt_region"),
        reply_markup=ReplyKeyboardMarkup(region_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    
    return config.SEARCH_PARTNER_REGION

def search_partner_region(update: Update, context: CallbackContext) -> int:
    """Handle region selection for partner search."""
    user = update.effective_user
    user_id = str(user.id)
    selected_region = update.message.text
    
    # Handle "Any Region" selection
    if selected_region == get_text(user_id, "any_region"):
        context.user_data["search_criteria"]["region"] = "any"
        context.user_data["search_criteria"]["country"] = "any"
        
        # Skip to search
        return perform_search(update, context)
    
    # Validate region
    regions = get_all_regions()
    if selected_region not in regions:
        region_keyboard = [[KeyboardButton(region)] for region in regions]
        
        # Add "Any Region" option
        region_keyboard.append([KeyboardButton(get_text(user_id, "any_region"))])
        
        update.message.reply_text(
            get_text(user_id, "invalid_region"),
            reply_markup=ReplyKeyboardMarkup(region_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return config.SEARCH_PARTNER_REGION
    
    # Store the selected region in search criteria and user data for next step
    context.user_data["search_criteria"]["region"] = selected_region
    context.user_data["selected_region"] = selected_region
    
    # Next, ask for country preference
    countries = get_countries_in_region(selected_region)
    country_keyboard = [[KeyboardButton(country)] for country in countries]
    
    # Add "Any Country" option
    country_keyboard.append([KeyboardButton(get_text(user_id, "any_country"))])
    
    update.message.reply_text(
        get_text(user_id, "search_partner_prompt_country"),
        reply_markup=ReplyKeyboardMarkup(country_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    
    return config.SEARCH_PARTNER_COUNTRY

def search_partner_country(update: Update, context: CallbackContext) -> int:
    """Handle country selection for partner search."""
    user = update.effective_user
    user_id = str(user.id)
    selected_country = update.message.text
    selected_region = context.user_data.get("selected_region")
    
    # Handle "Any Country" selection
    if selected_country == get_text(user_id, "any_country"):
        context.user_data["search_criteria"]["country"] = "any"
        
        # Perform the search
        return perform_search(update, context)
    
    # Validate country
    countries = get_countries_in_region(selected_region)
    if selected_country not in countries:
        country_keyboard = [[KeyboardButton(country)] for country in countries]
        
        # Add "Any Country" option
        country_keyboard.append([KeyboardButton(get_text(user_id, "any_country"))])
        
        update.message.reply_text(
            get_text(user_id, "invalid_country"),
            reply_markup=ReplyKeyboardMarkup(country_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return config.SEARCH_PARTNER_COUNTRY
    
    # Store the selected country in search criteria
    context.user_data["search_criteria"]["country"] = selected_country
    
    # Perform the search
    return perform_search(update, context)

def perform_search(update: Update, context: CallbackContext) -> int:
    """Perform search with the collected criteria and display results."""
    user = update.effective_user
    user_id = str(user.id)
    
    # Get the search criteria
    search_criteria = context.user_data.get("search_criteria", {})
    
    # Find matching users
    matching_users = find_matching_users(search_criteria)
    
    # Display results
    if not matching_users:
        update.message.reply_text(
            get_text(user_id, "search_results_none"),
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        # Prepare message with results
        result_message = get_text(user_id, "search_results_found", count=len(matching_users)) + "\n\n"
        
        for i, match in enumerate(matching_users, 1):
            match_info = (
                f"{i}. {match['name']}\n"
                f"   {get_text(user_id, 'language')}: {config.SUPPORTED_LANGUAGES.get(match['language'], match['language'])}\n"
                f"   {get_text(user_id, 'gender')}: {get_text(user_id, match['gender'])}\n"
                f"   {get_text(user_id, 'country')}: {match['country']}\n"
            )
            
            if match.get('username'):
                match_info += f"   @{match['username']}\n"
            
            result_message += match_info + "\n"
        
        update.message.reply_text(
            result_message,
            reply_markup=ReplyKeyboardRemove()
        )
    
    # Clear search criteria
    if "search_criteria" in context.user_data:
        del context.user_data["search_criteria"]
    if "selected_region" in context.user_data:
        del context.user_data["selected_region"]
    
    return ConversationHandler.END