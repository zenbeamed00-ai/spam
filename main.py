import asyncio
import logging
from typing import Optional
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import TelegramError, RetryAfter, TimedOut, NetworkError

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
        self.max_messages = 1_000_000
        self.batch_size = 30
        self.base_delay = 0.04
        self.batch_delay = 1.5

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

        welcome_text = f"""
🤖 **Mass Message Bot 2025** 🤖

**Authorized User Only**
Welcome back, @{self.allowed_user}!

**Available Commands:**
✅ /start - Show this message
✅ /send [number] [message] - Send multiple messages
✅ /status - Check bot status
✅ /help - Show help

**Features:**
• Send up to {self.max_messages:,} messages
• Intelligent rate limit handling
• Automatic error recovery
• Real-time progress tracking
• Optimized batch sending
        """
        await update.message.reply_text(welcome_text, parse_mode='Markdown')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help message"""
        if not await self.is_user_authorized(update):
            return

        help_text = f"""
📖 **Bot Help Guide**

**Usage Examples:**
`/send 1000 Hello World!` - Sends 1,000 messages
`/send 50000 🚀 Fast delivery` - Sends 50,000 messages

**Important Notes:**
• Maximum {self.max_messages:,} messages per command
• Optimized delays to avoid rate limits
• Automatic retry on network errors
• Progress updates every 500 messages
• Messages are numbered automatically

**Rate Limiting:**
The bot uses intelligent batching and delays to maximize speed while avoiding Telegram rate limits.
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def send_single_message(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        chat_id: int,
        text: str,
        retry_count: int = 3
    ) -> bool:
        """Send a single message with retry logic"""
        for attempt in range(retry_count):
            try:
                await context.bot.send_message(chat_id=chat_id, text=text)
                return True
            except RetryAfter as e:
                wait_time = e.retry_after + 1
                logger.warning(f"Rate limit hit. Waiting {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            except (TimedOut, NetworkError) as e:
                logger.warning(f"Network error (attempt {attempt + 1}/{retry_count}): {e}")
                await asyncio.sleep(2 ** attempt)
            except TelegramError as e:
                logger.error(f"Telegram error: {e}")
                return False
        return False

    async def send_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send multiple messages with optimized rate limiting"""
        if not await self.is_user_authorized(update):
            return

        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "❌ **Usage:** `/send [number] [message]`\n"
                f"Example: `/send 1000 Hello World!`",
                parse_mode='Markdown'
            )
            return

        try:
            num_messages = int(context.args[0])
            message_text = ' '.join(context.args[1:])

            if num_messages <= 0:
                await update.message.reply_text("❌ Number must be positive")
                return

            if num_messages > self.max_messages:
                await update.message.reply_text(
                    f"❌ Maximum {self.max_messages:,} messages allowed per command"
                )
                return

            progress_msg = await update.message.reply_text(
                f"🚀 **Starting Mass Send**\n\n"
                f"📊 Target: {num_messages:,} messages\n"
                f"⏳ Progress: 0/{num_messages:,} (0.0%)\n"
                f"✅ Sent: 0 | ❌ Failed: 0"
            )

            sent_count = 0
            failed_count = 0
            start_time = asyncio.get_event_loop().time()

            for i in range(num_messages):
                message_number = i + 1
                full_message = f"{message_text} [{message_number}]"

                success = await self.send_single_message(
                    context,
                    update.effective_chat.id,
                    full_message
                )

                if success:
                    sent_count += 1
                else:
                    failed_count += 1

                if message_number % self.batch_size == 0:
                    await asyncio.sleep(self.batch_delay)
                else:
                    await asyncio.sleep(self.base_delay)

                if message_number % 500 == 0 or message_number == num_messages:
                    progress = (message_number / num_messages) * 100
                    elapsed = asyncio.get_event_loop().time() - start_time
                    rate = sent_count / elapsed if elapsed > 0 else 0
                    eta = (num_messages - message_number) / rate if rate > 0 else 0

                    try:
                        await progress_msg.edit_text(
                            f"📤 **Sending Messages...**\n\n"
                            f"📊 Progress: {message_number:,}/{num_messages:,} ({progress:.1f}%)\n"
                            f"✅ Sent: {sent_count:,} | ❌ Failed: {failed_count:,}\n"
                            f"⚡ Rate: {rate:.1f} msg/sec\n"
                            f"⏱️ ETA: {eta:.0f} seconds",
                            parse_mode='Markdown'
                        )
                    except TelegramError as e:
                        logger.warning(f"Failed to update progress: {e}")

            elapsed = asyncio.get_event_loop().time() - start_time
            final_rate = sent_count / elapsed if elapsed > 0 else 0

            await progress_msg.edit_text(
                f"🎉 **Message Sending Complete!**\n\n"
                f"✅ Successfully sent: {sent_count:,}\n"
                f"❌ Failed: {failed_count:,}\n"
                f"📈 Success rate: {(sent_count/num_messages)*100:.1f}%\n"
                f"⏱️ Total time: {elapsed:.1f} seconds\n"
                f"⚡ Average rate: {final_rate:.1f} msg/sec",
                parse_mode='Markdown'
            )

        except ValueError:
            await update.message.reply_text("❌ Invalid number format. Please use a valid integer.")
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            await update.message.reply_text(f"❌ An unexpected error occurred: {str(e)}")

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check bot status"""
        if not await self.is_user_authorized(update):
            return

        status_text = f"""
🤖 **Bot Status Report**

✅ **Status:** Online and Operational
👤 **Authorized User:** @{self.allowed_user}
📊 **Maximum Messages:** {self.max_messages:,} per command
⚡ **Batch Size:** {self.batch_size} messages
⏱️ **Base Delay:** {self.base_delay}s per message
🔄 **Auto Retry:** Enabled (3 attempts)
📈 **Progress Updates:** Every 500 messages

**Optimizations:**
• Intelligent rate limiting
• Network error recovery
• Real-time statistics
• ETA calculations

**Ready to send messages!**
        """
        await update.message.reply_text(status_text, parse_mode='Markdown')

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)

    def run(self):
        """Start the bot"""
        self.application = Application.builder().token(self.token).build()

        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("send", self.send_messages))
        self.application.add_handler(CommandHandler("status", self.status))

        self.application.add_error_handler(self.error_handler)

        logger.info("🤖 Mass Message Bot 2025 is starting...")
        print("=" * 50)
        print("🤖 Mass Message Bot 2025")
        print("=" * 50)
        print(f"✅ Bot is running...")
        print(f"👤 Authorized user: @{self.allowed_user}")
        print(f"📊 Max messages: {self.max_messages:,}")
        print("Press Ctrl+C to stop")
        print("=" * 50)

        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    bot = MassMessageBot()
    bot.run()
                        
