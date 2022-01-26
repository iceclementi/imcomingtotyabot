"""Main Interface"""
import os
import logging
import backend
from backend import Session, Poll, Option
import util
from telegram import (
    Update, ParseMode, User, Message, KeyboardButton, ReplyKeyboardMarkup, InlineQueryResultArticle,
    InputTextMessageContent, ForceReply
)
from telegram.ext import (
    Updater, CallbackContext, CommandHandler, MessageHandler, CallbackQueryHandler, InlineQueryHandler,
    RegexHandler, Filters
)

# Environment settings
TOKEN = os.environ["TOKEN"]
PORT = int(os.environ.get("PORT", 5000))
BOT_NAME = "tyacountmeintbot"

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
ERROR_EARLY_DONE = "Sorry, please add at least one option to the poll."
REASON = "Please enter a reason/comment."


def handle_start(update: Update, context: CallbackContext) -> None:
    """Informs the user about what the bot can do."""
    user = update.effective_user
    Session.start_new_session(user.id)
    update.message.reply_text(NEW_POLL)


def handle_done(update: Update, context: CallbackContext) -> None:
    """Finishes building the poll."""
    uid = update.effective_user.id
    session = Session.get_session_by_id(uid)

    if not session:
        update.message.reply_text(HELP)
        return

    poll = Poll.get_poll_by_id(session.get_poll_id())

    if not poll.get_options():
        update.message.reply_text(ERROR_EARLY_DONE)
        return

    session.end_session()
    update.message.reply_text(DONE)
    deliver_poll(update, poll, True)


def handle_polls(update: Update, context: CallbackContext) -> None:
    """Displays all recent polls created by user."""
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
    """Displays the poll identified by its poll id"""
    uid = update.effective_user.id
    text = update.message.text

    poll = Poll.get_poll_by_id(text[6:])
    if poll and poll.get_creator_id() == uid:
        deliver_poll(update, poll, is_admin=True)
        return
    else:
        update.message.reply_text(HELP)


def handle_help(update: Update, context: CallbackContext) -> None:
    """Displays a help message."""
    update.message.reply_text(HELP)


def handle_message(update: Update, context: CallbackContext) -> None:
    """Handles a message from the user."""
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

        poll = Poll.get_poll_by_id(session.get_poll_id())
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
            poll = Poll.get_poll_by_id(session.get_poll_id())
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
    inline_mid = query.inline_message_id
    is_admin = not inline_mid

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
        query.answer(text="Sorry, this poll has been deleted.")
        return

    if inline_mid:
        poll.add_inline_id(inline_mid)

    # Handle poll option button
    if action.isdigit():
        if poll.is_user_comment_required(poll_id, uid):
            query.answer(text=REASON)
            query.message.reply_text(
                f"@{user_profile['username']} {REASON} #{poll_id}-{action}", parse_mode=ParseMode.HTML,
                reply_markup=ForceReply(input_field_placeholder=f"@{BOT_NAME} /comment_{poll_id}-{action}")
            )
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
            id= poll.get_poll_id(), title=poll.get_title(), description=poll.generate_options_summary(),
            input_message_content=InputTextMessageContent(poll.render_text(), parse_mode=ParseMode.HTML),
            reply_markup=poll.build_option_buttons()
        )
        results.append(query_result)

    inline_query.answer(results)


def handle_reply_message(update: Update, context: CallbackContext) -> None:
    """Handles a reply message to the bot."""
    uid, user_profile = extract_user_data(update.effective_user)
    comment = update.message.text

    try:
        reply, poll_details = update.message.reply_to_message.rsplit("#", 1)
        poll_id, option_id = poll_details.split("-")
        if not option_id.isdigit():
            raise ValueError
    except (AttributeError, IndexError, ValueError):
        update.message.reply_text("Invalid reply message format!")
        logger.warning("Invalid reply message format.")
        return

    poll = Poll.get_poll_by_id(poll_id)
    if not poll:
        update.message.reply_text("Sorry, the poll has been deleted.")
        return

    if int(option_id) >= len(poll.get_options()):
        update.message.reply_text("Invalid poll option.")
        logger.warning("Invalid poll option from reply message.")
        return

    poll.toggle(int(option_id), uid, user_profile, comment)
    for inline_id in poll.get_inline_ids():
        context.bot.edit_message_text(poll.render_text(), inline_message_id=inline_id, parse_mode=ParseMode.HTML,
                                      reply_markup=poll.build_option_buttons())


def handle_error(update: Update, context: CallbackContext) -> None:
    """Logs errors caused by Updates."""
    logger.warning(f"Update {update} caused error {context.error}")


def deliver_poll(update: Update, poll: Poll, is_admin=False) -> None:
    """Delivers the poll in admin mode."""
    if is_admin:
        update.message.reply_text(poll.render_text(), parse_mode=ParseMode.HTML,
                                  reply_markup=poll.build_admin_buttons())


def extract_user_data(user: User) -> tuple:
    return user.id, {"first_name": user.first_name, "last_name": user.last_name, "username": user.username}


def main():
    """Starts the bot."""
    updater = Updater(TOKEN, use_context=True)

    # Dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Command handlers
    dispatcher.add_handler(CommandHandler("start", handle_start))
    dispatcher.add_handler(CommandHandler("done", handle_done))
    dispatcher.add_handler(CommandHandler("polls", handle_polls))
    dispatcher.add_handler(CommandHandler("help", handle_help))

    # Message handlers
    dispatcher.add_handler(MessageHandler(Filters.regex(r"^\/poll_\w+$"), handle_poll_view))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_message))

    # Callback query handlers
    dispatcher.add_handler(CallbackQueryHandler(handle_callback_query))

    # Inline query handlers
    dispatcher.add_handler(InlineQueryHandler(handle_inline_query))

    # Error handlers
    dispatcher.add_error_handler(handle_error)

    # Start the bot
    updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN)
    updater.bot.setWebhook("https://tya-countmein.herokuapp.com/" + TOKEN)
    updater.idle()


if __name__ == "__main__":
    main()
