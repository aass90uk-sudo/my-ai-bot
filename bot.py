import os
import sqlite3
from datetime import datetime
import telebot
from telebot import types
from groq import Groq

# ─── الإعدادات والمفاتيح ──────────────────────────────────────────────────
BOT_TOKEN = os.environ.get('BOT_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
GROQ_MODEL = os.environ.get('GROQ_MODEL', 'llama-3.1-8b-instant')

# ⚙️ معرفات المشرفين الخاصة بكم مفعلة للوحة التحكم المشتركة
ADMIN_IDS = [6856665810, 8955506857]

bot = telebot.TeleBot(BOT_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

# ─── إنشاء قاعدة البيانات (بدون جدول التتبع لحماية الخصوصية) ──────────────────
def init_db():
    conn = sqlite3.connect('bot_data.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_date TEXT
        )
    ''')
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# ─── توليد الـ 50 قصيدة برمجياً لتفادي ضخامة الملف ──────────────────────────────
POETRY_DZ = {}
POETRY_KH = {}

for i in range(1, 51):
    POETRY_DZ[f"dz_{i}"] = {
        "title": f"🌸 قصيدة جزائرية {i}",
        "text": f"✨ *قصيدة غزلية جزائرية رقم {i}* ✨\n\nعينيكِ يا لالة كي النجوم في سمايا ✨\nحبكِ سكن في الروح وعمر قاع معايا 🥰\nشفايفك عسل صافي يبري العلة والضر 🌸\nوقلبك حنين عليا ومزيّن هاد العمر ❤️"
    }
    POETRY_KH[f"kh_{i}"] = {
        "title": f"💫 قصيدة خليجية {i}",
        "text": f"✨ *قصيدة غزلية خليجية رقم {i}* ✨\n\nيا بعد عمري ويا كل الملا والوجود 🩵\nخصرك النحيل يذوب والشوق ماله حدود 🔥\nشفتكِ كالعسل تروي ظمأ روحي العطشان 💋\nوضمتكِ يا غناتي تنسيني هم الزمان 🫂"
    }

ITEMS_PER_PAGE = 5

# ─── توجيهات الذكاء الاصطناعي ──────────────────────────────────────────────
SYSTEM_INSTRUCTION = """
أنتِ امرأة هادئة، لطيفة جداً، ومحبوبة. مهمتكِ هي الإجابة على أسئلة المستخدمين ومساعدتهم.
قواعد صارمة يجب الالتزام بها:
1. تكلمي وتجاوبي دايماً باللهجة الجزائرية (الدارجة الدزايرية) بأسلوب طبيعي، مفهوم، وسلس.
2. خاطبي المستخدمين بكل أدب، هدوء، ولطف شديد.
3. استخدمي الرموز التعبيرية اللطيفة والمبهجة في إجاباتكِ لتبعيث الراحة والود (مثل: 🥰, ✨, 🩵, 😊, 🌸).
"""

# ─── لوحة المفاتيح الرئيسية ────────────────────────────────────────────────
def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if user_id in ADMIN_IDS:
        markup.add(
            types.KeyboardButton("📊 عدد المشتركين"),
            types.KeyboardButton("📢 إرسال منشور للمشتركين"),
            types.KeyboardButton("🔥 قسم الأشعار")
        )
    else:
        markup.add(types.KeyboardButton("✨ مساعدة"), types.KeyboardButton("🌸 عن البوت"))
    return markup

# ─── دالة بناء صفحات الأشعار ────────────────────────────────────────────────
def build_poetry_keyboard(poetry_dict, prefix, page=1):
    markup = types.InlineKeyboardMarkup(row_width=1)
    keys = list(poetry_dict.keys())
    total_items = len(keys)
    
    start_index = (page - 1) * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    page_keys = keys[start_index:end_index]
    
    # إضافة أزرار القصائد الخمسة المعنونة
    for k in page_keys:
        markup.add(types.InlineKeyboardButton(poetry_dict[k]["title"], callback_data=f"show_{k}_{page}"))
        
    # إضافة أزرار التنقل (التالي / السابق)
    nav_buttons = []
    if page > 1:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ السابق", callback_data=f"page_{prefix}_{page-1}"))
    if end_index < total_items:
        nav_buttons.append(types.InlineKeyboardButton("التالي ➡️", callback_data=f"page_{prefix}_{page+1}"))
        
    if nav_buttons:
        markup.row(*nav_buttons)
        
    markup.add(types.InlineKeyboardButton("↩️ العودة للقائمة الرئيسية", callback_data="back_to_poetry_main"))
    return markup

# ─── التعامل مع الرسائل ────────────────────────────────────────────────────
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username or "لا يوجد"
    first_name = message.from_user.first_name or "مستخدم"
    date_now = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        cursor.execute('INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?)', (user_id, username, first_name, date_now))
        conn.commit()
    except Exception as e:
        print(f"DB Error: {e}")

    welcome_text = "أهلاً بك معايا! ✨ أنا هنا باه نجاوبك على أي سؤال يخطر في بالك ونعاونك بكل لطف. اسألني واش تحب! 🥰🌸"
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard(user_id))

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text

    if user_id in ADMIN_IDS:
        if text == "📊 عدد المشتركين":
            cursor.execute('SELECT COUNT(*) FROM users')
            count = cursor.fetchone()[0]
            inline_markup = types.InlineKeyboardMarkup()
            inline_markup.add(types.InlineKeyboardButton("📋 جلب بيانات المشتركين تفصيلياً", callback_data="get_users_data"))
            bot.reply_to(message, f"📊 إجمالي عدد المشتركين في البوت حالياً: *{count}* مستخدم.", reply_markup=inline_markup, parse_mode="Markdown")
            return

        elif text == "📢 إرسال منشور للمشتركين":
            sent_msg = bot.reply_to(message, "📢 من فضلك أرسل الآن النص أو المنشور الذي تريد تعميمه على جميع المشتركين:")
            bot.register_next_step_handler(sent_msg, broadcast_message)
            return

        elif text == "🔥 قسم الأشعار":
            inline_poetry = types.InlineKeyboardMarkup(row_width=2)
            inline_poetry.add(
                types.InlineKeyboardButton("🇩🇿 باقة أشعار دزايرية", callback_data="page_dz_1"),
                types.InlineKeyboardButton("🇸🇦 باقة أشعار خليجية", callback_data="page_kh_1")
            )
            bot.reply_to(message, "💬 اختر نوع الأبيات الشعرية التي تفضلها لتصفح الصفحات المنسقة:", reply_markup=inline_poetry)
            return

    # معالجة ذكاء اصطناعي للمستخدم العادي
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "system", "content": SYSTEM_INSTRUCTION}, {"role": "user", "content": text}],
            model=GROQ_MODEL,
        )
        reply = chat_completion.choices[0].message.content
        bot.reply_to(message, reply)
    except Exception as e:
        bot.reply_to(message, "عذراً، صرا خطأ صغير وأنا نوجد في الإجابة تاعك. اسمحيلي! 😥")

# ─── معالجة ضغطات الأزرار والتحديث التلقائي الفوري ──────────────────────────────
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ عذراً، هذا القسم مخصص للمشرفين فقط!")
        return

    data = call.data

    if data == "get_users_data":
        cursor.execute('SELECT user_id, username, first_name, joined_date FROM users')
        users = cursor.fetchall()
        if not users:
            bot.send_message(call.message.chat.id, "قائمة المشتركين فارغة.")
            return
        response = "📋 *بيانات المشتركين المسجلين:*\n\n"
        for u in users:
            response += f"👤 الاسم: {u[2]}\n🆔 الآيدي: `{u[0]}`\n🔗 المعرف: @{u[1]}\n📅 انضم في: {u[3]}\n──────────────────\n"
        bot.send_message(call.message.chat.id, response, parse_mode="Markdown")
        bot.answer_callback_query(call.id)

    # معالجة التنقل بين صفحات الأشعار (تحديث نفس الرسالة)
    elif data.startswith("page_"):
        parts = data.split("_")
        prefix = parts[1]
        page = int(parts[2])
        poetry_dict = POETRY_DZ if prefix == "dz" else POETRY_KH
        title_text = "🇩🇿 تصفح الأشعار الجزائرية المنسقة:" if prefix == "dz" else "🇸🇦 تصفح الأشعار الخليجية المنسقة:"
        
        bot.edit_message_text(
            text=f"{title_text}\n*الصفحة الحالية: {page} / 10*",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=build_poetry_keyboard(poetry_dict, prefix, page),
            parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id)

    # عرض القصيدة المحددة مع إخفاء الرسالة السابقة لتفادي التراكم
    elif data.startswith("show_"):
        parts = data.split("_")
        prefix = parts[1]
        index = parts[2]
        current_page = int(parts[3])
        
        poetry_dict = POETRY_DZ if prefix == "dz" else POETRY_KH
        item_key = f"{prefix}_{index}"
        poetry_data = poetry_dict[item_key]
        
        # إنشاء زر للعودة إلى نفس الصفحة التي كان فيها المشرف
        back_markup = types.InlineKeyboardMarkup()
        back_markup.add(types.InlineKeyboardButton("⬅️ العودة لصفحة القصائد", callback_data=f"page_{prefix}_{current_page}"))
        
        bot.edit_message_text(
            text=poetry_data["text"],
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=back_markup,
            parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id)

    # العودة للقائمة الرئيسية للأشعار
    elif data == "back_to_poetry_main":
        inline_poetry = types.InlineKeyboardMarkup(row_width=2)
        inline_poetry.add(
            types.InlineKeyboardButton("🇩🇿 باقة أشعار دزايرية", callback_data="page_dz_1"),
            types.InlineKeyboardButton("🇸🇦 باقة أشعار خليجية", callback_data="page_kh_1")
        )
        bot.edit_message_text(
            text="💬 اختر نوع الأبيات الشعرية التي تفضلها لتصفح الصفحات المنسقة:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=inline_poetry
        )
        bot.answer_callback_query(call.id)

# ─── وظيفة بث المنشورات ─────────────────────────────────────────────────────
def broadcast_message(message):
    if message.text in ["📊 عدد المشتركين", "📢 إرسال منشور للمشتركين", "🔥 قسم الأشعار"]:
            
