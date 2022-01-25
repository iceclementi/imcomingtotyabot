"""Main Interface"""
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
MAX_OPTION_TITLE_LENGTH = 50
NEW_POLL = "Let's create a new poll! First, send me the title."
NEW_OPTION = "New poll:\n {}\n\nNow send me the first answer option."
NEXT_OPTION = "Nice! Now send me another answer option, or /done to finish."
DONE = "\U0001f44d Poll created! You may now publish it to a group or send it to your friends."
HELP = "This bot will help you create polls where people can leave their names. " + \
           "Use /start to create a poll here, then publish it to groups or send it to" + \
           "individual friends.\n\nSend /polls to manage your existing polls."
ERROR_TITLE_TOO_LONG = f"Sorry, please enter a shorter title (maximum {MAX_TITLE_LENGTH} characters)."
ERROR_OPTION_TITLE_TOO_LONG = f"Sorry, please enter a shorter title (maximum {MAX_OPTION_TITLE_LENGTH} characters)."
ERROR_EARLY_DONE = "Sorry, please add at least one option to the poll."


def handle_start(update: Update, context: CallbackContext) -> None:
    """Inform the user about what the bot can do."""
    user = update.effective_user
    Session.start_new_session(user.id)
    update.message.reply_text(NEW_POLL)


def handle_done(update: Update, context: CallbackContext) -> None:
    """Finish building the poll."""
    user = update.effective_user
    uid = user.id
    session = Session.get_session_by_id(uid)

    if not session:
        update.message.reply_text(HELP)
        return

    poll = Poll.get_poll_by_id(session.get_poll_id())

    if not poll.get_options():
        update.message.reply_text(ERROR_EARLY_DONE)
        return

    session.set_progress(backend.NONE)
    update.message.reply_text(DONE)
    deliver_poll_admin(update, poll)


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

    # Handle title
    if session_progress == backend.TITLE:
        if len(text) > MAX_TITLE_LENGTH:
            update.message.reply_text(ERROR_TITLE_TOO_LONG)
            return

        poll = Poll.get_poll_by_id(session.get_poll_id())
        poll.set_title(text)
        session.set_progress(backend.OPTION)

        bold_title = backend.make_html_bold_first_line(text)
        response = NEW_OPTION.format(bold_title)
        update.message.reply_text(response, parse_mode="HTML")
        return
    # Handle option
    elif session_progress == backend.OPTION:
        if len(text) > MAX_OPTION_TITLE_LENGTH:
            update.message.reply_text(ERROR_OPTION_TITLE_TOO_LONG)
            return
        else:
            poll = Poll.get_poll_by_id(session.get_poll_id())
            poll.add_option(Option(text))

            if len(poll.get_options()) < 10:
                update.message.reply_text(NEXT_OPTION)
                return

            session.set_progress(backend.NONE)
            update.message.reply_text(DONE)
            deliver_poll_admin(update, poll)


def handle_help(update: Update, context: CallbackContext) -> None:
    """Display a help message."""
    update.message.reply_text("Use /quiz, /poll or /preview to test this bot.")


def handle_error(update: Update, context: CallbackContext) -> None:
    """Log errors caused by Updates."""
    logger.warning(f"Update {update} caused error {context.error}")


def deliver_poll_admin(update: Update, poll: Poll):
    # update.message.reply_text(poll.render_text(), parse_mode="HTML", reply_markup=poll.build_admin_buttons())
    update.message.reply_text(poll.render_text(), parse_mode="HTML")


def main():
    """Start the bot."""
    updater = Updater(TOKEN, use_context=True)

    # Dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Command handlers
    dispatcher.add_handler(CommandHandler("start", handle_start))
    dispatcher.add_handler(CommandHandler("help", handle_help))
    dispatcher.add_handler(CommandHandler("done", handle_done))

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
