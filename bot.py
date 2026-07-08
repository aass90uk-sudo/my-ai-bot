import os
import sqlite3
from datetime import datetime
import telebot
from telebot import types

# ─── الإعدادات ──────────────────────────────────────────────────
BOT_TOKEN = os.environ.get('BOT_TOKEN')

# معرفات المشرفين الخاصة بكم
ADMIN_IDS = [6856665810, 8955506857]

bot = telebot.TeleBot(BOT_TOKEN)

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
    return row if row else "MAIN_MENU"

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
        f"أهلاً وسهلاً بك يا وجوه الخير والبركة! ✨🌸\n\n"
        f"نورتني وشرفتني بحضورك الراقي.. تفضل، واش حاب تسألني اليوم؟ 🥰🩵"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard(user_id))

# ─── معالجة الرسائل والأزرار ───────────────────────────────────────────
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text
    current_state = get_user_state(user_id)

    if text in ["📊 عدد المشتركين", "📢 إرسال منشور للمشتركين", "🕌 سؤال شرعي", "🔬 سؤال علمي", "✨ مساعدة", "🌸 عن البوت"]:
        set_user_state(user_id, "MAIN_MENU")
        current_state = "MAIN_MENU"

    # لوحة تحكم المشرفين
    if user_id in ADMIN_IDS:
        if text == "📊 عدد المشتركين":
            cursor.execute('SELECT COUNT(*) FROM users')
            count = cursor.fetchone()
            inline_markup = types.InlineKeyboardMarkup()
            inline_markup.add(types.InlineKeyboardButton("📋 جلب بيانات المشتركين تفصيلياً", callback_data="get_users_data"))
            bot.reply_to(message, f"📊 إجمالي عدد المشتركين المسجلين حالياً: *{count[0]}* مستخدم.", reply_markup=inline_markup, parse_mode="Markdown")
            return

        elif text == "📢 إرسال منشور للمشتركين":
            sent_msg = bot.reply_to(message, "📢 من فضلك أرسل الآن النص أو المنشور الذي تريد تعميمه:")
            bot.register_next_step_handler(sent_msg, broadcast_message)
            return

    # الأزرار العامة للمستخدمين
    if text == "🕌 سؤال شرعي":
        set_user_state(user_id, "ASKING_SHARI")
        bot.reply_to(message, "تفضلي أختي الكريمة بطرح سؤالك الفقهي أو الشرعي، وسأجيبك بكل هدوء ولطف وبثقة 🥰🌸")
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

    # رد محلي فوري لا يحتاج للذكاء الاصطناعي الخارجي للتأكد من عمل البوت
    if current_state == "ASKING_SHARI":
        reply = f"صحة أختي، بخصوص سؤالك الشرعي: ({text})، تم استلامه بنجاح وجاري مراجعته بناءً على الكتاب والسنة ✨🌸."
    elif current_state == "ASKING_SCIENTIFIC":
        reply = f"يعطيك الصحة، بخصوص سؤالك العلمي: ({text})، تم تسجيل الطلب وبحث المعطيات بدقة 🔬✨."
    else:
        reply = f"مرحباً بك! لقد أرسلت: {text}. يرجى اختيار قسم من الأزرار بالأسفل لمساعدتك بدقة 🥰."

    bot.reply_to(message, reply)
    set_user_state(user_id, "MAIN_MENU")

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
            bot.send_message(u[0], message.text)
            success_count += 1
        except Exception:
            continue
            
    bot.reply_to(message, f"📢 تمت عملية البث بنجاح!\nوصل المنشور إلى *{success_count}* مستخدم.", parse_mode="Markdown")

# ─── تشغيل البوت ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    bot.infinity_polling()
                     
