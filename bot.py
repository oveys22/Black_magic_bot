from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import random, asyncio

ASK_NAME, PLAY = range(2)

spells = ['آب', 'آتش', 'سنگ']
players = {}

def who_wins(c1, c2):
    if c1 == c2:
        return 0  # مساوی
    if (c1 == 'آب' and c2 == 'آتش') or (c1 == 'آتش' and c2 == 'سنگ') or (c1 == 'سنگ' and c2 == 'آب'):
        return 1
    return 2

def build_keyboard():
    keyboard = [
        [InlineKeyboardButton("💧 آب", callback_data='آب')],
        [InlineKeyboardButton("🔥 آتش", callback_data='آتش')],
        [InlineKeyboardButton("🪨 سنگ", callback_data='سنگ')],
        [InlineKeyboardButton("❌ لغو بازی", callback_data='لغو')]
    ]
    return InlineKeyboardMarkup(keyboard)

def hearts(score):
    return "❤️" * score if score > 0 else "❌"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in players:
        await update.message.reply_text(
            f"🎮 سلام {update.effective_user.first_name}!\n"
            f"به دنیای جادوی سیاه خوش اومدی!\n\n"
            "🧙 لطفاً اسم یا یوزرنیم خودتو بفرست تا ثبت‌نامت کنیم."
        )
        return ASK_NAME
    else:
        await show_rules(update, context, user_id)
        return PLAY

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.message.text.strip()
    players[user_id] = {'name': name, 'score': 3}
    context.chat_data['bot_score'] = 3
    await show_rules(update, context, user_id)
    return PLAY

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    # نمایش قوانین قبل از شروع بازی
    rules_text = (
        "📜 *قوانین بازی جادوی سیاه:*\n\n"
        "💧 *آب*، 🔥 *آتش* رو شکست میده\n"
        "🔥 *آتش*، 🪨 *سنگ* رو شکست میده\n"
        "🪨 *سنگ*، 💧 *آب* رو شکست میده\n\n"
        "هر بازیکن 3 ❤️ داره؛ هر بار ببازی 1 ❤️ از دست میدی!\n"
        "هر کی زودتر همه ❤️هاشو از دست بده بازنده‌ست.\n\n"
        "✨ *حالا بازی شروع میشه...!*"
    )
    await update.message.reply_text(rules_text, parse_mode="Markdown")
    await start_game(update, context, user_id)

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id=None):
    if user_id is None:
        user_id = update.effective_user.id
    text = (
        f"🧙 {players[user_id]['name']}: {hearts(3)}\n"
        f"🤖 رقیب: {hearts(3)}\n\n"
        "جادوی خودتو انتخاب کن:"
    )
    msg = await update.message.reply_text(text, reply_markup=build_keyboard())
    context.chat_data['message_id'] = msg.message_id

    # تایمر 30 ثانیه‌ای برای حرکت
    context.chat_data['timeout_active'] = True
    context.chat_data['timeout_task'] = asyncio.create_task(timeout_checker(context, update, user_id))

async def timeout_checker(context, update, user_id):
    await asyncio.sleep(30)
    if context.chat_data.get('timeout_active', True):
        await update.effective_chat.send_message(
            f"⏰ زمان تموم شد!\nبرنده: 🤖 رقیب\nبازنده: {players[user_id]['name']}"
        )
        players[user_id]['score'] = 0

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in players:
        await query.edit_message_text("لطفا اول با /start ثبت‌نام کن.")
        return ConversationHandler.END

    if query.data == "لغو":
        await query.edit_message_text("❌ بازی لغو شد.")
        return ConversationHandler.END

    # ریست تایمر وقتی کاربر حرکت کرد
    context.chat_data['timeout_active'] = False

    player_choice = query.data
    bot_choice = random.choice(spells)
    result = who_wins(player_choice, bot_choice)

    if result == 1:
        context.chat_data['bot_score'] -= 1
    elif result == 2:
        players[user_id]['score'] -= 1

    text = (
        f"تو {player_choice} انتخاب کردی.\n"
        f"رقیب {bot_choice} انتخاب کرد.\n\n"
        f"🧙 {players[user_id]['name']}: {hearts(players[user_id]['score'])}\n"
        f"🤖 رقیب: {hearts(context.chat_data['bot_score'])}"
    )

    if players[user_id]['score'] <= 0:
        text += "\n\n❌ بازی تموم شد! رقیب برنده شد."
        await query.edit_message_text(text)
        return ConversationHandler.END
    elif context.chat_data['bot_score'] <= 0:
        text += f"\n\n🏆 تبریک! برنده {players[user_id]['name']} هست."
        await query.edit_message_text(text)
        return ConversationHandler.END
    else:
        text += "\n\nجادوی بعدی رو انتخاب کن:"
        context.chat_data['timeout_active'] = True
        await query.edit_message_text(text, reply_markup=build_keyboard())
        context.chat_data['timeout_task'] = asyncio.create_task(timeout_checker(context, update, user_id))
        return PLAY

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("بازی لغو شد.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

if __name__ == '__main__':
    TOKEN = "8070225493:AAEcEuOde4hfhkRwpa3B7rhV4d6uJLRgWW8"

    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & (~filters.COMMAND), ask_name)],
            PLAY: [CallbackQueryHandler(button_handler)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    app.add_handler(conv_handler)
    app.run_polling()
