import os
import pandas as pd
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters, ConversationHandler

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

def start(update: Update, context: CallbackContext):
    update.message.reply_text("Welcome to the Expense Tracker Bot. Type an amount to begin.")

def main():
    updater = Updater(os.getenv("TELEGRAM_TOKEN"), use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
