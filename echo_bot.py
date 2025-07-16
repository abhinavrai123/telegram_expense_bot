import asyncio
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN_HERE"

ASKING_AMOUNT, ASKING_TYPE, ASKING_MODE, ASKING_ACCOUNT, ASKING_NOTE, ASKING_DATETIME = range(6)
user_transactions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please enter the amount:")
    return ASKING_AMOUNT

async def ask_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    try:
        amount = float(text)
        context.user_data["entry"] = {"amount": amount}
        keyboard = [
            [InlineKeyboardButton("Expense", callback_data="expense"),
             InlineKeyboardButton("Income", callback_data="income")]
        ]
        await update.message.reply_text("Is this an expense or income?",
                                        reply_markup=InlineKeyboardMarkup(keyboard))
        return ASKING_TYPE
    except ValueError:
        await update.message.reply_text("Invalid input. Please enter a valid number.")
        return ASKING_AMOUNT

async def handle_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["entry"]["type"] = query.data
    keyboard = [
        [InlineKeyboardButton("Cash", callback_data="Cash"),
         InlineKeyboardButton("Online", callback_data="Online")]
    ]
    await query.message.reply_text("Select mode of payment:",
                                   reply_markup=InlineKeyboardMarkup(keyboard))
    return ASKING_MODE

async def handle_mode_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["entry"]["mode"] = query.data
    keyboard = [
        [InlineKeyboardButton("A", callback_data="A"),
         InlineKeyboardButton("S", callback_data="S"),
         InlineKeyboardButton("C", callback_data="C"),
         InlineKeyboardButton("O", callback_data="O")]
    ]
    await query.message.reply_text("Select account:",
                                   reply_markup=InlineKeyboardMarkup(keyboard))
    return ASKING_ACCOUNT

async def handle_account_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["entry"]["account"] = query.data
    await query.message.reply_text("Add a note (or type '-' for none):")
    return ASKING_NOTE

async def handle_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note = update.message.text
    context.user_data["entry"]["note"] = note if note.strip() != "-" else ""
    await update.message.reply_text("Enter date and time (dd/mm hh:mm):")
    return ASKING_DATETIME

async def handle_datetime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    entry = context.user_data.get("entry", {})
    entry["datetime"] = update.message.text.strip()
    user_id = update.effective_user.id
    user_transactions.setdefault(user_id, []).append(entry)
    await update.message.reply_text("Transaction saved.")
    return ConversationHandler.END

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    txns = user_transactions.get(user_id, [])
    if not txns:
        await update.message.reply_text("No transactions today.")
        return
    lines = []
    for t in txns:
        line = f"{t['datetime']} | {t['account']} | {t['amount']} | {t['mode']} | {t['note']}"
        lines.append(line)
    income = sum(t["amount"] for t in txns if t["type"] == "income")
    expense = sum(t["amount"] for t in txns if t["type"] == "expense")
    lines.append(f"Total Income: {income}, Total Expense: {expense}")
    await update.message.reply_text("\n".join(lines))

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END

async def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASKING_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_type)],
            ASKING_TYPE: [CallbackQueryHandler(handle_type_selection, pattern="^(expense|income)$")],
            ASKING_MODE: [CallbackQueryHandler(handle_mode_selection, pattern="^(Cash|Online)$")],
            ASKING_ACCOUNT: [CallbackQueryHandler(handle_account_selection, pattern="^(A|S|C|O)$")],
            ASKING_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_note)],
            ASKING_DATETIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_datetime)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("today", today))

    print("Bot is running.")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(run_bot())
