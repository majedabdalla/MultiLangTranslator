import json
import os
import logging
from typing import Dict, Any
import config

# Initialize logger
logger = logging.getLogger(__name__)

# Cache for loaded translations
loaded_translations = {}

def load_translation_file(lang_code: str) -> Dict[str, str]:
    """Load a translation file for a specific language."""
    if lang_code in loaded_translations:
        return loaded_translations[lang_code]
    
    try:
        file_path = os.path.join(config.LOCALES_DIR, f"{lang_code}.json")
        with open(file_path, "r", encoding="utf-8") as file:
            translations = json.load(file)
            loaded_translations[lang_code] = translations
            return translations
    except FileNotFoundError:
        logger.warning(f"Translation file for {lang_code} not found at {file_path}. Falling back to default language.")
        if lang_code != config.DEFAULT_LANGUAGE:
            return load_translation_file(config.DEFAULT_LANGUAGE)
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from translation file {file_path}: {e}")
        if lang_code != config.DEFAULT_LANGUAGE:
            return load_translation_file(config.DEFAULT_LANGUAGE)
        return {}
    except Exception as e:
        logger.error(f"Unexpected error loading translation file {file_path}: {e}")
        if lang_code != config.DEFAULT_LANGUAGE:
            return load_translation_file(config.DEFAULT_LANGUAGE)
        return {}

def get_user_language(user_id: str) -> str:
    """Get the language code for a specific user."""
    from data_handler import get_user_data
    user_data = get_user_data(user_id)
    return user_data.get("language", config.DEFAULT_LANGUAGE)

def get_text(user_id: str, key: str, lang_code: str = None, **kwargs) -> str:
    """Get a localized text string for a user."""
    effective_lang = lang_code or get_user_language(user_id)
    
    # Load translations if not already in cache
    if effective_lang not in loaded_translations:
        load_translation_file(effective_lang)
    
    # Get translations for the language
    translations = loaded_translations.get(effective_lang, {})
    
    # Fall back to default language if translation not found
    if not translations or key not in translations:
        if effective_lang != config.DEFAULT_LANGUAGE:
            return get_text(user_id, key, config.DEFAULT_LANGUAGE, **kwargs)
        else:
            return f"Missing translation: {key}"
    
    # Get the message and apply format parameters
    message = translations[key]
    if kwargs:
        try:
            message = message.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing placeholder {e} in translation key '{key}' for language '{effective_lang}'")
    
    return message

# Preload all supported languages
def preload_translations():
    """Preload all supported language translations into memory."""
    for lang_code in config.SUPPORTED_LANGUAGES.keys():
        load_translation_file(lang_code)
    logger.info(f"Preloaded translations for: {', '.join(config.SUPPORTED_LANGUAGES.keys())}")

# Initialize translations
preload_translations()
