import logging
from typing import Dict, Any, List
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler

import config
from data_handler import load_user_data, update_user_data, load_pending_payments, save_pending_payments
from localization import get_text

# Initialize logger
logger = logging.getLogger(__name__)

def block_user(update: Update, context: CallbackContext) -> None:
    """Block a user from using the bot."""
    # Check if command is from admin
    if update.effective_user.id != config.ADMIN_ID:
        return
    
    # Check if user ID was provided
    if not context.args or not context.args[0].isdigit():
        update.message.reply_text("Usage: /block <user_id>")
        return
    
    user_id = context.args[0]
    user_data = load_user_data()
    
    # Check if user exists
    if user_id not in user_data:
        update.message.reply_text(
            get_text("admin", "admin_error_user_not_found", user_id=user_id)
        )
        return
    
    # Update user's blocked status
    user_data[user_id]["blocked"] = True
    update_user_data(user_id, {"blocked": True})
    
    update.message.reply_text(
        get_text("admin", "admin_user_blocked", user_id=user_id)
    )

def unblock_user(update: Update, context: CallbackContext) -> None:
    """Unblock a user."""
    # Check if command is from admin
    if update.effective_user.id != config.ADMIN_ID:
        return
    
    # Check if user ID was provided
    if not context.args or not context.args[0].isdigit():
        update.message.reply_text("Usage: /unblock <user_id>")
        return
    
    user_id = context.args[0]
    user_data = load_user_data()
    
    # Check if user exists
    if user_id not in user_data:
        update.message.reply_text(
            get_text("admin", "admin_error_user_not_found", user_id=user_id)
        )
        return
    
    # Update user's blocked status
    user_data[user_id]["blocked"] = False
    update_user_data(user_id, {"blocked": False})
    
    update.message.reply_text(
        get_text("admin", "admin_user_unblocked", user_id=user_id)
    )

def list_users(update: Update, context: CallbackContext) -> None:
    """List all users of the bot."""
    # Check if command is from admin
    if update.effective_user.id != config.ADMIN_ID:
        return
    
    user_data = load_user_data()
    
    if not user_data:
        update.message.reply_text("No users registered yet.")
        return
    
    # Build user list message
    message_chunks = ["📊 Registered Users:\n"]
    
    for user_id, data in user_data.items():
        user_info = (
            f"👤 ID: {user_id}\n"
            f"   Name: {data.get('name', 'Unknown')}\n"
            f"   Username: {data.get('username', 'None')}\n"
            f"   Language: {data.get('language', 'Unknown')}\n"
            f"   Gender: {data.get('gender', 'Unknown')}\n"
            f"   Country: {data.get('country', 'Unknown')}\n"
            f"   Premium: {'✅' if data.get('premium', False) else '❌'}\n"
            f"   Blocked: {'⛔' if data.get('blocked', False) else '✅'}\n"
        )
        
        # Telegram has a message limit, so split into multiple messages if needed
        if len(message_chunks[-1] + user_info) > 4000:
            message_chunks.append(user_info)
        else:
            message_chunks[-1] += user_info
    
    # Send messages
    for chunk in message_chunks:
        update.message.reply_text(chunk)

def verify_payment_callback(update: Update, context: CallbackContext) -> None:
    """Handle admin's payment verification callbacks."""
    query = update.callback_query
    query.answer()
    
    # Check if admin
    if query.from_user.id != config.ADMIN_ID:
        return
    
    data = query.data
    
    # Extract action and user_id from callback data
    if data.startswith("approve_payment_") or data.startswith("reject_payment_"):
        action, user_id = data.split("_")[0], data.split("_")[2]
        
        # Handle approval
        if action == "approve":
            # Update user's premium status
            update_user_data(user_id, {"premium": True})
            
            # Update pending payment status
            pending_payments = load_pending_payments()
            for payment in pending_payments:
                if payment["user_id"] == user_id and payment["status"] == "pending":
                    payment["status"] = "approved"
            save_pending_payments(pending_payments)
            
            # Notify admin
            query.edit_message_text(
                get_text("admin", "admin_payment_verified", user_id=user_id)
            )
            
            # Notify user
            try:
                context.bot.send_message(
                    chat_id=int(user_id),
                    text=get_text(user_id, "feature_activated")
                )
            except Exception as e:
                logger.error(f"Error notifying user about payment approval: {e}")
        
        # Handle rejection
        elif action == "reject":
            # Update pending payment status
            pending_payments = load_pending_payments()
            for payment in pending_payments:
                if payment["user_id"] == user_id and payment["status"] == "pending":
                    payment["status"] = "rejected"
            save_pending_payments(pending_payments)
            
            # Notify admin
            query.edit_message_text(f"Payment from user {user_id} has been rejected.")
            
            # Notify user
            try:
                context.bot.send_message(
                    chat_id=int(user_id),
                    text=get_text(user_id, "payment_rejected")
                )
            except Exception as e:
                logger.error(f"Error notifying user about payment rejection: {e}")
