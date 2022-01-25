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

# Environment settings
TOKEN = os.environ["TOKEN"]
PORT = int(os.environ.get("PORT", 5000))

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot settings
MAX_TITLE_LENGTH = 200
NEW_POLL = "Let's create a new poll! First, send me the title."
NEW_OPTION = "New poll: '{}'\n\nNow send me the first answer option."
NEXT_OPTION = "Nice! Now send me another answer option, or /done to finish."
DONE = "\U0001f44d Poll created! You may now publish it to a group or send it to your friends."
HELP = "This bot will help you create polls where people can leave their names. " + \
           "Use /start to create a poll here, then publish it to groups or send it to" + \
           "individual friends.\n\nSend /polls to manage your existing polls."
ERROR_TITLE_TOO_LONG = f"Sorry, please enter a shorter title (maximum {MAX_TITLE_LENGTH} characters)."


def handle_start(update: Update, context: CallbackContext) -> None:
    """Inform the user about what the bot can do."""
    user = update.effective_user
    Session.start_new_session(user.id)
    update.message.reply_text(NEW_POLL)


def handle_message(update: Update, context: CallbackContext) -> None:
    text = update.message.text
    if not text:
        return

    user = update.effective_user
    uid = user.id
    session = Session.get_session_by_id(uid)

    if not session:
        update.message.reply_text(HELP)
        return

    session_progress = session.get_progress()

    if session_progress == backend.TITLE:
        if len(text) > MAX_TITLE_LENGTH:
            update.message.reply_text(ERROR_TITLE_TOO_LONG)
        else:
            poll = Poll.get_poll_by_id(session.get_poll_id())
            poll.set_title(text)
            bold_title = backend.make_html_bold_first_line(text)
            response = NEW_OPTION.format(bold_title)
            update.message.reply_text(response, parse_mode="HTML")
            session.set_progress(backend.OPTION)


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
