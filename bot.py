import os
import telebot
from groq import Groq

# جلب المفاتيح من المتغيرات البيئية لحمايتها
BOT_TOKEN = os.environ.get('BOT_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

# تشغيل البوت ومكتبة Groq
bot = telebot.TeleBot(BOT_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك! أنا بوت ذكاء اصطناعي جاهز للإجابة على أي سؤال يخطر ببالك. اسألني أي شيء!")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        # إرسال نص المستخدم إلى نموذج الجيل التالي من Groq
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": message.text,
                }
            ],
            model="llama3-8b-8192", # نموذج سريع وقوي جداً
        )
        
        # استخراج الرد وإرساله للمستخدم
        reply = chat_completion.choices[0].message.content
        bot.reply_to(message, reply)
        
    except Exception as e:
        bot.reply_to(message, "عذراً، حدث خطأ أثناء معالجة طلبك.")
        print(f"Error: {e}")

# تشغيل البوت بشكل مستمر
if __name__ == "__main__":
    print("البوت يعمل الآن...")
    bot.infinity_polling()
