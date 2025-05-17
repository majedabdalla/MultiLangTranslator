import logging
from typing import Dict, Any, List
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler

import config
from data_handler import is_premium_user, update_user_data, load_pending_payments, save_pending_payments
from localization import get_text

# Initialize logger
logger = logging.getLogger(__name__)

def show_payment_info(update: Update, context: CallbackContext) -> None:
    """Show payment information to the user."""
    user = update.effective_user
    user_id = str(user.id)
    
    # Check if user already has premium status
    if is_premium_user(user_id):
        update.message.reply_text(get_text(user_id, "feature_already_activated"))
        return
    
    # Show payment options
    payment_text = get_text(
        user_id, 
        "payment_prompt", 
        payeer_account=config.PAYEER_ACCOUNT,
        bitcoin_address=config.BITCOIN_ADDRESS
    )
    
    # Create inline keyboard for payment verification
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, "payment_verify_button"), callback_data="verify_payment")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(payment_text, reply_markup=reply_markup)

def payment_verification_callback(update: Update, context: CallbackContext) -> int:
    """Handle payment verification button click."""
    query = update.callback_query
    query.answer()
    
    user = query.from_user
    user_id = str(user.id)
    
    # Ask user to send payment proof
    query.edit_message_text(get_text(user_id, "payment_send_proof"))
    
    # Set conversation state to wait for payment proof
    context.user_data["awaiting_payment_proof"] = True
    
    return config.PAYMENT_PROOF

def handle_payment_proof(update: Update, context: CallbackContext) -> int:
    """Process payment proof sent by user."""
    user = update.effective_user
    user_id = str(user.id)
    
    # Only process if we're awaiting payment proof from this user
    if not context.user_data.get("awaiting_payment_proof"):
        return ConversationHandler.END
    
    # Reset the awaiting flag
    context.user_data["awaiting_payment_proof"] = False
    
    # Add to pending payments list
    pending_payments = load_pending_payments()
    pending_payments.append({
        "user_id": user_id,
        "name": user.full_name,
        "username": user.username,
        "timestamp": datetime.now().isoformat(),
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
        
        context.bot.send_message(
            chat_id=config.ADMIN_ID,
            text=admin_notification,
            reply_markup=reply_markup
        )
        
        # Forward the actual payment proof to admin
        context.bot.forward_message(
            chat_id=config.ADMIN_ID,
            from_chat_id=update.message.chat_id,
            message_id=update.message.message_id
        )
    except Exception as e:
        logger.error(f"Error notifying admin about payment: {e}")
    
    # Notify user that payment is being processed
    update.message.reply_text(get_text(user_id, "payment_received_pending_verification"))
    
    return ConversationHandler.END

def payment_command(update: Update, context: CallbackContext) -> None:
    """Handle /payment command to show payment information."""
    show_payment_info(update, context)