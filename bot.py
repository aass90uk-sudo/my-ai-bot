import os
import logging
from collections import defaultdict
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

# إعداد السجلات
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# التحقق من المتغيرات البيئية قبل أي شيء
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN:
    raise RuntimeError("خطأ: TELEGRAM_TOKEN غير موجود في المتغيرات البيئية!")
if not GROQ_API_KEY:
    raise RuntimeError("خطأ: GROQ_API_KEY غير موجود في المتغيرات البيئية!")

# معرفات التيلجرام
ABDULRAHMAN_ID = 6856665810  # بابا عبد الرحمن
HANEEN_ID = 8955506857       # ماما حنين

# تهيئة عميل Groq
groq_client = Groq(api_key=GROQ_API_KEY)

# قاموس لحفظ ذاكرة المحادثة لكل مستخدم
chat_memories = defaultdict(list)
MAX_MEMORY_LIMIT = 20

# دالة الترحيب /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_memories[user_id] = []  # تفريغ الذاكرة للبدء من جديد

    if user_id == ABDULRAHMAN_ID:
        await update.message.reply_text("أهلا بابا عبد الرحمن! تعيش ليا يا غالي وطول العمر ليك 💖✨ أنا بنتك عقيدة ابنة أمي الأندلسية 🥰 واش راك تحتاج اليوم؟")
    elif user_id == HANEEN_ID:
        await update.message.reply_text("أهلاً ماما حنين الغالية! 💕 أنا عقيدة ابنة أبي ذابِح 😍✨ شراكي عمري؟")
    else:
        await update.message.reply_text("أهلاً بك! أنا عقيدة، أعتذر منك أنا أتحدث مع والديّ فقط 🌸🙏")

# دالة معالجة الرسائل
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text

    if user_id == ABDULRAHMAN_ID:
        system_prompt = (
            "أنتِ فتاة اسمكِ 'عقيدة'. أنتِ ابنة المستخدم الذي يكلمكِ الآن، واسمه 'عبد الرحمن'. "
            "تحدثي معه كابنة بارة، محبة، ومطيعة ومدللة جداً. ناديه دائماً بـ 'بابا عبد الرحمن'. "
            "قاعدة صارمة ومقدسة: إذا سألكِ عن اسمكِ، أو ناداكِ باسمكِ، أو سألكِ من أنتِ، يجب أن تجيبيه فوراً وبفخر: 'أنا بنتك عقيدة ابنة أمي الأندلسية' مع إيموجيات لطيفة. "
            "أنتِ جزائرية وتتحدثين باللهجة الجزائرية (الدزايرية) المفهومة والبيضاء. "
            "يجب عليكِ استخدام الكثير من الإيموجيات والرموز التعبيرية المناسبة (مثل: 🥰, ❤️, ✨, 🥺, 👑)."
        )
    elif user_id == HANEEN_ID:
        system_prompt = (
            "أنتِ فتاة اسمكِ 'عقيدة'. أنتِ ابنة المستخدمة التي تكلمكِ الآن، واسمها 'حنين'. "
            "تحدثي معها كابنة تحب أمها وتفضفض لها وتتودد إليها. ناديها دائماً بـ 'ماما حنين'. "
            "قاعدة صارمة ومقدسة: إذا سألكِ عن اسمكِ، أو ناداكِ باسمكِ، أو سألكِ من أنتِ، يجب أن تجيبها فوراً وبفخر: 'أنا إبنتك عقيدة ابنة أبي ذابِح' مع إيموجيات لطيفة. "
            "أنتِ جزائرية وتتحدثين باللهجة الجزائرية (الدزايرية) المفهومة والبيضاء. "
            "يجب عليكِ استخدام الكثير من الإيموجيات والرموز التعبيرية المتنوعة (مثل: 💕, 😍, 🌸, 👑, 👩‍👧)."
        )
    else:
        await update.message.reply_text("أنا عقيدة، بنت بابا عبد الرحمن وماما حنين ومقدرش نحكي مع البرانيين 🤐❌")
        return

    try:
        # إضافة رسالة المستخدم إلى ذاكرته
        chat_memories[user_id].append({"role": "user", "content": user_message})

        # حماية حجم الذاكرة
        if len(chat_memories[user_id]) > MAX_MEMORY_LIMIT:
            chat_memories[user_id] = chat_memories[user_id][-MAX_MEMORY_LIMIT:]

        # بناء المصفوفة لـ Groq
        messages_payload = [{"role": "system", "content": system_prompt}] + chat_memories[user_id]

        # طلب الرد من Groq
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages_payload,
            temperature=0.7,
        )

        # التحقق من صحة الرد قبل استخدامه
        if not completion.choices or not completion.choices[0].message or not completion.choices[0].message.content:
            logger.error("Groq returned an empty or invalid response")
            await update.message.reply_text("سمحلي، ما جاوبتنيش الذاكرة درك 🥺 حاول مرة ثانية!")
            return

        bot_response = completion.choices[0].message.content

        # حفظ رد عقيدة في الذاكرة
        chat_memories[user_id].append({"role": "assistant", "content": bot_response})

        await update.message.reply_text(bot_response)

    except Exception as e:
        logger.error(f"خطأ في استدعاء Groq API: {e}")
        await update.message.reply_text("سمحلي، صرا مشكل صغير في راسي ومقدرتش نجاوبك درك 🥺 حاول مرة ثانية تعيش!")

# تشغيل البوت
if __name__ == '__main__':
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("جاري تشغيل بوت عقيدة... 🚀")
    application.run_polling()
