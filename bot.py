import os
import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

TOKEN = os.environ["TOKEN"]
PORT = int(os.environ.get("PORT", 5000))

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text("Hi!")


def help_command(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text("Help!")


def echo(update, context):
    """Echo the user's message."""
    update.message.reply_text(update.message.text)


def error(update, context):
    """Log errors from Updates."""
    logger.warning(f"Update {update} caused error {context.error}")


def main():
    """Start the bot."""
    updater = Updater(TOKEN, use_context=True)

    # Dispatcher to register handlers
    dp = updater.dispatcher

    # On command -> answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))

    # On non-command -> echo message on Telegram
    dp.add_handler(MessageHandler(Filters.text, echo))

    # Log all errors
    dp.add_error_handler(error)

    # Start the bot
    updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN)
    updater.bot.setWebhook("https://tya-countmein.herokuapp.com/" + TOKEN)
    updater.idle()


if __name__ == "__main__":
    main()
