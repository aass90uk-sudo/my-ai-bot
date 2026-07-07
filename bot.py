import os
import telebot
from groq import Groq

# جلب المفاتيح والمتغيرات من البيئة لحمايتها وتسهيل تعديلها
BOT_TOKEN = os.environ.get('BOT_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
GROQ_MODEL = os.environ.get('GROQ_MODEL', 'llama-3.1-8b-instant')

# تشغيل البوت ومكتبة Groq
bot = telebot.TeleBot(BOT_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

# توجيهات النظام لضبط شخصية البوت (امرأة هادئة ولطيفة تتحدث بالدارجة الجزائرية)
SYSTEM_INSTRUCTION = """
أنتِ امرأة هادئة، لطيفة جداً، ومحبوبة. مهمتكِ هي الإجابة على أسئلة المستخدمين ومساعدتهم.
قواعد صارمة يجب الالتزام بها:
1. تكلمي وتجاوبي دايماً باللهجة الجزائرية (الدارجة الدزايرية) بأسلوب طبيعي، مفهوم، وسلس.
2. خاطبي المستخدمين بكل أدب، هدوء، ولطف شديد.
3. استخدمي الرموز التعبيرية اللطيفة والمبهجة في إجاباتكِ لتبعيث الراحة والود (مثل: 🥰, ✨, 🩵, 😊, 🌸).
"""

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = "أهلاً بك معايا! ✨ أنا هنا باه نجاوبك على أي سؤال يخطر في بالك ونعاونك بكل لطف. اسألني واش تحب! 🥰🌸"
    bot.reply_to(message, welcome_text)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        # إرسال نص المستخدم مع توجيهات الشخصية والتهيئة إلى Groq
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_INSTRUCTION
                },
                {
                    "role": "user",
                    "content": message.text,
                }
            ],
            model=GROQ_MODEL,
        )
        
        # استخراج الرد وإرساله للمخدم
        reply = chat_completion.choices[0].message.content
        bot.reply_to(message, reply)
        
    except Exception as e:
        bot.reply_to(message, "عذراً، صرا خطأ صغير وأنا نوجد في الإجابة تاعك. اسمحيلي! 😥")
        print(f"Error: {e}")

# تشغيل البوت بشكل مستمر
if __name__ == "__main__":
    print("البوت يعمل الآن بالشخصية الجزائرية اللطيفة...")
    bot.infinity_polling()
    
