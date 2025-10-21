import asyncio
import logging
from typing import List, Dict
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import TelegramError, RetryAfter, TimedOut, NetworkError
from collections import deque
import time

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class BotPool:
    """Manages multiple bot instances for load distribution"""

    def __init__(self, tokens: List[str]):
        self.tokens = tokens
        self.bots: List[Bot] = []
        self.bot_stats: List[Dict] = []
        self.current_index = 0
        self.cooldowns = deque()

    async def initialize(self):
        """Initialize all bot instances"""
        for i, token in enumerate(self.tokens):
            bot = Bot(token=token)
            self.bots.append(bot)
            self.bot_stats.append({
                'index': i + 1,
                'sent': 0,
                'failed': 0,
                'rate_limited': 0,
                'last_used': 0
            })
        logger.info(f"✅ Initialized {len(self.bots)} bot instances")

    def get_next_bot(self) -> tuple[Bot, int]:
        """Get next available bot using round-robin with cooldown check"""
        current_time = time.time()

        while self.cooldowns and self.cooldowns[0][1] <= current_time:
            self.cooldowns.popleft()

        cooled_down_indices = {idx for idx, _ in self.cooldowns}

        attempts = 0
        while attempts < len(self.bots):
            if self.current_index not in cooled_down_indices:
                bot = self.bots[self.current_index]
                stats_index = self.current_index
                self.current_index = (self.current_index + 1) % len(self.bots)
                return bot, stats_index

            self.current_index = (self.current_index + 1) % len(self.bots)
            attempts += 1

        oldest_cooldown_idx, _ = self.cooldowns[0]
        return self.bots[oldest_cooldown_idx], oldest_cooldown_idx

    def add_cooldown(self, bot_index: int, seconds: float):
        """Add a cooldown for a specific bot"""
        cooldown_until = time.time() + seconds
        self.cooldowns.append((bot_index, cooldown_until))
        self.bot_stats[bot_index]['rate_limited'] += 1

    def update_stats(self, bot_index: int, success: bool):
        """Update bot statistics"""
        if success:
            self.bot_stats[bot_index]['sent'] += 1
        else:
            self.bot_stats[bot_index]['failed'] += 1
        self.bot_stats[bot_index]['last_used'] = time.time()

    def get_stats_summary(self) -> str:
        """Get formatted statistics for all bots"""
        total_sent = sum(s['sent'] for s in self.bot_stats)
        total_failed = sum(s['failed'] for s in self.bot_stats)
        total_rate_limited = sum(s['rate_limited'] for s in self.bot_stats)

        summary = "**Bot Pool Statistics:**\n\n"
        for stats in self.bot_stats:
            summary += (
                f"🤖 **Bot {stats['index']}:**\n"
                f"  ✅ Sent: {stats['sent']:,}\n"
                f"  ❌ Failed: {stats['failed']:,}\n"
                f"  ⏸️ Rate Limited: {stats['rate_limited']}\n\n"
            )

        summary += (
            f"**Totals:**\n"
            f"✅ Total Sent: {total_sent:,}\n"
            f"❌ Total Failed: {total_failed:,}\n"
            f"⏸️ Total Rate Limits: {total_rate_limited}"
        )

        return summary


class MassMessageBot:
    def __init__(self):
        self.bot_tokens = [
            "8466733422:AAHxjIE7cb5bLaACbJlsjJzL9Wds-p4NAvU",
            "8237233519:AAEI-SQlbUKEioLvRc8KJ1_e4a55Oe3SxnI",
            "8438094178:AAFvU4tugRbuaGlge4MSNmwK7hOOZa2iou4"
        ]
        self.allowed_user = "seh2ndacc"
        self.application = None
        self.bot_pool = None
        self.max_messages = 10_000_000
        self.base_delay = 0.03
        self.batch_size = 40
        self.batch_delay = 1.0

    async def initialize_pool(self):
        """Initialize the bot pool"""
        self.bot_pool = BotPool(self.bot_tokens)
        await self.bot_pool.initialize()

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
🤖 **Mass Message Bot 2025 - Multi-Bot Edition** 🤖

**Authorized User Only**
Welcome back, @{self.allowed_user}!

**Available Commands:**
✅ /start - Show this message
✅ /send [number] [message] - Send unlimited messages
✅ /status - Check bot pool status
✅ /stats - View detailed statistics
✅ /help - Show help

**Features:**
• 🚀 **{len(self.bot_tokens)} Bot Rotation** - Distributes load across multiple bots
• 📊 Send up to {self.max_messages:,} messages per command
• ⚡ Intelligent rate limit handling
• 🔄 Automatic bot rotation and cooldown management
• 📈 Real-time progress tracking
• 🎯 Optimized for maximum throughput
        """
        await update.message.reply_text(welcome_text, parse_mode='Markdown')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help message"""
        if not await self.is_user_authorized(update):
            return

        help_text = f"""
📖 **Bot Help Guide - Multi-Bot System**

**Usage Examples:**
`/send 10000 Hello World!` - Sends 10,000 messages
`/send 1000000 🚀 Unlimited Power!` - Sends 1M messages

**How It Works:**
• Uses {len(self.bot_tokens)} bots in rotation
• Each bot handles messages independently
• Automatic load balancing
• Smart cooldown management when rate limits hit

**Commands:**
• `/send [num] [msg]` - Send messages
• `/stats` - View bot pool statistics
• `/status` - Check system status

**Rate Limiting Strategy:**
• Round-robin bot rotation
• Automatic cooldown when limits hit
• Other bots continue while one is cooling down
• Maximum throughput with minimal delays
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def send_single_message(
        self,
        chat_id: int,
        text: str,
        retry_count: int = 3
    ) -> tuple[bool, int]:
        """Send a single message using bot pool with retry logic"""
        for attempt in range(retry_count):
            try:
                bot, bot_index = self.bot_pool.get_next_bot()
                await bot.send_message(chat_id=chat_id, text=text)
                self.bot_pool.update_stats(bot_index, success=True)
                return True, bot_index

            except RetryAfter as e:
                wait_time = e.retry_after + 1
                logger.warning(f"Bot {bot_index + 1} rate limited. Cooldown: {wait_time}s")
                self.bot_pool.add_cooldown(bot_index, wait_time)

                if attempt < retry_count - 1:
                    await asyncio.sleep(0.5)

            except (TimedOut, NetworkError) as e:
                logger.warning(f"Network error on bot {bot_index + 1} (attempt {attempt + 1}/{retry_count}): {e}")
                if attempt < retry_count - 1:
                    await asyncio.sleep(2 ** attempt)

            except TelegramError as e:
                logger.error(f"Telegram error on bot {bot_index + 1}: {e}")
                self.bot_pool.update_stats(bot_index, success=False)
                return False, bot_index

        return False, -1

    async def send_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send multiple messages with bot pool rotation"""
        if not await self.is_user_authorized(update):
            return

        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "❌ **Usage:** `/send [number] [message]`\n"
                f"Example: `/send 10000 Hello World!`",
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
                f"🚀 **Starting Multi-Bot Mass Send**\n\n"
                f"📊 Target: {num_messages:,} messages\n"
                f"🤖 Active Bots: {len(self.bot_tokens)}\n"
                f"⏳ Progress: 0/{num_messages:,} (0.0%)\n"
                f"✅ Sent: 0 | ❌ Failed: 0"
            )

            sent_count = 0
            failed_count = 0
            start_time = time.time()
            bot_usage = {i: 0 for i in range(len(self.bot_tokens))}

            for i in range(num_messages):
                message_number = i + 1
                full_message = f"{message_text} [{message_number}]"

                success, bot_index = await self.send_single_message(
                    update.effective_chat.id,
                    full_message
                )

                if success:
                    sent_count += 1
                    if bot_index >= 0:
                        bot_usage[bot_index] = bot_usage.get(bot_index, 0) + 1
                else:
                    failed_count += 1

                if message_number % self.batch_size == 0:
                    await asyncio.sleep(self.batch_delay)
                else:
                    await asyncio.sleep(self.base_delay)

                if message_number % 1000 == 0 or message_number == num_messages:
                    progress = (message_number / num_messages) * 100
                    elapsed = time.time() - start_time
                    rate = sent_count / elapsed if elapsed > 0 else 0
                    eta = (num_messages - message_number) / rate if rate > 0 else 0

                    bot_distribution = " | ".join([f"Bot{i+1}: {count}" for i, count in bot_usage.items()])

                    try:
                        await progress_msg.edit_text(
                            f"📤 **Sending Messages...**\n\n"
                            f"📊 Progress: {message_number:,}/{num_messages:,} ({progress:.1f}%)\n"
                            f"✅ Sent: {sent_count:,} | ❌ Failed: {failed_count:,}\n"
                            f"⚡ Rate: {rate:.1f} msg/sec\n"
                            f"⏱️ ETA: {eta:.0f}s\n\n"
                            f"🤖 {bot_distribution}",
                            parse_mode='Markdown'
                        )
                    except TelegramError as e:
                        logger.warning(f"Failed to update progress: {e}")

            elapsed = time.time() - start_time
            final_rate = sent_count / elapsed if elapsed > 0 else 0

            await progress_msg.edit_text(
                f"🎉 **Message Sending Complete!**\n\n"
                f"✅ Successfully sent: {sent_count:,}\n"
                f"❌ Failed: {failed_count:,}\n"
                f"📈 Success rate: {(sent_count/num_messages)*100:.1f}%\n"
                f"⏱️ Total time: {elapsed:.1f} seconds\n"
                f"⚡ Average rate: {final_rate:.1f} msg/sec\n\n"
                f"Use /stats for detailed bot statistics",
                parse_mode='Markdown'
            )

        except ValueError:
            await update.message.reply_text("❌ Invalid number format. Please use a valid integer.")
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            await update.message.reply_text(f"❌ An unexpected error occurred: {str(e)}")

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show detailed bot pool statistics"""
        if not await self.is_user_authorized(update):
            return

        if not self.bot_pool:
            await update.message.reply_text("❌ Bot pool not initialized")
            return

        stats_text = self.bot_pool.get_stats_summary()
        await update.message.reply_text(stats_text, parse_mode='Markdown')

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check bot status"""
        if not await self.is_user_authorized(update):
            return

        status_text = f"""
🤖 **Multi-Bot System Status**

✅ **Status:** Online and Operational
👤 **Authorized User:** @{self.allowed_user}
🤖 **Active Bots:** {len(self.bot_tokens)}
📊 **Maximum Messages:** {self.max_messages:,} per command
⚡ **Batch Size:** {self.batch_size} messages
⏱️ **Base Delay:** {self.base_delay}s per message
🔄 **Auto Retry:** Enabled (3 attempts per bot)
📈 **Progress Updates:** Every 1,000 messages

**Multi-Bot Features:**
• Round-robin bot rotation
• Automatic cooldown management
• Independent bot operation
• Load distribution across all bots
• Real-time statistics tracking

**Ready to send unlimited messages!**
Use /stats to see detailed bot statistics
        """
        await update.message.reply_text(status_text, parse_mode='Markdown')

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)

    async def post_init(self, application: Application):
        """Initialize bot pool after application starts"""
        await self.initialize_pool()

    def run(self):
        """Start the bot"""
        self.application = Application.builder().token(self.bot_tokens[0]).post_init(self.post_init).build()

        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("send", self.send_messages))
        self.application.add_handler(CommandHandler("status", self.status))
        self.application.add_handler(CommandHandler("stats", self.stats_command))

        self.application.add_error_handler(self.error_handler)

        logger.info("🤖 Multi-Bot Mass Message System 2025 is starting...")
        print("=" * 60)
        print("🤖 Multi-Bot Mass Message System 2025")
        print("=" * 60)
        print(f"✅ System is running...")
        print(f"👤 Authorized user: @{self.allowed_user}")
        print(f"🤖 Number of bots: {len(self.bot_tokens)}")
        print(f"📊 Max messages: {self.max_messages:,}")
        print("Press Ctrl+C to stop")
        print("=" * 60)

        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    bot = MassMessageBot()
    bot.run()
                
