import asyncio
import signal
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")  # Read from environment variable

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I will echo whatever you send.")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(update.message.text)

async def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

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
