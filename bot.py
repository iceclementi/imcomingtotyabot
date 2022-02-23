"""Main Interface"""
import os
import logging
import re
from typing import Tuple, List as Lst, Dict
import models
from models import (
    User, Group, Poll, Option, List, ListOption, Template, PollTemplate, ListTemplate, FormatTextCode, BotManager
)
import util
from telegram import (
    Update, ParseMode, User as TeleUser, Message, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup,
    ReplyKeyboardRemove, InlineQueryResultArticle, InputTextMessageContent, ForceReply, CallbackQuery, InlineQuery
)
from telegram.ext import (
    CallbackContext, CommandHandler, MessageHandler, CallbackQueryHandler, InlineQueryHandler,
    ChosenInlineResultHandler, RegexHandler, Filters, Updater, JobQueue
)
import telegram.error

# region SETTINGS

# Environment settings
WEB_URL = os.environ["WEB_URL"]
TOKEN = os.environ["TOKEN"]
ACCESS_KEY = os.environ["ACCESS_KEY"]
ADMIN_KEYS = os.environ["ADMIN_KEYS"].split("_")
PORT = int(os.environ.get("PORT", 8443))
updater = Updater(TOKEN, use_context=True)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot settings
MAX_TITLE_LENGTH = 100
MAX_OPTION_TITLE_LENGTH = 50
MAX_OPTIONS = 10
MAX_CHOICE_ITEM_NAME_LENGTH = 50
MAX_GROUP_NAME_LENGTH = 50
MIN_GROUP_PASS_LENGTH = 4
MAX_GROUP_PASS_LENGTH = 20
ACCESS_REQUIRED = True  # Set to False if access is not required to access bot
QUERY_RESULTS_LIMIT = 20

# endregion

# region RESPONSES

ACCESS_REQUEST = "To explore the full potential of this bot, please request for access from the bot admins \U0001f60e"
ACCESS_ENTER_USER_ID = "Enter the ID of the user you want to give access to."
ACCESS_DENIED = "Sorry, invalid or expired access key."
ACCESS_GRANTED = "Woohoo!! \U0001f973 You now have access to the bot!\n\nUse <b>/start</b> to get started."
USER_PROMOTED = "Yay!! \U0001f389 {} is now a bot leader!!"

NEW_POLL = "Let's create a new poll! First, send me the <b>title</b>."
NEW_POLL_DESCRIPTION = "{}\n\nNice! Now send me a poll <b>description</b> or <b>Skip</b> this step."
NEW_POLL_OPTION = "{}\n\nAlright, now send me your very first <b>option</b>."
NEXT_POLL_OPTION = "Nice! {} added!\n\n{}\n\nNow send me another <b>option</b> or press <b>Done</b> to finish."
POLL_DONE = "\U0001f44d Poll created! You may now publish it to your friends or share it with a group."
DELETED_POLL = "Sorry, the poll has been deleted."

NEW_LIST = "Let's create a new list! First, send me the <b>title</b>."
NEW_LIST_DESCRIPTION = "{}\n\nNice! Now send me a list <b>description</b> or <b>Skip</b> this step."
NEW_LIST_OPTION = "{}\n\nAlright, now send me your very first <b>option</b>."
NEXT_LIST_OPTION = "Nice! {} added!\n\n{}\n\n" \
                   "Now send me another <b>option</b> or press <b>Done</b> to go to the next step."
NEW_LIST_CHOICE = "Okay, now send me your first <b>choice</b> item."
NEXT_LIST_CHOICE = "Great! {} added!\n\n{}\n\nNow send me another <b>choice</b> item or press <b>Done</b> to finish."
LIST_DONE = "\U0001f44d List created! You may now publish it to your friends or share it with a group."
DELETED_LIST = "Sorry, the list has been deleted."

NEW_GROUP = "Let's create a new group! To begin, send me the group <b>name</b>."
GROUP_PASSWORD_REQUEST = "{}\n\nGreat! Now enter a secret <b>password</b> for your group or <b>Skip</b> this step."
GROUP_DONE = "\U0001f44d Group created! You are now the owner of this group. " \
             "Use /invite to invite your friends to join the group."
DELETED_GROUP = "Sorry, the group has been deleted."
GROUP_INVITATION = "Which group's invite code do you want to send?"

REASON = "You've selected {}.\nPlease enter a reason/comment for your selected option."
START = "Welcome to the bot! \U0001f60a\n\nUse <b>/keyboard</b> to show and hide the command keyboard.\n\n" \
        "Use <b>/help</b> to check the description for each bot command."

ERROR_ACCESS_ALREADY_GRANTED = "You already have access to the bot! Use <b>/start</b> to get started."
ERROR_ALREADY_PROMOTED = "The user is already a bot leader!"
ERROR_TITLE_TOO_LONG = f"Sorry, please enter a shorter <b>title</b> (maximum {MAX_TITLE_LENGTH} characters)."
ERROR_OPTION_TITLE_TOO_LONG = \
    f"Sorry, please enter a shorter <b>title</b> (maximum {MAX_OPTION_TITLE_LENGTH} characters)."
ERROR_CHOICE_NAME_TOO_LONG = \
    f"Sorry, please enter a shorter <b>name</b> (maximum {MAX_CHOICE_ITEM_NAME_LENGTH} characters)."
ERROR_DUPLICATE_OPTION_TITLE = "Sorry, there's already an <b>option</b> with the same title.\n\n{}\n\n" \
                               "Please enter a different <b>option</b> title."
ERROR_DUPLICATE_CHOICE_NAME = "Sorry, there's already a <b>choice</b> item with the same name.\n\n{}\n\n" \
                               "Please enter a different <b>choice</b> item name."
ERROR_EARLY_DONE_POLL_TITLE = "Sorry, please add a <b>title</b> to the poll."
ERROR_EARLY_DONE_POLL_OPTION = "Sorry, please add at least one <b>option</b> to the poll."
ERROR_GROUP_NAME_EXISTS = "You already have a group with this <b>name</b>. Please enter another group <b>name</b>."
ERROR_GROUP_NAME_TOO_LONG = \
    f"Sorry, please enter a shorter group <b>name</b> (maximum {MAX_GROUP_NAME_LENGTH} characters)."
ERROR_INVALID_GROUP_PASS_FORMAT = \
    f"Sorry, please ensure that you group <b>password</b> is between {MIN_GROUP_PASS_LENGTH} and {MAX_GROUP_PASS_LENGTH} " \
    f"characters long and contains only alphanumeric characters."
ERROR_EARLY_DONE_GROUP_NAME = "Sorry, please add a group <b>name</b>."
ERROR_INVALID_GROUP_INVITE = "Sorry, invalid or expired group invitation code."
ERROR_ALREADY_IN_GROUP = "You're already in the group! Use <b>/groups</b> to view all your groups."
ERROR_ILLEGAL_SECRET_CHANGE = "Only group owners can change the group's <b>password</b>!"
ERROR_ALREADY_VOTED = "You've already voted for this option in the poll!"
ERROR_NOT_VOTED = "Sorry, you've not voted for this option in the poll."
ERROR_USER_NOT_FOUND = "Sorry, the user does not exist."
ERROR_INVALID_POLL_COMMENT_REQUEST = "Sorry, invalid poll comment request."
ERROR_INVALID_POLL_VOTE_REQUEST = "Sorry, invalid poll vote request."
ERROR_INVALID_POLL_OPTION_REQUEST = "Sorry, invalid poll option request."
ERROR_INVALID_LIST_UPDATE_REQUEST = "Sorry, invalid list update request."

# endregion

# region COMMANDS

START_COMMAND = "start"
KEYBOARD_COMMAND = "keyboard"
POLL_COMMAND = "poll"
POLLS_COMMAND = "polls"
LIST_COMMAND = "list"
LISTS_COMMAND = "lists"
TEMPLATE_COMMAND = "temp"
TEMPLATES_COMMAND = "temps"
GROUP_COMMAND = "group"
GROUPS_COMMAND = "groups"
GROUP_POLLS_COMMAND = "gpolls"
GROUP_LISTS_COMMAND = "glists"
GROUP_TEMPLATES_COMMAND = "gtemps"
INVITE_COMMAND = "invite"
HELP_COMMAND = "help"
ACCESS_COMMAND = "access"
ENROL_COMMAND = "enrol"
PROMOTE_COMMAND = "promote"
SAVE_COMMAND = "save"
LOAD_COMMAND = "load"

# endregion

# region COMMAND HELP

START_HELP = "<b>/start</b>\nView the bot's welcome message"
KEYBOARD_HELP = "<b>/keyboard</b>\nChoose between showing or hiding the command keyboard"
POLL_HELP = "<b>/poll</b> [title]\nBuild a new poll with an optional title"
POLLS_HELP = "<b>/polls</b>\nView all the polls you have built"
LIST_HELP = "<b>/list</b> [title]\nBuild a new list with an optional title"
LISTS_HELP = "<b>/lists</b>\nView all the lists you have built"
TEMPLATE_HELP = "<b>/temp</b> [p/l name]\nCreate templates for your polls and lists, " \
                 "or create a poll or list based on the template\n" \
                 "<i>E.g. /temp p xyz</i>"
TEMPLATES_HELP = "<b>/temps</b>\nView all the templates you have created"
GROUP_HELP = "<b>/group</b> [name]\nCreate a new group with an optional name"
GROUPS_HELP = "<b>/groups</b>\nView all the groups you are in"
GROUP_POLLS_HELP = "<b>/gpolls</b>\nView all your group polls"
GROUP_LISTS_HELP = "<b>/glists</b>\nView all your group lists"
GROUP_TEMPLATES_HELP = "<b>/gtemps</b>\nView all your group templates"
INVITE_HELP = "<b>/invite</b>\nSend an invite link to your friends to join your group"
HELP_HELP = "<b>/help</b>\nView this help message"

# endregion

# region COMMAND HANDLERS


def handle_start(update: Update, context: CallbackContext) -> None:
    """Displays welcome message to the bot and manages pm messages."""
    update.message.delete()
    delete_old_chat_message(update, context)

    arguments = context.args
    if not arguments:
        update.message.reply_html(START, reply_markup=util.build_single_button_markup("Close", models.CLOSE))
        return

    if re.match(r"^\w+$", arguments[0]):
        handle_pm_command(arguments[0], update, context)
        return

    match = re.match(r"^(\w+)-(\w+)$", arguments[0])
    if not match:
        handle_help(update, context)
        return

    action, details = match.group(1), match.group(2)
    # Handle access
    if action == "access":
        handle_bot_access_pm(update, context, details)
        return
    # Handle join
    elif action == "join":
        handle_join_pm(update, context, details)
        return
    # Handle comment
    elif action == "comment":
        handle_comment_pm(update, context, details)
        return
    # Handle vote
    elif action == "vote":
        handle_vote_pm(update, context, details)
        return
    # Handle update
    elif action == "update":
        handle_update_pm(update, context, details)
        return
    # Handle others
    else:
        handle_help(update, context)
        return


def handle_pm_command(command: str, update: Update, context: CallbackContext) -> None:
    """Manages standard commands in pm mode with the bot."""
    if command == START_COMMAND:
        handle_start(update, context)
        return
    elif command == KEYBOARD_COMMAND:
        handle_keyboard(update, context)
        return
    elif command == POLL_COMMAND:
        title = context.user_data.get("title", "")
        update.message.text = f"/{command} {title}"
        handle_poll(update, context)
        return
    elif command == POLLS_COMMAND:
        handle_polls(update, context)
        return
    elif command == LIST_COMMAND:
        title = context.user_data.get("title", "")
        update.message.text = f"/{command} {title}"
        handle_list(update, context)
        return
    elif command == LISTS_COMMAND:
        handle_lists(update, context)
        return
    elif command == TEMPLATE_COMMAND:
        handle_template(update, context)
        return
    elif command == TEMPLATES_COMMAND:
        handle_templates(update, context)
        return
    elif command == GROUP_COMMAND:
        name = context.user_data.get("name", "")
        update.message.text = f"/{command} {name}"
        handle_group(update, context)
        return
    elif command == GROUPS_COMMAND:
        handle_groups(update, context)
        return
    elif command == GROUP_POLLS_COMMAND:
        handle_group_polls(update, context)
        return
    elif command == GROUP_LISTS_COMMAND:
        handle_group_lists(update, context)
        return
    elif command == GROUP_TEMPLATES_COMMAND:
        handle_group_templates(update, context)
        return
    elif command == INVITE_COMMAND:
        handle_invite(update, context)
        return
    elif command == ENROL_COMMAND:
        handle_enrol(update, context)
        return
    elif command == PROMOTE_COMMAND:
        handle_promote(update, context)
        return
    elif command == HELP_COMMAND:
        handle_help(update, context)
        return
    else:
        handle_start(update, context)
        return


def handle_bot_access_pm(update: Update, context: CallbackContext, details: str) -> None:
    """Handles user joining group through group invite code."""
    invitation_code = details
    uid = update.effective_user.id

    user = User.get_user_by_id(uid)
    if user:
        update.message.reply_html(
            ERROR_ACCESS_ALREADY_GRANTED, reply_markup=util.build_single_button_markup("Close", models.CLOSE)
        )
        logger.info("Bot access already granted!")
        return

    if invitation_code == BotManager.get_bot_token_hash(ACCESS_KEY, uid):
        register_user(update.effective_user)
        update.message.reply_html(ACCESS_GRANTED, reply_markup=util.build_single_button_markup("Close", models.CLOSE))
        return

    update.message.reply_html(ACCESS_DENIED, reply_markup=util.build_single_button_markup("Close", models.CLOSE))
    logger.warning("Invalid bot access attempt!!")
    return


def handle_join_pm(update: Update, context: CallbackContext, details: str) -> None:
    """Handles user joining group through group invite code."""
    invitation_code = details
    try_join_group_through_invitation(update, invitation_code)
    return


def handle_comment_pm(update: Update, context: CallbackContext, details: str) -> None:
    """Handles user voting for poll option that requires comment."""
    match = re.match(r"^([^_\W]+_[^_\W]+)$", details)
    if not match:
        update.message.reply_html(
            ERROR_INVALID_POLL_COMMENT_REQUEST, reply_markup=util.build_single_button_markup("Close", models.CLOSE)
        )
        logger.warning("Invalid poll comment request!")
        return

    poll_hash = match.group(1)
    poll_id = poll_hash.split("_")[0]
    poll = Poll.get_poll_by_id(poll_id)

    if not poll or poll.get_poll_hash() != poll_hash:
        update.message.reply_html(
            ERROR_INVALID_POLL_COMMENT_REQUEST, reply_markup=util.build_single_button_markup("Close", models.CLOSE)
        )
        logger.warning("Invalid poll comment request!")
        return

    response, buttons = poll.build_option_comment_text_and_buttons(update.effective_user.id)
    update.message.reply_html(response, reply_markup=buttons)
    return


def handle_vote_pm(update: Update, context: CallbackContext, details: str) -> None:
    """Handles user adding or changing comment for a poll option."""
    match = re.match(r"^([^_\W]+_[^_\W]+)_(\d+)$", details)
    if not match:
        update.message.reply_html(
            ERROR_INVALID_POLL_VOTE_REQUEST, reply_markup=util.build_single_button_markup("Close", models.RETURN)
        )
        logger.warning("Invalid poll vote request!")
        return

    uid, user_profile = extract_user_data(update.effective_user)

    poll_hash, opt_id = match.group(1), int(match.group(2))
    poll_id = poll_hash.split("_")[0]
    poll = Poll.get_poll_by_id(poll_id)

    if not poll or poll.get_poll_hash() != poll_hash:
        update.message.reply_html(
            ERROR_INVALID_POLL_VOTE_REQUEST, reply_markup=util.build_single_button_markup("Close", models.RETURN)
        )
        logger.warning("Invalid poll vote request!")
        return

    if opt_id >= len(poll.get_options()):
        update.message.reply_html(
            ERROR_INVALID_POLL_OPTION_REQUEST, reply_markup=util.build_single_button_markup("Close", models.RETURN)
        )
        logger.warning("Invalid option selected from poll vote!")
        return

    option = poll.get_options()[opt_id]

    if option.is_voted_by_user(uid):
        response = poll.toggle(opt_id, uid, user_profile)

        reply_message = update.message.reply_html(
            response, reply_markup=util.build_single_switch_button_markup("Return To Chat", "")
        )

        reply_message.delete()
        refresh_polls(poll, context)
        return

    reply_message = update.message.reply_html(
        REASON.format(util.make_html_bold(option.get_title())),
        reply_markup=util.build_single_button_markup("Cancel", models.RETURN),
    )
    context.user_data.update({"action": models.VOTE, "pid": poll_id, "opt": opt_id, "ed": reply_message.message_id})
    return


def handle_update_pm(update: Update, context: CallbackContext, details: str) -> None:
    """Handles user making updates to a list."""
    match = re.match(r"^([^_\W]+_[^_\W]+)$", details)
    if not match:
        update.message.reply_html(
            ERROR_INVALID_LIST_UPDATE_REQUEST, reply_markup=util.build_single_button_markup("Close", models.CLOSE)
        )
        logger.warning("Invalid list update request!")
        return

    list_hash = match.group(1)
    list_id = list_hash.split("_")[0]
    _list = List.get_list_by_id(list_id)

    if not _list or _list.get_list_hash() != list_hash:
        update.message.reply_html(
            ERROR_INVALID_LIST_UPDATE_REQUEST, reply_markup=util.build_single_button_markup("Close", models.CLOSE)
        )
        logger.warning("Invalid list update request!")
        return

    update.message.reply_html(
        _list.render_text(), reply_markup=_list.build_option_buttons()
    )
    return


def handle_keyboard(update: Update, context: CallbackContext) -> None:
    """Shows option to user to show or hide the command keyboard."""
    update.message.delete()
    delete_old_chat_message(update, context)
    context.user_data.clear()

    show_hide_buttons = util.build_multiple_stacked_buttons_markup(
        [util.generate_button_details("Show", models.SHOW), util.generate_button_details("Hide", models.HIDE)],
        [util.generate_button_details("Close", models.CLOSE)]
    )

    update.message.reply_html("Show or hide command keyboard?", reply_markup=show_hide_buttons)
    return


def handle_access(update: Update, context: CallbackContext) -> None:
    """Manages different accesses in the bot."""
    delete_chat_message(update.message)
    delete_old_chat_message(update, context)

    _, _, is_admin = get_user_permissions(update.effective_user.id)

    if not is_admin:
        handle_help(update, context)
        return

    response, buttons = BotManager.build_access_request_text_and_buttons()
    update.message.reply_html(response, reply_markup=buttons)


def handle_enrol(update: Update, context: CallbackContext) -> None:
    """Creates an invitation to this bot for a user."""
    delete_chat_message(update.message)

    _, _, is_admin = get_user_permissions(update.effective_user.id)

    if not is_admin:
        handle_help(update, context)
        return

    reply_message = update.message.reply_html(
        ACCESS_ENTER_USER_ID,
        reply_markup=util.build_single_button_markup("Cancel", models.RESET)
    )
    context.user_data.update({"action": models.BOT_ACCESS, "ed": reply_message.message_id})
    return


def handle_promote(update: Update, context: CallbackContext) -> None:
    """Promotes a user to a bot leader if uid is given, otherwise shows list of users to promote."""
    text = update.message.text.strip()
    delete_chat_message(update.message)

    _, _, is_admin = get_user_permissions(update.effective_user.id)

    if not is_admin:
        handle_help(update, context)
        return

    match = re.match(r"^/promote\s+(\w+)$", text)
    if not match:
        response, buttons = BotManager.build_leader_promote_invite_text_and_button()
        update.message.reply_html(response, reply_markup=buttons)
        return

    uid = util.decode(match.group(1))
    user = User.get_user_by_id(uid)
    if not user:
        update.message.reply_html(
            ERROR_USER_NOT_FOUND, reply_markup=util.build_single_button_markup("Close", models.CLOSE)
        )
        return

    if user.is_leader():
        update.message.reply_html(
            ERROR_ALREADY_PROMOTED, reply_markup=util.build_single_button_markup("Close", models.CLOSE)
        )
        return

    user.promote_to_leader()
    update.message.reply_html(
        USER_PROMOTED.format(util.make_html_bold(user.get_name())),
        reply_markup=util.build_single_button_markup("Close", models.CLOSE)
    )
    return


def handle_poll(update: Update, context: CallbackContext) -> None:
    """Begins building a new poll."""
    delete_chat_message(update.message)
    delete_old_chat_message(update, context)
    context.user_data.clear()

    if not is_registered(update.effective_user):
        handle_help(update, context)
        return

    context.user_data.update({"action": models.POLL, "step": 1, "title": "", "descr": "", "options": []})

    match = re.match(r"^/poll\s+((?:\n|.)+)$", update.message.text.strip())
    if not match:
        reply_message = update.message.reply_html(
            NEW_POLL, reply_markup=util.build_single_button_markup("Cancel", models.RESET)
        )
        context.user_data.update({"ed": reply_message.message_id})
        return

    title = match.group(1).replace("\n", " ")

    if len(title) > MAX_TITLE_LENGTH:
        reply_message = update.message.reply_html(
            ERROR_TITLE_TOO_LONG, reply_markup=util.build_single_button_markup("Cancel", models.RESET)
        )
        context.user_data.update({"ed": reply_message.message_id})
        return

    response = f"Your new poll <b>title</b> is\n<b>{title}</b>\n\n" \
               f"<b>Continue</b> to the next step or re-enter another title."
    reply_message = update.message.reply_html(
        response, reply_markup=build_progress_buttons(next_text="Continue")
    )
    context.user_data.update({"title": title, "ed": reply_message.message_id})
    return


def handle_polls(update: Update, context: CallbackContext) -> None:
    """Displays all polls created by user."""
    delete_chat_message(update.message)
    delete_old_chat_message(update, context)
    context.user_data.clear()

    if not is_registered(update.effective_user):
        handle_help(update, context)
        return

    user = User.get_user_by_id(update.effective_user.id)

    update.message.reply_html(
        user.render_poll_list(), reply_markup=util.build_single_button_markup("Close", models.CLOSE)
    )
    return


def handle_poll_view(update: Update, context: CallbackContext) -> None:
    """Displays the master poll identified by its poll id"""
    delete_chat_message(update.message)
    delete_old_chat_message(update, context)
    context.user_data.clear()

    if not is_registered(update.effective_user):
        handle_help(update, context)
        return

    uid = update.effective_user.id
    text = update.message.text

    poll_id = re.match(r"^/poll_(\w+)$", text).group(1)
    poll = Poll.get_poll_by_id(poll_id)
    if not poll:
        handle_help(update, context)
        return

    if poll.get_creator_id() == uid or User.get_user_by_id(uid).has_group_poll(poll_id):
        deliver_poll(update, poll)
        return

    handle_help(update, context)
    return


def handle_list(update: Update, context: CallbackContext) -> None:
    """Begins building a new list."""
    delete_chat_message(update.message)
    delete_old_chat_message(update, context)
    context.user_data.clear()

    if not is_registered(update.effective_user):
        handle_help(update, context)
        return

    context.user_data.update({"action": models.LIST, "step": 1, "title": "", "descr": "", "options": [], "choices": []})

    match = re.match(r"^/list\s+((?:\n|.)+)$", update.message.text.strip())
    if not match:
        reply_message = update.message.reply_html(
            NEW_LIST, reply_markup=util.build_single_button_markup("Cancel", models.RESET)
        )
        context.user_data.update({"ed": reply_message.message_id})
        return

    title = match.group(1).replace("\n", " ")

    if len(title) > MAX_TITLE_LENGTH:
        reply_message = update.message.reply_html(
            ERROR_TITLE_TOO_LONG, reply_markup=util.build_single_button_markup("Cancel", models.RESET)
        )
        context.user_data.update({"ed": reply_message.message_id})
        return

    response = f"Your new list <b>title</b> is\n<b>{title}</b>\n\n" \
               f"<b>Continue</b> to the next step or re-enter another title."
    reply_message = update.message.reply_html(
        response, reply_markup=build_progress_buttons(next_text="Continue")
    )
    context.user_data.update({"title": title, "ed": reply_message.message_id})
    return


def handle_lists(update: Update, context: CallbackContext) -> None:
    """Displays all lists created by user."""
    delete_chat_message(update.message)
    delete_old_chat_message(update, context)
    context.user_data.clear()

    if not is_registered(update.effective_user):
        handle_help(update, context)
        return

    user = User.get_user_by_id(update.effective_user.id)

    update.message.reply_html(
        user.render_list_list(), reply_markup=util.build_single_button_markup("Close", models.CLOSE)
    )
    return


def handle_list_view(update: Update, context: CallbackContext) -> None:
    """Displays the master list identified by its list id"""
    delete_chat_message(update.message)
    delete_old_chat_message(update, context)
    context.user_data.clear()

    user, _, _ = get_user_permissions(update.effective_user.id)
    if not user:
        handle_help(update, context)
        return

    text = update.message.text.strip()

    list_id = re.match(r"^/list_(\w+)$", text).group(1)
    _list = List.get_list_by_id(list_id)

    if not _list or (_list.get_creator_id() != user.get_uid() and not user.has_group_list(list_id)):
        handle_help(update, context)
        return

    deliver_list(update, _list)
    return


def handle_template(update: Update, context: CallbackContext) -> None:
    """Creates custom templates to build polls and lists."""
    delete_chat_message(update.message)
    delete_old_chat_message(update, context)
    context.user_data.clear()

    user, _, _ = get_user_permissions(update.effective_user.id)

    if not user:
        handle_help(update, context)
        return

    # Try to match the command to create a poll or list from a template
    match = re.match(r"^/temp\s+(p|poll|l|list)\s+(\w+)\s*(\n(?:\n|.)*)?$", update.message.text.strip())
    if match:
        template_type, name, format_inputs = match.group(1), match.group(2), match.group(3)
        format_inputs = format_inputs if format_inputs else ""
        if template_type in ("p", "poll"):
            temp_poll = user.get_temp_poll_by_name(name)
            if not temp_poll:
                response = f"No poll template with name <b>{name}</b> exists.\nUse /temps to view all your templates."
                reply_message = update.message.reply_html(
                    response, reply_markup=util.build_single_button_markup("Close", models.CLOSE)
                )
                context.user_data.update({"del": reply_message.message_id})
                return

            title, description, is_valid = temp_poll.render_title_and_description(format_inputs)
            if not is_valid:
                reply_message = update.message.reply_html(
                    title, reply_markup=util.build_single_button_markup("Close", models.CLOSE)
                )
                context.user_data.update({"del": reply_message.message_id})
                return
            poll: Poll = user.create_poll_from_template(temp_poll.temp_id, title, description)
            update.message.reply_html(POLL_DONE, reply_markup=util.build_single_button_markup("Close", models.CLOSE))
            update.message.reply_html(poll.render_text(), reply_markup=poll.build_admin_buttons())
            return
        elif template_type in ("l", "list"):
            temp_list = user.get_temp_list_by_name(name)
            if not temp_list:
                response = f"No list template with name <b>{name}</b> exists.\nUse /temps to view all your templates."
                reply_message = update.message.reply_html(
                    response, reply_markup=util.build_single_button_markup("Close", models.CLOSE)
                )
                context.user_data.update({"del": reply_message.message_id})
                return

            title, description, is_valid = temp_list.render_title_and_description(format_inputs)
            if not is_valid:
                reply_message = update.message.reply_html(
                    title, reply_markup=util.build_single_button_markup("Close", models.CLOSE)
                )
                context.user_data.update({"del": reply_message.message_id})
                return
            _list: List = user.create_list_from_template(temp_list.temp_id, title, description)
            update.message.reply_html(LIST_DONE, reply_markup=util.build_single_button_markup("Close", models.CLOSE))
            update.message.reply_html(_list.render_text(), reply_markup=_list.build_admin_buttons())
            return

    response_text = "Which <b>template</b> do you want to create?"
    buttons = util.build_multiple_stacked_buttons_markup(
        [
            util.generate_button_details("Poll", models.TEMP_POLL),
            util.generate_button_details("List", models.TEMP_LIST)
        ],
        [util.generate_button_details("Preset Format Guide", models.TEMP_GUIDE)],
        [util.generate_button_details("Close", models.CLOSE)]
    )
    update.message.reply_html(response_text, reply_markup=buttons)
    return


def handle_templates(update: Update, context: CallbackContext) -> None:
    """Views all the user's templates."""
    delete_chat_message(update.message)
    delete_old_chat_message(update, context)
    context.user_data.clear()

    user, _, _ = get_user_permissions(update.effective_user.id)

    if not user:
        handle_help(update, context)
        return

    update.message.reply_html(
        user.render_template_list(), reply_markup=util.build_single_button_markup("Close", models.CLOSE)
    )
    return


def handle_template_view(update: Update, context: CallbackContext) -> None:
    """Displays the template identified by its template id"""
    delete_chat_message(update.message)
    delete_old_chat_message(update, context)
    context.user_data.clear()

    user, _, _ = get_user_permissions(update.effective_user.id)
    text = update.message.text

    temp_id = re.match(r"^/temp_(\w+)$", text).group(1)
    template: Template = Template.get_template_by_id(temp_id)

    if not template or (template.creator_id != user.get_uid() and not user.has_group_template(temp_id)):
        handle_help(update, context)
        return

    update.message.reply_html(template.render_text(), reply_markup=template.build_main_buttons())
    return


def handle_group(update: Update, context: CallbackContext) -> None:
    """Begins creating a new group."""
    delete_chat_message(update.message)
    delete_old_chat_message(update, context)
    context.user_data.clear()

    user, is_leader, _ = get_user_permissions(update.effective_user.id)

    if not user or not is_leader:
        handle_help(update, context)
        return

    context.user_data.update({"action": models.GROUP, "step": 1, "name": "", "secret": ""})

    match = re.match(r"^/group\s+((?:\n|.)+)$", update.message.text.strip())
    if not match:
        reply_message = update.message.reply_html(
            NEW_GROUP, reply_markup=util.build_single_button_markup("Cancel", models.RESET)
        )
        context.user_data.update({"ed": reply_message.message_id})
        return

    group_name = match.group(1).replace("\n", " ")

    if len(group_name) > MAX_GROUP_NAME_LENGTH:
        reply_message = update.message.reply_html(
            ERROR_GROUP_NAME_TOO_LONG, reply_markup=util.build_single_button_markup("Cancel", models.RESET)
        )
        context.user_data.update({"ed": reply_message.message_id})
        return

    if user.has_group_with_name(group_name):
        reply_message = update.message.reply_html(
            ERROR_GROUP_NAME_EXISTS, reply_markup=util.build_single_button_markup("Cancel", models.RESET)
        )
        context.user_data.update({"ed": reply_message.message_id})
        return

    response = f"Your new group <b>name</b> is\n<b>{group_name}</b>\n\n" \
               f"<b>Continue</b> to the next step or re-enter another group name."
    reply_message = update.message.reply_html(
        response, reply_markup=build_progress_buttons(next_text="Continue")
    )
    context.user_data.update({"name": group_name, "ed": reply_message.message_id})
    return


def handle_groups(update: Update, context: CallbackContext) -> None:
    """Views all the user's groups."""
    delete_chat_message(update.message)
    delete_old_chat_message(update, context)
    context.user_data.clear()

    if not is_registered(update.effective_user):
        handle_help(update, context)
        return

    user = User.get_user_by_id(update.effective_user.id)

    update.message.reply_html(
        user.render_group_list(), reply_markup=util.build_single_button_markup("Close", models.CLOSE)
    )
    return


def handle_group_view(update: Update, context: CallbackContext) -> None:
    """Views details of a group."""
    delete_chat_message(update.message)
    delete_old_chat_message(update, context)
    context.user_data.clear()

    if not is_registered(update.effective_user):
        handle_help(update, context)
        return

    uid = update.effective_user.id
    text = update.message.text

    gid = re.match(r"^/group_(\w+).*$", text).group(1)
    group = Group.get_group_by_id(gid)
    if group and uid in group.get_member_ids():
        deliver_group(update, group)
    else:
        handle_help(update, context)
    return


def handle_group_polls(update: Update, context: CallbackContext) -> None:
    """Displays all group polls to the user."""
    delete_chat_message(update.message)
    delete_old_chat_message(update, context)
    context.user_data.clear()

    user, _, _ = get_user_permissions(update.effective_user.id)
    if not user:
        handle_help(update, context)
        return

    update.message.reply_html(
        user.render_group_poll_list(), reply_markup=util.build_single_button_markup("Close", models.CLOSE)
    )
    return


def handle_group_lists(update: Update, context: CallbackContext) -> None:
    """Displays all group lists to the user."""
    delete_chat_message(update.message)
    delete_old_chat_message(update, context)
    context.user_data.clear()

    user, _, _ = get_user_permissions(update.effective_user.id)
    if not user:
        handle_help(update, context)
        return

    update.message.reply_html(
        user.render_group_list_list(), reply_markup=util.build_single_button_markup("Close", models.CLOSE)
    )
    return


def handle_group_templates(update: Update, context: CallbackContext) -> None:
    """Displays all group templates to the user."""
    delete_chat_message(update.message)
    delete_old_chat_message(update, context)
    context.user_data.clear()

    user, _, _ = get_user_permissions(update.effective_user.id)
    if not user:
        handle_help(update, context)
        return

    update.message.reply_html(
        user.render_group_template_list(), reply_markup=util.build_single_button_markup("Close", models.CLOSE)
    )
    return


def handle_invite(update: Update, context: CallbackContext) -> None:
    """Sends group invitation code."""
    delete_chat_message(update.message)
    delete_old_chat_message(update, context)
    context.user_data.clear()

    if not is_registered(update.effective_user):
        handle_help(update, context)
        return

    uid = update.effective_user.id

    response, buttons = User.get_user_by_id(uid).build_invite_text_and_buttons()
    if response:
        update.message.reply_html(response, reply_markup=buttons)
    else:
        update.message.reply_html(util.make_html_italic("You do not own any groups!"), reply_markup=buttons)
    return


def handle_help(update: Update, context: CallbackContext) -> None:
    """Displays a help message to explain available bot commands."""
    delete_chat_message(update.message)
    delete_old_chat_message(update, context)
    context.user_data.clear()

    uid = update.effective_user.id
    user, is_leader, is_admin = get_user_permissions(uid)

    header = [util.make_html_bold("Available Bot Commands")]

    body = [START_HELP, KEYBOARD_HELP]
    if user:
        if is_leader:
            body += [POLL_HELP, POLLS_HELP, LIST_HELP, LISTS_HELP, TEMPLATE_HELP, TEMPLATES_HELP, GROUP_HELP,
                     GROUPS_HELP, GROUP_POLLS_HELP, GROUP_LISTS_HELP, GROUP_TEMPLATES_HELP, INVITE_HELP]
        else:
            body += [POLL_HELP, POLLS_HELP, LIST_HELP, LISTS_HELP, TEMPLATE_HELP, TEMPLATES_HELP, GROUPS_HELP,
                     GROUP_POLLS_HELP, GROUP_LISTS_HELP, GROUP_TEMPLATES_HELP, INVITE_HELP]
    body += [HELP_HELP]

    if not user:
        body += [util.make_html_italic(ACCESS_REQUEST)]

    response = "\n\n".join(header + body)
    update.message.reply_html(response, reply_markup=util.build_single_button_markup("Close", models.CLOSE))
    return


# endregion

# region MESSAGE HANDLERS


def handle_message(update: Update, context: CallbackContext) -> None:
    """Handles a message from the user."""
    if not update.message:
        return

    text = update.message.text
    if not text:
        return

    user, is_leader, is_admin = get_user_permissions(update.effective_user.id)

    # Handle messages according to their action type
    action = context.user_data.get("action", "")
    if action == models.BOT_ACCESS and is_admin:
        handle_bot_access_conversation(update, context)
        return
    elif action == models.POLL and user:
        handle_poll_conversation(update, context)
        return
    elif action == models.VOTE:
        handle_vote_conversation(update, context)
        return
    elif action == models.COMMENT:
        handle_comment_conversation(update, context)
        return
    elif action == models.LIST and user:
        handle_list_conversation(update, context)
        return
    elif action == models.GROUP and is_leader:
        handle_group_conversation(update, context)
        return
    elif action == models.TEMP_POLL and user:
        handle_temp_poll_conversation(update, context)
        return
    elif action == models.TEMP_LIST and user:
        handle_temp_list_conversation(update, context)
        return
    if is_private_chat(update.message):
        if text == ".":
            update.message.delete()
            return
        handle_help(update, context)
        return


def handle_bot_access_conversation(update: Update, context: CallbackContext) -> None:
    """Handles the conversation between the bot and the admin user to generate a bot access invitation."""
    uid = update.message.text.strip()

    delete_chat_message(update.message)
    delete_old_chat_message(update, context)

    if not uid.isdigit():
        response = "You've entered an invalid user id. Please enter again."
        edit_conversation_message(
            update, context, response,
            reply_markup=util.build_single_button_markup("Cancel", models.RESET)
        )
        return

    response, buttons = BotManager.build_bot_access_enrol_text_and_button(int(uid))
    edit_conversation_message(update, context, response, reply_markup=buttons)
    context.user_data.clear()
    return


def handle_poll_conversation(update: Update, context: CallbackContext) -> None:
    """Handles the conversation between the bot and the user to build a poll."""
    delete_chat_message(update.message)
    delete_old_chat_message(update, context)

    text = update.message.text.strip()
    step, title, description, options = \
        context.user_data.get("step", 1), context.user_data.get("title", ""), context.user_data.get("descr", ""), \
        context.user_data.get("options", [])

    # Handle title
    if step == 1:
        text = text.replace("\n", " ").strip()
        if len(text) > MAX_TITLE_LENGTH:
            edit_conversation_message(
                update, context, ERROR_TITLE_TOO_LONG,
                reply_markup=util.build_single_button_markup("Cancel", models.RESET)
            )
            return

        response = f"Your new poll <b>title</b> is\n<b>{text}</b>\n\n" \
                   f"<b>Continue</b> to the next step or re-enter another title."
        edit_conversation_message(
            update, context, response, reply_markup=build_progress_buttons(next_text="Continue")
        )
        context.user_data.update({"title": text})
        return
    # Handle description
    elif step == 2 and title:
        response = f"Your new poll <b>description</b> is\n<i>{text}</i>\n\n" \
                   f"<b>Continue</b> to the next step or re-enter another description."
        edit_conversation_message(
            update, context, response, reply_markup=build_progress_buttons(next_text="Continue")
        )
        context.user_data.update({"descr": text})
        return
    # Handle option
    elif step == 3 and title and description:
        if not options:
            buttons = util.build_single_button_markup("Cancel", models.RESET)
        else:
            buttons = build_progress_buttons()

        if len(text) > MAX_OPTION_TITLE_LENGTH:
            edit_conversation_message(
                update, context, ERROR_OPTION_TITLE_TOO_LONG, reply_markup=buttons
            )
            return

        if text in options:
            edit_conversation_message(
                update, context, ERROR_DUPLICATE_OPTION_TITLE.format(util.list_to_indexed_list_string(options)),
                reply_markup=buttons
            )
            return

        options.append(text)
        context.user_data.update({"options": options})

        if len(options) >= MAX_OPTIONS:
            response_text = f"You have a maximum of {MAX_OPTIONS} options already!\n\n" \
                            f"{util.list_to_indexed_list_string(options)}\n\n" \
                            f"Press <b>Done</b> to finish."
            edit_conversation_message(update, context, response_text, reply_markup=buttons)
            return

        edit_conversation_message(
            update, context,
            NEXT_LIST_OPTION.format(f"<b>{text}</b>", util.list_to_indexed_list_string(options)),
            reply_markup=build_progress_buttons()
        )
        return
    # Handle invalid step
    else:
        logger.warning("Error with poll conversation step index!!")
        context.user_data.clear()
        handle_help(update, context)
        return


def handle_list_conversation(update: Update, context: CallbackContext) -> None:
    """Handles the conversation between the bot and the user to build a list."""
    delete_chat_message(update.message)
    delete_old_chat_message(update, context)

    text = update.message.text.strip()
    step, title, description, options, choices = \
        context.user_data.get("step", 1), context.user_data.get("title", ""), context.user_data.get("descr", ""), \
        context.user_data.get("options", []), context.user_data.get("choices", [])

    # Handle title
    if step == 1:
        text = text.replace("\n", " ").strip()
        if len(text) > MAX_TITLE_LENGTH:
            edit_conversation_message(
                update, context, ERROR_TITLE_TOO_LONG,
                reply_markup=util.build_single_button_markup("Cancel", models.RESET)
            )
            return

        response = f"Your new list <b>title</b> is\n<b>{text}</b>\n\n" \
                   f"<b>Continue</b> to the next step or re-enter another title."
        edit_conversation_message(
            update, context, response, reply_markup=build_progress_buttons(next_text="Continue")
        )
        context.user_data.update({"title": text})
        return
    # Handle description
    elif step == 2 and title:
        response = f"Your new list <b>description</b> is\n<i>{text}</i>\n\n" \
                   f"<b>Continue</b> to the next step or re-enter another description."
        edit_conversation_message(
            update, context, response, reply_markup=build_progress_buttons(next_text="Continue")
        )
        context.user_data.update({"descr": text})
        return
    # Handle option
    elif step == 3 and title and description:
        if not options:
            buttons = util.build_single_button_markup("Cancel", models.RESET)
        else:
            buttons = build_progress_buttons()

        if len(text) > MAX_OPTION_TITLE_LENGTH:
            edit_conversation_message(
                update, context, ERROR_OPTION_TITLE_TOO_LONG, reply_markup=buttons
            )
            return

        if text in options:
            edit_conversation_message(
                update, context, ERROR_DUPLICATE_OPTION_TITLE.format(util.list_to_indexed_list_string(options)),
                reply_markup=buttons
            )
            return

        options.append(text)
        context.user_data.update({"options": options})

        if len(options) >= MAX_OPTIONS:
            response_text = f"You have a maximum of {MAX_OPTIONS} options already!\n\n" \
                            f"{util.list_to_indexed_list_string(options)}\n\n" \
                            f"Press <b>Done</b> to go to the next step."
            edit_conversation_message(update, context, response_text, reply_markup=buttons)
            return

        edit_conversation_message(
            update, context,
            NEXT_LIST_OPTION.format(f"<b>{text}</b>", util.list_to_indexed_list_string(options)),
            reply_markup=build_progress_buttons()
        )
        return
    # Handle choice
    elif step == 4 and title and description and options:
        if not choices:
            buttons = util.build_single_button_markup("Cancel", models.RESET)
        else:
            buttons = build_progress_buttons()

        if len(text) > MAX_CHOICE_ITEM_NAME_LENGTH:
            edit_conversation_message(
                update, context, ERROR_CHOICE_NAME_TOO_LONG, reply_markup=error_buttons
            )
            return

        if text in choices:
            edit_conversation_message(
                update, context, ERROR_DUPLICATE_CHOICE_NAME.format(util.list_to_indexed_list_string(choices)),
                reply_markup=buttons
            )
            return

        choices.append(text)
        context.user_data.update({"choices": choices})

        edit_conversation_message(
            update, context,
            NEXT_LIST_CHOICE.format(f"<b>{text}</b>", util.list_to_indexed_list_string(choices)),
            reply_markup=build_progress_buttons()
        )
        return
    # Handle invalid step
    else:
        logger.warning("Error with list conversation step index!!")
        context.user_data.clear()
        handle_help(update, context)
        return


def handle_vote_conversation(update: Update, context: CallbackContext) -> None:
    """Handles the conversation between the bot and the user to vote a poll option."""
    delete_chat_message(update.message),
    delete_old_chat_message(update, context)

    poll_id, opt_id = context.user_data.get("pid", ""), int(context.user_data.get("opt", -1))
    uid, user_profile = extract_user_data(update.effective_user)
    text = update.message.text.strip()

    poll = Poll.get_poll_by_id(poll_id)
    if not poll:
        edit_conversation_message(
            update, context, DELETED_POLL,
            reply_markup=util.build_single_button_markup("Close", models.RETURN)
        )
        logger.warning("Poll deleted before vote.")
        return

    if opt_id >= len(poll.get_options()) or opt_id < 0:
        edit_conversation_message(
            update, context, ERROR_INVALID_POLL_OPTION_REQUEST,
            reply_markup=util.build_single_button_markup("Close", models.RETURN)
        )
        logger.warning("Invalid option selected from poll vote!")
        return

    if poll.get_options()[opt_id].is_voted_by_user(uid):
        poll.edit_user_comment(opt_id, uid, text)
    else:
        poll.toggle(opt_id, uid, user_profile, text)

    response = f"{models.EMOJI_HAPPY} Comment has been updated to <b>{text}</b>\n\n" \
               f"<b>Return to Chat</b> or re-enter another comment to change."

    edit_conversation_message(
        update, context, response,
        reply_markup=util.build_single_button_markup("Return To Chat", models.RETURN)
    )
    refresh_polls(poll, context)
    return


def handle_comment_conversation(update: Update, context: CallbackContext) -> None:
    """Handles the conversation between the bot and the user to comment a poll option."""
    delete_chat_message(update.message),
    delete_old_chat_message(update, context)

    poll_id, opt_id = context.user_data.get("pid", ""), int(context.user_data.get("opt", -1))
    uid, user_profile = extract_user_data(update.effective_user)
    text = update.message.text.strip()

    poll = Poll.get_poll_by_id(poll_id)
    if not poll:
        edit_conversation_message(
            update, context, DELETED_POLL,
            reply_markup=util.build_single_button_markup("Close", models.RETURN)
        )
        logger.warning("Poll deleted before vote.")
        return

    if opt_id >= len(poll.get_options()) or opt_id < 0:
        edit_conversation_message(
            update, context, ERROR_INVALID_POLL_OPTION_REQUEST,
            reply_markup=util.build_single_button_markup("Close", models.RETURN)
        )
        logger.warning("Invalid option selected from poll vote!")
        return

    if not poll.get_options()[opt_id].is_voted_by_user(uid):
        edit_conversation_message(
            update, context, ERROR_NOT_VOTED,
            reply_markup=util.build_single_button_markup("Close", models.RETURN)
        )
        logger.warning("Poll option not voted by user!")
        return

    poll.edit_user_comment(opt_id, uid, text)

    response = f"{models.EMOJI_HAPPY} Comment has been updated to <b>{text}</b>\n\n" \
               f"<b>Return to Chat</b> or re-enter another comment to change."

    edit_conversation_message(
        update, context, response, reply_markup=poll.build_comment_complete_buttons()
    )
    refresh_polls(poll, context)
    return


def handle_group_conversation(update: Update, context: CallbackContext) -> None:
    """Handles the conversation between the bot and the user to create a group."""
    delete_chat_message(update.message)
    delete_old_chat_message(update, context)

    user, _, _ = get_user_permissions(update.effective_user.id)

    text = util.strip_html_symbols(update.message.text.strip())
    step, group_name, secret, gid = \
        context.user_data.get("step", 1), context.user_data.get("name", ""), context.user_data.get("secret", ""), \
        context.user_data.get("gid", "")

    group = Group.get_group_by_id(gid)

    # Handle group name
    if step == 1:
        text = text.replace("\n", " ")
        if len(group_name) > MAX_GROUP_NAME_LENGTH:
            edit_conversation_message(
                update, context, ERROR_GROUP_NAME_TOO_LONG,
                reply_markup=util.build_single_button_markup("Cancel", models.RESET)
            )
            return

        if user.has_group_with_name(text):
            edit_conversation_message(
                update, context, ERROR_GROUP_NAME_EXISTS,
                reply_markup=util.build_single_button_markup("Cancel", models.RESET)
            )
            return

        response = f"Your new group <b>name</b> is\n<b>{text}</b>\n\n" \
                   f"<b>Continue</b> to the next step or re-enter another group name."
        edit_conversation_message(
            update, context, response, reply_markup=build_progress_buttons(next_text="Continue")
        )
        context.user_data.update({"name": text})
        return
    # Handle secret
    elif step == 2 and group_name:
        if not re.match(r"^[A-Za-z0-9]{4,20}$", text):
            edit_conversation_message(
                update, context, ERROR_INVALID_GROUP_PASS_FORMAT,
                reply_markup=build_progress_buttons(next_text="Skip")
            )
            return

        response = f"Your new group <b>password</b> is added successfully.\n\n" \
                   f"<b>Create</b> the group or re-enter another password."
        edit_conversation_message(
            update, context, response, reply_markup=build_progress_buttons(next_text="Create")
        )
        context.user_data.update({"secret": text})
        return
    # Handle change group name
    elif step == 10 and group:
        if group.get_owner() != user.get_uid():
            edit_conversation_message(
                update, context, f"<b>Only group owners can change the group name!</b>",
                reply_markup=group.build_single_back_button(models.SETTINGS)
            )
            context.user_data.clear()
            logger.warning("Illegal group name change!")
            return

        group_name = text.replace("\n", " ")

        if len(group_name) > MAX_GROUP_NAME_LENGTH:
            edit_conversation_message(
                update, context, ERROR_GROUP_NAME_TOO_LONG,
                reply_markup=group.build_single_back_button(f"{models.RENAME}_{models.NAME}")
            )
            return

        if user.has_group_with_name(group_name):
            edit_conversation_message(
                update, context, ERROR_GROUP_NAME_EXISTS,
                reply_markup=group.build_single_back_button(f"{models.RENAME}_{models.NAME}")
            )
            return

        # Change group name
        group.edit_name(group_name)
        edit_conversation_message(
            update, context, f"Group name successfully changed to <b>{group_name}</b>",
            reply_markup=group.build_single_back_button(models.SETTINGS, "Continue")
        )

        # Clear user data
        context.user_data.clear()
        return
    # Handle change password
    elif step == 11 and group:
        if group.get_owner() != user.get_uid():
            edit_conversation_message(
                update, context, f"<b>{ERROR_ILLEGAL_SECRET_CHANGE}</b>",
                reply_markup=group.build_single_back_button(models.SETTINGS)
            )
            context.user_data.clear()
            logger.warning("Illegal password change!")
            return

        if not re.match(r"^[A-Za-z0-9]{4,20}$", text):
            edit_conversation_message(
                update, context, ERROR_INVALID_GROUP_PASS_FORMAT,
                reply_markup=group.build_single_back_button(models.SECRET)
            )
            return

        # Change password
        group.edit_password(text)
        edit_conversation_message(
            update, context, "Group password changed successfully!",
            reply_markup=group.build_single_back_button(models.SETTINGS, "Continue")
        )

        # Clear user data
        context.user_data.clear()
        return
    # Handle invalid step
    else:
        logger.warning("Error with group conversation step index!!")
        context.user_data.clear()
        handle_help(update, context)
        return


def handle_temp_poll_conversation(update: Update, context: CallbackContext) -> None:
    """Handles the conversation between the bot and the user to create a poll template."""
    delete_chat_message(update.message)
    delete_old_chat_message(update, context)

    user, _, _ = get_user_permissions(update.effective_user.id)

    text = util.strip_html_symbols(update.message.text.strip())
    step, title, description, options, name, temp_id = \
        context.user_data.get("step", 1), context.user_data.get("title", ""), context.user_data.get("descr", ""), \
        context.user_data.get("options", []), context.user_data.get("name", ""), context.user_data.get("tempId", "")

    template: PollTemplate = PollTemplate.get_template_by_id(temp_id)

    # Handle title
    if step == 1:
        text = text.replace("\n", " ").strip()
        if len(text) > MAX_TITLE_LENGTH:
            edit_conversation_message(
                update, context, ERROR_TITLE_TOO_LONG,
                reply_markup=util.build_single_button_markup("Cancel", models.RESET)
            )
            return

        format_text, format_codes, is_valid = FormatTextCode.parse_format_text(text)

        if not is_valid:
            response = f"{text}\n\n{format_text}\n\nPlease re-enter the <b>title format</b>."
            edit_conversation_message(
                update, context, response, reply_markup=util.build_single_button_markup("Cancel", models.RESET)
            )
            return

        header = f"<b>Poll Title Format</b>"
        format_text_code = FormatTextCode(format_text, format_codes)
        body = format_text_code.render_details()
        footer = f"<b>Continue</b> to the next step or re-enter the title format to make changes."
        response = "\n\n".join([f"{header}\n{body}"] + [footer])

        edit_conversation_message(
            update, context, response, reply_markup=build_progress_buttons(next_text="Continue")
        )
        context.user_data.update({"title": text})
        return
    # Handle description
    elif step == 2 and title:
        format_text, format_codes, is_valid = FormatTextCode.parse_format_text(text)

        if not is_valid:
            response = f"{text}\n\n{format_text}\n\nPlease re-enter the <b>description format</b>."
            edit_conversation_message(
                update, context, response, reply_markup=build_progress_buttons(next_text="Skip")
            )
            return

        header = f"<b>Description Format</b>"
        format_text_code = FormatTextCode(format_text, format_codes)
        body = format_text_code.render_details()
        footer = f"<b>Continue</b> to the next step or re-enter the description format to make changes."
        response = "\n\n".join([f"{header}\n{body}"] + [footer])

        edit_conversation_message(
            update, context, response, reply_markup=build_progress_buttons(next_text="Continue")
        )
        context.user_data.update({"descr": text})
        return
    # Handle option
    elif step == 3 and title and description:
        if not options:
            buttons = util.build_single_button_markup("Cancel", models.RESET)
        else:
            buttons = build_progress_buttons()

        if len(text) > MAX_OPTION_TITLE_LENGTH:
            edit_conversation_message(
                update, context, ERROR_OPTION_TITLE_TOO_LONG, reply_markup=buttons
            )
            return

        if text in options:
            edit_conversation_message(
                update, context, ERROR_DUPLICATE_OPTION_TITLE.format(util.list_to_indexed_list_string(options)),
                reply_markup=buttons
            )
            return

        options.append(text)
        context.user_data.update({"options": options})

        if len(options) >= MAX_OPTIONS:
            response_text = f"You have a maximum of {MAX_OPTIONS} options already!\n\n" \
                            f"{util.list_to_indexed_list_string(options)}\n\n" \
                            f"Press <b>Done</b> to go to the next step."
            edit_conversation_message(update, context, response_text, reply_markup=buttons)
            return

        edit_conversation_message(
            update, context,
            NEXT_POLL_OPTION.format(f"<b>{text}</b>", util.list_to_indexed_list_string(options)),
            reply_markup=build_progress_buttons()
        )
        return
    # Handle template name
    elif step == 5 and title and description and options:
        name_match = re.match(r"^\w{1,12}$", text)
        if not name_match:
            response = "Sorry, please ensure that the name consists only a maximum of 12 alphanumeric characters."
            edit_conversation_message(
                update, context, response, reply_markup=util.build_single_button_markup("Cancel", models.RESET)
            )
            return

        if user.has_temp_poll_with_name(text):
            response = "Sorry, you already have a poll template with the same name. Please enter a different name."
            edit_conversation_message(
                update, context, response, reply_markup=util.build_single_button_markup("Cancel", models.RESET)
            )
            return

        response = f"Your new poll <b>template name</b> is <b>{text}</b>\n\n" \
                   f"<b>Continue</b> to the next step or re-enter another name for your template."
        edit_conversation_message(
            update, context, response, reply_markup=build_progress_buttons(next_text="Continue")
        )
        context.user_data.update({"name": text})
        return
    # Handle template description
    elif step == 6 and title and description and options and name:
        if len(text) > 50:
            response = "Sorry, please enter a shorter <b>template description</b> (maximum 50 characters)."
            edit_conversation_message(
                update, context, response,
                reply_markup=build_progress_buttons(next_text="Skip")
            )
            return

        response = f"Your new poll <b>template description</b> is\n<i>{text}</i>\n\n" \
                   f"<b>Create</b> the poll template or re-enter another description for your template."
        edit_conversation_message(
            update, context, response, reply_markup=build_progress_buttons(next_text="Create")
        )
        context.user_data.update({"tempDescr": text})
        return
    # Handle format title
    elif step == 11 and template:
        title_text, is_valid = template.render_title(text)
        if not is_valid:
            edit_conversation_message(
                update, context, title_text, reply_markup=template.build_format_back_buttons(models.TEMP_TITLE)
            )
            return
        title = f"<b>Current Poll Title</b>\n<b>{title_text}</b>"
        body = f"Enter another format input to change the title or <b>Continue</b> to go to the next step."
        response = "\n\n".join([title] + [body])
        edit_conversation_message(update, context, response, reply_markup=template.build_format_title_buttons())
        context.user_data.update({"titleCode": text})
        return
    # Handle format description
    elif step == 12 and template:
        description_text, is_valid = template.render_description(text)
        if not is_valid:
            edit_conversation_message(
                update, context, description_text,
                reply_markup=template.build_format_back_buttons(models.TEMP_DESCRIPTION)
            )
            return
        title = f"<b>Current Poll Description</b>\n<i>{description_text}</i>"
        body = f"Enter another format input to change the description, or <b>Create</b> the poll, " \
               f"or <b>Skip</b> to create the poll without a description."
        response = "\n\n".join([title] + [body])
        edit_conversation_message(update, context, response, reply_markup=template.build_format_description_buttons())
        context.user_data.update({"descrCode": text})
        return
    # Handle rename title
    elif step == 21 and template:
        if len(text) > MAX_TITLE_LENGTH:
            edit_conversation_message(
                update, context, ERROR_TITLE_TOO_LONG,
                reply_markup=template.build_single_back_button(f"{models.RENAME}_{models.TITLE}")
            )
            return

        format_text, format_codes, is_valid = FormatTextCode.parse_format_text(text)

        if not is_valid:
            response = f"{text}\n\n{format_text}\n\nPlease re-enter the <b>title format</b>."
            edit_conversation_message(
                update, context, response,
                reply_markup=template.build_single_back_button(f"{models.RENAME}_{models.TITLE}")
            )
            return

        header = f"<b>Poll Title Format</b>"
        format_text_code = FormatTextCode(format_text, format_codes)
        body = format_text_code.render_details()
        footer = f"<b>Confirm</b> to change the title format or re-enter the title format to make changes."
        response = "\n\n".join([f"{header}\n{body}"] + [footer])

        edit_conversation_message(
            update, context, response,
            reply_markup=template.build_edit_confirm_buttons(f"{models.EDIT}_{models.TITLE}")
        )
        context.user_data.update({"title": text})
        return
    # Handle rename description
    elif step == 22 and template:
        format_text, format_codes, is_valid = FormatTextCode.parse_format_text(text)

        if not is_valid:
            response = f"{text}\n\n{format_text}\n\nPlease re-enter the <b>description format</b>."
            edit_conversation_message(
                update, context, response,
                reply_markup=template.build_single_back_button(f"{models.RENAME}_{models.DESCRIPTION}")
            )
            return

        header = f"<b>Description Format</b>"
        format_text_code = FormatTextCode(format_text, format_codes)
        body = format_text_code.render_details()
        footer = f"<b>Confirm</b> to change the description format or re-enter the description format to make changes."
        response = "\n\n".join([f"{header}\n{body}"] + [footer])

        edit_conversation_message(
            update, context, response,
            reply_markup=template.build_edit_confirm_buttons(f"{models.EDIT}_{models.DESCRIPTION}")
        )
        context.user_data.update({"descr": text})
        return
    # Handle add description
    elif step == 23 and template:
        format_text, format_codes, is_valid = FormatTextCode.parse_format_text(text)

        if not is_valid:
            response = f"{text}\n\n{format_text}\n\nPlease re-enter the <b>description format</b>."
            edit_conversation_message(
                update, context, response,
                reply_markup=template.build_single_back_button(f"{models.ADD}_{models.DESCRIPTION}")
            )
            return

        header = f"<b>Description Format</b>"
        format_text_code = FormatTextCode(format_text, format_codes)
        body = format_text_code.render_details()
        footer = f"<b>Confirm</b> to add the description format or re-enter the description format to make changes."
        response = "\n\n".join([f"{header}\n{body}"] + [footer])

        edit_conversation_message(
            update, context, response,
            reply_markup=template.build_edit_confirm_buttons(f"{models.EDIT}_{models.DESCRIPTION}")
        )
        context.user_data.update({"descr": text})
        return
    # Handle rename template name
    elif step == 25 and template:
        name_match = re.match(r"^\w{1,12}$", text)
        if not name_match:
            response = "Sorry, please ensure that the name consists only a maximum of 12 alphanumeric characters."
            edit_conversation_message(
                update, context, response,
                reply_markup=template.build_single_back_button(f"{models.RENAME}_{models.TEMPLATE}_{models.NAME}")
            )
            return

        if user.has_temp_poll_with_name(text):
            response = "Sorry, you already have a poll template with the same name. Please enter a different name."
            edit_conversation_message(
                update, context, response,
                reply_markup=template.build_single_back_button(f"{models.RENAME}_{models.TEMPLATE}_{models.NAME}")
            )
            return

        # Change template name
        template.name = text
        edit_conversation_message(
            update, context, f"Poll template name successfully changed to <b>{template.name}</b>",
            reply_markup=template.build_single_back_button(f"{models.EDIT}_{models.TEMPLATE}", "Continue")
        )

        # Clear user data
        context.user_data.clear()
        return
    # Handle rename template description
    elif step == 26 and template:
        if len(text) > 100:
            response = "Sorry, please enter a shorter template description (maximum 100 characters)."
            edit_conversation_message(
                update, context, response,
                reply_markup=template.build_single_back_button(
                    f"{models.RENAME}_{models.TEMPLATE}_{models.DESCRIPTION}"
                )
            )
            return

        # Change template description
        template.description = text
        edit_conversation_message(
            update, context, f"Poll template description successfully changed to <b>{template.description}</b>",
            reply_markup=template.build_single_back_button(f"{models.EDIT}_{models.TEMPLATE}", "Continue")
        )

        # Clear user data
        context.user_data.clear()
        return
    # Handle add template description:
    elif step == 27 and template:
        if len(text) > 50:
            response = "Sorry, please enter a shorter template description (maximum 50 characters)."
            edit_conversation_message(
                update, context, response,
                reply_markup=template.build_single_back_button(
                    f"{models.ADD}_{models.TEMPLATE}_{models.DESCRIPTION}"
                )
            )
            return

        # Change template description
        template.description = text
        edit_conversation_message(
            update, context, f"Poll template description successfully set to <b>{template.description}</b>",
            reply_markup=template.build_single_back_button(f"{models.EDIT}_{models.TEMPLATE}", "Continue")
        )

        # Clear user data
        context.user_data.clear()
        return
    # Handle invalid step
    else:
        logger.warning("Error with preset poll conversation step index!!")
        context.user_data.clear()
        handle_help(update, context)
        return


def handle_temp_list_conversation(update: Update, context: CallbackContext) -> None:
    """Handles the conversation between the bot and the user to create a poll template."""
    delete_chat_message(update.message)
    delete_old_chat_message(update, context)

    user, _, _ = get_user_permissions(update.effective_user.id)

    text = util.strip_html_symbols(update.message.text.strip())
    step, title, description, options, choices, name, temp_id = \
        context.user_data.get("step", 1), context.user_data.get("title", ""), context.user_data.get("descr", ""), \
        context.user_data.get("options", []), context.user_data.get("choices", []), \
        context.user_data.get("name", ""), context.user_data.get("tempId", "")

    template: ListTemplate = ListTemplate.get_template_by_id(temp_id)

    # Handle title
    if step == 1:
        text = text.replace("\n", " ").strip()
        if len(text) > MAX_TITLE_LENGTH:
            edit_conversation_message(
                update, context, ERROR_TITLE_TOO_LONG,
                reply_markup=util.build_single_button_markup("Cancel", models.RESET)
            )
            return

        format_text, format_codes, is_valid = FormatTextCode.parse_format_text(text)

        if not is_valid:
            response = f"{text}\n\n{format_text}\n\nPlease re-enter the <b>title format</b>."
            edit_conversation_message(
                update, context, response, reply_markup=util.build_single_button_markup("Cancel", models.RESET)
            )
            return

        header = f"<b>List Title Format</b>"
        format_text_code = FormatTextCode(format_text, format_codes)
        body = format_text_code.render_details()
        footer = f"<b>Continue</b> to the next step or re-enter the title format to make changes."
        response = "\n\n".join([f"{header}\n{body}"] + [footer])

        edit_conversation_message(
            update, context, response, reply_markup=build_progress_buttons(next_text="Continue")
        )
        context.user_data.update({"title": text})
        return
    # Handle description
    elif step == 2 and title:
        format_text, format_codes, is_valid = FormatTextCode.parse_format_text(text)

        if not is_valid:
            response = f"{text}\n\n{format_text}\n\nPlease re-enter the <b>description format</b>."
            edit_conversation_message(
                update, context, response, reply_markup=util.build_single_button_markup("Cancel", models.RESET)
            )
            return

        header = f"<b>Description Format</b>"
        format_text_code = FormatTextCode(format_text, format_codes)
        body = format_text_code.render_details()
        footer = f"<b>Continue</b> to the next step or re-enter the description format to make changes."
        response = "\n\n".join([f"{header}\n{body}"] + [footer])

        edit_conversation_message(
            update, context, response, reply_markup=build_progress_buttons(next_text="Continue")
        )
        context.user_data.update({"descr": text})
        return
    # Handle option
    elif step == 3 and title and description:
        if not options:
            buttons = util.build_single_button_markup("Cancel", models.RESET)
        else:
            buttons = build_progress_buttons()

        if len(text) > MAX_OPTION_TITLE_LENGTH:
            edit_conversation_message(
                update, context, ERROR_OPTION_TITLE_TOO_LONG, reply_markup=buttons
            )
            return

        if text in options:
            edit_conversation_message(
                update, context, ERROR_DUPLICATE_OPTION_TITLE.format(util.list_to_indexed_list_string(options)),
                reply_markup=buttons
            )
            return

        options.append(text)
        context.user_data.update({"options": options})

        if len(options) >= MAX_OPTIONS:
            response_text = f"You have a maximum of {MAX_OPTIONS} options already!\n\n" \
                            f"{util.list_to_indexed_list_string(options)}\n\n" \
                            f"Press <b>Done</b> to go to the next step."
            edit_conversation_message(update, context, response_text, reply_markup=buttons)
            return

        edit_conversation_message(
            update, context,
            NEXT_LIST_OPTION.format(f"<b>{text}</b>", util.list_to_indexed_list_string(options)),
            reply_markup=build_progress_buttons()
        )
        return
    # Handle choice
    elif step == 4 and title and description and options:
        if not choices:
            buttons = util.build_single_button_markup("Cancel", models.RESET)
        else:
            buttons = build_progress_buttons()

        if len(text) > MAX_CHOICE_ITEM_NAME_LENGTH:
            edit_conversation_message(
                update, context, ERROR_CHOICE_NAME_TOO_LONG, reply_markup=error_buttons
            )
            return

        if text in choices:
            edit_conversation_message(
                update, context, ERROR_DUPLICATE_CHOICE_NAME.format(util.list_to_indexed_list_string(choices)),
                reply_markup=buttons
            )
            return

        choices.append(text)
        context.user_data.update({"choices": choices})

        edit_conversation_message(
            update, context,
            NEXT_LIST_CHOICE.format(f"<b>{text}</b>", util.list_to_indexed_list_string(choices)),
            reply_markup=build_progress_buttons()
        )
        return
    # Handle template name
    elif step == 6 and title and description and options and choices:
        name_match = re.match(r"^\w{1,12}$", text)
        if not name_match:
            response = "Sorry, please ensure that the <b>name</b> consists only a maximum of " \
                       "12 alphanumeric characters."
            edit_conversation_message(
                update, context, response, reply_markup=util.build_single_button_markup("Cancel", models.RESET)
            )
            return

        if user.has_temp_list_with_name(text):
            response = "Sorry, you already have a list template with the same name. Please enter a different name."
            edit_conversation_message(
                update, context, response, reply_markup=util.build_single_button_markup("Cancel", models.RESET)
            )
            return

        response = f"Your new list <b>template name</b> is\n<b>{text}</b>\n\n" \
                   f"<b>Continue</b> to the next step or re-enter another name for your template."
        edit_conversation_message(
            update, context, response, reply_markup=build_progress_buttons(next_text="Continue")
        )
        context.user_data.update({"name": text})
        return
    # Handle template description
    elif step == 7 and title and description and options and choices and name:
        text = text.replace("\n", " ").strip()
        if len(text) > 50:
            response = "Sorry, please enter a shorter <b>template description</b> (maximum 50 characters)."
            edit_conversation_message(
                update, context, response,
                reply_markup=build_progress_buttons(next_text="Skip")
            )
            return

        response = f"Your new list template <b>description</b> is\n<i>{text}</i>\n\n" \
                   f"<b>Create</b> the list template or re-enter another description for your template."
        edit_conversation_message(
            update, context, response, reply_markup=build_progress_buttons(next_text="Create")
        )
        context.user_data.update({"tempDescr": text})
        return
    # Handle format title
    elif step == 11 and template:
        title_text, is_valid = template.render_title(text)
        if not is_valid:
            edit_conversation_message(
                update, context, title_text, reply_markup=template.build_format_back_buttons(models.TEMP_TITLE)
            )
            return
        title = f"<b>Current List Title</b>\n<b>{title_text}</b>"
        body = f"Enter another format input to change the title or <b>Continue</b> to go to the next step."
        response = "\n\n".join([title] + [body])
        edit_conversation_message(update, context, response, reply_markup=template.build_format_title_buttons())
        context.user_data.update({"titleCode": text})
        return
    # Handle format description
    elif step == 12 and template:
        description_text, is_valid = template.render_description(text)
        if not is_valid:
            edit_conversation_message(
                update, context, description_text,
                reply_markup=template.build_format_back_buttons(models.TEMP_DESCRIPTION)
            )
            return
        title = f"<b>Current List Description</b>\n<i>{description_text}</i>"
        body = f"Enter another format input to change the description, or <b>Create</b> the list, " \
               f"or <b>Skip</b> to create the list without a description."
        response = "\n\n".join([title] + [body])
        edit_conversation_message(update, context, response, reply_markup=template.build_format_description_buttons())
        context.user_data.update({"descrCode": text})
        return
    # Handle rename title
    elif step == 21 and template:
        if len(text) > MAX_TITLE_LENGTH:
            edit_conversation_message(
                update, context, ERROR_TITLE_TOO_LONG,
                reply_markup=template.build_single_back_button(f"{models.RENAME}_{models.TITLE}")
            )
            return

        format_text, format_codes, is_valid = FormatTextCode.parse_format_text(text)

        if not is_valid:
            response = f"{text}\n\n{format_text}\n\nPlease re-enter the <b>title format</b>."
            edit_conversation_message(
                update, context, response,
                reply_markup=template.build_single_back_button(f"{models.RENAME}_{models.TITLE}")
            )
            return

        header = f"<b>List Title Format</b>"
        format_text_code = FormatTextCode(format_text, format_codes)
        body = format_text_code.render_details()
        footer = f"<b>Confirm</b> to change the title format or re-enter the title format to make changes."
        response = "\n\n".join([f"{header}\n{body}"] + [footer])

        edit_conversation_message(
            update, context, response,
            reply_markup=template.build_edit_confirm_buttons(f"{models.EDIT}_{models.TITLE}")
        )
        context.user_data.update({"title": text})
        return
    # Handle rename description
    elif step == 22 and template:
        format_text, format_codes, is_valid = FormatTextCode.parse_format_text(text)

        if not is_valid:
            response = f"{text}\n\n{format_text}\n\nPlease re-enter the <b>description format</b>."
            edit_conversation_message(
                update, context, response,
                reply_markup=template.build_single_back_button(f"{models.RENAME}_{models.DESCRIPTION}")
            )
            return

        header = f"<b>Description Format</b>"
        format_text_code = FormatTextCode(format_text, format_codes)
        body = format_text_code.render_details()
        footer = f"<b>Confirm</b> to change the description format or re-enter the description format to make changes."
        response = "\n\n".join([f"{header}\n{body}"] + [footer])

        edit_conversation_message(
            update, context, response,
            reply_markup=template.build_edit_confirm_buttons(f"{models.EDIT}_{models.DESCRIPTION}")
        )
        context.user_data.update({"descr": text})
        return
    # Handle add description
    elif step == 23 and template:
        format_text, format_codes, is_valid = FormatTextCode.parse_format_text(text)

        if not is_valid:
            response = f"{text}\n\n{format_text}\n\nPlease re-enter the <b>description format</b>."
            edit_conversation_message(
                update, context, response,
                reply_markup=template.build_single_back_button(f"{models.ADD}_{models.DESCRIPTION}")
            )
            return

        header = f"<b>Description Format</b>"
        format_text_code = FormatTextCode(format_text, format_codes)
        body = format_text_code.render_details()
        footer = f"<b>Confirm</b> to add the description format or re-enter the description format to make changes."
        response = "\n\n".join([f"{header}\n{body}"] + [footer])

        edit_conversation_message(
            update, context, response,
            reply_markup=template.build_edit_confirm_buttons(f"{models.EDIT}_{models.DESCRIPTION}")
        )
        context.user_data.update({"descr": text})
        return
    # Handle rename template name
    elif step == 25 and template:
        name_match = re.match(r"^\w{1,12}$", text)
        if not name_match:
            response = "Sorry, please ensure that the name consists only a maximum of 12 alphanumeric characters."
            edit_conversation_message(
                update, context, response,
                reply_markup=template.build_single_back_button(f"{models.RENAME}_{models.TEMPLATE}_{models.NAME}")
            )
            return

        if user.has_temp_list_with_name(text):
            response = "Sorry, you already have a list template with the same name. Please enter a different name."
            edit_conversation_message(
                update, context, response,
                reply_markup=template.build_single_back_button(f"{models.RENAME}_{models.TEMPLATE}_{models.NAME}")
            )
            return

        # Change template name
        template.name = text
        edit_conversation_message(
            update, context, f"List template name successfully changed to <b>{template.name}</b>",
            reply_markup=template.build_single_back_button(f"{models.EDIT}_{models.TEMPLATE}", "Continue")
        )

        # Clear user data
        context.user_data.clear()
        return
    # Handle rename template description
    elif step == 26 and template:
        text = text.replace("\n", " ").strip()
        if len(text) > 100:
            response = "Sorry, please enter a shorter template description (maximum 100 characters)."
            edit_conversation_message(
                update, context, response,
                reply_markup=template.build_single_back_button(
                    f"{models.RENAME}_{models.TEMPLATE}_{models.DESCRIPTION}"
                )
            )
            return

        # Change template description
        template.description = text
        edit_conversation_message(
            update, context, f"List template description successfully changed to <b>{template.description}</b>",
            reply_markup=template.build_single_back_button(f"{models.EDIT}_{models.TEMPLATE}", "Continue")
        )

        # Clear user data
        context.user_data.clear()
        return
    # Handle add template description:
    elif step == 27 and template:
        text = text.replace("\n", " ").strip()
        if len(text) > 50:
            response = "Sorry, please enter a shorter template description (maximum 50 characters)."
            edit_conversation_message(
                update, context, response,
                reply_markup=template.build_single_back_button(
                    f"{models.ADD}_{models.TEMPLATE}_{models.DESCRIPTION}"
                )
            )
            return

        # Change template description
        template.description = text
        edit_conversation_message(
            update, context, f"List template description successfully set to <b>{template.description}</b>",
            reply_markup=template.build_single_back_button(f"{models.EDIT}_{models.TEMPLATE}", "Continue")
        )

        # Clear user data
        context.user_data.clear()
        return
    # Handle invalid step
    else:
        logger.warning("Error with preset list conversation step index!!")
        context.user_data.clear()
        handle_help(update, context)
        return


# endregion

# region CALLBACK QUERY HANDLERS


def handle_callback_query(update: Update, context: CallbackContext) -> None:
    """Handles a callback query."""
    query = update.callback_query

    match = re.match(r"^(\w+)\s+(\w+)\s+(\w+)$", query.data)
    if not match:
        handle_general_callback_query(query, context, query.data)
        return

    subject, action, identifier = match.group(1), match.group(2), match.group(3)

    if subject == models.USER_SUBJECT:
        handle_user_callback_query(query, context, action, identifier)
        return
    elif subject == models.POLL_SUBJECT:
        handle_poll_callback_query(query, context, action, identifier)
        return
    elif subject == models.LIST_SUBJECT:
        handle_list_callback_query(query, context, action, identifier)
        return
    elif subject == models.GROUP_SUBJECT:
        handle_group_callback_query(query, context, action, identifier)
        return
    elif subject == models.TEMP_POLL_SUBJECT:
        handle_temp_poll_callback_query(query, context, action, identifier)
        return
    elif subject == models.TEMP_LIST_SUBJECT:
        handle_temp_list_callback_query(query, context, action, identifier)
        return
    else:
        logger.warning("Invalid callback query data.")
        query.answer(text="Invalid callback query data!")
        return


def handle_general_callback_query(query: CallbackQuery, context: CallbackContext, action: str) -> None:
    """Handles a general callback query."""
    user, is_leader, is_admin = get_user_permissions(query.from_user.id)

    # Handle bot access button
    if action == models.BOT_ACCESS and is_admin:
        query.answer(text=ACCESS_ENTER_USER_ID)
        reply_message = query.edit_message_text(
            ACCESS_ENTER_USER_ID, parse_mode=ParseMode.HTML,
            reply_markup=util.build_single_button_markup("Cancel", models.RESET)
        )
        context.user_data.update({"action": models.BOT_ACCESS, "ed": reply_message.message_id})
        return
    # Handle leader access button
    elif action == models.PROMOTE and is_admin:
        response, buttons = BotManager.build_leader_promote_invite_text_and_button()
        query.answer(response)
        query.edit_message_text(response, parse_mode=ParseMode.HTML, reply_markup=buttons)
        return
    # Handle done button
    elif action == models.DONE:
        user_action = context.user_data.get("action", "")
        handle_done_callback_query(query, context, user_action)
        return
    # Handle show command button
    elif action == models.SHOW:
        handle_show_command_callback_query(query, context)
        query.answer(text="Command keyboard shown!")
        return
    # Handle hide command button
    elif action == models.HIDE:
        query.message.delete()
        reply_message = query.message.reply_html("Hiding command keyboard...", reply_markup=ReplyKeyboardRemove())
        reply_message.delete()
        query.answer(text="Command keyboard hidden!")
        return
    # Handle close button
    elif action == models.CLOSE:
        query.message.delete()
        query.answer(text=None)
        return
    # Handle return button
    elif action == models.RETURN:
        query.answer(text="Returning to chat...")
        response = "Returning to chat..."
        reply_message = query.message.reply_html(
            response, reply_markup=util.build_single_switch_button_markup("Return To Chat", "")
        )
        context.user_data.clear()
        reply_message.delete()
        query.message.delete()
        return
    # Handle reset button
    elif action == models.RESET:
        query.message.delete()
        query.answer(text="Process cancelled.")
        context.user_data.clear()
        return
    # Handle preset button
    elif action == models.TEMPLATE:
        query.answer(text=None)
        response_text = "Which <b>template</b> do you want to create?"
        buttons = util.build_multiple_stacked_buttons_markup(
            [
                util.generate_button_details("Poll", models.TEMP_POLL),
                util.generate_button_details("List", models.TEMP_LIST)
            ],
            [util.generate_button_details("Preset Format Guide", models.TEMP_GUIDE)],
            [util.generate_button_details("Close", models.CLOSE)]
        )
        query.edit_message_text(response_text, parse_mode=ParseMode.HTML, reply_markup=buttons)
    # Handle preset poll button
    elif action == models.TEMP_POLL:
        context.user_data.update({"action": models.TEMP_POLL, "step": 1, "title": "", "descr": "", "options": []})
        response_text = "You're about to build a new <b>poll template</b>.\n\n" \
                        "First, enter a <b>title format</b> for the poll."
        reply_message = query.edit_message_text(
            response_text, parse_mode=ParseMode.HTML,
            reply_markup=util.build_multiple_buttons_markup(
                util.generate_button_details("Cancel", models.RESET)
            )
        )
        query.answer(text="Enter a format title for your poll template.")
        context.user_data.update({"ed": reply_message.message_id})
        return
    # Handle preset list button
    elif action == models.TEMP_LIST:
        context.user_data.update(
            {"action": models.TEMP_LIST, "step": 1, "title": "", "descr": "", "options": [], "choices": []}
        )
        response_text = "You're about to build a new <b>list template</b>.\n\n" \
                        "First, enter a <b>title format</b> for the list."
        reply_message = query.edit_message_text(
            response_text, parse_mode=ParseMode.HTML, reply_markup=util.build_multiple_buttons_markup(
                util.generate_button_details("Cancel", models.RESET)
            )
        )
        query.answer(text="Enter a title format for your list template.")
        context.user_data.update({"ed": reply_message.message_id})
        return
    # Handle preset format guide button
    elif action == models.TEMP_GUIDE:
        query.answer(text="Here's the preset format guide!")
        query.edit_message_text(
            generate_preset_format_guide(), parse_mode=ParseMode.HTML,
            reply_markup=util.build_single_button_markup("Back", models.TEMPLATE)
        )
        return
    # Handle response button
    elif action.startswith(f"{models.RESPONSE}_"):
        _, response_type = action.split("_", 1)
        if response_type == "single":
            is_single_response = True
            response = "Response type set to single response."
        elif response_type == "multiple":
            is_single_response = False
            response = "Response type set to multiple response."
        else:
            query.answer(text="Invalid callback query data in poll template response type!")
            logger.warning("Invalid callback query data.")
            return

        user_action, step = context.user_data.get("action", ""), context.user_data.get("step", 0)
        if user_action == models.TEMP_POLL and step == 4:
            response_text = "Now, enter a unique <b>name</b> for your template for reference."
            query.edit_message_text(
                response_text, parse_mode=ParseMode.HTML, reply_markup=util.build_multiple_buttons_markup(
                    util.generate_button_details("Cancel", models.RESET)
                )
            )
            query.answer(response)
            context.user_data.update({"step": 5, "response": is_single_response})
            return
        elif user_action == models.TEMP_LIST and step == 5:
            response_text = "Now, enter a unique <b>name</b> for your template for reference."
            query.edit_message_text(
                response_text, parse_mode=ParseMode.HTML, reply_markup=util.build_multiple_buttons_markup(
                    util.generate_button_details("Cancel", models.RESET)
                )
            )
            query.answer(response)
            context.user_data.update({"step": 6, "response": is_single_response})
            return
        else:
            query.answer(text="Invalid callback query data in poll template response type!")
            logger.warning("Invalid callback query data.")
            query.edit_message_reply_markup(None)
            query.message.delete()
            return
    # Handle other cases
    else:
        query.answer(text="Invalid callback query data!")
        logger.warning("Invalid callback query data.")
        return


def handle_done_callback_query(query: CallbackQuery, context: CallbackContext, action: str) -> None:
    """Handles done button callbacks."""
    user, _, _ = get_user_permissions(query.from_user.id)

    if not user:
        query.answer(text="Invalid callback query data!")
        logger.warning("Invalid callback query data.")
        query.edit_message_reply_markup(None)
        query.message.delete()
        return

    # Handle poll
    if action == models.POLL:
        step, title, description, options = \
            context.user_data.get("step", 1), context.user_data.get("title", ""), context.user_data.get("descr", ""), \
            context.user_data.get("options", [])

        if step == 1 and title:
            response = "Very nice! Now, send me a <b>description</b> for the poll or <b>Skip</b> this step."
            query.edit_message_text(
                response, parse_mode=ParseMode.HTML, reply_markup=build_progress_buttons(next_text="Skip")
            )
            query.answer(text="Enter a description for the poll.")
            context.user_data.update({"step": 2})
            return
        elif step == 2 and title:
            if not description:
                response = "Awesome! Now send me your very first <b>option</b>."
                context.user_data.update({"descr": " "})
            else:
                response = "Awesome, description added! Now send me your first <b>option</b>."

            query.edit_message_text(
                response, parse_mode=ParseMode.HTML,
                reply_markup=util.build_single_button_markup("Cancel", models.RESET)
            )
            query.answer(text="Enter your first option.")
            context.user_data.update({"step": 3})
            return
        elif step == 3 and title and description and options:
            # Create poll
            poll, _ = user.create_poll(title, description.strip(), options)

            query.edit_message_text(
                POLL_DONE, parse_mode=ParseMode.HTML,
                reply_markup=util.build_single_button_markup("Close", models.CLOSE)
            )
            query.message.reply_html(poll.render_text(), reply_markup=poll.build_admin_buttons())
            query.answer(text="Poll created successfully!")
            context.user_data.clear()
            return
        else:
            query.answer(text="Invalid callback query data!")
            logger.warning("Invalid callback query data.")
            query.edit_message_reply_markup(None)
            query.message.delete()
            return
    # Handle list
    elif action == models.LIST:
        step, title, description, options, choices = \
            context.user_data.get("step", 1), context.user_data.get("title", ""), context.user_data.get("descr", ""), \
            context.user_data.get("options", []), context.user_data.get("choices", [])

        if step == 1 and title:
            response = "Very nice! Now, send me a <b>description</b> for the list or <b>Skip</b> this step."
            query.edit_message_text(
                response, parse_mode=ParseMode.HTML, reply_markup=build_progress_buttons(next_text="Skip")
            )
            query.answer(text="Enter a description for the list.")
            context.user_data.update({"step": 2})
            return
        elif step == 2 and title:
            if not description:
                response = "Awesome! Now send me your very first <b>option</b>."
                context.user_data.update({"descr": " "})
            else:
                response = "Awesome, description added! Now send me your first <b>option</b>."

            query.edit_message_text(
                response, parse_mode=ParseMode.HTML,
                reply_markup=util.build_single_button_markup("Cancel", models.RESET)
            )
            query.answer(text="Enter your first option.")
            context.user_data.update({"step": 3})
            return
        elif step == 3 and title and description and options:
            response = "Okay, now send me your first <b>choice</b> item."
            query.edit_message_text(
                response, parse_mode=ParseMode.HTML,
                reply_markup=util.build_single_button_markup("Cancel", models.RESET)
            )
            query.answer(text="Enter your first choice item.")
            context.user_data.update({"step": 4})
            return
        elif step == 4 and title and description and options and choices:
            # Create list
            _list, _ = user.create_list(title, description.strip(), options, choices)

            query.edit_message_text(
                LIST_DONE, parse_mode=ParseMode.HTML,
                reply_markup=util.build_single_button_markup("Close", models.CLOSE)
            )
            query.message.reply_html(_list.render_text(), reply_markup=_list.build_admin_buttons())
            query.answer(text="List created successfully!")
            context.user_data.clear()
            return
        else:
            query.answer(text="Invalid callback query data!")
            logger.warning("Invalid callback query data.")
            query.edit_message_reply_markup(None)
            query.message.delete()
            return
    # Handle preset poll
    elif action == models.TEMP_POLL:
        step, title, description, options, single_response, name, temp_description = \
            context.user_data.get("step", 1), context.user_data.get("title", ""), context.user_data.get("descr", ""), \
            context.user_data.get("options", []), context.user_data.get("response", True), \
            context.user_data.get("name", ""), context.user_data.get("tempDescr", "")

        if step == 1 and title:
            response = "Wonderful! Now, send me a <b>description format</b> for the poll template " \
                       "or <b>Skip</b> this step."
            query.edit_message_text(
                response, parse_mode=ParseMode.HTML, reply_markup=build_progress_buttons(next_text="Skip")
            )
            query.answer(text="Enter a description format for the poll template.")
            context.user_data.update({"step": 2})
        elif step == 2 and title:
            if not description:
                response = "Awesome! Now send me your first <b>option</b>."
                context.user_data.update({"descr": " "})
            else:
                response = "Awesome, description format added! Now send me your first <b>option</b>."

            query.edit_message_text(
                response, parse_mode=ParseMode.HTML,
                reply_markup=util.build_single_button_markup("Close", models.CLOSE)
            )
            query.answer(text="Enter your first option.")
            context.user_data.update({"step": 3})
            return
        elif step == 3 and title and description and options:
            response_text = "Nice! Now choose the <b>response type</b> for your poll template."
            query.edit_message_text(
                response_text, parse_mode=ParseMode.HTML,
                reply_markup=util.build_multiple_stacked_buttons_markup(
                    [
                        util.generate_button_details("Single Response", f"{models.RESPONSE}_single"),
                        util.generate_button_details("Multiple Response", f"{models.RESPONSE}_multiple")
                    ], [util.generate_button_details("Cancel", models.RESET)]
                )
            )
            query.answer(text="Nice! Now choose the response type for your poll template.")
            context.user_data.update({"step": 4})
            return
        elif step == 5 and title and description and options and name:
            response = "Great! Now, send me a short <b>description</b> to describe your poll template " \
                       "or <b>Skip</b> this step."
            query.edit_message_text(
                response, parse_mode=ParseMode.HTML, reply_markup=build_progress_buttons(next_text="Skip")
            )
            query.answer(text="Enter a short description for the poll template.")
            context.user_data.update({"step": 6})
        elif step == 6 and title and description and options and name:
            poll_template, _ = user.create_temp_poll(
                name, temp_description.strip(), title, description.strip(), options, single_response
            )
            edit_conversation_message(
                update, context, f"Poll template created! You may now use this template to generate a new poll!",
                reply_markup=util.build_single_button_markup("Close", models.CLOSE)
            )
            query.message.reply_html(
                poll_template.render_text(),
                reply_markup=poll_template.build_main_buttons()
            )
            query.answer(text="Poll template created successfully!")
            context.user_data.clear()
            return
        else:
            query.answer(text="Invalid callback query data!")
            logger.warning("Invalid callback query data.")
            query.edit_message_reply_markup(None)
            query.message.delete()
            return
    # Handle preset list
    elif action == models.TEMP_LIST:
        step, title, description, options, choices, single_response, name, temp_description = \
            context.user_data.get("step", 1), context.user_data.get("title", ""), context.user_data.get("descr", ""), \
            context.user_data.get("options", []), context.user_data.get("choices", []), \
            context.user_data.get("response", True), context.user_data.get("name", ""), \
            context.user_data.get("tempDescr", "")

        if step == 1 and title:
            response = "Fantastic! Now, send me a <b>description format</b> for the list template " \
                       "or <b>Skip</b> this step."
            query.edit_message_text(
                response, parse_mode=ParseMode.HTML, reply_markup=build_progress_buttons(next_text="Skip")
            )
            query.answer(text="Enter a description format for the list template.")
            context.user_data.update({"step": 2})
        elif step == 2 and title:
            if not description:
                response = "Awesome! Now send me your first <b>option</b>."
                context.user_data.update({"descr": " "})
            else:
                response = "Awesome, description format added! Now send me your first <b>option</b>."

            query.edit_message_text(
                response, parse_mode=ParseMode.HTML,
                reply_markup=util.build_single_button_markup("Cancel", models.RESET)
            )
            query.answer(text="Enter your first option.")
            context.user_data.update({"step": 3})
            return
        elif step == 3 and title and description and options:
            response = "Very nice! Now send me your first <b>choice</b> item."

            query.edit_message_text(
                response, parse_mode=ParseMode.HTML,
                reply_markup=util.build_single_button_markup("Cancel", models.RESET)
            )
            query.answer(text="Enter your first choice item.")
            context.user_data.update({"step": 4})
            return
        elif step == 4 and title and description and options and choices:
            response_text = "Nice! Now choose the <b>response type</b> for your list template."
            query.edit_message_text(
                response_text, parse_mode=ParseMode.HTML,
                reply_markup=util.build_multiple_stacked_buttons_markup(
                    [
                        util.generate_button_details("Single Response", f"{models.RESPONSE}_single"),
                        util.generate_button_details("Multiple Response", f"{models.RESPONSE}_multiple")
                    ], [util.generate_button_details("Cancel", models.RESET)]
                )
            )
            query.answer(text="Nice! Now choose the response type for your list template.")
            context.user_data.update({"step": 5})
            return
        elif step == 6 and title and description and options and name:
            response = "Great! Now, send me a short <b>description</b> to describe your list template " \
                       "or <b>Skip</b> this step."
            query.edit_message_text(
                response, parse_mode=ParseMode.HTML, reply_markup=build_progress_buttons(next_text="Skip")
            )
            query.answer(text="Enter a short description for the list template.")
            context.user_data.update({"step": 7})
        elif step == 7 and title and description and options and name:
            list_template, _ = user.create_temp_list(
                name, temp_description.strip(), title, description.strip(), options, choices, single_response
            )
            response = f"\U0001f44d List template created! You may now use this template to generate a new list!"
            query.edit_message_text(
                response, parse_mode=ParseMode.HTML,
                reply_markup=util.build_single_button_markup("Close", models.CLOSE)
            )
            query.message.reply_html(list_template.render_text(), reply_markup=list_template.build_main_buttons())
            query.answer(text="List template created successfully!")
            context.user_data.clear()
            return
        else:
            query.answer(text="Invalid callback query data!")
            logger.warning("Invalid callback query data.")
            query.edit_message_reply_markup(None)
            query.message.delete()
            return
    # Handle group
    elif action == models.GROUP:
        step, group_name, secret = \
            context.user_data.get("step", 1), context.user_data.get("name", ""), context.user_data.get("secret", "")

        if step == 1 and group_name:
            response = "Great! Now, send me a secret <b>password</b> for the group or <b>Skip</b> this step."
            query.edit_message_text(
                response, parse_mode=ParseMode.HTML, reply_markup=build_progress_buttons(next_text="Skip")
            )
            query.answer(text="Enter a password for the group.")
            context.user_data.update({"step": 2})
            return
        elif step == 2 and group_name:
            # Create group
            group, _ = user.create_group(group_name, secret)

            query.edit_message_text(
                GROUP_DONE, parse_mode=ParseMode.HTML,
                reply_markup=util.build_single_button_markup("Close", models.CLOSE)
            )
            query.message.reply_html(group.render_group_details_text(), reply_markup=group.build_main_buttons())
            query.answer(text="Group created successfully!")
            context.user_data.clear()
            return
        else:
            query.answer(text="Invalid callback query data!")
            logger.warning("Invalid callback query data.")
            query.edit_message_reply_markup(None)
            query.message.delete()
            return
    # Handle other cases
    else:
        query.answer(text="Invalid callback query data!")
        logger.warning("Invalid callback query data.")
        query.edit_message_reply_markup(None)
        query.message.delete()
        return


def handle_show_command_callback_query(query: CallbackQuery, context: CallbackContext) -> None:
    """Shows the command keyboard to the user."""
    query.message.delete()
    user, is_leader, is_admin = get_user_permissions(query.from_user.id)

    if not user:
        buttons = util.build_multiple_stacked_keyboard_buttons_markup(
            [f"/{START_COMMAND}", f"/{KEYBOARD_COMMAND}", f"/{HELP_COMMAND}"]
        )
    elif is_admin:
        buttons = util.build_multiple_stacked_keyboard_buttons_markup(
            [f"/{START_COMMAND}", f"/{KEYBOARD_COMMAND}", f"/{HELP_COMMAND}"],
            [f"/{POLL_COMMAND}", f"/{POLLS_COMMAND}", f"/{LIST_COMMAND}"],
            [f"/{LISTS_COMMAND}", f"/{TEMPLATE_COMMAND}", f"/{TEMPLATES_COMMAND}"],
            [f"/{GROUP_COMMAND}", f"/{GROUPS_COMMAND}", f"/{GROUP_POLLS_COMMAND}"],
            [f"/{GROUP_LISTS_COMMAND}", f"/{GROUP_TEMPLATES_COMMAND}", f"/{INVITE_COMMAND}"],
            [f"/{ACCESS_COMMAND}", f"/{ENROL_COMMAND}", f"/{PROMOTE_COMMAND}"],
            [f"/{SAVE_COMMAND}", f"/{LOAD_COMMAND}", "."]
        )
    elif is_leader:
        buttons = util.build_multiple_stacked_keyboard_buttons_markup(
            [f"/{START_COMMAND}", f"/{KEYBOARD_COMMAND}", f"/{HELP_COMMAND}"],
            [f"/{POLL_COMMAND}", f"/{POLLS_COMMAND}", f"/{LIST_COMMAND}"],
            [f"/{LISTS_COMMAND}", f"/{TEMPLATE_COMMAND}", f"/{TEMPLATES_COMMAND}"],
            [f"/{GROUP_COMMAND}", f"/{GROUPS_COMMAND}", f"/{GROUP_POLLS_COMMAND}"],
            [f"/{GROUP_LISTS_COMMAND}", f"/{GROUP_TEMPLATES_COMMAND}", f"/{INVITE_COMMAND}"]
        )
    else:
        buttons = util.build_multiple_stacked_keyboard_buttons_markup(
            [f"/{START_COMMAND}", f"/{KEYBOARD_COMMAND}", f"/{HELP_COMMAND}"],
            [f"/{POLL_COMMAND}", f"/{POLLS_COMMAND}", f"/{LIST_COMMAND}"],
            [f"/{LISTS_COMMAND}", f"/{TEMPLATE_COMMAND}", f"/{TEMPLATES_COMMAND}"],
            [f"/{GROUPS_COMMAND}", f"/{GROUP_POLLS_COMMAND}", f"/{GROUP_LISTS_COMMAND}"],
            [f"/{GROUP_TEMPLATES_COMMAND}", f"/{INVITE_COMMAND}", "."]
        )

    reply_message = query.message.reply_html("Loading command keyboard...", reply_markup=ReplyKeyboardRemove())
    reply_message.delete()
    query.message.reply_html("Select a bot command 🔽", reply_markup=buttons)
    return


def handle_user_callback_query(query: CallbackQuery, context: CallbackContext, action: str, uid_string: str) -> None:
    """Handles a user callback query."""
    user = User.get_user_by_id(util.decode(uid_string))

    if not user:
        query.answer(text=ERROR_USER_NOT_FOUND)
        return

    message = query.message
    is_pm = is_private_chat(message)
    _, _, is_admin = get_user_permissions(query.from_user.id)

    # Handle promote button
    if action == models.PROMOTE and is_pm and is_admin:
        if user.is_leader():
            query.answer(text=ERROR_ALREADY_PROMOTED)
            return

        user.promote_to_leader()
        _, buttons = BotManager.build_leader_promote_invite_text_and_button()
        query.edit_message_reply_markup(buttons)
        query.answer(text=USER_PROMOTED.format(user.get_name()))
        return
    else:
        query.answer(text=None)
        return


def handle_poll_callback_query(query: CallbackQuery, context: CallbackContext, action: str, poll_id: str) -> None:
    """Handles a poll callback query."""
    poll = Poll.get_poll_by_id(poll_id)

    # Poll is deleted or has error
    if not poll:
        query.answer(text=DELETED_POLL)
        query.edit_message_reply_markup(None)
        query.message.delete()
        return

    uid, user_profile = extract_user_data(query.from_user)
    user, _, _ = get_user_permissions(uid)
    message = query.message
    is_pm = is_private_chat(message)
    is_creator = poll.get_creator_id() == uid

    # Handle poll option button
    if action.isdigit():
        status = poll.toggle(int(action), uid, user_profile)
        query.edit_message_text(poll.render_text(), parse_mode=ParseMode.HTML, reply_markup=poll.build_option_buttons())
        query.answer(text=status)
        refresh_polls(poll, context)
        return
    # Handle refresh option button
    elif action == models.REFRESH_OPT:
        query.answer(text="Results updated!")
        query.edit_message_text(poll.render_text(), parse_mode=ParseMode.HTML, reply_markup=poll.build_option_buttons())
        return
    # Handle refresh button
    elif action == models.REFRESH and is_pm:
        query.answer(text="Results updated!")
        query.edit_message_text(
            poll.render_text(), parse_mode=ParseMode.HTML, reply_markup=poll.build_admin_buttons()
        )
        return
    # Handle customise button
    elif action == models.SETTINGS and is_pm:
        query.edit_message_reply_markup(poll.build_settings_buttons(is_creator=is_creator))
        query.answer(text=None)
        return
    # Handle toggle response button
    elif action == models.RESPONSE and is_pm:
        status = poll.toggle_response_type()
        query.edit_message_reply_markup(poll.build_settings_buttons(is_creator=is_creator))
        query.answer(text=status)
        return
    # Handle enforce comments button
    elif action == models.COMMENT and is_pm:
        query.edit_message_reply_markup(poll.build_option_comment_required_buttons())
        query.answer(text=None)
        return
    # Handle toggle comments required button
    elif action.startswith(f"{models.COMMENT}_") and is_pm:
        _, opt_id = action.rsplit("_", 1)
        if not opt_id.isdigit():
            logger.warning("Invalid callback query data.")
            query.answer(text="Invalid callback query data!")
            return
        status = poll.toggle_comment_requirement(int(opt_id))
        query.edit_message_reply_markup(poll.build_option_comment_required_buttons())
        query.answer(text=status)
        refresh_polls(poll, context, only_buttons=True)
        return
    # Handle edit comment button
    elif action == models.EDIT_COMMENT:
        response, buttons = poll.build_option_comment_text_and_buttons(uid)
        query.edit_message_text(response, parse_mode=ParseMode.HTML, reply_markup=buttons)
        query.answer(text=None)
        context.user_data.clear()
        return
    # Handle edit comment choice button
    elif action.startswith(f"{models.EDIT_COMMENT}_") and is_pm:
        _, opt_id = action.rsplit("_", 1)
        if not opt_id.isdigit():
            logger.warning("Invalid callback query data.")
            query.answer(text="Invalid callback query data!")
            return

        opt_id = int(opt_id)

        if opt_id >= len(poll.get_options()):
            logger.warning("Invalid option selected from poll vote!")
            query.answer(text=ERROR_INVALID_POLL_OPTION_REQUEST)
            return

        option = poll.get_options()[opt_id]

        reply_message = query.edit_message_text(
            REASON.format(util.make_html_bold(option.get_title())), parse_mode=ParseMode.HTML,
            reply_markup=util.build_single_button_markup("Back", models.EDIT_COMMENT)
        )
        query.answer(text="Please enter a reason/comment for your selected option.")
        context.user_data.update(
            {"action": models.COMMENT, "pid": poll_id, "opt": opt_id, "ed": reply_message.message_id}
        )
        return
    # Handle delete button
    elif action == models.DELETE and is_pm and is_creator:
        query.edit_message_reply_markup(poll.build_delete_confirm_buttons(models.POLL, models.SETTINGS))
        query.answer(text="Confirm delete?")
        return
    # Handle delete confirmation button
    elif action == f"{models.DELETE_YES}_{models.POLL}" and is_pm and is_creator:
        user.delete_poll(poll_id)
        for mid in poll.get_message_details():
            try:
                context.bot.edit_message_text(
                    f"<b>{poll.get_title()}</b>\n<i>This poll has been <b>closed</b>.</i>",
                    inline_message_id=mid, parse_mode=ParseMode.HTML, reply_markup=None
                )
            except telegram.error.TelegramError:
                continue
        query.answer(text="Poll deleted!")
        query.edit_message_reply_markup(None)
        query.message.delete()
        return
    # Handle back button
    elif action == models.BACK and is_pm:
        query.edit_message_reply_markup(poll.build_admin_buttons())
        query.answer(text=None)
        return
    # Handle return to chat button
    elif action == models.RETURN and is_pm:
        query.answer("Returning to chat...")
        reply_message = query.message.reply_html(
            "Returning to chat...",
            reply_markup=util.build_single_switch_button_markup("Return To Chat", "")
        )
        context.user_data.clear()
        query.message.delete()
        reply_message.delete()
    # Handle close button
    elif action == models.CLOSE:
        query.answer(text=None)
        query.edit_message_reply_markup(None)
        query.message.delete()
        return
    # Handle other cases
    else:
        logger.warning("Invalid callback query data.")
        query.answer(text="Invalid callback query data!")
        query.edit_message_reply_markup(None)
        query.message.delete()
        return


def handle_list_callback_query(query: CallbackQuery, context: CallbackContext, action: str, list_id: str) -> None:
    """Handles a poll callback query."""
    _list = List.get_list_by_id(list_id)

    # List is deleted or has error
    if not _list:
        query.answer(text=DELETED_LIST)
        query.edit_message_reply_markup(None)
        query.message.delete()
        return

    uid = query.from_user.id
    user, _, _ = get_user_permissions(uid)
    message = query.message
    is_pm = is_private_chat(message)
    is_creator = _list.get_creator_id() == uid

    # Handle list options button
    if action == models.OPTIONS:
        query.answer(text=None)
        query.edit_message_text(
            _list.render_text(), parse_mode=ParseMode.HTML, reply_markup=_list.build_option_buttons()
        )
        return
    # Handle list option button
    elif action.startswith(f"{models.OPTION}_") and is_pm:
        match = re.match(f"{models.OPTION}_(\\d+)", action)
        if not match:
            logger.warning("Invalid callback query data.")
            query.answer(text="Invalid callback query data!")
            return

        opt_id = int(match.group(1))

        if not _list.is_valid_option(opt_id):
            logger.warning(f"Invalid option selected: {opt_id} in list {_list.get_list_id()}.")
            query.answer(text="Invalid option selected!")
            return

        option = _list.get_option(opt_id)
        query.edit_message_reply_markup(_list.build_choice_buttons(opt_id))
        query.answer(text=f"Select the names you want to pick for {option.get_title()}.")
        return
    # Handle list choice button
    elif action.startswith(f"{models.CHOICE}_") and is_pm:
        match = re.match(f"{models.CHOICE}_(\\d+)_(\\d+)", action)
        if not match:
            logger.warning("Invalid callback query data.")
            query.answer(text="Invalid callback query data!")
            return

        opt_id, choice_id = int(match.group(1)), int(match.group(2))

        if not _list.is_valid_option(opt_id):
            logger.warning(f"Invalid option selected: {opt_id} in list {_list.get_list_id()}.")
            query.answer(text="Invalid option selected!")
            return

        if not _list.is_valid_choice(choice_id):
            logger.warning(f"Invalid choice selected: {choice_id} in list {_list.get_list_id()}.")
            query.answer(text="Invalid choice selected!")
            return

        status = _list.toggle(opt_id, choice_id)
        query.edit_message_text(
            _list.render_text(), parse_mode=ParseMode.HTML, reply_markup=_list.build_choice_buttons(opt_id)
        )
        query.answer(text=status)
        refresh_lists(_list, context)
        return
    # Handle user refresh option button
    elif action == models.USER_REFRESH:
        query.answer(text="Results updated!")
        query.edit_message_text(
            _list.render_text(), parse_mode=ParseMode.HTML, reply_markup=_list.build_update_buttons()
        )
        return
    # Handle refresh option button
    elif action == models.REFRESH_OPT and is_pm:
        query.answer(text="Results updated!")
        query.edit_message_text(
            _list.render_text(), parse_mode=ParseMode.HTML, reply_markup=_list.build_option_buttons()
        )
        return
    # Handle admin refresh button
    elif action == models.REFRESH and is_pm:
        query.answer(text="Results updated!")
        query.edit_message_text(
            _list.render_text(), parse_mode=ParseMode.HTML, reply_markup=_list.build_admin_buttons()
        )
        return
    # Handle customise button
    elif action == models.SETTINGS and is_pm:
        query.edit_message_reply_markup(_list.build_settings_buttons(is_creator=is_creator))
        query.answer(text=None)
        return
    # Handle toggle response button
    elif action == models.RESPONSE and is_pm:
        status = _list.toggle_response_type()
        query.answer(text=status)
        query.edit_message_reply_markup(_list.build_settings_buttons(is_creator=is_creator))
        return
    # Handle delete button
    elif action == models.DELETE and is_pm and is_creator:
        query.edit_message_reply_markup(_list.build_delete_confirm_buttons(models.LIST, models.SETTINGS))
        query.answer(text="Confirm delete?")
        return
    # Handle delete confirmation button
    elif action == f"{models.DELETE_YES}_{models.LIST}" and is_pm and is_creator:
        user.delete_list(list_id)
        for mid in _list.get_message_details():
            try:
                context.bot.edit_message_text(
                    f"<b>{_list.get_title()}</b>\n<i>This list has been <b>closed</b>.</i>",
                    inline_message_id=mid, parse_mode=ParseMode.HTML, reply_markup=None
                )
            except telegram.error.TelegramError:
                continue
        query.answer(text="List deleted!")
        query.edit_message_reply_markup(None)
        query.message.delete()
        return
    # Handle back button
    elif action == models.BACK and is_pm:
        query.answer(text=None)
        query.edit_message_reply_markup(_list.build_admin_buttons())
        return
    # Handle return to chat button
    elif action == models.RETURN and is_pm:
        query.answer("Returning to chat...")
        reply_message = query.message.reply_html(
            "Returning to chat...",
            reply_markup=util.build_single_switch_button_markup("Return To Chat", "")
        )
        context.user_data.clear()
        query.message.delete()
        reply_message.delete()
    # Handle close button
    elif action == models.CLOSE:
        query.answer(text=None)
        query.edit_message_reply_markup(None)
        query.message.delete()
        return
    # Handle other cases
    else:
        logger.warning("Invalid callback query data.")
        query.answer(text="Invalid callback query data!")
        query.edit_message_reply_markup(None)
        query.message.delete()
        return


def handle_group_callback_query(query: CallbackQuery, context: CallbackContext, action: str, gid: str) -> None:
    """Handles a group callback query."""
    if not is_private_chat(query.message):
        logger.warning("Invalid callback query data - group message not in private chat")
        query.answer(text="Invalid callback query data!")
        query.edit_message_reply_markup(None)
        query.message.delete()
        return

    group = Group.get_group_by_id(gid)

    # Group is deleted or has error
    if not group:
        query.answer(text=DELETED_GROUP)
        query.edit_message_reply_markup(None)
        query.message.delete()
        return

    user, _, _ = get_user_permissions(query.from_user.id)
    is_owner = group.get_owner() == user.get_uid()

    # User is no longer in the group
    if user.get_uid() not in group.get_member_ids():
        query.answer(text="You are not a member of this group.")
        query.edit_message_reply_markup(None)
        query.message.delete()
        return

    # Handle view button
    if action == models.VIEW:
        query.edit_message_text(
            group.render_group_details_text(), parse_mode=ParseMode.HTML, reply_markup=group.build_view_buttons()
        )
        query.answer(text=None)
        return
    # Handle view members button
    elif action == models.MEMBER:
        query.edit_message_text(
            group.render_group_members_text(), parse_mode=ParseMode.HTML,
            reply_markup=group.build_view_members_buttons(is_owner=is_owner)
        )
        query.answer(text=None)
        return
    # Handle remove member button
    elif action == f"{models.DELETE}_{models.MEMBER}" and is_owner:
        query.edit_message_reply_markup(
            group.build_members_buttons(f"{models.DELETE}_{models.MEMBER}", back_action=models.MEMBER)
        )
        query.answer(text="Select a member to remove.")
        return
    # Handle remove member choice button
    elif action.startswith(f"{models.DELETE}_{models.MEMBER}_") and is_owner:
        _, uid = action.rsplit("_", 1)
        member_name = User.get_user_by_id(uid).get_name()
        query.edit_message_reply_markup(
            group.build_delete_confirm_buttons(action, f"{models.MEMBER}_{uid}", delete_text="Remove")
        )
        query.answer(text=f"Confirm remove {member_name} from the group?")
        return
    # Handle remove member confirm button
    elif action.startswith(f"{models.DELETE_YES}_{models.MEMBER}_") and is_owner:
        _, uid = action.rsplit("_", 1)
        status = group.remove_member(uid)
        query.answer(text=status)
        query.edit_message_text(
            group.render_group_members_text(), parse_mode=ParseMode.HTML,
            reply_markup=group.build_members_buttons(f"{models.DELETE}_{models.MEMBER}", back_action=models.MEMBER)
        )
        return
    # Handle view group polls button
    elif action == models.POLL:
        query.edit_message_text(
            group.render_group_polls_text(), parse_mode=ParseMode.HTML,
            reply_markup=group.build_view_polls_buttons(user.get_polls(), is_owner=is_owner)
        )
        query.answer(text=None)
        return
    # Handle add poll button
    elif action == f"{models.ADD}_{models.POLL}":
        user_polls = user.get_polls()
        if user_polls:
            response = "Select a poll to add to the group."
        else:
            response = "You do not have any polls! Use /poll to create new poll."
        query.edit_message_reply_markup(group.build_add_polls_buttons(user_polls))
        query.answer(text=response)
        return
    # Handle add poll choice button
    elif action.startswith(f"{models.ADD}_{models.POLL}_"):
        _, poll_id = action.rsplit("_", 1)
        poll = Poll.get_poll_by_id(poll_id)
        if not poll:
            query.answer(text="Poll does not exist.")
            return

        response = group.add_poll(poll_id)
        query.answer(text=response)
        query.edit_message_text(
            group.render_group_polls_text(), parse_mode=ParseMode.HTML,
            reply_markup=group.build_add_polls_buttons(user.get_polls())
        )
        return
    # Handle remove poll button
    elif action == f"{models.DELETE}_{models.POLL}":
        user_polls = user.get_polls()
        query.edit_message_reply_markup(group.build_remove_polls_buttons(user_polls, is_owner=is_owner))
        query.answer(text="Select a poll to remove from the group.")
        return
    # Handle remove poll choice button
    elif action.startswith(f"{models.DELETE}_{models.POLL}_"):
        _, poll_id = action.rsplit("_", 1)
        poll = Poll.get_poll_by_id(poll_id)
        if not poll:
            query.answer(text="Poll does not exist.")
            return

        query.edit_message_reply_markup(
            group.build_delete_confirm_buttons(
                f"{models.POLL}_{poll_id}", f"{models.DELETE}_{models.POLL}", delete_text="Remove"
            )
        )
        query.answer(text=f"Confirm remove \"{poll.get_title()}\" from the group?")
        return
    # Handle remove poll confirm button
    elif action.startswith(f"{models.DELETE_YES}_{models.POLL}_"):
        _, poll_id = action.rsplit("_", 1)
        poll = Poll.get_poll_by_id(poll_id)
        if not poll:
            query.answer(text="Poll does not exist.")
            return

        response = group.remove_poll(poll_id)
        query.answer(text=response)
        query.edit_message_text(
            group.render_group_polls_text(), parse_mode=ParseMode.HTML,
            reply_markup=group.build_remove_polls_buttons(user.get_polls(), is_owner=is_owner)
        )
        return
    # Handle view group lists button
    elif action == models.LIST:
        query.edit_message_text(
            group.render_group_lists_text(), parse_mode=ParseMode.HTML,
            reply_markup=group.build_view_lists_buttons(user.get_lists(), is_owner=is_owner)
        )
        query.answer(text=None)
        return
    # Handle add list button
    elif action == f"{models.ADD}_{models.LIST}":
        user_lists = user.get_lists()
        if user_lists:
            response = "Select a list to add to the group."
        else:
            response = "You do not have any lists! Use /list to create new list."
        query.edit_message_reply_markup(group.build_add_lists_buttons(user_lists))
        query.answer(text=response)
        return
    # Handle add list choice button
    elif action.startswith(f"{models.ADD}_{models.LIST}_"):
        _, list_id = action.rsplit("_", 1)
        _list = List.get_list_by_id(list_id)
        if not _list:
            query.answer(text="List does not exist.")
            return

        response = group.add_list(list_id)
        query.answer(text=response)
        query.edit_message_text(
            group.render_group_lists_text(), parse_mode=ParseMode.HTML,
            reply_markup=group.build_add_lists_buttons(user.get_lists())
        )
        return
    # Handle remove list button
    elif action == f"{models.DELETE}_{models.LIST}":
        user_lists = user.get_lists()
        query.edit_message_reply_markup(group.build_remove_lists_buttons(user_lists, is_owner=is_owner))
        query.answer(text="Select a list to remove from the group.")
        return
    # Handle remove list choice button
    elif action.startswith(f"{models.DELETE}_{models.LIST}_"):
        _, list_id = action.rsplit("_", 1)
        _list = List.get_list_by_id(list_id)
        if not _list:
            query.answer(text="List does not exist.")
            return

        query.edit_message_reply_markup(
            group.build_delete_confirm_buttons(
                f"{models.LIST}_{list_id}", f"{models.DELETE}_{models.LIST}", delete_text="Remove"
            )
        )
        query.answer(text=f"Confirm remove \"{_list.get_title()}\" from the group?")
        return
    # Handle remove list confirm button
    elif action.startswith(f"{models.DELETE_YES}_{models.LIST}_"):
        _, list_id = action.rsplit("_", 1)
        _list = List.get_list_by_id(list_id)
        if not _list:
            query.answer(text="List does not exist.")
            return

        response = group.remove_list(list_id)
        query.answer(text=response)
        query.edit_message_text(
            group.render_group_lists_text(), parse_mode=ParseMode.HTML,
            reply_markup=group.build_remove_lists_buttons(user.get_lists(), is_owner=is_owner)
        )
        return
    # Handle view group templates button
    elif action == models.TEMPLATE:
        query.edit_message_text(
            group.render_group_templates_text(), parse_mode=ParseMode.HTML,
            reply_markup=group.build_view_templates_buttons(user.get_templates(), is_owner=is_owner)
        )
        query.answer(text=None)
        return
    # Handle add template button
    elif action == f"{models.ADD}_{models.TEMPLATE}":
        user_templates = user.get_templates()
        if user_templates:
            response = "Select a template to add to the group."
        else:
            response = "You do not have any templates! Use /temp to create new template."
        query.edit_message_reply_markup(group.build_add_templates_buttons(user_templates))
        query.answer(text=response)
        return
    # Handle add template choice button
    elif action.startswith(f"{models.ADD}_{models.TEMPLATE}_"):
        _, template_id = action.rsplit("_", 1)
        template = Template.get_template_by_id(template_id)
        if not template:
            query.answer(text="Template does not exist.")
            return

        response = group.add_template(template_id)
        query.answer(text=response)
        query.edit_message_text(
            group.render_group_templates_text(), parse_mode=ParseMode.HTML,
            reply_markup=group.build_add_templates_buttons(user.get_templates())
        )
        return
    # Handle remove template button
    elif action == f"{models.DELETE}_{models.TEMPLATE}":
        user_templates = user.get_templates()
        query.edit_message_reply_markup(group.build_remove_templates_buttons(user_templates, is_owner=is_owner))
        query.answer(text="Select a template to remove from the group.")
        return
    # Handle remove template choice button
    elif action.startswith(f"{models.DELETE}_{models.TEMPLATE}_"):
        _, temp_id = action.rsplit("_", 1)
        template = Template.get_template_by_id(temp_id)
        if not template:
            query.answer(text="Template does not exist.")
            return

        query.edit_message_reply_markup(
            group.build_delete_confirm_buttons(
                f"{models.TEMPLATE}_{temp_id}", f"{models.DELETE}_{models.TEMPLATE}", delete_text="Remove"
            )
        )
        query.answer(text=f"Confirm remove \"{template.name}\" from the group?")
        return
    # Handle remove template confirm button
    elif action.startswith(f"{models.DELETE_YES}_{models.TEMPLATE}_"):
        _, temp_id = action.rsplit("_", 1)
        template = Template.get_template_by_id(temp_id)
        if not template:
            query.answer(text="Template does not exist.")
            return

        response = group.remove_template(temp_id)
        query.answer(text=response)
        query.edit_message_text(
            group.render_group_templates_text(), parse_mode=ParseMode.HTML,
            reply_markup=group.build_remove_templates_buttons(user.get_templates(), is_owner=is_owner)
        )
        return
    # Handle settings button
    elif action == models.SETTINGS:
        query.edit_message_text(
            group.render_group_details_text(), parse_mode=ParseMode.HTML,
            reply_markup=group.build_settings_buttons(is_owner=is_owner)
        )
        query.answer(text=None)
        context.user_data.clear()
        return
    # Handle change name button
    elif action == f"{models.RENAME}_{models.NAME}" and is_owner:
        reply_message = query.edit_message_text(
            "Enter a new <b>name</b> for your group.", parse_mode=ParseMode.HTML,
            reply_markup=group.build_single_back_button(models.SETTINGS)
        )
        query.answer(text="Enter a new group name.")
        context.user_data.update({"action": models.GROUP, "step": 10, "gid": gid, "ed": reply_message.message_id})
        return
    # Handle change password button
    elif action == models.SECRET and is_owner:
        reply_message = query.edit_message_text(
            "Enter a new <b>secret password</b> for your group.", parse_mode=ParseMode.HTML,
            reply_markup=group.build_single_back_button(models.SETTINGS)
        )
        query.answer(text="Enter a new secret password.")
        context.user_data.update({"action": models.GROUP, "step": 11, "gid": gid, "ed": reply_message.message_id})
        return
    # Handle delete group button
    elif action == models.DELETE and is_owner:
        query.edit_message_reply_markup(group.build_delete_confirm_buttons(models.GROUP, models.SETTINGS))
        query.answer(text="Confirm delete group?")
    # Handle delete confirm button
    elif action == f"{models.DELETE_YES}_{models.GROUP}" and is_owner:
        status = user.delete_group(gid)
        query.answer(text=status)
        query.edit_message_reply_markup(None)
        query.message.delete()
        return
    # Handle leave group button
    elif action == models.LEAVE_GROUP and not is_owner:
        query.edit_message_reply_markup(
            group.build_delete_confirm_buttons(models.LEAVE_GROUP, models.SETTINGS, delete_text="Leave")
        )
        query.answer(text="Confirm leave group?")
        return
    # Handle confirm leave group button
    elif action == f"{models.DELETE_YES}_{models.LEAVE_GROUP}" and not is_owner:
        group.remove_member(user.get_uid())
        query.answer(text="You have left the group.")
        query.edit_message_reply_markup(None)
        query.message.delete()
        return
    # Handle refresh button
    elif action == models.REFRESH:
        query.answer(text="Group details updated!")
        query.edit_message_text(
            group.render_group_details_text(), parse_mode=ParseMode.HTML, reply_markup=group.build_main_buttons()
        )
        return
    # Handle back button
    elif action == models.BACK:
        query.edit_message_text(
            group.render_group_details_text(), parse_mode=ParseMode.HTML, reply_markup=group.build_main_buttons()
        )
        query.answer(text=None)
        return
    # Handle close button
    elif action == models.CLOSE:
        query.answer(text=None)
        query.edit_message_reply_markup(None)
        query.message.delete()
        return
    # Handle other cases
    else:
        logger.warning("Invalid callback query data.")
        query.answer(text="Invalid callback query data!")
        query.edit_message_reply_markup(None)
        query.message.delete()
        return


def handle_temp_poll_callback_query(query: CallbackQuery, context: CallbackContext, action: str, temp_id: str) -> None:
    """Handles a poll template callback query."""
    template: PollTemplate = PollTemplate.get_template_by_id(temp_id)

    # Poll is deleted or has error
    if not template:
        query.answer(text="Sorry, the poll template has been deleted.")
        query.edit_message_reply_markup(None)
        query.message.delete()
        return

    user, _, _ = get_user_permissions(query.from_user.id)
    message = query.message
    is_creator = template.creator_id == user.get_uid()

    user_action, step, title, title_code, description, description_code, context_id = \
        context.user_data.get("action", ""), context.user_data.get("step", 0), context.user_data.get("title", ""), \
        context.user_data.get("titleCode", ""), context.user_data.get("descr", ""), \
        context.user_data.get("descrCode", ""), context.user_data.get("tempId", "")

    if user_action != models.TEMP_POLL or context_id != temp_id:
        step, title, title_code, description, description_code = 0, "", "", "", ""

    # Handle generate poll button
    if action == models.POLL:
        title_text, is_valid = template.render_title()
        if not is_valid:
            message.reply_html(title_text, reply_markup=template.build_format_back_buttons(models.TEMP_TITLE))
            query.answer(text="Error parsing title format.")
            return
        title = f"<b>Current Poll Title</b>\n<b>{title_text}</b>"
        body = f"Enter another format input to change the title or <b>Continue</b> to go to the next step."
        response = "\n\n".join([title] + [body])
        reply_message = message.reply_html(response, reply_markup=template.build_format_title_buttons())
        query.answer(text="Change the title or continue to the next step.")
        context.user_data.update(
            {"action": models.TEMP_POLL, "step": 11, "title": title_text, "ed": reply_message.message_id,
             "tempId": template.temp_id}
        )
        return
    # Handle format title button
    elif action == models.TEMP_TITLE:
        title_text, is_valid = template.render_title(title_code)
        if not is_valid:
            message.edit_text(
                title_text, parse_mode=ParseMode.HTML,
                reply_markup=template.build_format_back_buttons(models.TEMP_TITLE)
            )
            query.answer(text="Error parsing title format.")
            return
        title = f"<b>Current Poll Title</b>\n<b>{title_text}</b>"
        body = f"Enter another format input to change the title or <b>Continue</b> to go to the next step."
        response = "\n\n".join([title] + [body])
        message.edit_text(
            response, parse_mode=ParseMode.HTML, reply_markup=template.build_format_title_buttons()
        )
        query.answer(text=None)
        return
    # Handle format title code button
    elif action == models.TEMP_TITLE_CODE:
        response = template.render_title_code()
        message.edit_text(
            response, parse_mode=ParseMode.HTML, reply_markup=template.build_format_back_buttons(models.TEMP_TITLE)
        )
        query.answer(text=None)
        return
    # Handle format description button
    elif action == models.TEMP_DESCRIPTION and title:
        descr_text, is_valid = template.render_description(description_code)
        if not is_valid:
            message.edit_text(
                descr_text, parse_mode=ParseMode.HTML,
                reply_markup=template.build_format_back_buttons(models.TEMP_DESCRIPTION)
            )
            query.answer(text="Error parsing description format.")
            return
        title = f"<b>Current Poll Description</b>\n<i>{descr_text}</i>"
        body = f"Enter another format input to change the description, or <b>Create</b> the poll, " \
               f"or <b>Skip</b> to create the poll without a description."
        response = "\n\n".join([title] + [body])
        message.edit_text(
            response, parse_mode=ParseMode.HTML, reply_markup=template.build_format_description_buttons()
        )
        query.answer(text=None)
        return
    # Handle format description code button
    elif action == models.TEMP_DESCRIPTION_CODE:
        response = template.render_description_code()
        message.edit_text(
            response, parse_mode=ParseMode.HTML,
            reply_markup=template.build_format_back_buttons(models.TEMP_DESCRIPTION)
        )
        query.answer(text=None)
        return
    # Handle skip button
    elif action == models.SKIP and title:
        poll = user.create_poll_from_template(temp_id, title, "")
        message.edit_text(
            POLL_DONE, parse_mode=ParseMode.HTML, reply_markup=util.build_single_button_markup("Close", models.CLOSE)
        )
        message.reply_html(poll.render_text(), reply_markup=poll.build_admin_buttons())
        context.user_data.clear()
        return
    # Handle done button
    elif action == models.DONE:
        if step == 11 and title:
            descr_text, is_valid = template.render_description(description_code)
            if not is_valid:
                message.edit_text(
                    descr_text, parse_mode=ParseMode.HTML,
                    reply_markup=template.build_format_back_buttons(models.TEMP_DESCRIPTION)
                )
                query.answer(text="Error parsing description format.")
                context.user_data.update({"step": 12})
                return
            title = f"<b>Current Poll Description</b>\n<i>{descr_text}</i>"
            body = f"Enter another format input to change the description, or <b>Create</b> the poll, " \
                   f"or <b>Skip</b> to create the poll without a description."
            response = "\n\n".join([title] + [body])
            message.edit_text(
                response, parse_mode=ParseMode.HTML, reply_markup=template.build_format_description_buttons()
            )
            query.answer(text="Change the description, skip, or create the poll.")
            context.user_data.update({"step": 12, "descr": descr_text})
            return
        elif step == 12 and title:
            poll = user.create_poll_from_template(temp_id, title, description)
            query.edit_message_text(
                POLL_DONE, parse_mode=ParseMode.HTML,
                reply_markup=util.build_single_button_markup("Close", models.CLOSE)
            )
            message.reply_html(poll.render_text(), reply_markup=poll.build_admin_buttons())
            query.answer(text="Poll created successfully!")
            context.user_data.clear()
            return
        elif step == 21 and title:
            template.title_format = title
            query.edit_message_text(
                template.render_description_code("Current Title Format"), parse_mode=ParseMode.HTML,
                reply_markup=template.build_edit_title_buttons()
            )
            query.answer(text="Title format changed successfully!")
            context.user_data.clear()
            return
        elif step == 22 and description:
            template.description_format = description
            query.edit_message_text(
                template.render_description_code("Current Description Format"), parse_mode=ParseMode.HTML,
                reply_markup=template.build_edit_description_buttons()
            )
            query.answer(text="Description format changed successfully!")
            context.user_data.clear()
            return
        elif step == 23 and description:
            template.description_format = description
            query.edit_message_text(
                template.render_description_code("Current Description Format"), parse_mode=ParseMode.HTML,
                reply_markup=template.build_edit_description_buttons()
            )
            query.answer(text="Description format added successfully!")
            context.user_data.clear()
            return
        else:
            logger.warning("Invalid callback query data.")
            query.answer(text="Invalid callback query data!")
            message.edit_reply_markup(None)
            message.delete()
            context.user_data.clear()
            return
    # Handle refresh button
    elif action == models.REFRESH:
        query.answer(text="Results updated!")
        query.edit_message_text(
            template.render_text(), parse_mode=ParseMode.HTML, reply_markup=template.build_main_buttons()
        )
        return
    # Handle settings button
    elif action == models.SETTINGS:
        query.edit_message_text(
            template.render_text(), parse_mode=ParseMode.HTML,
            reply_markup=template.build_settings_buttons(is_creator=is_creator)
        )
        query.answer(text=None)
        return
    # Handle delete template button
    elif action == models.DELETE and is_creator:
        query.edit_message_reply_markup(
            template.build_delete_confirm_buttons(models.TEMPLATE, models.SETTINGS)
        )
        query.answer(text="Confirm delete?")
        return
    # Handle edit template details button
    elif action == f"{models.EDIT}_{models.TEMPLATE}":
        template_name = f"<b>Template Name</b>\n<b>{template.name}</b>"
        template_description = f"<b>Template Description</b>\n<i>{template.description or 'None'}</i>"
        query.edit_message_text(
            f"{template_name}\n\n{template_description}", parse_mode=ParseMode.HTML,
            reply_markup=template.build_edit_template_details_buttons()
        )
        query.answer(text=None)
        context.user_data.clear()
        return
    # Handle rename template button
    elif action == f"{models.RENAME}_{models.TEMPLATE}_{models.NAME}":
        template_name = f"<b>Template Name</b>\n<b>{template.name}</b>"
        template_description = f"<b>Template Description</b>\n<i>{template.description or 'None'}</i>"
        response = f"{template_name}\n\n{template_description}\n\nEnter a new <b>template name</b>."
        reply_message = query.edit_message_text(
            response, parse_mode=ParseMode.HTML,
            reply_markup=template.build_single_back_button(f"{models.EDIT}_{models.TEMPLATE}")
        )
        query.answer(text="Enter a new template name.")
        context.user_data.update(
            {"action": models.TEMP_POLL, "step": 25, "tempId": template.temp_id, "ed": reply_message.message_id}
        )
        return
    # Handle rename template description button
    elif action == f"{models.RENAME}_{models.TEMPLATE}_{models.DESCRIPTION}":
        template_name = f"<b>Template Name</b>\n<b>{template.name}</b>"
        template_description = f"<b>Template Description</b>\n<i>{template.description or 'None'}</i>"
        response = f"{template_name}\n\n{template_description}\n\nEnter a new <b>template description</b>."
        reply_message = query.edit_message_text(
            response, parse_mode=ParseMode.HTML,
            reply_markup=template.build_single_back_button(f"{models.EDIT}_{models.TEMPLATE}")
        )
        query.answer(text="Enter a new template description.")
        context.user_data.update(
            {"action": models.TEMP_POLL, "step": 26, "tempId": template.temp_id, "ed": reply_message.message_id}
        )
        return
    # Handle remove template description button
    elif action == f"{models.DELETE}_{models.TEMPLATE}_{models.DESCRIPTION}":
        query.edit_message_reply_markup(template.build_delete_confirm_buttons(
            f"{models.TEMPLATE}_{models.DESCRIPTION}", f"{models.EDIT}_{models.TEMPLATE}", delete_text="Remove")
        )
        query.answer(text="Confirm remove?")
        return
    # Handle add template description button
    elif action == f"{models.ADD}_{models.TEMPLATE}_{models.DESCRIPTION}":
        template_name = f"<b>Template Name</b>\n<b>{template.name}</b>"
        template_description = f"<b>Template Description</b>\n<i>{template.description or 'None'}</i>"
        response = f"{template_name}\n\n{template_description}\n\nEnter a new <b>template description</b>."
        reply_message = query.edit_message_text(
            response, parse_mode=ParseMode.HTML,
            reply_markup=template.build_single_back_button(f"{models.EDIT}_{models.TEMPLATE}")
        )
        query.answer(text="Enter a new template description.")
        context.user_data.update(
            {"action": models.TEMP_POLL, "step": 27, "tempId": template.temp_id, "ed": reply_message.message_id}
        )
        return
    # Handle edit title button
    elif action == f"{models.EDIT}_{models.TITLE}":
        query.edit_message_text(
            template.render_title_code("Current Title Format"), parse_mode=ParseMode.HTML,
            reply_markup=template.build_edit_title_buttons()
        )
        query.answer(text=None)
        context.user_data.clear()
        return
    # Handle edit description button
    elif action == f"{models.EDIT}_{models.DESCRIPTION}":
        query.edit_message_text(
            template.render_description_code("Current Description Format"), parse_mode=ParseMode.HTML,
            reply_markup=template.build_edit_description_buttons()
        )
        query.answer(text=None)
        context.user_data.clear()
        return
    # Handle edit options button
    elif action == f"{models.EDIT}_{models.OPTIONS}":
        query.answer(text="Sorry, this feature has not been implemented yet.")
        return
    # Handle toggle response button
    elif action == f"{models.EDIT}_{models.RESPONSE}":
        status = template.toggle_response_type()
        query.answer(text=status)
        query.edit_message_text(
            template.render_text(), parse_mode=ParseMode.HTML,
            reply_markup=template.build_settings_buttons(is_creator=is_creator)
        )
        return
    # Handle rename title button
    elif action == f"{models.RENAME}_{models.TITLE}":
        title_format = template.render_title_code("Current Title Format")
        response = f"{title_format}\n\nEnter a new <b>title format</b>."
        reply_message = query.edit_message_text(
            response, parse_mode=ParseMode.HTML,
            reply_markup=template.build_single_back_button(f"{models.EDIT}_{models.TITLE}")
        )
        query.answer(text="Enter a new title format.")
        context.user_data.update(
            {"action": models.TEMP_POLL, "step": 21, "tempId": template.temp_id, "ed": reply_message.message_id}
        )
        return
    # Handle rename description button
    elif action == f"{models.RENAME}_{models.DESCRIPTION}":
        description_format = template.render_description_code("Current Description Format")
        response = f"{description_format}\n\nEnter a new <b>description format</b>."
        reply_message = query.edit_message_text(
            response, parse_mode=ParseMode.HTML,
            reply_markup=template.build_single_back_button(f"{models.EDIT}_{models.DESCRIPTION}")
        )
        query.answer(text="Enter a new description format.")
        context.user_data.update(
            {"action": models.TEMP_POLL, "step": 22, "tempId": template.temp_id, "ed": reply_message.message_id}
        )
        return
    # Handle remove description button
    elif action == f"{models.DELETE}_{models.DESCRIPTION}":
        query.edit_message_reply_markup(template.build_delete_confirm_buttons(
            models.DESCRIPTION, f"{models.EDIT}_{models.DESCRIPTION}", delete_text="Remove")
        )
        query.answer(text="Confirm remove?")
        return
    # Handle add description button
    elif action == f"{models.ADD}_{models.DESCRIPTION}":
        description_format = template.render_description_code("Current Description Format")
        response = f"{description_format}\n\nEnter a new <b>description format</b>."
        reply_message = query.edit_message_text(
            response, parse_mode=ParseMode.HTML,
            reply_markup=template.build_single_back_button(f"{models.EDIT}_{models.DESCRIPTION}")
        )
        query.answer(text="Enter a new description format.")
        context.user_data.update(
            {"action": models.TEMP_POLL, "step": 23, "tempId": template.temp_id, "ed": reply_message.message_id}
        )
        return
    # Handle confirm delete template button
    elif action == f"{models.DELETE_YES}_{models.TEMPLATE}" and is_creator:
        user.delete_temp_poll(temp_id)
        query.answer(text="Poll template deleted!")
        message.delete()
        return
    # Handle confirm remove description button
    elif action == f"{models.DELETE_YES}_{models.DESCRIPTION}":
        template.description_format = ""
        query.edit_message_text(
            template.render_description_code("Current Description Format"), parse_mode=ParseMode.HTML,
            reply_markup=template.build_edit_description_buttons()
        )
        query.answer(text="Description removed.")
        return
    # Handle confirm remove template description button
    elif action == f"{models.DELETE_YES}_{models.TEMPLATE}_{models.DESCRIPTION}":
        template.description = ""
        template_name = f"<b>Template Name</b>\n<b>{template.name}</b>"
        template_description = f"<b>Template Description</b>\n<i>{template.description or 'None'}</i>"
        query.edit_message_text(
            f"{template_name}\n\n{template_description}", parse_mode=ParseMode.HTML,
            reply_markup=template.build_edit_template_details_buttons()
        )
        query.answer(text="Description removed.")
        return
    # Handle back button
    elif action == models.BACK:
        query.answer(text=None)
        query.edit_message_reply_markup(template.build_main_buttons())
        return
    # Handle close button
    elif action == models.CLOSE:
        query.answer(text=None)
        message.edit_reply_markup(None)
        message.delete()
        return
    # Handle reset button
    elif action == models.RESET:
        query.answer(text="Process cancelled.")
        context.user_data.clear()
        message.edit_reply_markup(None)
        message.delete()
        return
    # Handle other cases
    else:
        logger.warning("Invalid callback query data.")
        query.answer(text="Invalid callback query data!")
        message.edit_reply_markup(None)
        message.delete()
        return


def handle_temp_list_callback_query(query: CallbackQuery, context: CallbackContext, action: str, temp_id: str) -> None:
    """Handles a poll template callback query."""
    template: ListTemplate = ListTemplate.get_template_by_id(temp_id)

    # List is deleted or has error
    if not template:
        query.message.delete()
        query.answer(text="Sorry, the list template has been deleted.")
        context.user_data.clear()
        return

    user, _, _ = get_user_permissions(query.from_user.id)
    message = query.message
    is_creator = template.creator_id == user.get_uid()

    user_action, step, title, title_code, description, description_code, context_id = \
        context.user_data.get("action", ""), context.user_data.get("step", 0), context.user_data.get("title", ""), \
        context.user_data.get("titleCode", ""), context.user_data.get("descr", ""), \
        context.user_data.get("descrCode", ""), context.user_data.get("tempId", "")

    if user_action != models.TEMP_LIST or context_id != temp_id:
        step, title, title_code, description, description_code = 0, "", "", "", ""

    # Handle generate list button
    if action == models.LIST:
        title_text, is_valid = template.render_title()
        if not is_valid:
            message.reply_html(title_text, reply_markup=template.build_format_back_buttons(models.TEMP_TITLE))
            query.answer(text="Error parsing title format.")
            return
        title = f"<b>Current List Title</b>\n<b>{title_text}</b>"
        body = f"Enter another format input to change the title or <b>Continue</b> to go to the next step."
        response = "\n\n".join([title] + [body])
        reply_message = message.reply_html(response, reply_markup=template.build_format_title_buttons())
        query.answer(text="Change the title or continue to the next step.")
        context.user_data.update(
            {"action": models.TEMP_LIST, "step": 11, "title": title_text, "ed": reply_message.message_id,
             "tempId": template.temp_id}
        )
        return
    # Handle format title button
    elif action == models.TEMP_TITLE:
        title_text, is_valid = template.render_title(title_code)
        if not is_valid:
            message.edit_text(
                    title_text, parse_mode=ParseMode.HTML,
                    reply_markup=template.build_format_back_buttons(models.TEMP_TITLE)
                )
            query.answer(text="Error parsing title format.")
            return
        title = f"<b>Current List Title</b>\n<b>{title_text}</b>"
        body = f"Enter another format input to change the title or <b>Continue</b> to go to the next step."
        response = "\n\n".join([title] + [body])
        message.edit_text(
            response, parse_mode=ParseMode.HTML, reply_markup=template.build_format_title_buttons()
        )
        query.answer(text=None)
        return
    # Handle format title code button
    elif action == models.TEMP_TITLE_CODE:
        response = template.render_title_code()
        message.edit_text(
            response, parse_mode=ParseMode.HTML, reply_markup=template.build_format_back_buttons(models.TEMP_TITLE)
        )
        query.answer(text=None)
        return
    # Handle format description button
    elif action == models.TEMP_DESCRIPTION and title:
        descr_text, is_valid = template.render_description(description_code)
        if not is_valid:
            message.edit_text(
                descr_text, parse_mode=ParseMode.HTML,
                reply_markup=template.build_format_back_buttons(models.TEMP_DESCRIPTION)
            )
            query.answer(text="Error parsing description format.")
            return
        title = f"<b>Current List Description</b>\n<i>{descr_text}</i>"
        body = f"Enter another format input to change the description, or <b>Create</b> the list, " \
               f"or <b>Skip</b> to create the list without a description."
        response = "\n\n".join([title] + [body])
        message.edit_text(
            response, parse_mode=ParseMode.HTML, reply_markup=template.build_format_description_buttons()
        )
        query.answer(text=None)
        return
    # Handle format description code button
    elif action == models.TEMP_DESCRIPTION_CODE:
        response = template.render_description_code()
        message.edit_text(
            response, parse_mode=ParseMode.HTML,
            reply_markup=template.build_format_back_buttons(models.TEMP_DESCRIPTION)
        )
        query.answer(text=None)
        return
    # Handle skip button
    elif action == models.SKIP and title:
        _list: List = user.create_list_from_template(temp_id, title, "")
        message.edit_text(
            LIST_DONE, parse_mode=ParseMode.HTML, reply_markup=util.build_single_button_markup("Close", models.CLOSE)
        )
        message.reply_html(_list.render_text(), reply_markup=_list.build_admin_buttons())
        context.user_data.clear()
        return
    # Handle done button
    elif action == models.DONE:
        if step == 11 and title:
            descr_text, is_valid = template.render_description(description_code)
            if not is_valid:
                message.edit_text(
                    descr_text, parse_mode=ParseMode.HTML,
                    reply_markup=template.build_format_back_buttons(models.TEMP_DESCRIPTION)
                )
                query.answer(text="Error parsing description format.")
                context.user_data.update({"step": 12})
                return
            title = f"<b>Current List Description</b>\n<i>{descr_text}</i>"
            body = f"Enter another format input to change the description, or <b>Create</b> the list, " \
                   f"or <b>Skip</b> to create the list without a description."
            response = "\n\n".join([title] + [body])
            message.edit_text(
                response, parse_mode=ParseMode.HTML, reply_markup=template.build_format_description_buttons()
            )
            query.answer(text="Change the description, skip, or create the list.")
            context.user_data.update({"step": 12, "descr": descr_text})
            return
        elif step == 12 and title:
            _list = user.create_list_from_template(temp_id, title, description)
            query.edit_message_text(
                LIST_DONE, parse_mode=ParseMode.HTML,
                reply_markup=util.build_single_button_markup("Close", models.CLOSE)
            )
            message.reply_html(_list.render_text(), reply_markup=_list.build_admin_buttons())
            query.answer(text="List created successfully!")
            context.user_data.clear()
            return
        elif step == 21 and title:
            template.title_format = title
            query.edit_message_text(
                template.render_title_code("Current Title Format"), parse_mode=ParseMode.HTML,
                reply_markup=template.build_edit_title_buttons()
            )
            query.answer(text="Title format changed successfully!")
            context.user_data.clear()
            return
        elif step == 22 and description:
            template.description_format = description
            query.edit_message_text(
                template.render_description_code("Current Description Format"), parse_mode=ParseMode.HTML,
                reply_markup=template.build_edit_description_buttons()
            )
            query.answer(text="Description format changed successfully!")
            context.user_data.clear()
            return
        elif step == 23 and description:
            template.description_format = description
            query.edit_message_text(
                template.render_description_code("Current Description Format"), parse_mode=ParseMode.HTML,
                reply_markup=template.build_edit_description_buttons()
            )
            query.answer(text="Description format added successfully!")
            context.user_data.clear()
            return
        else:
            logger.warning("Invalid callback query data.")
            query.answer(text="Invalid callback query data!")
            message.edit_reply_markup(None)
            message.delete()
            context.user_data.clear()
            return
    # Handle refresh button
    elif action == models.REFRESH:
        query.answer(text="Results updated!")
        query.edit_message_text(
            template.render_text(), parse_mode=ParseMode.HTML, reply_markup=template.build_main_buttons()
        )
        return
    # Handle settings button
    elif action == models.SETTINGS:
        query.edit_message_text(
            template.render_text(), parse_mode=ParseMode.HTML,
            reply_markup=template.build_settings_buttons(is_creator=is_creator)
        )
        query.answer(text=None)
        return
    # Handle delete template button
    elif action == models.DELETE and is_creator:
        query.edit_message_reply_markup(
            template.build_delete_confirm_buttons(models.TEMPLATE, models.SETTINGS)
        )
        query.answer(text="Confirm delete?")
        return
    # Handle edit template details button
    elif action == f"{models.EDIT}_{models.TEMPLATE}":
        template_name = f"<b>Template Name</b>\n<b>{template.name}</b>"
        template_description = f"<b>Template Description</b>\n<i>{template.description or 'None'}</i>"
        query.edit_message_text(
            f"{template_name}\n\n{template_description}", parse_mode=ParseMode.HTML,
            reply_markup=template.build_edit_template_details_buttons()
        )
        query.answer(text=None)
        context.user_data.clear()
        return
    # Handle rename template button
    elif action == f"{models.RENAME}_{models.TEMPLATE}_{models.NAME}":
        template_name = f"<b>Template Name</b>\n<b>{template.name}</b>"
        template_description = f"<b>Template Description</b>\n<i>{template.description or 'None'}</i>"
        response = f"{template_name}\n\n{template_description}\n\nEnter a new <b>template name</b>."
        reply_message = query.edit_message_text(
            response, parse_mode=ParseMode.HTML,
            reply_markup=template.build_single_back_button(f"{models.EDIT}_{models.TEMPLATE}")
        )
        query.answer(text="Enter a new template name.")
        context.user_data.update(
            {"action": models.TEMP_LIST, "step": 25, "tempId": template.temp_id, "ed": reply_message.message_id}
        )
        return
    # Handle rename template description button
    elif action == f"{models.RENAME}_{models.TEMPLATE}_{models.DESCRIPTION}":
        template_name = f"<b>Template Name</b>\n<b>{template.name}</b>"
        template_description = f"<b>Template Description</b>\n<i>{template.description or 'None'}</i>"
        response = f"{template_name}\n\n{template_description}\n\nEnter a new <b>template description</b>."
        reply_message = query.edit_message_text(
            response, parse_mode=ParseMode.HTML,
            reply_markup=template.build_single_back_button(f"{models.EDIT}_{models.TEMPLATE}")
        )
        query.answer(text="Enter a new template description.")
        context.user_data.update(
            {"action": models.TEMP_LIST, "step": 26, "tempId": template.temp_id, "ed": reply_message.message_id}
        )
        return
    # Handle remove template description button
    elif action == f"{models.DELETE}_{models.TEMPLATE}_{models.DESCRIPTION}":
        query.edit_message_reply_markup(template.build_delete_confirm_buttons(
            f"{models.TEMPLATE}_{models.DESCRIPTION}", f"{models.EDIT}_{models.TEMPLATE}", delete_text="Remove")
        )
        query.answer(text="Confirm remove?")
        return
    # Handle add template description button
    elif action == f"{models.ADD}_{models.TEMPLATE}_{models.DESCRIPTION}":
        template_name = f"<b>Template Name</b>\n<b>{template.name}</b>"
        template_description = f"<b>Template Description</b>\n<i>{template.description or 'None'}</i>"
        response = f"{template_name}\n\n{template_description}\n\nEnter a new <b>template description</b>."
        reply_message = query.edit_message_text(
            response, parse_mode=ParseMode.HTML,
            reply_markup=template.build_single_back_button(f"{models.EDIT}_{models.TEMPLATE}")
        )
        query.answer(text="Enter a new template description.")
        context.user_data.update(
            {"action": models.TEMP_LIST, "step": 27, "tempId": template.temp_id, "ed": reply_message.message_id}
        )
        return
    # Handle edit title button
    elif action == f"{models.EDIT}_{models.TITLE}":
        query.edit_message_text(
            template.render_title_code("Current Title Format"), parse_mode=ParseMode.HTML,
            reply_markup=template.build_edit_title_buttons()
        )
        query.answer(text=None)
        context.user_data.clear()
        return
    # Handle edit description button
    elif action == f"{models.EDIT}_{models.DESCRIPTION}":
        query.edit_message_text(
            template.render_description_code("Current Description Format"), parse_mode=ParseMode.HTML,
            reply_markup=template.build_edit_description_buttons()
        )
        query.answer(text=None)
        context.user_data.clear()
        return
    # Handle edit options button
    elif action == f"{models.EDIT}_{models.OPTIONS}":
        query.answer(text="Sorry, this feature has not been implemented yet.")
        return
    # Handle edit choices button
    elif action == f"{models.EDIT}_{models.CHOICES}":
        query.answer(text="Sorry, this feature has not been implemented yet.")
        return
    # Handle toggle response button
    elif action == f"{models.EDIT}_{models.RESPONSE}":
        status = template.toggle_response_type()
        query.answer(text=status)
        query.edit_message_text(
            template.render_text(), parse_mode=ParseMode.HTML,
            reply_markup=template.build_settings_buttons(is_creator=is_creator)
        )
        return
    # Handle rename title button
    elif action == f"{models.RENAME}_{models.TITLE}":
        title_format = template.render_title_code("Current Title Format")
        response = f"{title_format}\n\nEnter a new <b>title format</b>."
        reply_message = query.edit_message_text(
            response, parse_mode=ParseMode.HTML,
            reply_markup=template.build_single_back_button(f"{models.EDIT}_{models.TITLE}")
        )
        query.answer(text="Enter a new title format.")
        context.user_data.update(
            {"action": models.TEMP_LIST, "step": 21, "tempId": template.temp_id, "ed": reply_message.message_id}
        )
        return
    # Handle rename description button
    elif action == f"{models.RENAME}_{models.DESCRIPTION}":
        description_format = template.render_description_code("Current Description Format")
        response = f"{description_format}\n\nEnter a new <b>description format</b>."
        reply_message = query.edit_message_text(
            response, parse_mode=ParseMode.HTML,
            reply_markup=template.build_single_back_button(f"{models.EDIT}_{models.DESCRIPTION}")
        )
        query.answer(text="Enter a new description format.")
        context.user_data.update(
            {"action": models.TEMP_LIST, "step": 22, "tempId": template.temp_id, "ed": reply_message.message_id}
        )
        return
    # Handle remove description button
    elif action == f"{models.DELETE}_{models.DESCRIPTION}":
        query.edit_message_reply_markup(template.build_delete_confirm_buttons(
            models.DESCRIPTION, f"{models.EDIT}_{models.DESCRIPTION}", delete_text="Remove")
        )
        query.answer(text="Confirm remove?")
        return
    # Handle add description button
    elif action == f"{models.ADD}_{models.DESCRIPTION}":
        description_format = template.render_description_code("Current Description Format")
        response = f"{description_format}\n\nEnter a new <b>description format</b>."
        reply_message = query.edit_message_text(
            response, parse_mode=ParseMode.HTML,
            reply_markup=template.build_single_back_button(f"{models.EDIT}_{models.DESCRIPTION}")
        )
        query.answer(text="Enter a new description format.")
        context.user_data.update(
            {"action": models.TEMP_LIST, "step": 23, "tempId": template.temp_id, "ed": reply_message.message_id}
        )
        return
    # Handle delete template button
    elif action == f"{models.DELETE_YES}_{models.TEMPLATE}" and is_creator:
        user.delete_temp_list(temp_id)
        message.delete()
        query.answer(text="List template deleted!")
        return
    # Handle remove description button
    elif action == f"{models.DELETE_YES}_{models.DESCRIPTION}":
        template.description_format = ""
        query.edit_message_text(
            template.render_description_code("Current Description Format"), parse_mode=ParseMode.HTML,
            reply_markup=template.build_edit_description_buttons()
        )
        query.answer(text="Description removed.")
        return
    # Handle confirm remove template description button
    elif action == f"{models.DELETE_YES}_{models.TEMPLATE}_{models.DESCRIPTION}":
        template.description = ""
        template_name = f"<b>Template Name</b>\n<b>{template.name}</b>"
        template_description = f"<b>Template Description</b>\n<i>{template.description or 'None'}</i>"
        query.edit_message_text(
            f"{template_name}\n\n{template_description}", parse_mode=ParseMode.HTML,
            reply_markup=template.build_edit_template_details_buttons()
        )
        query.answer(text="Description removed.")
        return
    # Handle back button
    elif action == models.BACK:
        query.answer(text=None)
        query.edit_message_reply_markup(template.build_main_buttons())
        return
    # Handle close button
    elif action == models.CLOSE:
        query.answer(text=None)
        message.edit_reply_markup(None)
        message.delete()
        return
    # Handle reset button
    elif action == models.RESET:
        query.answer(text="Process cancelled.")
        context.user_data.clear()
        message.edit_reply_markup(None)
        message.delete()
    # Handle other cases
    else:
        logger.warning("Invalid callback query data.")
        query.answer(text="Invalid callback query data!")
        message.edit_reply_markup(None)
        message.delete()
        return

# endregion

# region INLINE QUERY HANDLERS


def handle_inline_query(update: Update, context: CallbackContext) -> None:
    """Handles an inline query."""
    query = update.inline_query
    text = query.query.strip()
    uid = update.effective_user.id
    user, is_leader, is_admin = get_user_permissions(uid)
    is_sender = query.chat_type == "sender"

    results = []

    # Handle vote and comment queries
    match = re.match(r"^/(vote|comment|update|join|access)\s+(\w+)$", text)
    if match:
        handle_inline_pm_query(query, match.group(1), match.group(2))
        return

    # Display incomplete commands
    match = re.match(r"^/([a-z]*)$", text)
    if match and is_sender:
        command = match.group(1)
        # Handle start query
        if START_COMMAND[:-1].startswith(command):
            query_result = InlineQueryResultArticle(
                id="startcom", title="/start", description="View the bot's welcome message",
                input_message_content=InputTextMessageContent("/start")
            )
            results.append(query_result)
        # Handle keyboard query
        if KEYBOARD_COMMAND[:-1].startswith(command):
            query_result = InlineQueryResultArticle(
                id="keyboardcom", title="/keyboard", description="Show or hide the command keyboard",
                input_message_content=InputTextMessageContent("/keyboard")
            )
            results.append(query_result)
        # Handle poll query
        if POLL_COMMAND[:-1].startswith(command) and user:
            query_result = InlineQueryResultArticle(
                id="pollcom", title="/poll", description="Build a new poll",
                input_message_content=InputTextMessageContent("/poll")
            )
            results.append(query_result)
        # Handle polls query
        if POLLS_COMMAND[:-1].startswith(command) and user:
            query_result = InlineQueryResultArticle(
                id="pollscom", title="/polls", description="View all the polls you have built",
                input_message_content=InputTextMessageContent("/polls")
            )
            results.append(query_result)
        # Handle list query
        if LIST_COMMAND[:-1].startswith(command) and user:
            query_result = InlineQueryResultArticle(
                id="listcom", title="/list", description="Build a new list",
                input_message_content=InputTextMessageContent("/list")
            )
            results.append(query_result)
        # Handle lists query
        if LISTS_COMMAND[:-1].startswith(command) and user:
            query_result = InlineQueryResultArticle(
                id="listscom", title="/lists", description="View all the lists you have built",
                input_message_content=InputTextMessageContent("/lists")
            )
            results.append(query_result)
        # Handle template query
        if TEMPLATE_COMMAND[:-1].startswith(command) and user:
            query_result = InlineQueryResultArticle(
                id="tempcom", title="/temp", description="Create a new poll or list template",
                input_message_content=InputTextMessageContent("/temp")
            )
            results.append(query_result)
        # Handle templates query
        if TEMPLATES_COMMAND[:-1].startswith(command) and user:
            query_result = InlineQueryResultArticle(
                id="tempscom", title="/temps", description="View all the templates you have created",
                input_message_content=InputTextMessageContent("/temps")
            )
            results.append(query_result)
        # Handle group query
        if GROUP_COMMAND[:-1].startswith(command) and is_leader:
            query_result = InlineQueryResultArticle(
                id="groupcom", title="/group", description="Create a new group",
                input_message_content=InputTextMessageContent("/group")
            )
            results.append(query_result)
        # Handle groups query
        if GROUPS_COMMAND[:-1].startswith(command) and user:
            query_result = InlineQueryResultArticle(
                id="groupscom", title="/groups", description="View all the groups you are in",
                input_message_content=InputTextMessageContent("/groups")
            )
            results.append(query_result)
        # Handle group polls query
        if GROUP_POLLS_COMMAND[:-1].startswith(command) and user:
            query_result = InlineQueryResultArticle(
                id="gpollscom", title="/gpolls", description="View all the polls in your groups",
                input_message_content=InputTextMessageContent("/gpolls")
            )
            results.append(query_result)
        # Handle group lists query
        if GROUP_LISTS_COMMAND[:-1].startswith(command) and user:
            query_result = InlineQueryResultArticle(
                id="glistscom", title="/glists", description="View all the lists in your groups",
                input_message_content=InputTextMessageContent("/glists")
            )
            results.append(query_result)
        # Handle group templates query
        if GROUP_TEMPLATES_COMMAND[:-1].startswith(command) and user:
            query_result = InlineQueryResultArticle(
                id="gtempscom", title="/gtemps", description="View all the templates in your groups",
                input_message_content=InputTextMessageContent("/gtemps")
            )
            results.append(query_result)
        # Handle invite query
        if INVITE_COMMAND[:-1].startswith(command) and user:
            query_result = InlineQueryResultArticle(
                id="invitecom", title="/invite", description="Send a group invite to your friends",
                input_message_content=InputTextMessageContent("/invite")
            )
            results.append(query_result)
        # Handle access query
        if ACCESS_COMMAND[:-1].startswith(command) and is_admin:
            query_result = InlineQueryResultArticle(
                id="accesscom", title="/access", description="Manage access rights",
                input_message_content=InputTextMessageContent("/access")
            )
            results.append(query_result)
        # Handle invite access query
        if ENROL_COMMAND[:-1].startswith(command) and is_admin:
            query_result = InlineQueryResultArticle(
                id="enrolcom", title="/enrol", description="Send a bot access invite to your friends",
                input_message_content=InputTextMessageContent("/enrol")
            )
            results.append(query_result)
        # Handle promote query
        if PROMOTE_COMMAND[:-1].startswith(command) and is_admin:
            query_result = InlineQueryResultArticle(
                id="promotecom", title="/promote", description="Promote users to be bot leaders",
                input_message_content=InputTextMessageContent("/promote")
            )
            results.append(query_result)
        # Handle help query
        if HELP_COMMAND[:-1].startswith(command):
            query_result = InlineQueryResultArticle(
                id="helpcom", title="/help", description="View the help message",
                input_message_content=InputTextMessageContent("/help")
            )
            results.append(query_result)

    # Display complete commands as pm text
    match = \
        re.match(r"^/(\w+)(?:\s+((?:.|\n)+))?$", text)
    if match:
        command, details = match.group(1), match.group(2)
        details = details.strip() if details else ""
        # Handle start query
        if command == START_COMMAND and is_sender:
            query.answer(results, switch_pm_text="Click to view the bot's welcome message", switch_pm_parameter=command)
            return
        # Handle keyboard query
        elif command == KEYBOARD_COMMAND and is_sender:
            query.answer(results, switch_pm_text="Show or hide the command keyboard", switch_pm_parameter=command)
            return
        # Handle poll query
        elif command == POLL_COMMAND and user and is_sender:
            if details:
                context.user_data.update({"title": details})
                query.answer(
                    results, switch_pm_text="Click to build a new poll with the title", switch_pm_parameter=command
                )
            else:
                query.answer(results, switch_pm_text="Click to build a new poll", switch_pm_parameter=command)
            return
        # Handle polls query
        elif command == POLLS_COMMAND and user and is_sender:
            for poll in user.get_polls(details)[:QUERY_RESULTS_LIMIT]:
                query_result = InlineQueryResultArticle(
                    id=f"poll_{poll.get_poll_id()}", title=poll.get_title(),
                    description=poll.generate_options_summary(),
                    input_message_content=InputTextMessageContent(f"/poll_{poll.get_poll_id()}")
                )
                results.append(query_result)
            query.answer(results, switch_pm_text="Click to view all your polls", switch_pm_parameter=command)
            return
        # Handle list query
        elif command == LIST_COMMAND and user and is_sender:
            if details:
                context.user_data.update({"title": details})
                query.answer(
                    results, switch_pm_text="Click to build a new list with the title", switch_pm_parameter=command
                )
            else:
                query.answer(results, switch_pm_text="Click to build a new list", switch_pm_parameter=command)
            return
        # Handle lists query
        elif command == LISTS_COMMAND and user and is_sender:
            for _list in user.get_lists(details)[:QUERY_RESULTS_LIMIT]:
                query_result = InlineQueryResultArticle(
                    id=f"list_{_list.get_list_id()}", title=_list.get_title(),
                    description=_list.generate_options_summary(),
                    input_message_content=InputTextMessageContent(f"/list_{_list.get_list_id()}")
                )
                results.append(query_result)
            query.answer(results, switch_pm_text="Click to view all your lists", switch_pm_parameter=command)
            return
        # Handle template query
        elif command == TEMPLATE_COMMAND and user and is_sender:
            create_match = re.match(r"^(p|poll|l|list)\s+(\w+)\s*(\n(?:\n|.)*)?$", details)
            if not create_match:
                query.answer(results, switch_pm_text="Click to create a new template", switch_pm_parameter=command)
                return

            template_type, name, format_inputs = create_match.group(1), create_match.group(2), create_match.group(3)
            format_inputs = format_inputs if format_inputs else ""
            if template_type in ("p", "poll"):
                template = user.get_temp_poll_by_name(name)
            elif template_type in ("l", "list"):
                template = user.get_temp_list_by_name(name)
            else:
                query.answer(results, switch_pm_text="Click to create a new template", switch_pm_parameter=command)
                return

            if not template:
                query.answer(results, switch_pm_text="Click to create a new template", switch_pm_parameter=command)
                return

            title, description, is_valid = template.render_title_and_description(format_inputs)
            if not is_valid:
                query.answer(results, switch_pm_text="Click to create a new template", switch_pm_parameter=command)
                return

            query_result = InlineQueryResultArticle(
                id=f"temp_{name}", title=title, description=description,
                input_message_content=InputTextMessageContent(f"/temp {template_type} {name}\n{format_inputs}")
            )

            results.append(query_result)
            return
        # Handle templates query
        elif command == TEMPLATES_COMMAND and user and is_sender:
            for template in user.get_templates(details)[:QUERY_RESULTS_LIMIT]:
                query_result = InlineQueryResultArticle(
                    id=f"temp_{template.temp_id}", title=template.name,
                    description=(template.description or f"{template.icon} {template.temp_type.capitalize()} template"),
                    input_message_content=InputTextMessageContent(f"/temp_{template.temp_id}")
                )
                results.append(query_result)
            query.answer(results, switch_pm_text="Click to view all your templates", switch_pm_parameter=command)
            return
        # Handle group query
        elif command == GROUP_COMMAND and is_leader and is_sender:
            if details:
                context.user_data.update({"name": details})
                query.answer(
                    results, switch_pm_text="Click to create a new group with a name", switch_pm_parameter=command
                )
            else:
                query.answer(results, switch_pm_text="Click to create a new group", switch_pm_parameter=command)
            return
        # Handle groups query
        elif command == GROUPS_COMMAND and user and is_sender:
            for group in user.get_all_groups(details)[:QUERY_RESULTS_LIMIT]:
                query_result = InlineQueryResultArticle(
                    id=f"group_{group.get_gid()}", title=group.get_name(),
                    description=group.generate_group_description_summary(),
                    input_message_content=InputTextMessageContent(f"/group_{group.get_gid()}")
                )
                results.append(query_result)
            query.answer(results, switch_pm_text="Click to view all your joined groups", switch_pm_parameter=command)
            return
        # Handle group polls query
        elif command == GROUP_POLLS_COMMAND and user and is_sender:
            for poll in user.get_group_polls(details)[:QUERY_RESULTS_LIMIT]:
                query_result = InlineQueryResultArticle(
                    id=f"gpoll_{poll.get_poll_id()}", title=poll.get_title(),
                    description=poll.generate_options_summary(),
                    input_message_content=InputTextMessageContent(f"/poll_{poll.get_poll_id()}")
                )
                results.append(query_result)
            query.answer(results, switch_pm_text="Click to view all your group polls", switch_pm_parameter=command)
            return
        # Handle group lists query
        elif command == GROUP_LISTS_COMMAND and user and is_sender:
            for _list in user.get_group_lists(details)[:QUERY_RESULTS_LIMIT]:
                query_result = InlineQueryResultArticle(
                    id=f"glist_{_list.get_list_id()}", title=_list.get_title(),
                    description=_list.generate_options_summary(),
                    input_message_content=InputTextMessageContent(f"/list_{_list.get_list_id()}")
                )
                results.append(query_result)
            query.answer(results, switch_pm_text="Click to view all your group lists", switch_pm_parameter=command)
            return
        # Handle group templates query
        elif command == GROUP_TEMPLATES_COMMAND and user and is_sender:
            for template in user.get_group_templates(details)[:QUERY_RESULTS_LIMIT]:
                query_result = InlineQueryResultArticle(
                    id=f"gtemp_{template.temp_id}", title=template.name,
                    description=(template.description or f"{template.icon} {template.temp_type.capitalize()} template"),
                    input_message_content=InputTextMessageContent(f"/temp_{template.temp_id}")
                )
                results.append(query_result)
            query.answer(results, switch_pm_text="Click to view all your group templates", switch_pm_parameter=command)
            return
        # Handle invite query
        elif command == INVITE_COMMAND and user:
            if is_sender:
                query.answer(results, switch_pm_text="Click to send a group invite", switch_pm_parameter=command)
                return
            for group in user.get_owned_groups(details)[:QUERY_RESULTS_LIMIT]:
                invitation, join_button = group.build_invite_text_and_button(update.effective_user.first_name)
                query_result = InlineQueryResultArticle(
                    id=group.get_gid(), title=group.get_name(), description=group.generate_group_description_summary(),
                    input_message_content=InputTextMessageContent(invitation, parse_mode=ParseMode.HTML),
                    reply_markup=join_button
                )
                results.append(query_result)
            query.answer(results)
            return
        # Handle enrol query
        elif command == ENROL_COMMAND and is_admin:
            if is_sender:
                query.answer(results, switch_pm_text="Click to send a bot access invite", switch_pm_parameter=command)
                return
            if details.isdigit():
                invitation, access_button = BotManager.build_invite_text_and_button(ACCESS_KEY, int(details))
                query_result = InlineQueryResultArticle(
                    id=details, title="Invite user with ID to access bot", description=details,
                    input_message_content=InputTextMessageContent(invitation, parse_mode=ParseMode.HTML),
                    reply_markup=access_button
                )
                results.append(query_result)
            query.answer(results)
            return
        # Handle promote query
        elif command == PROMOTE_COMMAND and is_admin and is_sender:
            for user in User.get_users_by_name(details)[:QUERY_RESULTS_LIMIT]:
                if not user.is_leader():
                    query_result = InlineQueryResultArticle(
                        id=str(user.get_uid()), title=user.get_name(), description=f"@{user.get_username()}",
                        input_message_content=InputTextMessageContent(f"/promote {util.encode(user.get_uid())}"),
                    )
                    results.append(query_result)
            query.answer(
                results[:20], switch_pm_text="Click to promote a user to a bot leader", switch_pm_parameter=command
            )
            return
        # Handle help query
        elif command == HELP_COMMAND and is_sender:
            query.answer(results, switch_pm_text="Click to view the help message", switch_pm_parameter=command)
            return
        # Handle other query
        else:
            query.answer(results)
            return

    # Handle search everything
    if user:
        items = user.get_everything(text)[:QUERY_RESULTS_LIMIT]
        for item in items:
            if type(item) == Poll:
                query_result = InlineQueryResultArticle(
                    id=f"poll {item.get_poll_id()}", title=item.get_title(),
                    description=item.generate_options_summary(),
                    input_message_content=InputTextMessageContent(item.render_text(), parse_mode=ParseMode.HTML),
                    reply_markup=item.build_option_buttons()
                )
            elif type(item) == List:
                query_result = InlineQueryResultArticle(
                    id=f"list {item.get_list_id()}", title=item.get_title(),
                    description=item.generate_options_summary(),
                    input_message_content=InputTextMessageContent(item.render_text(), parse_mode=ParseMode.HTML),
                    reply_markup=item.build_update_buttons()
                )
            else:
                continue
            results.append(query_result)

    query.answer(results)
    return


def handle_inline_pm_query(query: InlineQuery, action: str, details: str) -> None:
    """Handles specific inline to pm queries."""
    if action == models.VOTE:
        text = "Click here to toggle your vote."
    elif action == models.COMMENT:
        text = "Click here to add a comment to the poll."
    elif action == "update":
        text = "Click here to update the list."
    elif action == "join":
        text = "Click here to join group"
    elif action == "access":
        text = "Click here to have access to the bot"
    else:
        text = ""

    query.answer([], switch_pm_text=text, switch_pm_parameter=f"{action}-{details}")
    return


def handle_chosen_poll_result(update: Update, context: CallbackContext) -> None:
    chosen_poll = update.chosen_inline_result
    match = re.match(r"^poll (\w+)$", chosen_poll.result_id)

    if not match:
        logger.warning(f"Invalid poll result! {chosen_poll.result_id}")
        return

    poll_id = match.group(1)
    poll = Poll.get_poll_by_id(poll_id)
    if poll:
        poll.add_message_details(chosen_poll.inline_message_id)
    else:
        logger.warning(f"Invalid poll from chosen poll result! {poll_id}")
    return


def handle_chosen_list_result(update: Update, context: CallbackContext) -> None:
    chosen_list = update.chosen_inline_result
    match = re.match(r"^list (\w+)$", chosen_list.result_id)

    if not match:
        logger.warning(f"Invalid list result! {chosen_list.result_id}")
        return

    list_id = match.group(1)
    _list = List.get_list_by_id(list_id)
    if _list:
        _list.add_message_details(chosen_list.inline_message_id)
    else:
        logger.warning(f"Invalid list from chosen list result! {list_id}")
    return


# endregion

# region OTHER HANDLERS


def handle_error(update: Update, context: CallbackContext) -> None:
    """Logs errors caused by Updates."""
    logger.warning(f"Update {update} caused error {context.error}")


def handle_save(update: Update, context: CallbackContext) -> None:
    """Saves data to database (Temporary)."""
    delete_chat_message(update.message)

    _, _, is_admin = get_user_permissions(update.effective_user.id)
    if not is_admin:
        handle_help(update, context)
        return
    status = BotManager.save_data()
    update.message.reply_html(status, reply_markup=util.build_single_button_markup("Close", models.CLOSE))
    return


def handle_load(update: Update, context: CallbackContext) -> None:
    """Loads data from database (Temporary)."""
    delete_chat_message(update.message)

    _, _, is_admin = get_user_permissions(update.effective_user.id)
    if not is_admin:
        handle_help(update, context)
        return
    status = BotManager.load_data()
    update.message.reply_html(status, reply_markup=util.build_single_button_markup("Close", models.CLOSE))
    return

# endregion

# region HELPERS


def get_user_permissions(uid: int) -> Tuple[User, bool, bool]:
    """Checks the user's permissions."""
    user = User.get_user_by_id(uid)
    is_leader = user and user.is_leader()
    is_admin = BotManager.is_admin(uid, ADMIN_KEYS)
    return user, is_leader, is_admin


def is_registered(user: TeleUser) -> bool:
    """Validates if user has access to the bot and registers user if required."""
    if User.get_user_by_id(user.id):
        return True
    if ACCESS_REQUIRED:
        return False
    register_user(user)
    return True


def register_user(user: TeleUser) -> User:
    """Registers the user to have access to use the bot."""
    uid, user_profile = extract_user_data(user)
    return User.register(uid, user_profile["first_name"], user_profile["last_name"], user_profile["username"])


def is_private_chat(message: Message) -> bool:
    """Verifies if a user is in a private chat."""
    return message and message.chat.type == "private"


def extract_user_data(user: TeleUser) -> tuple:
    """Extracts user data from User object."""
    return user.id, {"first_name": user.first_name, "last_name": user.last_name or "", "username": user.username or ""}


def edit_conversation_message(update: Update, context: CallbackContext, text: str, reply_markup: InlineKeyboardMarkup):
    """Edits a previous bot message in the conversation."""
    mid = context.user_data.get("ed", "")
    if not mid:
        response = "Message not found. Process cancelled."
        update.message.reply_html(response, reply_markup=util.build_single_button_markup("Close", models.CLOSE))
        context.user_data.clear()
        return
    try:
        context.bot.edit_message_text(
            text, chat_id=update.effective_chat.id, message_id=mid, parse_mode=ParseMode.HTML, reply_markup=reply_markup
        )
    except telegram.error.TelegramError as err:
        if "Message is not modified" in err:
            return
        response = "Error editing chat message!"
        logger.warning(f"{response} - {err}")
        update.message.reply_html(response, reply_markup=util.build_single_button_markup("Close", models.CLOSE))
        context.user_data.clear()
        return
    return


def delete_old_chat_message(update: Update, context: CallbackContext) -> None:
    """Deletes any old chat message."""
    old_mid = context.user_data.get("del", "")
    if not old_mid:
        return
    try:
        context.bot.delete_message(update.effective_chat.id, old_mid)
    except telegram.error.TelegramError:
        logger.warning("Error deleting chat message!")
    context.user_data.pop("del")
    return


def delete_chat_message(message: Message) -> None:
    """Deletes a chat message."""
    try:
        message.delete()
    except telegram.error.TelegramError:
        logger.info("Message already deleted!")
    return


def delete_message_with_timer(message: Message, countdown: int) -> None:
    """Deletes a message after a given countdown"""
    updater.job_queue.run_once(delete_message_from_job, countdown, context=message)


def delete_message_from_job(context: CallbackContext) -> None:
    """Deletes a message from the job queue."""
    try:
        message = context.job.context
        message.delete()
    except telegram.error.TelegramError:
        logger.info("Message has been deleted.")


def deliver_poll(update: Update, poll: Poll) -> None:
    """Delivers the poll."""
    update.message.reply_html(poll.render_text(), reply_markup=poll.build_admin_buttons())
    return


def refresh_polls(poll: Poll, context: CallbackContext, only_buttons=False) -> None:
    """Refreshes all polls to update changes."""
    if only_buttons:
        for mid in poll.get_message_details():
            try:
                context.bot.edit_message_reply_markup(inline_message_id=mid, reply_markup=poll.build_option_buttons())
            except telegram.error.TelegramError as err:
                logger.warning(err)
                continue
    else:
        for mid in poll.get_message_details():
            try:
                context.bot.edit_message_text(
                    poll.render_text(), inline_message_id=mid, parse_mode=ParseMode.HTML,
                    reply_markup=poll.build_option_buttons()
                )
            except telegram.error.TelegramError as err:
                logger.warning(err)
                continue
    return


def deliver_list(update: Update, _list: List) -> None:
    """Delivers the list."""
    update.message.reply_html(_list.render_text(), reply_markup=_list.build_admin_buttons())
    return


def refresh_lists(_list: List, context: CallbackContext, only_buttons=False) -> None:
    """Refreshes all lists to update changes."""
    if only_buttons:
        for mid in _list.get_message_details():
            try:
                context.bot.edit_message_reply_markup(inline_message_id=mid, reply_markup=_list.build_update_buttons())
            except telegram.error.TelegramError as err:
                logger.warning(err)
                continue
    else:
        for mid in _list.get_message_details():
            try:
                context.bot.edit_message_text(
                    _list.render_text(), inline_message_id=mid, parse_mode=ParseMode.HTML,
                    reply_markup=_list.build_update_buttons()
                )
            except telegram.error.TelegramError as err:
                logger.warning(err)
                continue
    return


def deliver_group(update: Update, group: Group) -> None:
    """Delivers the group details."""
    update.message.reply_html(group.render_group_details_text(), reply_markup=group.build_main_buttons())
    return


def try_join_group_through_invitation(update: Update, invitation_code: str) -> None:
    """Authenticates group invitation code for user to join group."""
    match = re.match(r"^([^_\W]+)(_[^_\W]+)?$", invitation_code)
    if match:
        gid = match.group(1)
        group = Group.get_group_by_id(gid)

        if group and group.get_password_hash() == invitation_code:
            response = group.add_member(update.effective_user.id)
            update.message.reply_html(response, reply_markup=util.build_single_button_markup("Close", models.CLOSE))
            return
        else:
            update.message.reply_html(
                ERROR_INVALID_GROUP_INVITE, reply_markup=util.build_single_button_markup("Close", models.CLOSE)
            )
        return

    update.message.reply_html(
        ERROR_INVALID_GROUP_INVITE, reply_markup=util.build_single_button_markup("Close", models.CLOSE)
    )
    return


def generate_preset_format_guide() -> str:
    return "<b>Preset Placeholder Format Guide</b>"


def build_progress_buttons(next_action=models.DONE, back_action=models.RESET, next_text="Done", back_text="Cancel") \
        -> InlineKeyboardMarkup:
    return util.build_multiple_stacked_buttons_markup(
        [util.generate_button_details(back_text, back_action), util.generate_button_details(next_text, next_action)]
    )


def save_data(context: CallbackContext) -> None:
    """Saves data to database."""
    status = BotManager.save_data()
    logger.info(status)
    return


def load_data(context: CallbackContext) -> None:
    """Loads data from database."""
    status = BotManager.load_data()
    logger.info(status)
    return

# endregion


def main() -> None:
    """Starts the bot."""
    # Dispatcher to register handlers
    dispatcher = updater.dispatcher

    private_filter = Filters.chat_type.private

    # Command handlers
    dispatcher.add_handler(CommandHandler(START_COMMAND, handle_start, filters=private_filter))
    dispatcher.add_handler(CommandHandler(KEYBOARD_COMMAND, handle_keyboard, filters=private_filter))
    dispatcher.add_handler(CommandHandler(POLL_COMMAND, handle_poll, filters=private_filter))
    dispatcher.add_handler(CommandHandler(POLLS_COMMAND, handle_polls, filters=private_filter))
    dispatcher.add_handler(CommandHandler(LIST_COMMAND, handle_list, filters=private_filter))
    dispatcher.add_handler(CommandHandler(LISTS_COMMAND, handle_lists, filters=private_filter))
    dispatcher.add_handler(CommandHandler(TEMPLATE_COMMAND, handle_template, filters=private_filter))
    dispatcher.add_handler(CommandHandler(TEMPLATES_COMMAND, handle_templates, filters=private_filter))
    dispatcher.add_handler(CommandHandler(GROUP_COMMAND, handle_group, filters=private_filter))
    dispatcher.add_handler(CommandHandler(GROUPS_COMMAND, handle_groups, filters=private_filter))
    dispatcher.add_handler(CommandHandler(GROUP_POLLS_COMMAND, handle_group_polls, filters=private_filter))
    dispatcher.add_handler(CommandHandler(GROUP_LISTS_COMMAND, handle_group_lists, filters=private_filter))
    dispatcher.add_handler(CommandHandler(GROUP_TEMPLATES_COMMAND, handle_group_templates, filters=private_filter))
    dispatcher.add_handler(CommandHandler(INVITE_COMMAND, handle_invite, filters=private_filter))
    dispatcher.add_handler(CommandHandler(HELP_COMMAND, handle_help, filters=private_filter))
    dispatcher.add_handler(CommandHandler(ACCESS_COMMAND, handle_access, filters=private_filter))
    dispatcher.add_handler(CommandHandler(ENROL_COMMAND, handle_enrol, filters=private_filter))
    dispatcher.add_handler(CommandHandler(PROMOTE_COMMAND, handle_promote, filters=private_filter))
    dispatcher.add_handler(CommandHandler(SAVE_COMMAND, handle_save, filters=private_filter))
    dispatcher.add_handler(CommandHandler(LOAD_COMMAND, handle_load, filters=private_filter))

    # Message handlers
    dispatcher.add_handler(
        MessageHandler((Filters.regex(r"^\/poll_\w+$") & private_filter), handle_poll_view)
    )
    dispatcher.add_handler(
        MessageHandler((Filters.regex(r"^\/list_\w+$") & private_filter), handle_list_view)
    )
    dispatcher.add_handler(
        MessageHandler((Filters.regex(r"^\/group_\w+$") & private_filter), handle_group_view)
    )
    dispatcher.add_handler(
        MessageHandler((Filters.regex(r"^\/temp_\w+$") & private_filter), handle_template_view)
    )
    dispatcher.add_handler(MessageHandler((Filters.text & private_filter), handle_message))

    # Callback query handlers
    dispatcher.add_handler(CallbackQueryHandler(handle_callback_query))

    # Inline query handlers
    dispatcher.add_handler(InlineQueryHandler(handle_inline_query))

    # Chosen inline result handlers
    dispatcher.add_handler(ChosenInlineResultHandler(handle_chosen_poll_result, pattern=r"^poll \w+$"))
    dispatcher.add_handler(ChosenInlineResultHandler(handle_chosen_list_result, pattern=r"^list \w+$"))

    # Error handlers
    dispatcher.add_error_handler(handle_error)

    # Start database operations
    updater.job_queue.run_once(load_data, 0)
    updater.job_queue.run_repeating(save_data, 600, first=60)

    # Start the bot
    updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN, webhook_url=WEB_URL + TOKEN)
    updater.idle()


if __name__ == "__main__":
    main()
