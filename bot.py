"""Main Interface"""
import os
import logging
import re
import backend
from backend import Session, Poll, Option
import util
from telegram import (
    Update, ParseMode, User, Message, KeyboardButton, ReplyKeyboardMarkup, InlineQueryResultArticle,
    InputTextMessageContent, ForceReply
)
from telegram.ext import (
    CallbackContext, CommandHandler, MessageHandler, CallbackQueryHandler, InlineQueryHandler,
    RegexHandler, Filters, Updater, JobQueue
)
import telegram.error

# Environment settings
TOKEN = os.environ["TOKEN"]
PORT = int(os.environ.get("PORT", 8443))
BOT_NAME = "tyacountmeintbot"
updater = Updater(TOKEN, use_context=True)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot settings
MAX_TITLE_LENGTH = 100
MAX_OPTION_TITLE_LENGTH = 50
NEW_POLL = "Let's create a new poll! First, send me the title."
NEW_OPTION = "New poll:\n{}\n\nNow send me the first answer option."
NEXT_OPTION = "Nice! Now send me another answer option, or /done to finish."
DONE = "\U0001f44d Poll created! You may now publish it to a group or send it to your friends."
HELP = "This bot will help you create polls where people can leave their names. " + \
           "Use /start to create a poll here, then publish it to groups or send it to" + \
           "individual friends.\n\nSend /polls to manage your existing polls."
ERROR_TITLE_TOO_LONG = f"Sorry, please enter a shorter title (maximum {MAX_TITLE_LENGTH} characters)."
ERROR_OPTION_TITLE_TOO_LONG = f"Sorry, please enter a shorter title (maximum {MAX_OPTION_TITLE_LENGTH} characters)."
ERROR_EARLY_DONE_TITLE = "Sorry, please add a title to the poll."
ERROR_EARLY_DONE_OPTION = "Sorry, please add at least one option to the poll."
REASON = "Please enter a reason/comment."
DELETED_POLL = "Sorry, the poll has been deleted."


def handle_start(update: Update, context: CallbackContext) -> None:
    """Informs the user about what the bot can do."""
    # Start command only work in private chat
    if not is_user_admin(update.message):
        return

    user = update.effective_user
    Session.start_new_session(user.id)
    update.message.reply_text(NEW_POLL)


def handle_done(update: Update, context: CallbackContext) -> None:
    """Finishes building the poll."""
    # Done command only work in private chat
    if not is_user_admin(update.message):
        return

    uid = update.effective_user.id
    session = Session.get_session_by_id(uid)

    if not session:
        update.message.reply_text(HELP)
        return

    poll = Poll.get_temp_poll_by_id(session.get_poll_id())

    # Check if there is a title
    if not poll.get_title():
        update.message.reply_text(ERROR_EARLY_DONE_TITLE)
        return

    # Check if there are options
    if not poll.get_options():
        update.message.reply_text(ERROR_EARLY_DONE_OPTION)
        return

    session.end_session()
    update.message.reply_text(DONE)
    deliver_poll(update, poll, True)


def handle_polls(update: Update, context: CallbackContext) -> None:
    """Displays all recent polls created by user."""
    # Polls command only work in private chat
    if not is_user_admin(update.message):
        return

    uid = update.effective_user.id

    header = [util.make_html_bold("Your polls")]

    recent_polls = Poll.get_polls_created_by_user(uid, limit=20)
    if recent_polls:
        body = [f"{i + 1}. {poll.generate_linked_summary()}" for i, poll in enumerate(recent_polls)]
    else:
        body = ["You have no polls! Use /start to build a new poll."]

    response = "\n\n".join(header + body)
    update.message.reply_text(response, parse_mode=ParseMode.HTML)


def handle_poll_view(update: Update, context: CallbackContext) -> None:
    """Displays the master poll identified by its poll id"""
    # Poll view command only work in private chat
    if not is_user_admin(update.message):
        return

    uid = update.effective_user.id
    text = update.message.text

    poll_id = re.match(r"^/poll_(\w+).*$", text).group(1)
    poll = Poll.get_poll_by_id(poll_id)
    if poll and poll.get_creator_id() == uid:
        deliver_poll(update, poll, is_admin=True)
        return
    else:
        update.message.reply_text(HELP)


def handle_show(update: Update, context: CallbackContext) -> None:
    """Displays the standard poll identified by its poll id"""
    text = update.message.text

    poll_id = re.match(r"^/show_(\w+).*$", text).group(1)
    poll = Poll.get_poll_by_id(poll_id)

    if poll:
        update.message.reply_text(poll.render_text(), parse_mode=ParseMode.HTML,
                                  reply_markup=poll.build_option_buttons(), reply_to_message_id=-1)


def handle_help(update: Update, context: CallbackContext) -> None:
    """Displays a help message."""
    # Help command only work in private chat
    if not is_user_admin(update.message):
        return
    update.message.reply_text(HELP)


def handle_message(update: Update, context: CallbackContext) -> None:
    """Handles a message from the user."""
    if not update.message:
        return

    if update.message.reply_to_message:
        handle_reply_message(update, context)
        return

    text = update.message.text
    if not text:
        return

    uid = update.effective_user.id
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

        poll = Poll.get_temp_poll_by_id(session.get_poll_id())
        poll.set_title(text)
        session.set_progress(backend.OPTION)

        bold_title = util.make_html_bold_first_line(text)
        response = NEW_OPTION.format(bold_title)
        update.message.reply_text(response, parse_mode=ParseMode.HTML)
        return
    # Handle option
    elif session_progress == backend.OPTION:
        if len(text) > MAX_OPTION_TITLE_LENGTH:
            update.message.reply_text(ERROR_OPTION_TITLE_TOO_LONG)
            return
        else:
            poll = Poll.get_temp_poll_by_id(session.get_poll_id())
            poll.add_option(Option(text))

            if len(poll.get_options()) < 10:
                update.message.reply_text(NEXT_OPTION)
                return

            session.end_session()
            update.message.reply_text(DONE)
            deliver_poll(update, poll, True)
            return
    # Handle other cases
    else:
        update.message.reply_text(HELP)


def handle_callback_query(update: Update, context: CallbackContext) -> None:
    """Handles a callback query."""
    query = update.callback_query
    uid, user_profile = extract_user_data(query.from_user)
    message = query.message

    try:
        poll_id, action = query.data.split()
    except (AttributeError, IndexError, ValueError):
        logger.warning("Invalid callback query data.")
        query.answer(text="Invalid callback query data!")
        return

    poll = Poll.get_poll_by_id(poll_id)

    # Poll is deleted or has error
    if not poll:
        query.edit_message_reply_markup(None)
        query.answer(text=DELETED_POLL)
        return

    is_admin = is_user_admin(message)

    # Handle poll option button
    if action.isdigit():
        if poll.is_user_comment_required(int(action), uid):
            query.answer(text=REASON)
            reply_message = query.message.reply_text(
                f"@{user_profile['username']} {REASON} #{poll_id}_{action}_{message.message_id}",
                parse_mode=ParseMode.HTML, reply_markup=ForceReply()
            )

            # Delete reply message after 10 minutes
            updater.job_queue.run_once(delete_message, 600, context=reply_message)
            return
        status = poll.toggle(int(action), uid, user_profile)
        query.edit_message_text(poll.render_text(), parse_mode=ParseMode.HTML,
                                reply_markup=poll.build_option_buttons(is_admin))
        query.answer(text=status)
        return
    # Handle refresh button
    elif action == backend.REFRESH and is_admin:
        query.edit_message_text(poll.render_text(), parse_mode=ParseMode.HTML, reply_markup=poll.build_admin_buttons())
        query.answer(text="Results updated!")
        return
    # Handle customise button
    elif action == backend.CUSTOMISE and is_admin:
        query.edit_message_reply_markup(poll.build_customise_buttons())
        query.answer(text=None)
        return
    # Handle toggle response button
    elif action == backend.RESPONSE and is_admin:
        status = poll.toggle_response_type()
        query.answer(text=status)
        query.edit_message_reply_markup(poll.build_customise_buttons())
        return
    # Handle enforce comments button
    elif action == backend.COMMENT and is_admin:
        query.edit_message_reply_markup(poll.build_option_comment_buttons())
        query.answer(text=None)
        return
    # Handle toggle comments required button
    elif action.startswith(f"{backend.COMMENT}-") and is_admin:
        _, opt_id = action.rsplit("-", 1)
        if opt_id.isdigit():
            status = poll.toggle_comment_requirement(int(opt_id))
            query.edit_message_reply_markup(poll.build_option_comment_buttons())
            query.answer(text=status)
            return
        else:
            logger.warning("Invalid callback query data.")
            query.answer(text="Invalid callback query data!")
            return
    # Handle vote button
    elif action == backend.VOTE and is_admin:
        query.edit_message_reply_markup(poll.build_option_buttons(True))
        query.answer(text="You may now vote!")
        return
    # Handle delete button
    elif action == backend.DELETE and is_admin:
        query.edit_message_reply_markup(poll.build_delete_confirmation_buttons())
        query.answer(text="Confirm delete?")
        return
    # Handle delete confirmation button
    elif action == backend.DELETE_YES and is_admin:
        poll.delete_poll()
        query.edit_message_reply_markup(None)
        query.answer(text="Poll deleted!")
        return
    # Handle back button
    elif action == backend.BACK and is_admin:
        query.edit_message_reply_markup(poll.build_admin_buttons())
        query.answer(text=None)
        return
    # Handle other cases
    else:
        logger.warning("Invalid callback query data.")
        query.answer(text="Invalid callback query data!")
        return


def handle_inline_query(update: Update, context: CallbackContext) -> None:
    """Handles an inline query."""
    uid = update.effective_user.id
    inline_query = update.inline_query
    text = inline_query.query.lower()

    results = []
    polls = Poll.get_polls_created_by_user(uid, filters=text, limit=10)
    for poll in polls:
        query_result = InlineQueryResultArticle(
            id=poll.get_poll_id(), title=poll.get_title(), description=poll.generate_options_summary(),
            input_message_content=InputTextMessageContent(f"/show_{poll.get_poll_id()} @{BOT_NAME}")
        )
        results.append(query_result)

    inline_query.answer(results)


def handle_reply_message(update: Update, context: CallbackContext) -> None:
    """Handles a reply message to the bot."""
    uid, user_profile = extract_user_data(update.effective_user)
    comment = update.message.text

    text = update.message.reply_to_message.text

    try:
        # Check if username matches
        username, _ = text.split(" ", 1)
        if username.lstrip("@") != user_profile["username"]:
            return

        # Retrieve poll details
        _, poll_details = text.rsplit("#", 1)
        poll_id, opt_id, message_id = poll_details.split("_")
        if not opt_id.isdigit():
            raise ValueError
    except (AttributeError, IndexError, ValueError):
        update.message.reply_text("Invalid reply message format!")
        logger.warning("Invalid reply message format.")
        return

    poll = Poll.get_poll_by_id(poll_id)
    if not poll:
        update.message.reply_text(DELETED_POLL)
        return

    if int(opt_id) >= len(poll.get_options()):
        update.message.reply_text("Invalid poll option.")
        logger.warning("Invalid poll option from reply message.")
        return

    poll.toggle(int(opt_id), uid, user_profile, comment)
    is_admin = is_user_admin(update.message)

    chat_id = update.message.chat_id
    context.bot.edit_message_text(
        poll.render_text(), message_id=message_id, chat_id=chat_id,
        parse_mode=ParseMode.HTML, reply_markup=poll.build_option_buttons(is_admin=is_admin)
    )

    # Delete user and bot message
    update.message.reply_to_message.delete()
    update.message.delete()


def handle_error(update: Update, context: CallbackContext) -> None:
    """Logs errors caused by Updates."""
    logger.warning(f"Update {update} caused error {context.error}")


def deliver_poll(update: Update, poll: Poll, is_admin=False) -> None:
    """Delivers the poll in admin mode."""
    if is_admin:
        update.message.reply_text(poll.render_text(), parse_mode=ParseMode.HTML,
                                  reply_markup=poll.build_admin_buttons())


def is_user_admin(message: Message) -> bool:
    return message and message.chat.type == "private"


def extract_user_data(user: User) -> tuple:
    return user.id, {"first_name": user.first_name, "last_name": user.last_name, "username": user.username}


def delete_message(context: CallbackContext) -> None:
    try:
        message = context.job.context
        message.delete()
    except telegram.error.TelegramError:
        logger.info("Message has been deleted.")


def main():
    """Starts the bot."""
    # Dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Command handlers
    dispatcher.add_handler(CommandHandler("start", handle_start))
    dispatcher.add_handler(CommandHandler("done", handle_done))
    dispatcher.add_handler(CommandHandler("polls", handle_polls))
    dispatcher.add_handler(CommandHandler("help", handle_help))

    # Message handlers
    dispatcher.add_handler(MessageHandler(Filters.regex(r"^\/poll_\w+.*$"), handle_poll_view))
    dispatcher.add_handler(MessageHandler(Filters.regex(r"^\/show_\w+.*$"), handle_show))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_message))

    # Callback query handlers
    dispatcher.add_handler(CallbackQueryHandler(handle_callback_query))

    # Inline query handlers
    dispatcher.add_handler(InlineQueryHandler(handle_inline_query))

    # Error handlers
    dispatcher.add_error_handler(handle_error)

    # Start the bot
    updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN,
                          webhook_url="https://tya-countmein.herokuapp.com/" + TOKEN)
    updater.idle()


if __name__ == "__main__":
    main()
