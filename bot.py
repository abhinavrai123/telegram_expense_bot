from flask import Flask, request
import telegram
import os
import pandas as pd
from datetime import datetime, date

TOKEN = os.environ.get("TELEGRAM_TOKEN")
bot = telegram.Bot(token=TOKEN)
app = Flask(__name__)
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

def save_entry(user_id, amount, mode, category, note, entry_type):
    file_path = os.path.join(DATA_DIR, f"{user_id}_{date.today()}.csv")
    df = pd.DataFrame([{
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "amount": amount,
        "mode": mode,
        "category": category,
        "note": note,
        "type": entry_type
    }])
    if os.path.exists(file_path):
        df.to_csv(file_path, mode="a", header=False, index=False)
    else:
        df.to_csv(file_path, index=False)

def format_today_summary(user_id):
    file_path = os.path.join(DATA_DIR, f"{user_id}_{date.today()}.csv")
    if not os.path.exists(file_path):
        return "📭 No records for today."
    df = pd.read_csv(file_path)
    if df.empty:
        return "📭 No records for today."

    msg = "*📊 Today's Summary:*
"
    total = 0
    for _, row in df.iterrows():
        dt = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")
        t = dt.strftime("%H:%M")
        amt = row["amount"]
        sign = "+" if row.get("type") == "income" else "-"
        total += amt if sign == "+" else -amt
        icon = "💰" if sign == "+" else "💸"
        msg += f"{icon} {t} | {sign}₹{amt:.2f} | {row['mode']} | {row['category']} | {row['note']}
"
    msg += f"
💰 Net Total: {'+' if total >=0 else '-'}₹{abs(total):.2f}"
    return msg

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    chat_id = update.message.chat.id
    text = update.message.text.strip()

    if text.lower() == "/today":
        msg = format_today_summary(chat_id)
        bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
        return "ok"

    if text.startswith("+") or text.replace(".", "").isdigit():
        amount = float(text.lstrip("+"))
        entry_type = "income" if text.startswith("+") else "expense"
        bot.send_message(chat_id=chat_id, text="Mode? (Cash/Online)")
        context[chat_id] = {"amount": amount, "type": entry_type, "step": "mode"}
        return "ok"

    if chat_id in context:
        state = context[chat_id]
        if state["step"] == "mode":
            state["mode"] = text
            bot.send_message(chat_id=chat_id, text="Category? (A/S/L/C/O)")
            state["step"] = "category"
        elif state["step"] == "category":
            state["category"] = text
            bot.send_message(chat_id=chat_id, text="Note?")
            state["step"] = "note"
        elif state["step"] == "note":
            state["note"] = text
            save_entry(chat_id, state["amount"], state["mode"], state["category"], state["note"], state["type"])
            bot.send_message(chat_id=chat_id, text="✅ Entry saved.")
            context.pop(chat_id)
        return "ok"

    bot.send_message(chat_id=chat_id, text="Send an amount (e.g. 250 or +1000) to begin.")
    return "ok"

context = {}

@app.route("/", methods=["GET"])
def index():
    return "Bot is running."
