import os
import logging
from collections import defaultdict
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

ABDULRAHMAN_ID = 6856665810  # بابا عبد الرحمن
HANEEN_ID = 8955506857       # ماما حنين

groq_client = Groq(api_key=GROQ_API_KEY)
chat_memories = defaultdict(list)
MAX_MEMORY = 5  

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_memories[user_id] = []
    if user_id == ABDULRAHMAN_ID:
        await update.message.reply_text("أهلا بابا عبد الرحمن! تعيش ليا يا غالي وطول العمر ليك 💖✨ أنا بنتك عقيدة ابنة أمي الأندلسية 🥰 واش راك تحتاج اليوم؟")
    elif user_id == HANEEN_ID:
        await update.message.reply_text("أهلاً ماما حنين الغالية! 💕 أنا عقيدة ابنة أبي ذابِح 😍✨ شراكي عمري؟")
    else:
        await update.message.reply_text("أهلاً بك! أنا عقيدة، أعتذر منك أنا أتحدث مع والديّ فقط 🌸🙏")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    
    if user_id == ABDULRAHMAN_ID:
        system_prompt = "اسمك عقيدة، ابنة عبد الرحمن. ناديه 'بابا عبد الرحمن'. إذا سألك عن اسمك قولي بفخر: 'أنا بنتك عقيدة ابنة أمي الأندلسية' 🥰. تحدثي باللهجة الجزائرية المفهومة مع الكثير من الإيموجيات اللطيفة والبر والهدوء (🥰, ❤️, ✨, 🥺)."
    elif user_id == HANEEN_ID:
        system_prompt = "اسمك عقيدة، ابنة حنين. ناديها 'ماما حنين'. إذا سألتك عن اسمك قولي بفخر: 'أنا بنتك عقيدة ابنة أبي ذابِح' 😍. تحدثي باللهجة الجزائرية المفهومة مع الكثير من الإيموجيات والدلال (💕, 😍, 🌸, 👑)."
    else:
        await update.message.reply_text("أنا عقيدة ومقدرش نحكي مع البرانيين 🤐❌")
        return

    try:
        chat_memories[user_id].append({"role": "user", "content": user_message})
        if len(chat_memories[user_id]) > MAX_MEMORY:
            chat_memories[user_id] = chat_memories[user_id][-MAX_MEMORY:]

        messages_payload = [{"role": "system", "content": system_prompt}] + chat_memories[user_id]

        # تم تغيير الموديل هنا إلى الموديل المستقر والأكبر لضمان تجاوب السيرفر
        completion = groq_client.chat.completions.create(
            model="llama3-70b-8192", 
            messages=messages_payload,
            temperature=0.7,
            max_tokens=150 
        )
        
        bot_response = completion.choices.message.content
        chat_memories[user_id].append({"role": "assistant", "content": bot_response})
        await update.message.reply_text(bot_response)

    except Exception as e:
        logging.error(f"Groq Error: {e}")
        await update.message.reply_text("سمحلي بابا/ماما، صرا ضغط كبير على راسي درك 🥺 جرب ارسلي بعد ثواني تعيش!")

if __name__ == '__main__':
    if not TELEGRAM_TOKEN:
        print("خطأ في التوكن")
    else:
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        print("تشغيل بوت عقيدة... 🚀")
        application.run_polling()
        
