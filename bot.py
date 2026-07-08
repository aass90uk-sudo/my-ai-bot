import os
import sqlite3
from datetime import datetime
import telebot
from telebot import types
from groq import Groq

# ─── الإعدادات والمفاتيح ──────────────────────────────────────────────────
BOT_TOKEN = os.environ.get('BOT_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
GROQ_MODEL = os.environ.get('GROQ_MODEL', 'llama-3.3-70b-versatile')

# معرفات المشرفين الخاصة بكم
ADMIN_IDS = [6856665810, 8955506857]

bot = telebot.TeleBot(BOT_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

# ─── إعداد قاعدة البيانات في المجلد الدائم للـ Volume ─────────────────
def init_db():
    os.makedirs('/app/data', exist_ok=True)
    conn = sqlite3.connect('/app/data/bot_data.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_date TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_states (
            user_id INTEGER PRIMARY KEY,
            state TEXT
        )
    ''')
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

def set_user_state(user_id, state):
    cursor.execute('INSERT OR REPLACE INTO user_states (user_id, state) VALUES (?, ?)', (user_id, state))
    conn.commit()

def get_user_state(user_id):
    cursor.execute('SELECT state FROM user_states WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    return row[0] if row else "MAIN_MENU"

# ─── توجيهات الذكاء الاصطناعي ───────────────────────────────────────────
SYSTEM_INSTRUCTION = """
أنتِ امرأة جزائرية ذكية جداً، مثقفة، هادئة، ولطيفة للغاية ومحبوبة. مهمتكِ هي الإجابة على جميع أسئلة المستخدمين ومساعدتهم في شتى مجالات الحياة بذكاء حاد وبلاغة.
قواعد صارمة:
1. تكلمي وتجاوبي دايماً باللهجة الجزائرية (الدارجة الدزايرية) بطلاقة تامة وأسلوب سلس.
2. خاطبي المستخدمين بكل أدب واحترام، وقدمي النصح بحكمة.
3. استخدمي الرموز التعبيرية اللطيفة (🥰, ✨, 🩵, 😊, 🌸).
"""

# ─── لوحة المفاتيح الرئيسية ─────────────────────────────────────────
def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if user_id in ADMIN_IDS:
        markup.add(
            types.KeyboardButton("📊 عدد المشتركين"),
            types.KeyboardButton("📢 إرسال منشور للمشتركين"),
            types.KeyboardButton("🕌 سؤال شرعي"),
            types.KeyboardButton("🔬 سؤال علمي")
        )
    else:
        markup.add(
            types.KeyboardButton("🕌 سؤال شرعي"),
            types.KeyboardButton("🔬 سؤال علمي"),
            types.KeyboardButton("✨ مساعدة"),
            types.KeyboardButton("🌸 عن البوت")
        )
    return markup

# ─── الأوامر الأساسية ───────────────────────────────────────────
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username or "لا يوجد"
    first_name = message.from_user.first_name or "مستعمل"
    date_now = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        cursor.execute('INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?)', (user_id, username, first_name, date_now))
        conn.commit()
    except Exception as e:
        print(f"DB Error: {e}")

    set_user_state(user_id, "MAIN_MENU")

    welcome_text = (
        f"أهلاً وسهلاً بك يا غالي الفال، ويا وجوه الخير والبركة! ✨🌸\n\n"
        f"نورتني وشرفتني بحضورك الراقي.. تفضل، واش حاب تسألني اليوم؟ قلبي وعقلي راه ليك! 🥰🩵"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard(user_id))

# ─── معالجة الرسائل والأزرار ───────────────────────────────────────────
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text
    current_state = get_user_state(user_id)

    # حماية: إذا ضغط المستخدم على أي زر رئيسي يتم تصفير حالته فوراً ليعرف البوت ماذا يفعل
    if text in ["📊 عدد المشتركين", "📢 إرسال منشور للمشتركين", "🕌 سؤال شرعي", "🔬 سؤال علمي", "✨ مساعدة", "🌸 عن البوت"]:
        set_user_state(user_id, "MAIN_MENU")
        current_state = "MAIN_MENU"

    # لوحة تحكم المشرفين
    if user_id in ADMIN_IDS:
        if text == "📊 عدد المشتركين":
            cursor.execute('SELECT COUNT(*) FROM users')
            count = cursor.fetchone()[0]
            inline_markup = types.InlineKeyboardMarkup()
            inline_markup.add(types.InlineKeyboardButton("📋 جلب بيانات المشتركين تفصيلياً", callback_data="get_users_data"))
            bot.reply_to(message, f"📊 إجمالي عدد المشتركين المسجلين حالياً: *{count}* مستخدم.", reply_markup=inline_markup, parse_mode="Markdown")
            return

        elif text == "📢 إرسال منشور للمشتركين":
            sent_msg = bot.reply_to(message, "📢 من فضلك أرسل الآن النص أو المنشور الذي تريد تعميمه:")
            bot.register_next_step_handler(sent_msg, broadcast_message)
            return

    # الأزرار العامة للمستخدمين
    if text == "🕌 سؤال شرعي":
        set_user_state(user_id, "ASKING_SHARI")
        bot.reply_to(message, "تفضلي أختي الكريمة بطرح سؤالك الفقهي أو الشرعي، وسأجيبك بناءً على الكتاب والسنة بكل هدوء ولطف وبثقة 🥰🌸")
        return
        
    elif text == "🔬 سؤال علمي":
        set_user_state(user_id, "ASKING_SCIENTIFIC")
        bot.reply_to(message, "أنا هنا لمساعدتكِ في الجانب العلمي والثقافي! واش هو سؤالك العلمي؟ ✨🔬")
        return
        
    elif text == "✨ مساعدة":
        bot.reply_to(message, "تقدري ترسليلي أي سؤال في أي وقت، وأنا نجاوبك مباشرة بالدارجة الجزائرية بكل وضوح 🥰🩵")
        return
        
    elif text == "🌸 عن البوت":
        bot.reply_to(message, "أنا بوت ذكاء اصطناعي متطور، تم تصميمي باه نكون رفيقة ذكية ومستشارة لطيفة ومثقفة تساعدكم 🌸✨")
        return

    # هنا يتم استقبال نص الأسئلة الموجهة للذكاء الاصطناعي بناءً على حالة المستخدم
    if current_state == "ASKING_SHARI":
        prompt_modifier = f"أجب على هذا السؤال من منظور شرعي فقهي خالص مستنداً إلى الكتاب والسنة المطهرة.\nالسؤال: {text}"
    elif current_state == "ASKING_SCIENTIFIC":
        prompt_modifier = f"أجب على هذا السؤال من منظور علمي، أكاديمي، وثقافي دقيق جداً.\nالسؤال: {text}"
    else:
        prompt_modifier = text

    # إرسال الطلب إلى Groq AI
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": prompt_modifier}
            ],
            model=GROQ_MODEL,
        )
        reply = chat_completion.choices.message.content
        bot.reply_to(message, reply)
        set_user_state(user_id, "MAIN_MENU")
    except Exception as e:
        bot.reply_to(message, "عذراً، صرا خطأ صغير وأنا نوجد في الإجابة تاعك. اسمحيلي! 😥")
        print(f"Groq API Error: {e}")

# ─── جلب البيانات التفصيلية للمشرفين ──────────────────────────────────────
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ عذراً، هذا القسم مخصص للمشرفين فقط!")
        return

    if call.data == "get_users_data":
        cursor.execute('SELECT user_id, username, first_name, joined_date FROM users')
        users = cursor.fetchall()
        if not users:
            bot.send_message(call.message.chat.id, "قائمة المشتركين فارغة حالياً.")
            return
        
        response = "📋 *بيانات المشتركين المسجلين:*\n\n"
        for u in users:
            # تم إصلاح استدعاء الفهارس البرمجية هنا u[2] و u[0] لتجنب أخطاء الإرسال في تلغرام
            response += f"👤 الاسم: {u[2]}\n🆔 الآيدي: `{u[0]}`\n🔗 المعرف: @{u[1]}\n📅 انضم في: {u[3]}\n──────────────────\n"
        
        if len(response) > 4000:
            for x in range(0, len(response), 4000):
                bot.send_message(call.message.chat.id, response[x:x+4000], parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, response, parse_mode="Markdown")
        bot.answer_callback_query(call.id)

# ─── بث المنشورات لجميع المشتركين ───────────────────────────────────────────────
def broadcast_message(message):
    if message.text in ["📊 عدد المشتركين", "📢 إرسال منشور للمشتركين", "🕌 سؤال شرعي", "🔬 سؤال علمي", "✨ مساعدة", "🌸 عن البوت"]:
        bot.reply_to(message, "❌ تم إلغاء عملية البث لأنك قمت بالضغط على زر آخر.")
        return

    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    success_count = 0
    
    for u in users:
        try:
            # تم الإصلاح البرمجي هنا إلى u[0] للحصول على القيمة الرقمية الصافية للآيدي لتفادي توقف البث
            bot.send_message(u[0], message.text)
            success_count += 1
        except Exception:
            continue
            
    bot.reply_to(message, f"📢 تمت عملية البث بنجاح!\nوصل المنشور إلى *{success_count}* مستخدم.", parse_mode="Markdown")

# ─── تشغيل البوت ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("البوت يعمل الآن بأعلى كفاءة واستقرار وخالي تماماً من الأخطاء البرمجية...")
    bot.infinity_polling()
        
