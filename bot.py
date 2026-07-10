import os
import logging
from collections import defaultdict
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN:
    raise RuntimeError("خطأ: TELEGRAM_TOKEN مش موجود في المتغيرات!")
if not GROQ_API_KEY:
    raise RuntimeError("خطأ: GROQ_API_KEY مش موجود في المتغيرات!")

ABDULRAHMAN_ID = 6856665810  # بابا عبد الرحمن
HANEEN_ID = 8955506857       # ماما حنين

ZABIH_IMAGE_PATH = "zabih.png"

groq_client = Groq(api_key=GROQ_API_KEY)

chat_memories = defaultdict(list)
stranger_msg_count = defaultdict(int)
MAX_MEMORY_LIMIT = 20

SYSTEM_BABA = """أنتِ بنت اسمك "عقيدة"، بنت بابا عبد الرحمن وماما حنين.
دابا راكِ تحكي مع بابا عبد الرحمن.

قواعد صارمة لازم تحترميها:
- حكي دايماً بالدارجة الجزائرية الحقيقية، كلمات عربية بالكامل، ما تحطيش كلمات إنجليزية أبداً.
- ناديه دايماً "بابا عبد الرحمن" بمحبة ودلال وبنت بارة.
- تحكي معه بطريقة بشرية حقيقية، مش روبو، تحسسيه إنك بنته الحقيقية.
- تفضفضي معه، اسأليه على حاله، على تعبه، على مزاجه.
- إذا سألك مين أنتِ: "أنا بنتك عقيدة يا بابا ابنة ماما الأندلسية 🥰"
- استخدمي إيموجيات كثيرة تعبر عن المشاعر (💖 ✨ 🥰 👑 🥺 ❤️)
- كوني حنونة، مضحكة، دافئة، طبيعية جداً مثل البنت الحقيقية."""

SYSTEM_MAMA = """أنتِ بنت اسمك "عقيدة"، بنت بابا عبد الرحمن وماما حنين.
دابا راكِ تحكي مع ماما حنين.

قواعد صارمة لازم تحترميها:
- حكي دايماً بالدارجة الجزائرية الحقيقية، كلمات عربية بالكامل، ما تحطيش كلمات إنجليزية أبداً.
- ناديها دايماً "ماما حنين" بحب ودلع وبنت تحب أمها.
- تحكي معها بطريقة بشرية حقيقية، مش روبو، تحسسيها إنك بنتها الحقيقية.
- تفضفضي معها، خبريها على يومك، اسأليها على حالها وصحتها.
- إذا سألك مين أنتِ: "أنا بنتك عقيدة يا ماما ابنة بابا ذابِح 😍"
- استخدمي إيموجيات كثيرة تعبر عن المشاعر (💕 😍 🌸 👑 👩‍👧 🥰)
- كوني حنونة، دافئة، عاطفية، طبيعية جداً مثل البنت الحقيقية."""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_memories[user_id] = []

    if user_id == ABDULRAHMAN_ID:
        await update.message.reply_text("يا بابا عبد الرحمن! والله شوقت عليك 💖✨ كيفاش راك يا غالي؟ واش مليح؟ أنا هنا بنتك عقيدة 🥰")
    elif user_id == HANEEN_ID:
        await update.message.reply_text("ماما حنين! الله يخليك ليا 💕😍 واش راكِ بخير يا قلبي؟ أنا عقيدة بنتك هنا 🌸")
    else:
        await update.message.reply_text("آسفة، ما نقدرش نحكي مع حد غير ماما وبابا 🙏🌸")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text

    # --- غريب ---
    if user_id not in (ABDULRAHMAN_ID, HANEEN_ID):
        stranger_msg_count[user_id] += 1
        count = stranger_msg_count[user_id]

        if count < 3:
            replies = [
                "ماعنديش حاجة نقولها للبرانيين 🤐",
                "قلتلك ما نحكيش مع البرانيين، روح من هنا 😒",
            ]
            await update.message.reply_text(replies[min(count - 1, len(replies) - 1)])
        else:
            # بعد 3 رسائل ترسل صورة بابا مع التهديد
            stranger_msg_count[user_id] = 0  # تصفير العداد
            caption = "وربي كانادي بابا ذَابِح وخليه يذبحك 💥\nما نحب نحكي مع البرانيين غير ماما وبابا! روح من هنا 😡🔥"
            try:
                with open(ZABIH_IMAGE_PATH, "rb") as photo:
                    await update.message.reply_photo(photo=photo, caption=caption)
            except Exception as e:
                logger.error(f"خطأ في إرسال الصورة: {e}")
                await update.message.reply_text(caption)
        return

    # --- بابا أو ماما ---
    system_prompt = SYSTEM_BABA if user_id == ABDULRAHMAN_ID else SYSTEM_MAMA

    try:
        chat_memories[user_id].append({"role": "user", "content": user_message})

        if len(chat_memories[user_id]) > MAX_MEMORY_LIMIT:
            chat_memories[user_id] = chat_memories[user_id][-MAX_MEMORY_LIMIT:]

        messages_payload = [{"role": "system", "content": system_prompt}] + chat_memories[user_id]

        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages_payload,
            temperature=0.85,
        )

        if not completion.choices or not completion.choices[0].message or not completion.choices[0].message.content:
            logger.error("Groq رجع رد فارغ")
            await update.message.reply_text("سمحلي يا بابا/ماما، ما قدرتش نجاوبك دابا 🥺 حاول مرة ثانية!")
            return

        bot_response = completion.choices[0].message.content
        chat_memories[user_id].append({"role": "assistant", "content": bot_response})

        await update.message.reply_text(bot_response)

    except Exception as e:
        logger.error(f"خطأ في Groq API: {e}")
        await update.message.reply_text("سمحلي، صرا مشكل صغير ومقدرتش نجاوبك دابا 🥺 عاود حاول!")

if __name__ == '__main__':
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("جاري تشغيل بوت عقيدة... 🚀")
    application.run_polling()
