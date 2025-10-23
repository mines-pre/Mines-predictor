from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import os
import sqlite3
import random
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Environment variables - Vercel me ye add karna hai
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID', '123456789')  # Your Telegram ID
VERCEL_URL = os.environ.get('VERCEL_URL', 'https://your-app.vercel.app')
AFFILIATE_LINK = os.environ.get('AFFILIATE_LINK', 'https://lkpq.cc/cd7800')

# Telegram app initialize
if BOT_TOKEN:
    telegram_app = Application.builder().token(BOT_TOKEN).build()
else:
    telegram_app = None

# Database setup
def init_db():
    try:
        conn = sqlite3.connect('users.db', check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                player_id TEXT UNIQUE,
                language TEXT DEFAULT 'en',
                registered INTEGER DEFAULT 0,
                total_deposit REAL DEFAULT 0,
                predictions_used INTEGER DEFAULT 0,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS postback_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                user_id TEXT,
                amount REAL,
                event_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database error: {e}")

init_db()

# Conversation states
ENTER_PLAYER_ID = 1

# All Mines Signals
MINES_SIGNALS = [
    {
        "traps": 1, "accuracy": 97,
        "grid": ["🔒🔒🔒🔒💰", "🔒🔒🔒💰🔒", "💰🔒🔒🔒🔒", "🔒💰🔒🔒🔒", "🔒🔒🔒🔒💰"]
    },
    {
        "traps": 1, "accuracy": 90,
        "grid": ["🔒🔒🔒🔒🔒", "💰🔒💰🔒🔒", "🔒💰🔒🔒🔒", "🔒💰🔒💰🔒", "🔒🔒🔒🔒🔒"]
    },
    {
        "traps": 1, "accuracy": 96,
        "grid": ["🔒🔒🔒🔒🔒", "🔒🔒🔒💰🔒", "🔒💰🔒🔒💰", "💰🔒🔒🔒💰", "🔒🔒🔒🔒🔒"]
    },
    {
        "traps": 1, "accuracy": 95,
        "grid": ["💰🔒🔒🔒🔒", "💰🔒🔒🔒🔒", "🔒🔒🔒🔒🔒", "💰🔒🔒🔒🔒", "💰🔒🔒💰🔒"]
    },
    {
        "traps": 1, "accuracy": 96,
        "grid": ["🔒🔒💰🔒🔒", "🔒💰🔒💰🔒", "💰🔒🔒🔒🔒", "🔒🔒💰🔒🔒", "🔒🔒🔒🔒🔒"]
    },
    {
        "traps": 1, "accuracy": 91,
        "grid": ["🔒💰🔒🔒🔒", "🔒💰🔒🔒🔒", "🔒💰🔒💰🔒", "💰🔒🔒🔒🔒", "🔒🔒🔒🔒🔒"]
    },
    {
        "traps": 1, "accuracy": 94,
        "grid": ["🔒💰💰🔒🔒", "🔒🔒🔒🔒🔒", "🔒🔒🔒🔒💰", "🔒🔒🔒🔒🔒", "💰🔒💰🔒🔒"]
    },
    {
        "traps": 1, "accuracy": 92,
        "grid": ["🔒🔒🔒💰🔒", "💰💰🔒🔒💰", "🔒🔒🔒🔒🔒", "🔒🔒🔒💰🔒", "🔒🔒🔒🔒🔒"]
    },
    {
        "traps": 1, "accuracy": 90,
        "grid": ["💰🔒🔒💰🔒", "💰🔒💰🔒🔒", "🔒🔒🔒🔒🔒", "🔒💰🔒🔒🔒", "🔒🔒🔒🔒🔒"]
    },
    {
        "traps": 1, "accuracy": 92,
        "grid": ["🔒🔒🔒💰🔒", "🔒🔒🔒🔒🔒", "🔒🔒🔒🔒🔒", "🔒🔒💰🔒🔒", "💰🔒💰💰🔒"]
    },
    {
        "traps": 1, "accuracy": 93,
        "grid": ["💰🔒🔒🔒🔒", "🔒🔒💰🔒🔒", "💰🔒🔒🔒🔒", "🔒🔒💰🔒🔒", "💰🔒🔒🔒🔒"]
    },
    {
        "traps": 1, "accuracy": 97,
        "grid": ["💰🔒🔒🔒🔒", "🔒💰🔒🔒🔒", "🔒🔒🔒🔒🔒", "💰💰🔒🔒💰", "🔒🔒🔒🔒🔒"]
    },
    {
        "traps": 1, "accuracy": 90,
        "grid": ["💰🔒🔒💰🔒", "🔒🔒🔒🔒🔒", "🔒🔒🔒🔒🔒", "💰🔒💰🔒🔒", "💰🔒🔒🔒🔒"]
    },
    {
        "traps": 1, "accuracy": 96,
        "grid": ["🔒🔒🔒🔒🔒", "🔒💰🔒🔒🔒", "🔒🔒🔒🔒🔒", "🔒🔒💰🔒🔒", "💰🔒💰💰🔒"]
    },
    {
        "traps": 1, "accuracy": 94,
        "grid": ["🔒🔒💰🔒🔒", "🔒🔒💰🔒🔒", "💰🔒🔒🔒🔒", "🔒💰🔒🔒🔒", "🔒💰🔒🔒🔒"]
    }
]

# Language Messages
MESSAGES = {
    'en': {
        'welcome': '✅ *You selected English!*',
        'step1': '🌐 *Step 1 - Register*',
        'account_must_be_new': '‼️ THE ACCOUNT MUST BE NEW',
        'step1_instructions': '1️⃣ If after clicking the "REGISTER" button you get to the old account, you need to log out of it and click the button again.\n\n2️⃣ Specify a promocode during registration: *OGGY*\n\n3️⃣ Make a Minimum deposit atleast *500₹ or 5$* in any currency',
        'after_success': '✅ After Successfully REGISTRATION, click the "CHECK REGISTRATION" button',
        'enter_player_id': '🎯 *Please enter your 1Win Player ID to verify:*',
        'how_to_find_id': '📝 *How to find Player ID:*\n1. Login to 1Win account\n2. Go to Profile Settings\n3. Copy Player ID number\n4. Paste it here',
        'enter_id_now': '🔢 *Enter your Player ID now:*',
        'congratulations': '🎉 *Congratulations!*',
        'not_registered': '❌ *Sorry, You are Not Registered!*',
        'not_registered_msg': 'Please click the REGISTER button first and complete your registration using our link.\n\nAfter successful registration, come back and enter your Player ID.',
        'registered_no_deposit': '🎉 *Great, you have successfully completed registration!*',
        'sync_success': '✅ Your account is synchronized with the bot',
        'deposit_required': '💴 To gain access to signals, deposit your account (make a deposit) with at least *500₹ or $5* in any currency',
        'after_deposit': '🕹️ After successfully replenishing your account, click on the CHECK DEPOSIT button and gain access',
        'limit_reached': "⚠️ *You've Reached Your Limit!*",
        'deposit_again': 'Please deposit again atleast *400₹ or 4$* in any currency for continue prediction',
        'get_signal': '🕹️ Get a signal',
        'next_signal': '🔄 Next Signal',
        'back': '🔙 Back',
        'deposit_again_btn': '💰 Deposit Again',
        'register_now': '📲 Register Now',
        'check_deposit': '🔍 Check Deposit',
        'register_btn': '📲 Register',
        'check_registration_btn': '🔍 Check Registration'
    },
    'hi': {
        'welcome': '✅ *आपने हिंदी चुनी!*',
        'step1': '🌐 *चरण 1 - पंजीकरण*',
        'account_must_be_new': '‼️ खाता नया होना चाहिए',
        'step1_instructions': '1️⃣ यदि "पंजीकरण" बटन पर क्लिक करने के बाद आपको पुराना खाता मिलता है, तो आपको उससे लॉग आउट करना होगा और बटन को फिर से क्लिक करना होगा।\n\n2️⃣ पंजीकरण के दौरान प्रोमोकोड निर्दिष्ट करें: *OGGY*\n\n3️⃣ न्यूनतम जमा करें कम से कम *500₹ या 5$* किसी भी मुद्रा में',
        'after_success': '✅ सफल पंजीकरण के बाद, "पंजीकरण जांचें" बटन पर क्लिक करें',
        'enter_player_id': '🎯 *कृपया सत्यापन के लिए अपना 1Win Player ID दर्ज करें:*',
        'how_to_find_id': '📝 *Player ID कैसे ढूंढें:*\n1. 1Win खाते में लॉगिन करें\n2. प्रोफाइल सेटिंग्स पर जाएं\n3. Player ID नंबर कॉपी करें\n4. यहां पेस्ट करें',
        'enter_id_now': '🔢 *अपना Player ID अभी दर्ज करें:*',
        'congratulations': '🎉 *बधाई हो!*',
        'not_registered': '❌ *क्षमा करें, आप पंजीकृत नहीं हैं!*',
        'not_registered_msg': 'कृपया पहले REGISTER बटन पर क्लिक करें और हमारे लिंक का उपयोग करके अपना पंजीकरण पूरा करें।\n\nसफल पंजीकरण के बाद, वापस आएं और अपना Player ID दर्ज करें।',
        'registered_no_deposit': '🎉 *बढ़िया, आपने सफलतापूर्वक पंजीकरण पूरा कर लिया है!*',
        'sync_success': '✅ आपका खाता बॉट के साथ सिंक्रनाइज़ हो गया है',
        'deposit_required': '💴 सिग्नल तक पहुंच प्राप्त करने के लिए, अपने खाते में कम से कम *500₹ या $5* किसी भी मुद्रा में जमा करें',
        'after_deposit': '🕹️ अपना खाता सफलतापूर्वक भरने के बाद, CHECK DEPOSIT बटन पर क्लिक करें और पहुंच प्राप्त करें',
        'limit_reached': "⚠️ *आप अपनी सीमा तक पहुँच गए हैं!*",
        'deposit_again': 'कृपया भविष्यवाणी जारी रखने के लिए फिर से कम से कम *400₹ या 4$* किसी भी मुद्रा में जमा करें',
        'get_signal': '🕹️ सिग्नल प्राप्त करें',
        'next_signal': '🔄 अगला सिग्नल',
        'back': '🔙 वापस',
        'deposit_again_btn': '💰 फिर से जमा करें',
        'register_now': '📲 अभी पंजीकरण करें',
        'check_deposit': '🔍 जमा जांचें',
        'register_btn': '📲 पंजीकरण',
        'check_registration_btn': '🔍 पंजीकरण जांचें'
    },
    'bn': {
        'welcome': '✅ *আপনি বাংলা নির্বাচন করেছেন!*',
        'step1': '🌐 *ধাপ 1 - নিবন্ধন*',
        'account_must_be_new': '‼️ অ্যাকাউন্টটি নতুন হতে হবে',
        'step1_instructions': '১️⃣ "নিবন্ধন" বাটনে ক্লিক করার পরে যদি আপনি পুরানো অ্যাকাউন্টে প্রবেশ করেন, তাহলে আপনাকে এটি থেকে লগ আউট করতে হবে এবং বাটনটি আবার ক্লিক করতে হবে।\n\n২️⃣ নিবন্ধনের সময় প্রমোকোড নির্দিষ্ট করুন: *OGGY*\n\n৩️⃣ ন্যূনতম জমা করুন কমপক্ষে *500₹ বা 5$* যেকোনো মুদ্রায়',
        'after_success': '✅ সফল নিবন্ধনের পরে, "নিবন্ধন পরীক্ষা করুন" বাটনে ক্লিক করুন',
        'enter_player_id': '🎯 *যাচাই করার জন্য আপনার 1Win Player ID লিখুন:*',
        'how_to_find_id': '📝 *Player ID কিভাবে খুঁজে পাবেন:*\n1. 1Win অ্যাকাউন্টে লগইন করুন\n2. প্রোফাইল সেটিংসে যান\n3. Player ID নম্বর কপি করুন\n4. এখানে পেস্ট করুন',
        'enter_id_now': '🔢 *এখনই আপনার Player ID লিখুন:*',
        'congratulations': '🎉 *অভিনন্দন!*',
        'not_registered': '❌ *দুঃখিত, আপনি নিবন্ধিত নন!*',
        'not_registered_msg': 'অনুগ্রহ করে প্রথমে REGISTER বাটনে ক্লিক করুন এবং আমাদের লিঙ্ক ব্যবহার করে আপনার নিবন্ধন সম্পূর্ণ করুন।\n\nসফল নিবন্ধনের পরে, ফিরে আসুন এবং আপনার Player ID লিখুন।',
        'registered_no_deposit': '🎉 *দারুন, আপনি সফলভাবে নিবন্ধন সম্পূর্ণ করেছেন!*',
        'sync_success': '✅ আপনার অ্যাকাউন্ট বটের সাথে সিঙ্ক্রোনাইজ হয়েছে',
        'deposit_required': '💴 সিগন্যাল অ্যাক্সেস পেতে, আপনার অ্যাকাউন্টে কমপক্ষে *500₹ বা $5* যেকোনো মুদ্রায় জমা করুন',
        'after_deposit': '🕹️ আপনার অ্যাকাউন্ট সফলভাবে রিচার্জ করার পরে, CHECK DEPOSIT বাটনে ক্লিক করুন এবং অ্যাক্সেস পান',
        'limit_reached': "⚠️ *আপনি আপনার সীমায় পৌঁছে গেছেন!*",
        'deposit_again': 'অনুগ্রহ করে ভবিষ্যদ্বাণী চালিয়ে যেতে আবার কমপক্ষে *400₹ বা 4$* যেকোনো মুদ্রায় জমা করুন',
        'get_signal': '🕹️ সিগন্যাল পান',
        'next_signal': '🔄 পরবর্তী সিগন্যাল',
        'back': '🔙 ফিরে যান',
        'deposit_again_btn': '💰 আবার জমা করুন',
        'register_now': '📲 এখনই নিবন্ধন করুন',
        'check_deposit': '🔍 জমা পরীক্ষা করুন',
        'register_btn': '📲 নিবন্ধন',
        'check_registration_btn': '🔍 নিবন্ধন পরীক্ষা'
    }
}

def get_message(lang, key):
    return MESSAGES.get(lang, MESSAGES['en']).get(key, '')

# Database functions
def get_user(user_id):
    conn = sqlite3.connect('users.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def update_user(user_id, **kwargs):
    conn = sqlite3.connect('users.db', check_same_thread=False)
    cursor = conn.cursor()
    
    if not get_user(user_id):
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
    
    set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
    values = list(kwargs.values())
    values.append(user_id)
    
    cursor.execute(f"UPDATE users SET {set_clause} WHERE user_id = ?", values)
    conn.commit()
    conn.close()

def add_postback_event(event_type, user_id, amount=0, event_data=""):
    conn = sqlite3.connect('users.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO postback_events (event_type, user_id, amount, event_data) VALUES (?, ?, ?, ?)",
        (event_type, user_id, amount, event_data)
    )
    conn.commit()
    conn.close()

# Telegram Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    keyboard = [
        [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇮🇳 हिंदी", callback_data="lang_hi")],
        [InlineKeyboardButton("🇧🇩 বাংলা", callback_data="lang_bn")],
        [InlineKeyboardButton("🇵🇰 اردو", callback_data="lang_ur")],
        [InlineKeyboardButton("🇳🇵 नेपाली", callback_data="lang_ne")]
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
    
    update_user(user_id, language=language, last_activity=datetime.now())
    
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
    
    await query.edit_message_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_check_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = get_user(user_id)
    language = user[2] if user else 'en'
    
    await query.edit_message_text(
        f"{get_message(language, 'enter_player_id')}\n\n"
        f"{get_message(language, 'how_to_find_id')}\n\n"
        f"{get_message(language, 'enter_id_now')}",
        parse_mode='Markdown'
    )
    
    return ENTER_PLAYER_ID

async def handle_player_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    player_id = update.message.text
    language = get_user(user_id)[2] if get_user(user_id) else 'en'
    
    # Check user status from database
    user_status = check_user_status(player_id)
    
    if user_status == "not_registered":
        keyboard = [[InlineKeyboardButton(get_message(language, 'register_now'), url=AFFILIATE_LINK)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"{get_message(language, 'not_registered')}\n\n{get_message(language, 'not_registered_msg')}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
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
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    elif user_status == "verified":
        update_user(user_id, player_id=player_id, last_activity=datetime.now())
        
        keyboard = [[InlineKeyboardButton(get_message(language, 'get_signal'), callback_data="get_signal")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            get_message(language, 'congratulations'),
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    return ConversationHandler.END

def check_user_status(player_id):
    """Check user registration and deposit status"""
    conn = sqlite3.connect('users.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Check if we have postback events for this player
    cursor.execute("SELECT * FROM postback_events WHERE user_id = ?", (player_id,))
    events = cursor.fetchall()
    conn.close()
    
    if not events:
        return "not_registered"
    
    # Check if user has made a deposit of at least $5
    total_deposit = 0
    has_registration = False
    
    for event in events:
        event_type = event[1]
        amount = event[3] or 0
        
        if event_type == 'registration':
            has_registration = True
        elif event_type in ['first_deposit', 'deposit']:
            total_deposit += amount
    
    if not has_registration:
        return "not_registered"
    elif total_deposit < 5:  # $5 minimum
        return "registered_no_deposit"
    else:
        return "verified"

async def handle_get_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = get_user(user_id)
    language = user[2] if user else 'en'
    
    # Check prediction limit
    predictions_used = user[5] if user else 0
    
    if predictions_used >= 15:
        await show_deposit_again_message(query, context, language)
        return
    
    # Get random signal
    signal = random.choice(MINES_SIGNALS)
    
    # Update prediction count
    update_user(user_id, predictions_used=predictions_used + 1, last_activity=datetime.now())
    
    # Format signal message
    signal_text = (
        f"💣 *Mines - Signals* 💣\n"
        f"➖➖➖➖➖➖➖\n"
        f"💣 *Select:* {signal['traps']} traps\n"
        f"💡 *Accuracy:* {signal['accuracy']}%\n"
        f"➖➖➖➖➖➖➖\n"
        f"👉 *Open the cells* 👇\n\n"
    )
    
    for row in signal['grid']:
        signal_text += f"{row}\n"
    
    signal_text += f"\n➖➖➖➖➖➖➖\n"
    signal_text += f"❇️ *Get a new signal* 👇"
    
    # Create buttons
    keyboard = [
        [
            InlineKeyboardButton(get_message(language, 'next_signal'), callback_data="next_signal"),
            InlineKeyboardButton(get_message(language, 'back'), callback_data="back_to_start")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        signal_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_next_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Delete previous message and send new one
    await query.delete_message()
    await handle_get_signal(update, context)

async def handle_back_to_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = get_user(user_id)
    language = user[2] if user else 'en'
    
    await show_registration_section(query, context, language)

async def handle_check_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = get_user(user_id)
    language = user[2] if user else 'en'
    
    await query.edit_message_text(
        f"{get_message(language, 'enter_player_id')}\n\n"
        f"{get_message(language, 'how_to_find_id')}\n\n"
        f"{get_message(language, 'enter_id_now')}",
        parse_mode='Markdown'
    )
    
    return ENTER_PLAYER_ID

async def show_deposit_again_message(query, context: ContextTypes.DEFAULT_TYPE, language):
    keyboard = [[InlineKeyboardButton(get_message(language, 'deposit_again_btn'), url=AFFILIATE_LINK)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"{get_message(language, 'limit_reached')}\n\n{get_message(language, 'deposit_again')}",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Postback Handler
@app.route('/postback', methods=['GET'])
def handle_postback():
    try:
        event_type = request.args.get('type')
        user_id = request.args.get('user_id')
        amount = request.args.get('amount', 0, type=float)
        
        logger.info(f"Postback received: {event_type} for user {user_id} amount {amount}")
        
        # Store postback event
        add_postback_event(event_type, user_id, amount, str(dict(request.args)))
        
        # Update user status based on postback
        if event_type == 'registration':
            # User registered
            pass
        elif event_type in ['first_deposit', 'deposit']:
            # User made a deposit
            conn = sqlite3.connect('users.db', check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET total_deposit = total_deposit + ? WHERE player_id = ?",
                (amount, user_id)
            )
            conn.commit()
            conn.close()
        
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        logger.error(f"Postback error: {e}")
        return jsonify({"status": "error"}), 500

# Flask Routes
@app.route('/')
def home():
    return "🤖 Mines Predictor Bot is Running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    if telegram_app:
        update = Update.de_json(request.get_json(), telegram_app.bot)
        telegram_app.update_queue.put(update)
    return "OK"

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    if telegram_app:
        webhook_url = f"{VERCEL_URL}/webhook"
        telegram_app.bot.set_webhook(webhook_url)
        return f"Webhook set to: {webhook_url}"
    return "Telegram app not initialized"

# Setup Telegram Handlers
def setup_handlers():
    if not telegram_app:
        return
    
    # Conversation handler for player ID input
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_check_registration, pattern="^check_registration$"),
            CallbackQueryHandler(handle_check_deposit, pattern="^check_deposit$")
        ],
        states={
            ENTER_PLAYER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_player_id)]
        },
        fallbacks=[]
    )
    
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CallbackQueryHandler(handle_language, pattern="^lang_"))
    telegram_app.add_handler(conv_handler)
    telegram_app.add_handler(CallbackQueryHandler(handle_get_signal, pattern="^get_signal$"))
    telegram_app.add_handler(CallbackQueryHandler(handle_next_signal, pattern="^next_signal$"))
    telegram_app.add_handler(CallbackQueryHandler(handle_back_to_start, pattern="^back_to_start$"))
    
    telegram_app.initialize()

# Initialize
setup_handlers()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
