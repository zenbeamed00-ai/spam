import asyncio
import logging
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.error import TelegramError, RetryAfter
import time

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
        # Your channel ID (you need to get the numeric ID)
        self.channel_id = None  # Will be detected automatically
        
    async def is_user_authorized(self, update: Update) -> bool:
        """Check if user is authorized to use the bot"""
        user = update.effective_user
        if user.username and user.username.lower() == self.allowed_user.lower():
            return True
        
        # If command is sent in channel, check if it's from authorized user via linked chat
        if update.effective_chat.type == "channel":
            try:
                # Try to get sender chat information
                sender_chat = update.effective_message.sender_chat
                if sender_chat and sender_chat.username and sender_chat.username.lower() == self.allowed_user.lower():
                    return True
            except:
                pass
        
        # If it's a private message from unauthorized user
        if update.effective_chat.type == "private":
            await update.message.reply_text("❌ Unauthorized access. You are not allowed to use this bot.")
        
        return False
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send welcome message"""
        if not await self.is_user_authorized(update):
            return
        
        # Auto-detect channel ID if command is sent in channel
        if update.effective_chat.type == "channel":
            self.channel_id = update.effective_chat.id
            logger.info(f"Auto-detected channel ID: {self.channel_id}")
            
        welcome_text = """
🤖 **Mass Message Bot 2025** 🤖

**Authorized User Only**
Welcome back, @seh2ndacc!

**Available Commands:**
✅ /start - Show this message
✅ /send [number] [message] - Send multiple messages
✅ /broadcast [message] - Broadcast message
✅ /status - Check bot status
✅ /help - Show help

**Features:**
• Send up to 10,000+ messages
• Rate limit handling
• Error recovery
• Progress tracking
• Direct channel commands
        """
        
        if update.effective_chat.type == "channel":
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=welcome_text,
                parse_mode='Markdown'
            )
        else:
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
/broadcast Important announcement! - Broadcasts message

**Important Notes:**
• Maximum 10,000 messages per command
• Built-in delay to avoid rate limits
• Automatic retry on errors
• Progress updates every 100 messages
• Can command directly in channel
        """
        
        if update.effective_chat.type == "channel":
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=help_text,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def send_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send multiple messages to the channel"""
        if not await self.is_user_authorized(update):
            return
        
        if not context.args or len(context.args) < 2:
            error_msg = "❌ Usage: /send [number] [message]"
            if update.effective_chat.type == "channel":
                await context.bot.send_message(chat_id=update.effective_chat.id, text=error_msg)
            else:
                await update.message.reply_text(error_msg)
            return
        
        try:
            # Parse arguments
            num_messages = int(context.args[0])
            message_text = ' '.join(context.args[1:])
            
            # Validate number of messages
            if num_messages <= 0:
                error_msg = "❌ Number must be positive"
                if update.effective_chat.type == "channel":
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=error_msg)
                else:
                    await update.message.reply_text(error_msg)
                return
                
            if num_messages > 10000:
                error_msg = "❌ Maximum 10000 messages allowed"
                if update.effective_chat.type == "channel":
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=error_msg)
                else:
                    await update.message.reply_text(error_msg)
                return
            
            # Determine target chat (channel or private)
            target_chat_id = update.effective_chat.id
            if update.effective_chat.type == "channel":
                self.channel_id = update.effective_chat.id
                target_chat_id = self.channel_id
            
            # Send initial confirmation
            progress_text = f"🚀 Starting to send {num_messages} messages...\n📊 Progress: 0/{num_messages} (0%)"
            
            if update.effective_chat.type == "channel":
                progress_msg = await context.bot.send_message(
                    chat_id=target_chat_id,
                    text=progress_text
                )
            else:
                progress_msg = await update.message.reply_text(progress_text)
            
            sent_count = 0
            failed_count = 0
            
            # Send messages with rate limiting
            for i in range(num_messages):
                try:
                    await context.bot.send_message(
                        chat_id=target_chat_id,
                        text=f"{message_text} [{i+1}]"
                    )
                    sent_count += 1
                    
                    # Progress update every 100 messages
                    if (i + 1) % 100 == 0 or (i + 1) == num_messages:
                        progress = (i + 1) / num_messages * 100
                        update_text = (
                            f"📤 Sending messages...\n"
                            f"📊 Progress: {i+1}/{num_messages} ({progress:.1f}%)\n"
                            f"✅ Sent: {sent_count} | ❌ Failed: {failed_count}"
                        )
                        
                        try:
                            await progress_msg.edit_text(update_text)
                        except:
                            # If message editing fails, send new progress message
                            if update.effective_chat.type == "channel":
                                progress_msg = await context.bot.send_message(
                                    chat_id=target_chat_id,
                                    text=update_text
                                )
                            else:
                                progress_msg = await update.message.reply_text(update_text)
                    
                    # Rate limiting delay - optimized for large volumes
                    if (i + 1) % 50 == 0:  # Longer delay every 50 messages
                        await asyncio.sleep(3)
                    elif (i + 1) % 20 == 0:  # Medium delay every 20 messages
                        await asyncio.sleep(1.5)
                    else:
                        await asyncio.sleep(0.3)  # Short delay
                        
                except RetryAfter as e:
                    # Handle rate limits
                    wait_time = e.retry_after
                    try:
                        await progress_msg.edit_text(f"⏳ Rate limit hit. Waiting {wait_time} seconds...")
                    except:
                        pass
                    await asyncio.sleep(wait_time)
                    # Retry the failed message
                    i -= 1
                    
                except TelegramError as e:
                    logger.error(f"Failed to send message {i+1}: {e}")
                    failed_count += 1
                    await asyncio.sleep(2)  # Wait before continuing
            
            # Final report
            final_text = (
                f"🎉 **Message Sending Complete!**\n\n"
                f"✅ Successfully sent: {sent_count}\n"
                f"❌ Failed: {failed_count}\n"
                f"📈 Success rate: {(sent_count/num_messages)*100:.1f}%"
            )
            
            try:
                await progress_msg.edit_text(final_text)
            except:
                # Send final report as new message if editing fails
                if update.effective_chat.type == "channel":
                    await context.bot.send_message(chat_id=target_chat_id, text=final_text)
                else:
                    await update.message.reply_text(final_text)
            
        except ValueError:
            error_msg = "❌ Invalid number format"
            if update.effective_chat.type == "channel":
                await context.bot.send_message(chat_id=update.effective_chat.id, text=error_msg)
            else:
                await update.message.reply_text(error_msg)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            error_msg = "❌ An unexpected error occurred"
            if update.effective_chat.type == "channel":
                await context.bot.send_message(chat_id=update.effective_chat.id, text=error_msg)
            else:
                await update.message.reply_text(error_msg)
    
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check bot status"""
        if not await self.is_user_authorized(update):
            return
        
        # Auto-detect channel ID if command is sent in channel
        if update.effective_chat.type == "channel":
            self.channel_id = update.effective_chat.id
        
        channel_status = "✅ Connected" if self.channel_id else "❓ Not detected"
        
        status_text = f"""
🤖 **Bot Status Report**

✅ **Online and Operational**
👤 **Authorized User:** @seh2ndacc
📢 **Channel Status:** {channel_status}
📊 **Maximum Messages:** 10,000 per command
⚡ **Rate Limit Handling:** Enabled
🔄 **Auto Retry:** Enabled
📈 **Progress Tracking:** Enabled

**Ready to send messages!**
        """
        
        if update.effective_chat.type == "channel":
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=status_text,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(status_text, parse_mode='Markdown')
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
