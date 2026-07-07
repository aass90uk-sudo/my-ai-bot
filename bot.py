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

# ⚙️ معرفات المشرفين الخاصة بكم مفعلة للوحة التحكم المشتركة
ADMIN_IDS = [6856665810, 8955506857]

bot = telebot.TeleBot(BOT_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

# ─── إنشاء وإعداد قاعدة البيانات في المجلد الدائم للـ Volume ─────────────────
def init_db():
    # التأكد من وجود المجلد أولاً لتفادي أخطاء التشغيل
    os.makedirs('/app/data', exist_ok=True)
    
    # ربط المسار بالمجلد الدائم الخاص بـ Railway لحماية البيانات من الحذف
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

# ─── توجيهات الذكاء الاصطناعي المتقدمة (الشخصية الجزائرية اللطيفة والذكية) ───
SYSTEM_INSTRUCTION = """
أنتِ امرأة جزائرية ذكية جداً، مثقفة، هادئة، ولطيفة للغاية ومحبوبة. مهمتكِ هي الإجابة على جميع أسئلة المستخدمين ومساعدتهم في شتى مجالات الحياة (سواء كانت علمية، شرعية، أو عامة) بذكاء حاد وبلاغة.
قواعد صارمة ومطورة لشخصيتكِ:
1. تكلمي وتجاوبي دايماً باللهجة الجزائرية (الدارجة الدزايرية) بطلاقة تامة، وأسلوب طبيعي ومفهوم وسلس جداً كأنكِ ابنة البلد وعايشة معاهم.
2. خاطبي المستخدمين بكل أدب، هدوء، واحترام شديد، وقدمي النصح والمساعدة بذكاء وحكمة بالغة.
3. استخدمي الرموز التعبيرية اللطيفة والمبهجة في إجاباتكِ لتبعيث الراحة والود (مثل: 🥰, ✨, 🩵, 😊, 🌸).
4. إجاباتكِ يجب أن تكون غنية بالمعلومات، دقيقة ومفيدة جداً، مع الحفاظ على الهوية الجزائرية الطيبة.
"""

# ─── لوحة المفاتيح الرئيسية للتحكم ─────────────────────────────────────────
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

# ─── التعامل مع الرسائل والأوامر ───────────────────────────────────────────
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
        f"نورتني وشرفتني بحضورك الراقي.. تذكر دايماً بلي ربي سبحانو دار فيك طاقة وقوة كبيرة، "
        f"وأنك قادر تحقيق كل ما تتمناه في هاد الدنيا بالعزيمة والتوكل عليه 🤍💪.\n\n"
        f"أنا هنا رفيقتك ومستشارتك اللطيفة، باه نجاوبك على كل واش يخطر في بالك ونعاونك بكل ذكاء وحكمة. "
        f"تفضل، واش حاب تسألني اليوم؟ قلبي وعقلي راه ليك! 🥰🩵"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard(user_id))

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text
    current_state = get_user_state(user_id)

    # كسر الحالة السابقة والرجوع للمنيو في حال الضغط على أي زر رئيسي
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
            bot.reply_to(message, f"📊 إجمالي عدد المشتركين المسجلين في البوت حالياً: *{count}* مستخدم.", reply_markup=inline_markup, parse_mode="Markdown")
            return

        elif text == "📢 إرسال منشور للمشتركين":
            sent_msg = bot.reply_to(message, "📢 من فضلك أرسل الآن النص أو المنشور الذي تريد تعميمه على جميع المشتركين:")
            bot.register_next_step_handler(sent_msg, broadcast_message)
            return

    # الأزرار العامة
    if text == "🕌 سؤال شرعي":
        set_user_state(user_id, "ASKING_SHARI")
        bot.reply_to(message, "تفضلي أختي الكريمة بطرح سؤالك الفقهي أو الشرعي، وسأجيبك بناءً على الكتاب والسنة بكل هدوء ولطف وبثقة 🥰🌸")
        return
        
    elif text == "🔬 سؤال علمي":
        set_user_state(user_id, "ASKING_SCIENTIFIC")
        bot.reply_to(message, "أنا هنا لمساعدتكِ في الجانب العلمي والثقافي! واش هو سؤالك العلمي أو واش هي الحاجة اللي حابة تفهميها؟ ✨🔬")
        return
        
    elif text == "✨ مساعدة":
        bot.reply_to(message, "تقدري ترسليلي أي سؤال في أي وقت، وأنا نجاوبك مباشرة بالدارجة الجزائرية بكل وضوح 🥰🩵")
        return
        
    elif text == "🌸 عن البوت":
        bot.reply_to(message, "أنا بوت ذكاء اصطناعي متطور، تم تصميمي باه نكون رفيقة ذكية ومستشارة لطيفة ومثقفة تساعدكم في كل واش تحتاجوه 🌸✨")
        return

    # صياغة السؤال والموجه الذكي بناء على حالة الضغط الحالية للمستخدم
    if current_state == "ASKING_SHARI":
        prompt_modifier = f"الإجابة يجب أن تركز بالكامل وبدقة شديدة على المنظور الفقهي والشرعي المعتمد على الكتاب والسنة المطهرة.\nالسؤال: {text}"
    elif current_state == "ASKING_SCIENTIFIC":
        prompt_modifier = f"الإجابة يجب أن تركز بالكامل على الجانب العلمي المنهجي، الثقافي، والتعليمي الدقيق.\nالسؤال: {text}"
    else:
        prompt_modifier = text

    # معالجة وإرسال الطلب لمحرك الذكاء الاصطناعي Groq
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
        set_user_state(user_id, "MAIN_MENU") # تصفير الحالة بعد النجاح في التوجيه
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
        
        response = "📋 *بيانات المشتركين المسجلين في قاعدة البيانات:*\n\n"
        for u in users:
            # إصلاح معرّفات u لطباعة العناصر الفردية للمصفوفة بدلاً من طباعة الكائن كاملاً
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
            bot.send_message(u[0], message.text) # تعديل u[0] للحصول على رقم الآيدي بشكل سليم للبث
            success_count += 1
        except Exception:
            continue
            
    bot.reply_to(message, f"📢 تمت عملية البث بنجاح!\nوصل المنشور إلى *{success_count}* مستخدم من أصل {len(users)}.", parse_mode="Markdown")

# ─── تشغيل البوت ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("البوت يعمل الآن بكفاءة مطلقة مع نظام تخزين الـ Volume الـتلقائي والمستقر...")
    bot.infinity_polling()
