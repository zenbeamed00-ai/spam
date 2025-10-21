import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import TelegramError, RetryAfter

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class MassMessageBot:
    def __init__(self):
        self.token = "8466733422:AAHxjIE7cb5bLaACbJlsjJzL9Wds-p4NAvU"
        self.allowed_user = "seh2ndacc"
        self.application = None
        
    async def is_user_authorized(self, update: Update) -> bool:
        """Check if user is authorized to use the bot"""
        user = update.effective_user
        if user and user.username and user.username.lower() == self.allowed_user.lower():
            return True
        
        if update.message:
            await update.message.reply_text("❌ Unauthorized access. You are not allowed to use this bot.")
        return False
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send welcome message"""
        if not await self.is_user_authorized(update):
            return
            
        welcome_text = """
🤖 **Mass Message Bot 2025** 🤖

**Authorized User Only**
Welcome back, @seh2ndacc!

**Available Commands:**
✅ /start - Show this message
✅ /send [number] [message] - Send multiple messages
✅ /status - Check bot status
✅ /help - Show help

**Features:**
• Send up to 10,000+ messages
• Rate limit handling
• Error recovery
• Progress tracking
        """
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help message"""
        if not await self.is_user_authorized(update):
            return
            
        help_text = """
📖 **Bot Help Guide**

**Usage Examples:**
/send 10000 ANG BABAGAL NINYO HAHAHA MGA MABUTITEGAYS - Sends 10,000 messages
/send 5000 🚀 - Sends 5000 rocket emojis

**Important Notes:**
• Maximum 10,000 messages per command
• Built-in delay to avoid rate limits
• Automatic retry on errors
• Progress updates every 100 messages
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def send_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send multiple messages"""
        if not await self.is_user_authorized(update):
            return
        
        if not context.args or len(context.args) < 2:
            await update.message.reply_text("❌ Usage: /send [number] [message]")
            return
        
        try:
            # Parse arguments
            num_messages = int(context.args[0])
            message_text = ' '.join(context.args[1:])
            
            # Validate number of messages
            if num_messages <= 0:
                await update.message.reply_text("❌ Number must be positive")
                return
                
            if num_messages > 10000:
                await update.message.reply_text("❌ Maximum 10000 messages allowed")
                return
            
            # Send initial confirmation
            progress_msg = await update.message.reply_text(
                f"🚀 Starting to send {num_messages} messages...\n"
                f"📊 Progress: 0/{num_messages} (0%)"
            )
            
            sent_count = 0
            failed_count = 0
            
            # Send messages with rate limiting
            for i in range(num_messages):
                try:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"{message_text} [{i+1}]"
                    )
                    sent_count += 1
                    
                    # Progress update every 100 messages
                    if (i + 1) % 100 == 0 or (i + 1) == num_messages:
                        progress = (i + 1) / num_messages * 100
                        await progress_msg.edit_text(
                            f"📤 Sending messages...\n"
                            f"📊 Progress: {i+1}/{num_messages} ({progress:.1f}%)\n"
                            f"✅ Sent: {sent_count} | ❌ Failed: {failed_count}"
                        )
                    
                    # Rate limiting delay
                    if (i + 1) % 50 == 0:
                        await asyncio.sleep(2)
                    else:
                        await asyncio.sleep(0.5)
                        
                except RetryAfter as e:
                    # Handle rate limits
                    wait_time = e.retry_after
                    await progress_msg.edit_text(f"⏳ Rate limit hit. Waiting {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    # Retry the failed message
                    i -= 1
                    
                except TelegramError as e:
                    logger.error(f"Failed to send message {i+1}: {e}")
                    failed_count += 1
                    await asyncio.sleep(1)
            
            # Final report
            await progress_msg.edit_text(
                f"🎉 **Message Sending Complete!**\n\n"
                f"✅ Successfully sent: {sent_count}\n"
                f"❌ Failed: {failed_count}\n"
                f"📈 Success rate: {(sent_count/num_messages)*100:.1f}%"
            )
            
        except ValueError:
            await update.message.reply_text("❌ Invalid number format")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            await update.message.reply_text("❌ An unexpected error occurred")
    
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check bot status"""
        if not await self.is_user_authorized(update):
            return
        
        status_text = """
🤖 **Bot Status Report**

✅ **Online and Operational**
👤 **Authorized User:** @seh2ndacc
📊 **Maximum Messages:** 10,000 per command
⚡ **Rate Limit Handling:** Enabled
🔄 **Auto Retry:** Enabled
📈 **Progress Tracking:** Enabled

**Ready to send messages!**
        """
        await update.message.reply_text(status_text, parse_mode='Markdown')
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Exception while handling an update: {context.error}")
    
    def run(self):
        """Start the bot"""
        # Create application
        self.application = Application.builder().token(self.token).build()
        
        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("send", self.send_messages))
        self.application.add_handler(CommandHandler("status", self.status))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
        
        # Start the bot
        logger.info("🤖 Mass Message Bot 2025 is starting...")
        print("Bot is running... Press Ctrl+C to stop")
        
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    bot = MassMessageBot()
    bot.run()
