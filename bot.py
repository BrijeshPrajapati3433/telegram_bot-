import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

# Logging setup taaki Render ke logs me error dikhein
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment Variables se keys uthana (GitHub par safe rahega)
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Groq Client Initialize karna
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# 1. /start Command Handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Oi {user_name}! Main hoon Lisa. 😎\n"
        f"Main is group ko manage bhi kar sakti hoon aur AI ke saath tumhare sawalon ke jawab bhi de sakti hoon.\n"
        f"Batao kya seva karein?"
    )

# 2. Group Management: /ban Command
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if bot has admin rights and sender is admin
    chat = update.effective_chat
    user = update.effective_user
    
    # Simple check for group chat
    if chat.type == "private":
        await update.message.reply_text("Ye command sirf group me kaam karegi bhai.")
        return

    # User admin hai ya nahi check karein
    member = await chat.get_member(user.id)
    if member.status not in ["administrator", "creator"]:
        await update.message.reply_text("Aabe tu admin nahi hai, chup baith! 🤫")
        return

    # Check if reply to a message
    if not update.message.reply_to_message:
        await update.message.reply_text("Kisko ban karna hai? Uske message par reply karke /ban likho.")
        return

    target_user = update.message.reply_to_message.from_user
    try:
        await chat.ban_member(target_user.id)
        await update.message.reply_text(f"💥 {target_user.first_name} ko nikal diya group se!")
    except Exception as e:
        await update.message.reply_text(f"Error: Mujhe admin rights do pehle! ({str(e)})")

# 3. AI Chat Handler (Groq Integration)
async def handle_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_type = update.effective_chat.type

    # Agar group hai, toh bot ko mention karne par hi reply karega
    if chat_type in ["group", "supergroup"]:
        if not context.bot.username or f"@{context.bot.username}" not in user_text:
            return
        # Remove bot username mention from text
        user_text = user_text.replace(f"@{context.bot.username}", "").strip()

    if not groq_client:
        await update.message.reply_text("Groq API Key set nahi hai Render par!")
        return

    try:
        # Lisa ka custom system prompt persona ke liye
        system_prompt = (
            "You are Lisa, a smart, cool, and witty AI group manager. "
            "You speak fluently in Hindi, English, and Hinglish. Keep your responses short, "
            "direct, and matching the user's vibe. Do not give long boring lectures."
        )

        # Groq se chat completion request
        completion = groq_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            temperature=0.7,
            max_tokens=250
        )
        
        bot_response = completion.choices[0].message.content
        await update.message.reply_text(bot_response)

    except Exception as e:
        logger.error(f"Groq AI Error: {e}")
        await update.message.reply_text("Dimaag kharab ho gaya mera (AI Error). Thodi der baad try kar.")

def main():
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable nahi mila!")
        return

    # Application Build karna
    application = Application.builder().token(BOT_TOKEN).build()

    # Handlers Register karna
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ban", ban_user))
    
    # Text messages handle karne ke liye (Filters out commands)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ai_chat))

    # Bot ko start karna (Render background worker ke liye polling mode perfect hai)
    logger.info("Lisa Bot starting...")
    application.run_polling()

if __name__ == "__main__":
    main()
