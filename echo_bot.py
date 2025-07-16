import asyncio
import signal
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)
from datetime import datetime
import csv
import io

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ENTER_NOTE = 1

def format_entry(index, e):
    amount = f'₹{e["amount"]:.2f}'
    note = f'| {e["note"]}' if e.get("note") else ""
    return f'{index:<2}. {e["timestamp"]} | {e["account"]:<1} | {amount:<8} | {e["mode"]:<6} {note:<25}'

async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    chat_id = update.effective_chat.id

    if not text:
        return

    entry = {"chat_id": chat_id, "raw": text}

    try:
        cleaned = text.replace('₹', '').replace('rs', '').replace('RS', '').replace(' ', '')
        if cleaned.startswith('+'):
            entry["type"] = "income"
            entry["amount"] = float(cleaned[1:])
        elif cleaned.startswith('-'):
            entry["type"] = "expense"
            entry["amount"] = float(cleaned[1:])
        else:
            entry["type"] = "expense"
            entry["amount"] = float(cleaned)
    except ValueError:
        await update.message.reply_text("Invalid amount. Try:
200 → expense
+500 → income
₹300 → expense")
        return

    context.user_data["pending_entry"] = entry

    keyboard = [
        [InlineKeyboardButton("Cash", callback_data="mode:Cash"),
         InlineKeyboardButton("Online", callback_data="mode:Online")]
    ]
    await update.message.reply_text("Select mode of payment:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    entry = context.user_data.get("pending_entry", {})

    if data.startswith("mode:"):
        entry["mode"] = data.split(":", 1)[1]
        keyboard = [
            [InlineKeyboardButton("A", callback_data="acct:A"),
             InlineKeyboardButton("S", callback_data="acct:S"),
             InlineKeyboardButton("C", callback_data="acct:C"),
             InlineKeyboardButton("O", callback_data="acct:O")]
        ]
        await query.edit_message_text("Select account:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("acct:"):
        entry["account"] = data.split(":", 1)[1]
        now = datetime.now()
        entry["timestamp"] = now.strftime("%a %d/%m %H:%M")  # Day + Date
        await query.edit_message_text("Enter a short note for this entry (or type '-' to skip):")
        return ENTER_NOTE

    elif data.startswith("filter_acct:"):
        account = data.split(":")[1]
        entries = context.user_data.get("entries", [])
        filtered = [e for e in entries if e["account"] == account]
        if not filtered:
            await query.edit_message_text(f"No entries found for account {account}.")
            return

        filtered.sort(key=lambda x: x["account"])
        lines = [format_entry(i + 1, e) for i, e in enumerate(filtered)]
        total_income = sum(e["amount"] for e in filtered if e["type"] == "income")
        total_expense = sum(e["amount"] for e in filtered if e["type"] == "expense")
        lines.append(f'\nTotal Income: ₹{total_income:.2f}')
        lines.append(f'Total Expense: ₹{total_expense:.2f}')
        await query.edit_message_text("\n".join(lines))

async def handle_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note = update.message.text.strip()
    entry = context.user_data.get("pending_entry", {})
    entry["note"] = "" if note == "-" else note
    context.user_data.setdefault("entries", []).append(entry)
    context.user_data["pending_entry"] = None
    await update.message.reply_text("Entry saved.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today_str = datetime.now().strftime("%d/%m")
    entries = context.user_data.get("entries", [])
    today_entries = [e for e in entries if today_str in e["timestamp"]]
    if not today_entries:
        await update.message.reply_text("No entries for today.")
        return

    today_entries.sort(key=lambda x: x["account"])
    lines = [format_entry(i + 1, e) for i, e in enumerate(today_entries)]
    total_income = sum(e["amount"] for e in today_entries if e["type"] == "income")
    total_expense = sum(e["amount"] for e in today_entries if e["type"] == "expense")
    lines.append(f'\nTotal Income: ₹{total_income:.2f}')
    lines.append(f'Total Expense: ₹{total_expense:.2f}')
    await update.message.reply_text("\n".join(lines))

async def export_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    entries = context.user_data.get("entries", [])
    if not entries:
        await update.message.reply_text("No data to export.")
        return

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["type", "amount", "mode", "account", "timestamp", "note"])
    writer.writeheader()
    writer.writerows(entries)
    output.seek(0)
    await update.message.reply_document(document=io.BytesIO(output.read().encode()), filename="expenses.csv")

async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Edit feature not implemented yet.")

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["entries"] = []
    await update.message.reply_text("All entries deleted.")

async def filter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("A", callback_data="filter_acct:A"),
         InlineKeyboardButton("S", callback_data="filter_acct:S"),
         InlineKeyboardButton("C", callback_data="filter_acct:C"),
         InlineKeyboardButton("O", callback_data="filter_acct:O")]
    ]
    await update.message.reply_text("Select account to filter:", reply_markup=InlineKeyboardMarkup(keyboard))

async def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)],
        states={
            ENTER_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_note)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("csv", export_csv))
    app.add_handler(CommandHandler("edit", edit))
    app.add_handler(CommandHandler("delete", delete))
    app.add_handler(CommandHandler("filter", filter_command))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    print("Bot is running. Press Ctrl+C to stop.")

    stop_event = asyncio.Event()

    def handle_shutdown():
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in ('SIGINT', 'SIGTERM'):
        loop.add_signal_handler(getattr(signal, sig), handle_shutdown)

    try:
        await stop_event.wait()
    finally:
        print("Shutting down...")
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped.")
