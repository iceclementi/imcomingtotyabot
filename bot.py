import os
import logging
import backend
from backend import Session, Poll, Option
from telegram import (
    ParseMode, KeyboardButton, KeyboardButtonPollType, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
)
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters, CallbackContext
)

TOKEN = os.environ["TOKEN"]
PORT = int(os.environ.get("PORT", 5000))

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def handle_start(update: Update, context: CallbackContext) -> None:
    """Inform the user about what the bot can do."""
    user = update.effective_user
    backend.start_new_session(user.id)
    session = Session.get_session_by_id(user.id)
    update.message.reply_text(
        "Let's create a new poll! First, send me the title."
    )
    update.message.reply_text(
        session.get_poll().get_poll_id()
    )


def handle_message(update: Update, context: CallbackContext) -> None:
    if state == "title":
        pass


def handle_help(update: Update, context: CallbackContext) -> None:
    """Display a help message."""
    update.message.reply_text("Use /quiz, /poll or /preview to test this bot.")


def handle_error(update: Update, context: CallbackContext) -> None:
    """Log errors caused by Updates."""
    logger.warning(f"Update {update} caused error {context.error}")


def main():
    """Start the bot."""
    updater = Updater(TOKEN, use_context=True)

    # Dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Command handlers
    dispatcher.add_handler(CommandHandler("start", handle_start))
    dispatcher.add_handler(CommandHandler("help", handle_help))

    # Message handlers
    dispatcher.add_handler(MessageHandler(Filters.text, handle_message))

    # Error handlers
    dispatcher.add_error_handler(handle_error)

    # Start the bot
    updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN)
    updater.bot.setWebhook("https://tya-countmein.herokuapp.com/" + TOKEN)
    updater.idle()


if __name__ == "__main__":
    main()
