import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = "7837128791:AAEH5JYPFuF3oqbDwA2Og7SGZDpSS0sgGOA"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I will echo whatever you send.")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(update.message.text)

async def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Initialize and start the bot
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    print("Bot is running. Press Ctrl+C to stop.")

    # Wait until interrupted
    stop_event = asyncio.Event()

    def handle_shutdown(*_):
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

# Entry point
if __name__ == "__main__":
    import signal

    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped.")
