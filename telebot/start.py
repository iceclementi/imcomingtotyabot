"""Main Interface"""
import logging
import os
import re

import telegram.error
from telegram import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardRemove,
    Update,
    WebAppInfo,
)
from telegram import User as TeleUser
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    Updater,
)

from models import constant as const
from utils import util

# region SETTINGS

# Environment settings
WEB_URL = os.environ["WEB_URL"]
TOKEN = os.environ["TOKEN"]
PORT = int(os.environ.get("PORT", 8443))
updater = Updater(TOKEN, use_context=True)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# endregion

# region RESPONSES

START_RESPONSE = (
    "Welcome to the bot! \U0001f60a\n\nUse <b>/keyboard</b> to show and hide the command keyboard.\n\n"
    "Use <b>/help</b> to check the description for each bot command."
)
MAINTENANCE_RESPONSE = (
    "⚠ <b>MAINTENANCE BREAK</b>\n\nSorry, the developer is currently making some upgrades to the "
    "bot. He apologises for any inconvenience caused 😓\n\nDo look forward to the next update!! 😎"
)

# endregion

# region COMMANDS

START_COMMAND = "start"
KEYBOARD_COMMAND = "keyboard"
HELP_COMMAND = "help"
TEST_COMMAND = "test"

# endregion

# region COMMAND HELP

START_HELP = "<b>/start</b>\nView the bot's welcome message"
KEYBOARD_HELP = (
    "<b>/keyboard</b>\nChoose between showing or hiding the command keyboard"
)
HELP_HELP = "<b>/help</b>\nView this help message"


# endregion

# region COMMAND HANDLERS


def handle_start(update: Update, context: CallbackContext) -> None:
    """Displays start message to the bot and manages pm messages."""
    update.message.delete()

    arguments = context.args
    if not arguments:
        update.message.reply_html(
            START_RESPONSE,
            reply_markup=util.build_single_button_markup("Close", const.CLOSE),
        )
        update.message.reply_html(
            MAINTENANCE_RESPONSE,
            reply_markup=util.build_single_button_markup("Close", const.CLOSE),
        )
        return

    if re.match(r"^\w+$", arguments[0]):
        handle_pm_command(arguments[0], update, context)
        return

    match = re.match(r"^(\w+)-(\w+)$", arguments[0])
    if not match:
        handle_help(update, context)
        return

    handle_pm_command(arguments[0], update, context)
    return


def handle_pm_command(command: str, update: Update, context: CallbackContext) -> None:
    """Manages standard commands in pm mode with the bot."""
    update.message.reply_html(
        MAINTENANCE_RESPONSE,
        reply_markup=util.build_single_button_markup("Back", const.RETURN),
    )
    return


def handle_keyboard(update: Update, context: CallbackContext) -> None:
    """Shows option to user to show or hide the command keyboard."""
    update.message.delete()
    context.user_data.clear()

    show_hide_buttons = util.build_multiple_stacked_buttons_markup(
        [
            util.generate_button_details("Show", const.SHOW),
            util.generate_button_details("Hide", const.HIDE),
        ],
        [util.generate_button_details("Close", const.CLOSE)],
    )

    update.message.reply_html(
        "Show or hide command keyboard?", reply_markup=show_hide_buttons
    )
    return


def handle_help(update: Update, context: CallbackContext) -> None:
    """Displays a help message to explain available bot commands."""
    delete_chat_message(update.message)
    context.user_data.clear()

    header = [util.make_html_bold("Available Bot Commands")]
    body = [START_HELP, KEYBOARD_HELP, HELP_HELP]

    response = "\n\n".join(header + body)
    update.message.reply_html(
        response, reply_markup=util.build_single_button_markup("Close", const.CLOSE)
    )
    return


def handle_test(update: Update, context: CallbackContext) -> None:
    """Tests the webapp."""
    delete_chat_message(update.message)
    context.user_data.clear()

    header = [util.make_html_bold("Testing Webapp")]
    body = ["Web app testing..."]

    response = "\n".join(header + body)
    buttons = [
        [
            InlineKeyboardButton(
                "Test",
                web_app=WebAppInfo(url=f"https://tya-srg-bot-webapp.herokuapp.com/"),
                callback_data="test",
            )
        ],
        [InlineKeyboardButton("Close", callback_data=const.CLOSE)],
    ]
    update.message.reply_html(response, reply_markup=InlineKeyboardMarkup(buttons))


# endregion

# region MESSAGE HANDLERS


def handle_message(update: Update, context: CallbackContext) -> None:
    """Handles a message from the user."""
    if not update.message:
        return

    text = update.message.text
    if not text:
        return

    delete_chat_message(update.message)

    update.message.reply_html(
        MAINTENANCE_RESPONSE,
        reply_markup=util.build_single_button_markup("Close", const.CLOSE),
    )
    return


# endregion

# region CALLBACK QUERY HANDLERS


def handle_callback_query(update: Update, context: CallbackContext) -> None:
    """Handles a callback query."""
    query = update.callback_query

    handle_general_callback_query(query, context, query.data.strip())
    return


def handle_general_callback_query(
    query: CallbackQuery, context: CallbackContext, action: str
) -> None:
    """Handles a general callback query."""
    # Handle show command button
    if action == const.SHOW:
        handle_show_command_callback_query(query, context)
        query.answer(text="Command keyboard shown!")
        return
    # Handle hide command button
    elif action == const.HIDE:
        query.message.delete()
        reply_message = query.message.reply_html(
            "Hiding command keyboard...", reply_markup=ReplyKeyboardRemove()
        )
        reply_message.delete()
        query.answer(text="Command keyboard hidden!")
        return
    # Handle close button
    elif action == const.CLOSE:
        query.message.delete()
        query.answer(text=None)
        return
    # Handle return button
    elif action == const.RETURN:
        query.answer(text="Returning to chat...")
        response = "Returning to chat..."
        reply_message = query.message.reply_html(
            response,
            reply_markup=util.build_single_switch_button_markup("Return To Chat", ""),
        )
        context.user_data.clear()
        reply_message.delete()
        query.message.delete()
        return
    # Handle other cases
    else:
        query.answer(text="Invalid callback query data!")
        logger.warning("Invalid callback query data.")
        return


def handle_show_command_callback_query(
    query: CallbackQuery, context: CallbackContext
) -> None:
    """Shows the command keyboard to the user."""
    query.message.delete()

    buttons = util.build_multiple_stacked_keyboard_buttons_markup(
        [f"/{START_COMMAND}", f"/{KEYBOARD_COMMAND}", f"/{HELP_COMMAND}"]
    )

    reply_message = query.message.reply_html(
        "Showing command keyboard...", reply_markup=ReplyKeyboardRemove()
    )
    reply_message.delete()
    query.message.reply_html("Select a bot command 🔽", reply_markup=buttons)
    return


# endregion


# region OTHER HANDLERS


def handle_error(update: Update, context: CallbackContext) -> None:
    """Logs errors caused by Updates."""
    logger.warning(f"Update {update} caused error {context.error}")


# endregion

# region HELPERS


def is_private_chat(message: Message) -> bool:
    """Verifies if a user is in a private chat."""
    return message and message.chat.type == "private"


def extract_user_data(user: TeleUser) -> tuple:
    """Extracts user data from User object."""
    return user.id, {
        "first_name": user.first_name,
        "last_name": user.last_name or "",
        "username": user.username or "",
    }


def delete_chat_message(message: Message) -> None:
    """Deletes a chat message."""
    try:
        message.delete()
    except telegram.error.TelegramError:
        logger.info("Message already deleted!")
    return


# endregion

# region JOBS


def ping_server_job(context: CallbackContext) -> None:
    """Pings the server"""
    status = util.ping(WEB_URL)
    logger.info(status)
    return


# endregion


def main() -> None:
    """Starts the bot."""
    # Dispatcher to register handlers
    dispatcher = updater.dispatcher

    private_filter = Filters.chat_type.private

    # Command handlers
    dispatcher.add_handler(
        CommandHandler(START_COMMAND, handle_start, filters=private_filter)
    )
    dispatcher.add_handler(
        CommandHandler(KEYBOARD_COMMAND, handle_keyboard, filters=private_filter)
    )
    dispatcher.add_handler(
        CommandHandler(HELP_COMMAND, handle_help, filters=private_filter)
    )
    dispatcher.add_handler(
        CommandHandler(TEST_COMMAND, handle_test, filters=private_filter)
    )

    # Callback query handlers
    dispatcher.add_handler(CallbackQueryHandler(handle_callback_query))

    # Error handlers
    dispatcher.add_error_handler(handle_error)

    # Ping server every 15 minutes to prevent server from sleeping
    updater.job_queue.run_repeating(
        ping_server_job, 900, first=900, name="Ping server job"
    )

    # Start the bot
    updater.start_webhook(
        listen="0.0.0.0", port=PORT, url_path=TOKEN, webhook_url=WEB_URL + TOKEN
    )
    updater.idle()


if __name__ == "__main__":
    main()
