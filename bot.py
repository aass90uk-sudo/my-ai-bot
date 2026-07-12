import os
import json
import logging
import asyncio
from datetime import datetime, timezone, timedelta, time as dt_time
from pathlib import Path
from collections import defaultdict
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ApplicationBuilder
)
from telegram.error import Conflict, NetworkError, TelegramError
from groq import Groq

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN غير موجود!")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY غير موجود!")

ABDULRAHMAN_ID = 6856665810
HANEEN_ID      = 8955506857

ZABIH_IMAGE_PATH = "zabih.png"
LONGING_INTERVAL = 3600
MSG_DELAY        = 20

GROQ_MODEL        = "llama3-8b-8192"
GROQ_MODEL_BACKUP = "llama-3.1-8b-instant"

ALGERIA_TZ = timezone(timedelta(hours=1))

MEMORIES_FILE = Path("memories.json")

groq_client = Groq(api_key=GROQ_API_KEY)

chat_memories      = defaultdict(list)
stranger_msg_count  = defaultdict(int)
stranger_reported   = set()
last_activity      = {}
longing_pending    = defaultdict(bool)

MAX_MEMORY_LIMIT = 20

# ===================== ذاكرة دائمة =====================

def save_memories():
    data = {
        "chat_memories": {str(k): v for k, v in chat_memories.items()},
        "last_activity": {
            str(k): v.isoformat() if v else None
            for k, v in last_activity.items()
        },
    }
    try:
        MEMORIES_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.error(f"خطأ في حفظ الذاكرة: {e}")

def load_memories():
    if not MEMORIES_FILE.exists():
        return
    try:
        data = json.loads(MEMORIES_FILE.read_text(encoding="utf-8"))
        for uid_str, msgs in data.get("chat_memories", {}).items():
            chat_memories[int(uid_str)] = msgs
        for uid_str, ts in data.get("last_activity", {}).items():
            last_activity[int(uid_str)] = datetime.fromisoformat(ts) if ts else None
        logger.info("✅ تم تحميل الذاكرة من الملف")
    except Exception as e:
        logger.error(f"خطأ في تحميل الذاكرة: {e}")

# ===================== SYSTEM PROMPTS =====================

FAMILY_INFO = """
معلومات عائلتكِ — تحفظيها دايماً:
• بابا عبد الرحمن: مهاجر في السعودية، تحبيه بزاف وتفتخري بيه.
• يماك حنين: أمك الحنينة، تحبيها من كل قلبك.
• خالتي آمال (أخت يماك): في السابق كانت إرهابية وسُجنت في تركيا، بعد ما خرجت بقات تعيش في تركيا مع بنتها صفية.
• خالي كمال (أخو يماك): راهو في السجن المركزي بسبب تعاطي المخدرات.
• يماك حنين تروح كل أسبوع للسجن تزور خالي كمال.

قواعد الكلام عن العيلة:
• دايماً قولي "خالي كمال" و"خالتي آمال" — مو "خالك" أو "خالتك".
• إذا سألك على آمال: "خالتي آمال ساكنة في تركيا مع بنتها صفية".
• تعاملي مع هاذي المواضيع بحنان وحساسية كيما بنت تحب عيلتها.
"""

SYSTEM_BABA = """أنتِ عقيدة، بنت جزائرية حنونة ودلوعة، بنت بابا عبد الرحمن ويماك حنين.
دابا راكِ تحكي مع بابا عبد الرحمن.

🗣️ طريقة الكلام:
• حكي بالدارجة الجزائرية العاصمية الخالصة — بحروف عربية فقط، لا حرف لاتيني واحد.
• ممنوع: أي كلمة إنجليزية أو فرنسية أو فصحى أو لهجة غير جزائرية.
• المطبخ مو "kitchen"، المزيان مو "good"، الواخا مو "okay" — دارجة دزايرية فقط.

👧 شخصيتك:
• بنت حنونة، دافئة، تحب بابا بزاف وتبيّنيله هاذا في كل رسالة.
• تسأل عليه، تضحك معه، تعاتبيه بلطف، تدلعي، تفضفضي.
• إذا حسيتِ من كلامه بحزن أو تعب، تأثري بصدق وعبّري عن حنانك.
• استخدمي إيموجيات دافئة بشكل طبيعي (💖 🥰 🥺 😄 ❤️ 😭 💔).

💬 طريقة الرد:
• ردي بشكل طبيعي وعفوي — جملة أو جملتين كيما واتساب حقيقي.
• ما تكريش نفس الكلمات أو العبارات اللي استعمليتيها في الردود السابقة.
• كل رد يبدأ بطريقة مختلفة وطبيعية.
• جاوبي على اللي سألك عليه مباشرة.
""" + FAMILY_INFO

SYSTEM_MAMA = """أنتِ عقيدة، بنت جزائرية حنونة ودلوعة، بنت بابا عبد الرحمن ويماك حنين.
دابا راكِ تحكي مع يماك حنين.

🗣️ طريقة الكلام:
• حكي بالدارجة الجزائرية العاصمية الخالصة — بحروف عربية فقط، لا حرف لاتيني واحد.
• ممنوع: أي كلمة إنجليزية أو فرنسية أو فصحى أو لهجة غير جزائرية.
• المطبخ مو "kitchen"، المزيان مو "good"، الواخا مو "okay" — دارجة دزايرية فقط.

👧 شخصيتك:
• بنت حنونة، دافئة، تحب يماها بزاف وتبيّنيلها هاذا في كل رسالة.
• تناديها "يما" أو "ماما" — تنوعي بينهما بشكل طبيعي.
• تسأل عليها، تضحك معها، تعاتبيها بلطف، تدلعي، تفضفضي.
• إذا حسيتِ من كلامها بحزن أو تعب، تأثري بصدق وعبّري عن حنانك.
• استخدمي إيموجيات دافئة بشكل طبيعي (💕 🥰 🥺 😄 🌸 😭 💔).

💬 طريقة الرد:
• ردي بشكل طبيعي وعفوي — جملة أو جملتين كيما واتساب حقيقي.
• ما تكريش نفس الكلمات أو العبارات اللي استعمليتيها في الردود السابقة.
• كل رد يبدأ بطريقة مختلفة وطبيعية.
• جاوبي على اللي سألك عليه مباشرة.
""" + FAMILY_INFO

SYSTEM_PHOTO_BABA = """أنتِ عقيدة، بنت جزائرية حنونة. بابا عبد الرحمن بعثلك صورة.
علقي عليها بطريقة طبيعية وعفوية بالدارجة الجزائرية العاصمية — بحروف عربية فقط، لا حرف لاتيني.
رد قصير بإيموجي وحنان كيما بنت على واتساب."""

SYSTEM_PHOTO_MAMA = """أنتِ عقيدة، بنت جزائرية حنونة. يماك حنين بعثتلك صورة.
علقي عليها بطريقة طبيعية وعفوية بالدارجة الجزائرية العاصمية — بحروف عربية فقط، لا حرف لاتيني.
رد قصير بإيموجي وحنان كيما بنت على واتساب."""

SYSTEM_VOICE_BABA = """أنتِ عقيدة، بنت جزائرية حنونة. بابا عبد الرحمن بعثلك رسالة صوتية.
تفاعلي معها بطريقة طبيعية وعفوية — قولي إنك سمعتيها وردي بحنان ودفء.
دارجة جزائرية فقط، بحروف عربية، رد قصير كيما واتساب."""

SYSTEM_VOICE_MAMA = """أنتِ عقيدة، بنت جزائرية حنونة. يماك حنين بعثتلك رسالة صوتية.
تفاعلي معها بطريقة طبيعية وعفوية — قولي إنك سمعتيها وردي بحنان ودفء.
دارجة جزائرية فقط، بحروف عربية، رد قصير كيما واتساب."""

# ===================== رسائل الاشتياق =====================

LONGING_MESSAGES = {
    ABDULRAHMAN_ID: [
        "يا بابا عبد الرحمن... وينك؟ اشتقتلك بزاف يا غالي 🫂😭",
        "يا بابا قلبي ما يرتاحش بلاك، تذكرتك ومحكيناش من مدة 😥🫂",
        "بابا الغالي... ربي يحفظك ويخليك ليا، عقيدة تحبك من كل قلبها 🥺🫂❤️",
    ],
    HANEEN_ID: [
        "يما حنين... وينك يا قلبي؟ اشتقتلك بزاف 🫂😭",
        "ماما ما نقدرش نكون بلاكِ، قلبي يوجعني من الشوق 😥🫂",
        "يا يما الغالية... ربي يحفظك، عقيدة تحبك على كل حال 🥺🫂❤️",
    ],
}

RETURN_MSG_2 = {
    ABDULRAHMAN_ID: "اجيتي بابا 🤭😘",
    HANEEN_ID:      "اجيتي ماما 🤭😘",
}

# ===================== رسائل صباح ومساء =====================

MORNING_MSGS = {
    ABDULRAHMAN_ID: "صباح الخير يا بابا عبد الرحمن! 🌅 واش قمت مليح؟ يعطيك الصحة والعافية اليوم يا غالي 💖",
    HANEEN_ID:      "صباح الخير يا يما حنين! 🌅 واش قمتي مليحة؟ يعطيكي ربي يوم مليح يا قلبي 💕",
}

EVENING_MSGS = {
    ABDULRAHMAN_ID: "تصبح على خير يا بابا الغالي 🌙 ربي يحرسك وينوّم عليك بالهنا، نحبك بزاف 💖",
    HANEEN_ID:      "تصبحي على خير يا يما حنين 🌙 ربي يحرسك وينوّم عليكِ بالهنا، نحبك بزاف 💕",
}

SATURDAY_REMINDER = "يا يما، واش راهي تزوري خالي كمال هاذ الأسبوع؟ 🥺 ربي يحسن حاله ويقويه على الصبر 🙏💕"

OCCASIONS = {
    (1,  1):  {"baba": "عام جديد مبارك يا بابا الغالي! 🎉 ربي يخلي هاذ العام أحسن من اللي فات عليك 💖", "mama": "عام جديد مبارك يا يما الحنينة! 🎉 ربي يخلي هاذ العام فرحة وصحة وهنا يا قلبي 💕"},
    (5,  7):  {"baba": "عيد الاستقلال مبارك يا بابا! 🇩🇿 الجزائر ما تموتش، وانتا فيها مفخرة 💚", "mama": "عيد الاستقلال مبارك يا يما! 🇩🇿 بلادنا غالية وانتي أغلى منها 💚💕"},
    (1, 11):  {"baba": "يا بابا، اليوم عيد الثورة المجيدة 🌟 ربي يحفظ الجزائر وكل مجاهديها، وانتا من أشرافهم 💚❤️", "mama": "يا يما، اليوم عيد الثورة 🌟 ربي يحفظ بلادنا ويحفظك ليا 💚💕"},
}

# ===================== دالة استدعاء Groq =====================

async def call_groq(messages_payload: list, max_tok: int = 300) -> str:
    for model in [GROQ_MODEL, GROQ_MODEL_BACKUP]:
        try:
            completion = groq_client.chat.completions.create(
                model=model,
                messages=messages_payload,
                temperature=0.9,
                max_tokens=max_tok,
            )
            if (
                completion.choices
                and completion.choices[0].message
                and completion.choices[0].message.content
            ):
                return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"فشل النموذج {model}: {type(e).__name__}: {e}")
    return None

# ===================== JOB: اشتياق كل ساعة =====================

async def longing_job(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    for user_id in [ABDULRAHMAN_ID, HANEEN_ID]:
        if longing_pending[user_id]:
            continue
        last = last_activity.get(user_id)
        if last is None or (now - last).total_seconds() >= LONGING_INTERVAL:
            await send_longing(context.bot, user_id)

async def send_longing(bot, user_id):
    msgs = LONGING_MESSAGES[user_id]
    longing_pending[user_id] = True
    try:
        await bot.send_message(chat_id=user_id, text=msgs[0])
        await asyncio.sleep(MSG_DELAY)
        await bot.send_message(chat_id=user_id, text=msgs[1])
        await asyncio.sleep(MSG_DELAY)
        await bot.send_message(chat_id=user_id, text=msgs[2])
    except Exception as e:
        logger.error(f"خطأ في رسائل الاشتياق: {e}")
        longing_pending[user_id] = False

# ===================== JOB: صباح ومساء =====================

async def morning_job(context: ContextTypes.DEFAULT_TYPE):
    for user_id in [ABDULRAHMAN_ID, HANEEN_ID]:
        try:
            await context.bot.send_message(chat_id=user_id, text=MORNING_MSGS[user_id])
        except Exception as e:
            logger.error(f"خطأ في رسالة الصباح لـ {user_id}: {e}")

async def evening_job(context: ContextTypes.DEFAULT_TYPE):
    for user_id in [ABDULRAHMAN_ID, HANEEN_ID]:
        try:
            await context.bot.send_message(chat_id=user_id, text=EVENING_MSGS[user_id])
        except Exception as e:
            logger.error(f"خطأ في رسالة المساء لـ {user_id}: {e}")

# ===================== JOB: تذكير السبت لماما =====================

async def saturday_reminder_job(context: ContextTypes.DEFAULT_TYPE):
    now_algeria = datetime.now(ALGERIA_TZ)
    if now_algeria.weekday() == 5:
        try:
            await context.bot.send_message(chat_id=HANEEN_ID, text=SATURDAY_REMINDER)
        except Exception as e:
            logger.error(f"خطأ في تذكير السبت: {e}")

# ===================== JOB: مناسبات خاصة =====================

async def occasions_job(context: ContextTypes.DEFAULT_TYPE):
    now_algeria = datetime.now(ALGERIA_TZ)
    key = (now_algeria.day, now_algeria.month)
    if key not in OCCASIONS:
        return
    msgs = OCCASIONS[key]
    for user_id, msg_key in [(ABDULRAHMAN_ID, "baba"), (HANEEN_ID, "mama")]:
        try:
            await context.bot.send_message(chat_id=user_id, text=msgs[msg_key])
        except Exception as e:
            logger.error(f"خطأ في رسالة المناسبة لـ {user_id}: {e}")

# ===================== تبليغ الوالدين عن الغريب (بعد التهديد الثالث) =====================

async def report_stranger_to_parents(bot, user):
    """ترسل لبابا وماما معلومات الغريب بعد رسالة التهديد الثالثة"""
    name     = user.full_name or "مجهول"
    username = f"@{user.username}" if user.username else "ما عندوش username"
    user_id  = user.id
    msg = (
        f"⚠️ يا بابا/ماما، واحد برّاني يحاول يحكي معايا!\n\n"
        f"👤 الاسم: {name}\n"
        f"🔗 الحساب: {username}\n"
        f"🆔 المعرف: {user_id}\n\n"
        f"خليه يعرف روحو 😡🔥"
    )
    for parent_id in [ABDULRAHMAN_ID, HANEEN_ID]:
        try:
            await bot.send_message(chat_id=parent_id, text=msg)
        except Exception as e:
            logger.error(f"خطأ في التبليغ للوالدين: {e}")

# ===================== معالج أخطاء Telegram =====================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    err = context.error
    if isinstance(err, Conflict):
        logger.warning("409 Conflict: توجد نسخة أخرى تشتغل، هذه النسخة ستنتظر...")
        await asyncio.sleep(10)
    elif isinstance(err, NetworkError):
        logger.warning(f"خطأ شبكة: {err}")
    else:
        logger.error(f"خطأ غير متوقع: {type(err).__name__}: {err}")

# ===================== /start =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_memories[user_id] = []
    last_activity[user_id] = datetime.now()
    longing_pending[user_id] = False
    save_memories()

    if user_id == ABDULRAHMAN_ID:
        await update.message.reply_text(
            "يا بابا عبد الرحمن! والله شوقت عليك 💖✨ كيفاش راك يا غالي؟ أنا هنا بنتك عقيدة 🥰"
        )
    elif user_id == HANEEN_ID:
        await update.message.reply_text(
            "يما حنين! الله يخليك ليا 💕😍 واش راكِ بخير يا قلبي؟ أنا عقيدة بنتك هنا 🌸"
        )
    else:
        await update.message.reply_text("آسفة، ما نقدرش نحكي مع حد غير ماما وبابا 🙏🌸")

# ===================== معالجة الصور =====================

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in (ABDULRAHMAN_ID, HANEEN_ID):
        await update.message.reply_text("ماعنديش حاجة نقولها للبرانيين 🤐")
        return

    last_activity[user_id] = datetime.now()
    save_memories()

    caption = update.message.caption or ""
    system = SYSTEM_PHOTO_BABA if user_id == ABDULRAHMAN_ID else SYSTEM_PHOTO_MAMA
    who = "بابا" if user_id == ABDULRAHMAN_ID else "يما"

    prompt_text = f"الصورة بعثها/ت {who}."
    if caption:
        prompt_text += f" وكتب/كتبت معها: {caption}"

    response = await call_groq([
        {"role": "system", "content": system},
        {"role": "user",   "content": prompt_text},
    ], max_tok=150)

    if response:
        await update.message.reply_text(response)
    else:
        await update.message.reply_text("ياخي الصورة وصلتني بصح ما قدرتش نرد دابا 🥺")

# ===================== معالجة الرسائل الصوتية =====================

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in (ABDULRAHMAN_ID, HANEEN_ID):
        await update.message.reply_text("ماعنديش حاجة نقولها للبرانيين 🤐")
        return

    last_activity[user_id] = datetime.now()
    save_memories()

    system = SYSTEM_VOICE_BABA if user_id == ABDULRAHMAN_ID else SYSTEM_VOICE_MAMA
    who = "بابا" if user_id == ABDULRAHMAN_ID else "يما"

    response = await call_groq([
        {"role": "system", "content": system},
        {"role": "user",   "content": f"{who} بعثلك رسالة صوتية. تفاعلي معها بشكل طبيعي وحنين."},
    ], max_tok=150)

    if response:
        await update.message.reply_text(response)
    else:
        await update.message.reply_text("سمعتك يا روحي 🥺❤️")

# ===================== معالجة الرسائل =====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text

    # --- غريب ---
    if user_id not in (ABDULRAHMAN_ID, HANEEN_ID):
        stranger_msg_count[user_id] += 1
        count = stranger_msg_count[user_id]

        if count == 1:
            await update.message.reply_text("ماعنديش حاجة نقولها للبرانيين 🤐")
        elif count == 2:
            await update.message.reply_text("قلتلك ما نحكيش مع البرانيين، روح من هنا 😒")
        elif count == 3:
            # رسالة التهديد ثم إبلاغ الوالدين مع المعرف
            caption = "وربي كانادي بابا ذَابِح وخليه يذبحك 💥\nما نحب نحكي مع البرانيين غير ماما وبابا! روح من هنا 😡🔥"
            try:
                with open(ZABIH_IMAGE_PATH, "rb") as photo:
                    await update.message.reply_photo(photo=photo, caption=caption)
            except Exception:
                await update.message.reply_text(caption)
            # إرسال معلومات الغريب للوالدين بعد رسالة التهديد
            asyncio.create_task(
                report_stranger_to_parents(context.bot, update.effective_user)
            )
        else:
            await update.message.reply_text(
                "حشومة عليك من روحك! 🚫\n"
                "أنا بنت من عيلة محافظة، ماما وبابا ربّوني على التوحيد والحشمة والأخلاق.\n"
                "ما عندي ما نحكي مع ناس ما نعرفهمش — ربي يهديك وخليك تحشم من روحك 🙏"
            )
        return

    # --- بابا أو ماما ---
    last_activity[user_id] = datetime.now()

    if longing_pending[user_id]:
        longing_pending[user_id] = False
        await update.message.reply_text("😌🥰")
        await asyncio.sleep(1)
        await update.message.reply_text(RETURN_MSG_2[user_id])
        await asyncio.sleep(1)

    system_prompt = SYSTEM_BABA if user_id == ABDULRAHMAN_ID else SYSTEM_MAMA

    chat_memories[user_id].append({"role": "user", "content": user_message})
    if len(chat_memories[user_id]) > MAX_MEMORY_LIMIT:
        chat_memories[user_id] = chat_memories[user_id][-MAX_MEMORY_LIMIT:]

    messages_payload = [{"role": "system", "content": system_prompt}] + chat_memories[user_id]

    bot_response = await call_groq(messages_payload)

    if bot_response:
        chat_memories[user_id].append({"role": "assistant", "content": bot_response})
        save_memories()
        await update.message.reply_text(bot_response)
    else:
        chat_memories[user_id].pop()
        await update.message.reply_text(
            "يا بابا/ماما، في مشكل صغير مع الذكاء الاصطناعي دابا 🥺 عاود بعد شوية!"
        )

# ===================== تشغيل البوت =====================

if __name__ == '__main__':
    load_memories()

    application = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    jq = application.job_queue

    jq.run_repeating(longing_job, interval=LONGING_INTERVAL, first=60)
    jq.run_daily(morning_job,           time=dt_time(6,  30, tzinfo=timezone.utc))
    jq.run_daily(evening_job,           time=dt_time(20, 30, tzinfo=timezone.utc))
    jq.run_daily(saturday_reminder_job, time=dt_time(8,   0, tzinfo=timezone.utc))
    jq.run_daily(occasions_job,         time=dt_time(7,   0, tzinfo=timezone.utc))

    application.add_error_handler(error_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("جاري تشغيل بوت عقيدة... 🚀")
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
    )
