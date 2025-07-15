import telebot
import os
import pandas as pd
from datetime import datetime, date
from flask import Flask, request

bot = telebot.TeleBot("")
app = Flask(__name__)

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

context = {}

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
        return "No records for today."
    df = pd.read_csv(file_path)
    if df.empty:
        return "No records for today."

    msg = "*Today's Summary:*\n"
    total = 0
    for _, row in df.iterrows():
        dt = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")
        t = dt.strftime("%H:%M")
        amt = row["amount"]
        sign = "+" if row.get("type") == "income" else "-"
        total += amt if sign == "+" else -amt
        msg += f"{t} | {sign}₹{amt:.2f} | {row['mode']} | {row['category']} | {row['note']}\n"
    msg += f"\nNet Total: {'+' if total >=0 else '-'}₹{abs(total):.2f}"
    return msg


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "Welcome to Expense Tracker Bot!\nEnter an amount to begin. Use + for income, e.g., +500")

@bot.message_handler(commands=['today'])
def send_summary(message):
    summary = format_today_summary(message.chat.id)
    bot.send_message(message.chat.id, summary, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text.startswith("+") or msg.text.replace(".", "").isdigit())
def handle_amount(message):
    amount = float(message.text.lstrip("+"))
    entry_type = "income" if message.text.startswith("+") else "expense"
    bot.send_message(message.chat.id, "Mode? (Cash/Online)")
    context[message.chat.id] = {"amount": amount, "type": entry_type, "step": "mode"}

@bot.message_handler(func=lambda msg: msg.chat.id in context)
def handle_steps(message):
    state = context[message.chat.id]
    if state["step"] == "mode":
        state["mode"] = message.text
        bot.send_message(message.chat.id, "Category? (A/S/L/C/O)")
        state["step"] = "category"
    elif state["step"] == "category":
        state["category"] = message.text
        bot.send_message(message.chat.id, "Note?")
        state["step"] = "note"
    elif state["step"] == "note":
        state["note"] = message.text
        save_entry(message.chat.id, state["amount"], state["mode"], state["category"], state["note"], state["type"])
        bot.send_message(message.chat.id, "Entry saved.")
        context.pop(message.chat.id)

@app.route(f"/{""}", methods=["POST"])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "ok"

@app.route("/", methods=["GET"])
def index():
    return "Bot is running."
