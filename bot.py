import os
import logging
from telegram import (
    Poll, ParseMode, KeyboardButton, KeyboardButtonPollType, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
)
from telegram.ext import (
    Updater, CommandHandler, PollAnswerHandler, PollHandler, MessageHandler, Filters, CallbackContext
)

TOKEN = os.environ["TOKEN"]
PORT = int(os.environ.get("PORT", 5000))

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# State Types
NONE = "none"; TITLE = "title"; OPTION = "option"
state = "none"


def start_handler(update: Update, context: CallbackContext) -> None:
    """Inform the user about what the bot can do"""
    global state
    state = "title"
    update.message.reply_text(
        "Let's create a new poll! First, send me the title."
    )


def message_handler(update: Update, context: CallbackContext) -> None:
    if state == "title":
        pass


def help_handler(update: Update, context: CallbackContext) -> None:
    """Display a help message"""
    update.message.reply_text("Use /quiz, /poll or /preview to test this bot.")


def error_handler(update: Update, context: CallbackContext) -> None:
    """Log errors caused by Updates."""
    logger.warning(f"Update {update} caused error {context.error}")


def main():
    """Start the bot."""
    updater = Updater(TOKEN, use_context=True)

    # Dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Command handlers
    dispatcher.add_handler(CommandHandler("start", start_handler))
    dispatcher.add_handler(CommandHandler("help", help_handler))

    # Message handlers
    dispatcher.add_handler(MessageHandler(Filters.text, message_handler))

    # Error handlers
    dispatcher.add_error_handler(error_handler)

    # Start the bot
    updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN)
    updater.bot.setWebhook("https://tya-countmein.herokuapp.com/" + TOKEN)
    updater.idle()


if __name__ == "__main__":
    main()
