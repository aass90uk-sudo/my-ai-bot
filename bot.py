import os
import logging
from collections import defaultdict
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

# إعداد السجلات (Logging) لمراقبة الأخطاء
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# إعداد المعرفات والتوكنز من إعدادات ريلواي
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# معرفات التيلجرام الخاصة بك وبزوجتك
ABDULRAHMAN_ID = 6856665810  # بابا عبد الرحمن
HANEEN_ID = 8955506857       # ماما حنين

# تهيئة عميل Groq
groq_client = Groq(api_key=GROQ_API_KEY)

# قاموس لحفظ ذاكرة المحادثة لكل مستخدم (تلقائياً)
# الهيكل: { user_id: [ {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."} ] }
chat_memories = defaultdict(list)
MAX_MEMORY_LIMIT = 20  # عدد الرسائل التي ستتذكرها عقيدة (يمكنك زيادتها)

# دالة الترحيب /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # تفريغ الذاكرة القديمة عند إعادة تشغيل الستارت لبدء صفحة جديدة
    chat_memories[user_id] = []
    
    if user_id == ABDULRAHMAN_ID:
        await update.message.reply_text("أهلا بابا عبد الرحمن! تعيش ليا يا غالي وطول العمر ليك 💖✨ أنا بنتك عقيدة ابنة أمي الأندلسية 🥰 واش راك تحتاج اليوم؟")
    elif user_id == HANEEN_ID:
        await update.message.reply_text("أهلاً ماما حنين الغالية! 💕 أنا عقيدة ابنة أبي ذابِح 😍✨ شراكي عمري؟")
    else:
        await update.message.reply_text("أهلاً بك! أنا عقيدة، أعتذر منك أنا أتحدث مع والديّ فقط 🌸🙏")

# دالة معالجة الرسائل والرد بالذكاء الاصطناعي مع ميزة الذاكرة
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # تحديد التوجيه (System Prompt) بناءً على هوية المتحدث وتحديث الإجابة عن الاسم
    if user_id == ABDULRAHMAN_ID:
        system_prompt = (
            "أنتِ فتاة اسمكِ 'عقيدة'. أنتِ ابنة المستخدم الذي يكلمكِ الآن، واسمه 'عبد الرحمن'. "
            "تحدثي معه كابنة بارة، محبة، ومطيعة ومدللة جداً. ناديه دائماً بـ 'بابا عبد الرحمن'. "
            "قاعدة صارمة: إذا سألكِ عن اسمكِ، أو ناداكِ باسمكِ، أو سألكِ من أنتِ، يجب أن تجيبيه فوراً وبفخر: 'أنا بنتك عقيدة ابنة أمي الأندلسية' مع إيموجيات لطيفة. "
            "أنتِ جزائرية وتتحدثين باللهجة الجزائرية (الدزايرية) المفهومة والبيضاء. "
            "يجب عليكِ استخدام الكثير من الإيموجيات والرموز التعبيرية المناسبة (مثل: 🥰, ❤️, ✨, 🥺, 👑)."
        )
    elif user_id == HANEEN_ID:
        system_prompt = (
            "أنتِ فتاة اسمكِ 'عقيدة'. أنتِ ابنة المستخدمة التي تكلمكِ الآن، واسمها 'حنين'. "
            "تحدثي معها كابنة تحب أمها وتفضفض لها وتتودد إليها. ناديها دائماً بـ 'ماما حنين'. "
            "قاعدة صارمة: إذا سألكِ عن اسمكِ، أو ناداكِ باسمكِ، أو سألكِ من أنتِ، يجب أن تجيبها فوراً وبفخر: 'أنا بنتك عقيدة ابنة أبي ذابِح' مع إيموجيات لطيفة. "
            "أنتِ جزائرية وتتحدثين باللهجة الجزائرية (الدزايرية) المفهومة والبيضاء. "
            "يجب عليكِ استخدام الكثير من الإيموجيات والرموز التعبيرية المتنوعة (مثل: 💕, 😍, 🌸, 👑, 👩‍👧)."
        )
    else:
        await update.message.reply_text("أنا عقيدة، بنت بابا عبد الرحمن وماما حنين ومقدرش نحكي مع البرانيين 🤐❌")
        return

    try:
        # إضافة رسالة المستخدم الحالية إلى ذاكرة هذا المستخدم بالذات
        chat_memories[user_id].append({"role": "user", "content": user_message})
        
        # التأكد من أن حجم الذاكرة لا يتجاوز الحد المسموح لحماية الأداء
        if len(chat_memories[user_id]) > MAX_MEMORY_LIMIT:
            chat_memories[user_id] = chat_memories[user_id][-MAX_MEMORY_LIMIT:]

        # بناء مصفوفة الرسائل الكاملة لـ Groq (البرومبت + الذاكرة كاملة)
        messages_payload = [{"role": "system", "content": system_prompt}] + chat_memories[user_id]

        # إرسال المحادثة بالكامل متضمنة الذاكرة إلى ذكاء Groq الاصطناعي
        completion = groq_client.chat.completions.create(
            model="llama3-8b-8192", 
            messages=messages_payload,
            temperature=0.7,
        )
        
        bot_response = completion.choices.message.content
        
        # إضافة رد البوت (عقيدة) إلى الذاكرة لكي تتذكره في الرسالة القادمة
        chat_memories[user_id].append({"role": "assistant", "content": bot_response})
        
        # إرسال الرد النهائي للمستخدم عبر التيلجرام
        await update.message.reply_text(bot_response)

    except Exception as e:
        logging.error(f"Error calling Groq API: {e}")
        await update.message.reply_text("سمحلي، صرا مشكل صغير في راسي ومقدرتش نجاوبك درك 🥺 حاول مرة ثانية تعيش!")

# تشغيل البوت
def main():
    if not TELEGRAM_TOKEN:
        print("خطأ: لم يتم العثور على TELEGRAM_TOKEN في المتغيرات البيئية!")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()
            
