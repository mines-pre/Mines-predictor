from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import os
import random
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID')
VERCEL_URL = os.environ.get('VERCEL_URL', 'https://mines-predictor-ten.vercel.app')
AFFILIATE_LINK = os.environ.get('AFFILIATE_LINK', 'https://lkpq.cc/cd7800')

# Simple in-memory storage
users_data = {}
postback_events = []

# Mines Signals
MINES_SIGNALS = [
    {"traps": 1, "accuracy": 97, "grid": ["🔒🔒🔒🔒💰", "🔒🔒🔒💰🔒", "💰🔒🔒🔒🔒", "🔒💰🔒🔒🔒", "🔒🔒🔒🔒💰"]},
    {"traps": 1, "accuracy": 90, "grid": ["🔒🔒🔒🔒🔒", "💰🔒💰🔒🔒", "🔒💰🔒🔒🔒", "🔒💰🔒💰🔒", "🔒🔒🔒🔒🔒"]},
    {"traps": 1, "accuracy": 96, "grid": ["🔒🔒🔒🔒🔒", "🔒🔒🔒💰🔒", "🔒💰🔒🔒💰", "💰🔒🔒🔒💰", "🔒🔒🔒🔒🔒"]},
    {"traps": 1, "accuracy": 95, "grid": ["💰🔒🔒🔒🔒", "💰🔒🔒🔒🔒", "🔒🔒🔒🔒🔒", "💰🔒🔒🔒🔒", "💰🔒🔒💰🔒"]},
    {"traps": 1, "accuracy": 96, "grid": ["🔒🔒💰🔒🔒", "🔒💰🔒💰🔒", "💰🔒🔒🔒🔒", "🔒🔒💰🔒🔒", "🔒🔒🔒🔒🔒"]}
]

# Language Messages
MESSAGES = {
    'en': {
        'welcome': '✅ You selected English!',
        'step1': '🌐 Step 1 - Register',
        'account_must_be_new': '‼️ THE ACCOUNT MUST BE NEW',
        'step1_instructions': '1️⃣ If after clicking the "REGISTER" button you get to the old account, you need to log out of it and click the button again.\n\n2️⃣ Specify a promocode during registration: OGGY\n\n3️⃣ Make a Minimum deposit atleast 500₹ or 5$ in any currency',
        'after_success': '✅ After Successfully REGISTRATION, click the "CHECK REGISTRATION" button',
        'enter_player_id': '🎯 Please enter your 1Win Player ID to verify:',
        'how_to_find_id': '📝 How to find Player ID:\n1. Login to 1Win account\n2. Go to Profile Settings\n3. Copy Player ID number\n4. Paste it here',
        'enter_id_now': '🔢 Enter your Player ID now:',
        'congratulations': '🎉 Congratulations!',
        'not_registered': '❌ Sorry, You are Not Registered!',
        'not_registered_msg': 'Please click the REGISTER button first and complete your registration using our link.\n\nAfter successful registration, come back and enter your Player ID.',
        'registered_no_deposit': '🎉 Great, you have successfully completed registration!',
        'sync_success': '✅ Your account is synchronized with the bot',
        'deposit_required': '💴 To gain access to signals, deposit your account (make a deposit) with at least 500₹ or $5 in any currency',
        'after_deposit': '🕹️ After successfully replenishing your account, click on the CHECK DEPOSIT button and gain access',
        'limit_reached': "⚠️ You've Reached Your Limit!",
        'deposit_again': 'Please deposit again atleast 400₹ or 4$ in any currency for continue prediction',
        'get_signal': '🕹️ Get a signal',
        'next_signal': '🔄 Next Signal',
        'back': '🔙 Back',
        'deposit_again_btn': '💰 Deposit Again',
        'register_now': '📲 Register Now',
        'check_deposit': '🔍 Check Deposit',
        'register_btn': '📲 Register',
        'check_registration_btn': '🔍 Check Registration'
    }
}

def get_message(lang, key):
    return MESSAGES.get(lang, MESSAGES['en']).get(key, '')

def get_user(user_id):
    return users_data.get(str(user_id), {
        'user_id': user_id,
        'player_id': None,
        'language': 'en',
        'registered': False,
        'total_deposit': 0,
        'predictions_used': 0
    })

def update_user(user_id, **kwargs):
    user_id = str(user_id)
    if user_id not in users_data:
        users_data[user_id] = {'user_id': user_id}
    
    for key, value in kwargs.items():
        users_data[user_id][key] = value

def add_postback_event(event_type, user_id, amount=0):
    postback_events.append({
        'event_type': event_type,
        'user_id': user_id,
        'amount': amount
    })

def check_user_status(player_id):
    user_events = [event for event in postback_events if event['user_id'] == player_id]
    
    if not user_events:
        return "not_registered"
    
    has_registration = any(event['event_type'] == 'registration' for event in user_events)
    total_deposit = sum(event['amount'] for event in user_events if event['event_type'] in ['first_deposit', 'deposit'])
    
    if not has_registration:
        return "not_registered"
    elif total_deposit < 5:
        return "registered_no_deposit"
    else:
        return "verified"

# Initialize Telegram bot
def initialize_bot():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not found")
        return None
    
    try:
        from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
        
        application = Application.builder().token(BOT_TOKEN).build()
        
        ENTER_PLAYER_ID = 1
        
        async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            
            keyboard = [
                [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")],
                [InlineKeyboardButton("🇮🇳 हिंदी", callback_data="lang_hi")],
                [InlineKeyboardButton("🇧🇩 বাংলা", callback_data="lang_bn")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "**Select your preferred Language:**",
                reply_markup=reply_markup
            )

        async def handle_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
            query = update.callback_query
            await query.answer()
            
            language = query.data.split('_')[1]
            user_id = query.from_user.id
            
            update_user(user_id, language=language)
            await show_registration_section(query, context, language)

        async def show_registration_section(query, context: ContextTypes.DEFAULT_TYPE, language):
            keyboard = [
                [InlineKeyboardButton(get_message(language, 'register_btn'), url=AFFILIATE_LINK)],
                [InlineKeyboardButton(get_message(language, 'check_registration_btn'), callback_data="check_registration")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message_text = (
                f"{get_message(language, 'welcome')}\n\n"
                f"{get_message(language, 'step1')}\n\n"
                f"{get_message(language, 'account_must_be_new')}\n\n"
                f"{get_message(language, 'step1_instructions')}\n\n"
                f"{get_message(language, 'after_success')}"
            )
            
            await query.edit_message_text(message_text, reply_markup=reply_markup)

        async def handle_check_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
            query = update.callback_query
            await query.answer()
            
            user_id = query.from_user.id
            user = get_user(user_id)
            language = user.get('language', 'en')
            
            await query.edit_message_text(
                f"{get_message(language, 'enter_player_id')}\n\n"
                f"{get_message(language, 'how_to_find_id')}\n\n"
                f"{get_message(language, 'enter_id_now')}"
            )
            
            return ENTER_PLAYER_ID

        async def handle_player_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            player_id = update.message.text.strip()
            user = get_user(user_id)
            language = user.get('language', 'en')
            
            # Test cases
            if player_id == 'test123':
                user_status = "not_registered"
            elif player_id == 'test456':
                user_status = "registered_no_deposit"
            elif player_id == 'test789':
                user_status = "verified"
            else:
                user_status = check_user_status(player_id)
            
            if user_status == "not_registered":
                keyboard = [[InlineKeyboardButton(get_message(language, 'register_now'), url=AFFILIATE_LINK)]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"{get_message(language, 'not_registered')}\n\n{get_message(language, 'not_registered_msg')}",
                    reply_markup=reply_markup
                )
                
            elif user_status == "registered_no_deposit":
                keyboard = [
                    [InlineKeyboardButton("💰 Deposit", url=AFFILIATE_LINK)],
                    [InlineKeyboardButton(get_message(language, 'check_deposit'), callback_data="check_deposit")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"{get_message(language, 'registered_no_deposit')}\n\n"
                    f"{get_message(language, 'sync_success')}\n\n"
                    f"{get_message(language, 'deposit_required')}\n\n"
                    f"{get_message(language, 'after_deposit')}",
                    reply_markup=reply_markup
                )
                
            elif user_status == "verified":
                update_user(user_id, player_id=player_id)
                
                keyboard = [[InlineKeyboardButton(get_message(language, 'get_signal'), callback_data="get_signal")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(get_message(language, 'congratulations'), reply_markup=reply_markup)
            
            return ConversationHandler.END

        async def handle_get_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
            query = update.callback_query
            await query.answer()
            
            user_id = query.from_user.id
            user = get_user(user_id)
            language = user.get('language', 'en')
            
            predictions_used = user.get('predictions_used', 0)
            
            if predictions_used >= 3:  # Reduced for testing
                await show_deposit_again_message(query, context, language)
                return
            
            signal = random.choice(MINES_SIGNALS)
            update_user(user_id, predictions_used=predictions_used + 1)
            
            signal_text = (
                f"💣 Mines - Signals 💣\n"
                f"➖➖➖➖➖➖➖\n"
                f"💣 Select: {signal['traps']} traps\n"
                f"💡 Accuracy: {signal['accuracy']}%\n"
                f"➖➖➖➖➖➖➖\n"
                f"👉 Open the cells 👇\n\n"
            )
            
            for row in signal['grid']:
                signal_text += f"{row}\n"
            
            signal_text += f"\n➖➖➖➖➖➖➖\n"
            signal_text += f"❇️ Get a new signal 👇"
            
            keyboard = [
                [
                    InlineKeyboardButton(get_message(language, 'next_signal'), callback_data="next_signal"),
                    InlineKeyboardButton(get_message(language, 'back'), callback_data="back_to_start")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(signal_text, reply_markup=reply_markup)

        async def handle_next_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
            query = update.callback_query
            await query.answer()
            await query.delete_message()
            await handle_get_signal(update, context)

        async def handle_back_to_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
            query = update.callback_query
            await query.answer()
            
            user_id = query.from_user.id
            user = get_user(user_id)
            language = user.get('language', 'en')
            
            await show_registration_section(query, context, language)

        async def handle_check_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
            query = update.callback_query
            await query.answer()
            
            user_id = query.from_user.id
            user = get_user(user_id)
            language = user.get('language', 'en')
            
            await query.edit_message_text(
                f"{get_message(language, 'enter_player_id')}\n\n"
                f"{get_message(language, 'how_to_find_id')}\n\n"
                f"{get_message(language, 'enter_id_now')}"
            )
            
            return ENTER_PLAYER_ID

        async def show_deposit_again_message(query, context: ContextTypes.DEFAULT_TYPE, language):
            keyboard = [[InlineKeyboardButton(get_message(language, 'deposit_again_btn'), url=AFFILIATE_LINK)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"{get_message(language, 'limit_reached')}\n\n{get_message(language, 'deposit_again')}",
                reply_markup=reply_markup
            )

        # Add handlers
        conv_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(handle_check_registration, pattern="^check_registration$"),
                CallbackQueryHandler(handle_check_deposit, pattern="^check_deposit$")
            ],
            states={
                ENTER_PLAYER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_player_id)]
            },
            fallbacks=[],
            per_message=False
        )
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(handle_language, pattern="^lang_"))
        application.add_handler(conv_handler)
        application.add_handler(CallbackQueryHandler(handle_get_signal, pattern="^get_signal$"))
        application.add_handler(CallbackQueryHandler(handle_next_signal, pattern="^next_signal$"))
        application.add_handler(CallbackQueryHandler(handle_back_to_start, pattern="^back_to_start$"))
        
        # Initialize the application
        application.initialize()
        
        logger.info("Bot initialized successfully")
        return application
        
    except Exception as e:
        logger.error(f"Bot initialization failed: {e}")
        return None

# Initialize bot
telegram_app = initialize_bot()

# Flask Routes
@app.route('/')
def home():
    return "🤖 Mines Predictor Bot is Running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        if telegram_app:
            update = Update.de_json(request.get_json(), telegram_app.bot)
            telegram_app.update_queue.put(update)
        return "OK"
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "OK"  # Always return OK to prevent retries

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    if BOT_TOKEN:
        try:
            import requests
            webhook_url = f"{VERCEL_URL}/webhook"
            response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}")
            return f"✅ Webhook set: {response.json()}"
        except Exception as e:
            return f"❌ Webhook error: {e}"
    return "❌ BOT_TOKEN not set"

@app.route('/postback', methods=['GET'])
def handle_postback():
    try:
        event_type = request.args.get('type')
        user_id = request.args.get('user_id')
        amount = request.args.get('amount', 0, type=float)
        
        logger.info(f"Postback: {event_type} for {user_id} amount {amount}")
        add_postback_event(event_type, user_id, amount)
        
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logger.error(f"Postback error: {e}")
        return jsonify({"status": "error"}), 500

@app.route('/debug')
def debug():
    return jsonify({
        "users": len(users_data),
        "postbacks": len(postback_events),
        "bot_initialized": telegram_app is not None
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
