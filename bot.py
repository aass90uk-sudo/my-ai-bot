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

# ─── إنشاء وإعداد قاعدة البيانات ──────────────────────────────────────────
def init_db():
    conn = sqlite3.connect('bot_data.db', check_same_thread=False)
    cursor = conn.cursor()
    # جدول المشتركين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_date TEXT
        )
    ''')
    # جدول تتبع الرسائل
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message_text TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# ─── توجيهات الذكاء الاصطناعي ──────────────────────────────────────────────
SYSTEM_INSTRUCTION = """
أنتِ امرأة هادئة، لطيفة جداً، ومحبوبة. مهمتكِ هي الإجابة على أسئلة المستخدمين ومساعدتهم.
قواعد صارمة يجب الالتزام بها:
1. تكلمي وتجاوبي دايماً باللهجة الجزائرية (الدارجة الدزايرية) بأسلوب طبيعي، مفهوم، وسلس.
2. خاطبي المستخدمين بكل أدب، هدوء، ولطف شديد.
3. استخدمي الرموز التعبيرية اللطيفة والمبهجة في إجاباتكِ لتبعيث الراحة والود (مثل: 🥰, ✨, 🩵, 😊, 🌸).
"""

# ─── لوحات المفاتيح (Keyboards) ───────────────────────────────────────────
def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    # إذا كان المستخدم أحد المشرفين تظهر له أزرار الإدارة المعدلة
    if user_id in ADMIN_IDS:
        markup.add(
            types.KeyboardButton("📊 عدد المشتركين"),
            types.KeyboardButton("📢 إرسال منشور للمشتركين"),
            types.KeyboardButton("🔥 قسم الأشعار"),
            types.KeyboardButton("👀 تتبع رسائل المشتركين")
        )
    else:
        # أزرار المستخدم العادي
        markup.add(types.KeyboardButton("✨ مساعدة"), types.KeyboardButton("🌸 عن البوت"))
    return markup

# ─── التعامل مع الأوامر والرسائل ───────────────────────────────────────────
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

    # حفظ رسالة المستخدم في جدول التتبع
    date_now = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute('INSERT INTO logs (user_id, message_text, timestamp) VALUES (?, ?, ?)', (user_id, text, date_now))
    conn.commit()

    # 🛑 فحص أزرار تحكم المشرفين 🛑
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
                types.InlineKeyboardButton("🇩🇿 شعر بالدارجة الدزايرية", callback_data="poetry_dz"),
                types.InlineKeyboardButton("🇸🇦 شعر باللهجة الخليجية", callback_data="poetry_kh")
            )
            bot.reply_to(message, "💬 اختر نوع الأبيات الشعرية الغزلية التي تفضلها:", reply_markup=inline_poetry)
            return

        elif text == "👀 تتبع رسائل المشتركين":
            cursor.execute('SELECT user_id, message_text, timestamp FROM logs ORDER BY id DESC LIMIT 10')
            logs = cursor.fetchall()
            if not logs:
                bot.reply_to(message, "❌ لا توجد أي رسائل مسجلة بعد في قاعدة البيانات.")
                return
            
            report = "👀 *آخر 10 رسائل تم كتابتها داخل البوت:*\n\n"
            for log in logs:
                report += f"👤 مستخدم: `{log[0]}`\n💬 كتب: {log[1]}\n⏰ الوقت: {log[2]}\n──────────────────\n"
            bot.reply_to(message, report, parse_mode="Markdown")
            return

    # 💬 معالجة طلبات الذكاء الاصطناعي للمستخدمين العاديين
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "system", "content": SYSTEM_INSTRUCTION}, {"role": "user", "content": text}],
            model=GROQ_MODEL,
        )
        reply = chat_completion.choices[0].message.content
        bot.reply_to(message, reply)
    except Exception as e:
        bot.reply_to(message, "عذراً، صرا خطأ صغير وأنا نوجد في الإجابة تاعك. اسمحيلي! 😥")
        print(f"Error: {e}")

# ─── وظائف الـ Callback والأزرار الفرعية ─────────────────────────────────────
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ عذراً، هذا القسم مخصص للمشرفين فقط!")
        return

    if call.data == "get_users_data":
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

    elif call.data == "poetry_dz":
        text_dz = "✨ *أبيات غزلية بالدارجة الجزائرية:*\n\nعينيكِ يا لالة كي النجوم في سمايا ✨\nحبكِ سكن في الروح وعمر قاع معايا 🥰\nشفايفك عسل صافي يبري العلة والضر 🌸\nوقلبك حنين عليا ومزيّن هاد العمر ❤️"
        bot.send_message(call.message.chat.id, text_dz, parse_mode="Markdown")
        bot.answer_callback_query(call.id)

    elif call.data == "poetry_kh":
        text_kh = "✨ *أبيات غزلية باللهجة الخليجية:*\n\nيا بعد عمري ويا كل الملا والوجود 🩵\nخصرك النحيل يذوب والشوق ماله حدود 🔥\nشفتكِ كالعسل تروي ظمأ روحي العطشان 💋\nوضمتكِ يا غناتي تنسيني هم الزمان 🫂"
        bot.send_message(call.message.chat.id, text_kh, parse_mode="Markdown")
        bot.answer_callback_query(call.id)

# ─── وظيفة بث المنشورات ─────────────────────────────────────────────────────
def broadcast_message(message):
    if message.text in ["📊 عدد المشتركين", "📢 إرسال منشور للمشتركين", "🔥 قسم الأشعار", "👀 تتبع رسائل المشتركين"]:
        bot.reply_to(message, "❌ تم إلغاء العملية لأنك ضغطت على زر آخر.")
        return
        
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    success_count = 0
    
    for u in users:
        try:
            bot.send_message(u[0], message.text)
            success_count += 1
        except Exception:
            continue
            
    bot.reply_to(message, f"📢 تمت عملية البث بنجاح!\nوصل المنشور إلى *{success_count}* مستخدم من أصل {len(users)}.", parse_mode="Markdown")

# ─── تشغيل البوت ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("البوت يعمل الآن مع تحديث التسميات...")
    bot.infinity_polling()
        
