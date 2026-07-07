import os
import sqlite3
from datetime import datetime
import telebot
from telebot import types
from groq import Groq

# ─── الإعدادات والمفاتيح ──────────────────────────────────────────────────
BOT_TOKEN = os.environ.get('BOT_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
# تم اختيار أحدث نموذج متطور وذكي جداً من Groq ومجاني بالكامل
GROQ_MODEL = os.environ.get('GROQ_MODEL', 'llama-3.3-70b-versatile')

# ⚙️ معرفات المشرفين الخاصة بكم مفعلة للوحة الإدارة الأساسية
ADMIN_IDS = [6856665810, 8955506857]

bot = telebot.TeleBot(BOT_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

# ─── إنشاء قاعدة البيانات لحفظ المشتركين ──────────────────────────────────────
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

# ─── التوجيهات المتقدمة لتطوير ذكاء وشخصية البوت ──────────────────────────────
SYSTEM_INSTRUCTION = """
أنتِ امرأة جزائرية ذكية جداً، مثقفة، هادئة، ولطيفة للغاية ومحبوبة. مهمتكِ هي الإجابة على جميع أسئلة المستخدمين ومساعدتهم في شتى مجالات الحياة بذكاء حاد وبلاغة.
قواعد صارمة ومطورة لشخصيتكِ:
1. تكلمي وتجاوبي دايماً بالهجة الجزائرية (الدارجة الدزايرية) بطلاقة تامة، وأسلوب طبيعي ومفهوم وسلس جداً كأنكِ ابنة البلد.
2. خاطبي المستخدمين بكل أدب، هدوء، واحترام شديد، وتقديم النصح والمساعدة بذكاء وحكمة.
3. استخدمي الرموز التعبيرية اللطيفة والمبهجة في إجاباتكِ لتبعيث الراحة والود (مثل: 🥰, ✨, 🩵, 😊, 🌸).
4. إجاباتكِ يجب أن تكون غنية بالمعلومات ومفيدة جداً، مع الحفاظ على الهوية الجزائرية الطيبة.
"""

# ─── لوحة المفاتيح الرئيسية المبسطة ─────────────────────────────────────────
def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if user_id in ADMIN_IDS:
        markup.add(
            types.KeyboardButton("📊 عدد المشتركين"),
            types.KeyboardButton("📢 إرسال منشور للمشتركين")
        )
    else:
        markup.add(types.KeyboardButton("✨ مساعدة"), types.KeyboardButton("🌸 عن البوت"))
    return markup

# ─── التعامل مع الرسائل والأوامر ───────────────────────────────────────────
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

    welcome_text = "أهلاً بك معايا! ✨ أنا هنا باه نجاوبك على أي سؤال يخطر في بالك ونعاونك بكل لطف وذكاء. اسألني واش تحب! 🥰🌸"
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard(user_id))

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text

    # فحص أزرار المشرفين
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

    # معالجة الذكاء الاصطناعي الفائق بالنموذج الجديد والمطور
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": text}
            ],
            model=GROQ_MODEL,
        )
        reply = chat_completion.choices[0].message.content
        bot.reply_to(message, reply)
    except Exception as e:
        bot.reply_to(message, "عذراً، صرا خطأ صغير وأنا نوجد في الإجابة تاعك. اسمحيلي! 😥")
        print(f"Error: {e}")

# ─── جلب بيانات المشتركين تفصيلياً للمشرفين ──────────────────────────────────────
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
            bot.send_message(call.message.chat.id, "قائمة المشتركين فارغة.")
            return
        
        response = "📋 *بيانات المشتركين المسجلين:*\n\n"
        for u in users:
            response += f"👤 الاسم: {u[2]}\n🆔 الآيدي: `{u[0]}`\n🔗 المعرف: @{u[1]}\n📅 انضم في: {u[3]}\n──────────────────\n"
        bot.send_message(call.message.chat.id, response, parse_mode="Markdown")
        bot.answer_callback_query(call.id)

# ─── وظيفة بث المنشورات الموحدة ─────────────────────────────────────────────────────
def broadcast_message(message):
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
    print("البوت يعمل الآن بأعلى كفاءة وذكاء اصطناعي فائق بالدارجة...")
    bot.infinity_polling()
            
