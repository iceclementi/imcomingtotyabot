"""Main Interface"""
import os
import logging
import re
import backend
from backend import User, Group, Poll, Option, BotManager
import util
from telegram import (
    Update, ParseMode, User as TeleUser, Message, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup,
    InlineQueryResultArticle, InputTextMessageContent, ForceReply, CallbackQuery, InlineQuery
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
MAX_GROUP_NAME_LENGTH = 50
MIN_GROUP_PASS_LENGTH = 4
MAX_GROUP_PASS_LENGTH = 20
ACCESS_REQUIRED = True  # Set to False if access is not required to access bot

# endregion

# region RESPONSES

ACCESS_REQUEST = "To explore the full potential of this bot, please request for access from the creator \U0001f60e"
ACCESS_ENTER_USER_ID = "Enter the ID of the user you want to give access to."
ACCESS_DENIED = "Sorry, invalid or expired access key."
ACCESS_GRANTED = "Woohoo!! \U0001f973 You now have access to the bot!\n\nUse /start to get started."
USER_PROMOTED = "Yay!! \U0001f389 {} is now a bot leader!!"

NEW_POLL = "Let's create a new poll! First, send me the title."
NEW_POLL_DESCRIPTION = "{}\n\nNice! Now send me a poll description or skip this step."
NEW_OPTION = "{}\n\nAlright, now send me your very first option."
NEXT_OPTION = "Nice! {} added!\n\nNow send me another answer option or press <b>Done</b> to finish."
POLL_DONE = "\U0001f44d Poll created! You may now publish it to a group or send it to your friends."
DELETED_POLL = "Sorry, the poll has been deleted."

NEW_GROUP = "Let's create a new group! To begin, send me the group name."
GROUP_PASSWORD_REQUEST = "{}\n\nGreat! Now enter a secret password for your group or skip this step."
GROUP_DONE = "\U0001f44d Group created! You are now the owner of this group. " \
             "Use /invite to invite your friends to join the group."
DELETED_GROUP = "Sorry, the group has been deleted."
GROUP_INVITATION = "Which group's invite code do you want to send?"

REASON = "You've selected {}.\nPlease enter a reason/comment for your selected option."
START = "Welcome to the bot! \U0001f60a\n\nClick the button below to show available bot commands.\n\n" \
        "Use /help to check the description for each bot command."

ERROR_ACCESS_ALREADY_GRANTED = "You already have access to the bot! Use /start to get started."
ERROR_ALREADY_PROMOTED = "The user is already a bot leader!"
ERROR_TITLE_TOO_LONG = f"Sorry, please enter a shorter title (maximum {MAX_TITLE_LENGTH} characters)."
ERROR_OPTION_TITLE_TOO_LONG = f"Sorry, please enter a shorter title (maximum {MAX_OPTION_TITLE_LENGTH} characters)."
ERROR_EARLY_DONE_TITLE = "Sorry, please add a title to the poll."
ERROR_EARLY_DONE_OPTION = "Sorry, please add at least one option to the poll."
ERROR_GROUP_NAME_EXISTS = "You already have a group with this name. Please enter another group name."
ERROR_GROUP_NAME_TOO_LONG = f"Sorry, please enter a shorter group name (maximum {MAX_GROUP_NAME_LENGTH} characters)."
ERROR_INVALID_GROUP_PASS_FORMAT = \
    f"Sorry, please ensure that you group secret key is between {MIN_GROUP_PASS_LENGTH} and {MAX_GROUP_PASS_LENGTH} " \
    f"characters long and contains only alphanumeric characters."
ERROR_EARLY_DONE_GROUP_NAME = "Sorry, please add a group name."
ERROR_INVALID_GROUP_INVITE = "Sorry, invalid or expired group invitation code."
ERROR_ALREADY_IN_GROUP = "You're already in the group! Use /groups to view all your groups."
ERROR_ILLEGAL_SECRET_CHANGE = "Only group owners can change the group's password!"
ERROR_INVALID_POLL_COMMENT_REQUEST = "Sorry, invalid poll comment request."
ERROR_INVALID_POLL_VOTE_REQUEST = "Sorry, invalid poll vote request."
ERROR_INVALID_POLL_OPTION_REQUEST = "Sorry, invalid poll option request."
ERROR_ALREADY_VOTED = "You've already voted for this option in the poll!"
ERROR_NOT_VOTED = "Sorry, you've not voted for this option in the poll."
ERROR_USER_NOT_FOUND = "Sorry, the user does not exist."

# endregion

# region COMMAND GUIDE

START_GUIDE = "<b>/start</b>\nView the bot's welcome message"
POLL_GUIDE = "<b>/poll</b> &lt;title&gt;\nBuild a new poll with an optional title"
POLLS_GUIDE = "<b>/polls</b>\nView all the polls you have built"
GROUP_GUIDE = "<b>/group</b> &lt;name&gt\nCreate a new group with an optional name"
GROUPS_GUIDE = "<b>/groups</b>\nView all the groups you are in"
INVITE_GUIDE = "<b>/invite</b>\nSend an invite link to your friends to join your group"
HELP_GUIDE = "<b>/help</b>\nView this help message"

# endregion

# region COMMAND HANDLERS


def handle_start(update: Update, context: CallbackContext) -> None:
    """Displays welcome message to the bot and manages pm messages."""
    update.message.delete()
    delete_old_chat_message(update, context)

    arguments = context.args
    if not arguments:
        update.message.reply_html(
            START,
            reply_markup=util.build_multiple_buttons_markup(
                util.generate_button_details("View Commands", "/", True, True),
                util.generate_button_details("Close", backend.CLOSE)
            )
        )
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
    # Handle vote
    elif action == "vote":
        handle_vote_pm(update, context, details)
        return
    # Handle others
    else:
        handle_help(update, context)
        return


def handle_pm_command(command: str, update: Update, context: CallbackContext) -> None:
    """Manages standard commands in pm mode with the bot."""
    if command == "start":
        handle_start(update, context)
        return
    elif command == "poll":
        title = context.user_data.get("title", "")
        update.message.text = f"/{command} {title}"
        handle_poll(update, context)
        return
    elif command == "polls":
        handle_polls(update, context)
        return
    elif command == "group":
        name = context.user_data.get("name", "")
        update.message.text = f"/{command} {name}"
        handle_group(update, context)
        return
    elif command == "groups":
        handle_groups(update, context)
        return
    elif command == "invite":
        handle_invite(update, context)
        return
    elif command == "enrol":
        handle_enrol(update, context)
        return
    elif command == "promote":
        handle_promote(update, context)
        return
    elif command == "help":
        handle_help(update, context)
        return


def handle_bot_access_pm(update: Update, context: CallbackContext, details: str) -> None:
    """Handles user joining group through group invite code."""
    invitation_code = details
    uid = update.effective_user.id

    user = User.get_user_by_id(uid)
    if user:
        update.message.reply_html(
            ERROR_ACCESS_ALREADY_GRANTED, reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
        )
        logger.info("Bot access already granted!")
        return

    if invitation_code == BotManager.get_bot_token_hash(ACCESS_KEY, uid):
        register_user(update.effective_user)
        update.message.reply_html(ACCESS_GRANTED, reply_markup=util.build_single_button_markup("Close", backend.CLOSE))
        return

    update.message.reply_html(ACCESS_DENIED, reply_markup=util.build_single_button_markup("Close", backend.CLOSE))
    logger.warning("Invalid bot access attempt!!")
    return


def handle_join_pm(update: Update, context: CallbackContext, details: str) -> None:
    """Handles user joining group through group invite code."""
    invitation_code = details
    try_join_group_through_invitation(update, invitation_code)
    return


def handle_vote_pm(update: Update, context: CallbackContext, details: str) -> None:
    """Handles user voting for poll option that requires comment."""
    match = re.match(r"^([^_\W]+_[^_\W]+)$", details)
    if not match:
        update.message.reply_html(
            ERROR_INVALID_POLL_COMMENT_REQUEST, reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
        )
        logger.warning("Invalid poll comment request!")
        return

    poll_hash = match.group(1)
    poll_id = poll_hash.split("_")[0]
    poll = Poll.get_poll_by_id(poll_id)

    if not poll or poll.get_poll_hash() != poll_hash:
        update.message.reply_html(
            ERROR_INVALID_POLL_COMMENT_REQUEST, reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
        )
        logger.warning("Invalid poll comment request!")
        return

    response, buttons = poll.build_option_comment_text_and_buttons(update.effective_user.id)
    reply_message = update.message.reply_html(response, reply_markup=buttons)
    delete_message_with_timer(reply_message, 300)
    return


def handle_comment_pm(update: Update, context: CallbackContext, details: str) -> None:
    """Handles user adding or changing comment for a poll option."""
    match = re.match(r"^([^_\W]+_[^_\W]+)_(\d+)$", details)
    if not match:
        update.message.reply_html(
            ERROR_INVALID_POLL_VOTE_REQUEST, reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
        )
        logger.warning("Invalid poll vote request!")
        return

    poll_hash, opt_id = match.group(1), int(match.group(2))
    poll_id = poll_hash.split("_")[0]
    poll = Poll.get_poll_by_id(poll_id)

    if not poll or poll.get_poll_hash() != poll_hash:
        update.message.reply_html(
            ERROR_INVALID_POLL_VOTE_REQUEST, reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
        )
        logger.warning("Invalid poll vote request!")
        return

    if opt_id >= len(poll.get_options()):
        update.message.reply_html(
            ERROR_INVALID_POLL_OPTION_REQUEST, reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
        )
        logger.warning("Invalid option selected from poll vote!")
        return

    option = poll.get_options()[opt_id]

    if option.is_voted_by_user(update.effective_user.id):
        response = poll.toggle(opt_id, uid, user_profile)

        reply_message = update.message.reply_html(
            response, reply_markup=util.build_single_switch_button_markup("Return To Chat", "")
        )

        reply_message.delete()
        refresh_polls(poll, context)
        return

    reply_message = update.message.reply_html(
        REASON.format(util.make_html_bold(option.get_title())),
        reply_markup=util.build_single_button_markup("Close", backend.RESET),
    )
    context.user_data.update({"action": "vote", "pid": poll_id, "opt": opt_id, "del": reply_message.message_id})
    delete_message_with_timer(reply_message, 900)
    return


def handle_access(update: Update, context: CallbackContext) -> None:
    """Manages different accesses in the bot."""
    delete_chat_message(update.message)

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
        reply_markup=util.build_single_button_markup("Cancel", backend.RESET)
    )
    context.user_data.update({"action": "bot_access", "del": reply_message.message_id})
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
            ERROR_USER_NOT_FOUND, reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
        )
        return

    if user.is_leader():
        update.message.reply_html(
            ERROR_ALREADY_PROMOTED, reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
        )
        return

    user.promote_to_leader()
    update.message.reply_html(
        USER_PROMOTED.format(util.make_html_bold(user.get_name())),
        reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
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

    context.user_data.update({"action": "poll", "title": "", "descr": "", "options": []})

    match = re.match(r"^\s*/poll\s+(.+)$", update.message.text.strip())
    if not match:
        reply_message = update.message.reply_html(
            NEW_POLL, reply_markup=util.build_single_button_markup("Cancel", backend.RESET)
        )
        context.user_data.update({"del": reply_message.message_id})
        return

    title = match.group(1)

    if len(title) > MAX_TITLE_LENGTH:
        reply_message = update.message.reply_html(
            ERROR_TITLE_TOO_LONG, reply_markup=util.build_single_button_markup("Cancel", backend.RESET)
        )
        context.user_data.update({"del": reply_message.message_id})
        return

    bold_title = util.make_html_bold_first_line(title)
    response = NEW_POLL_DESCRIPTION.format(bold_title)
    reply_message = update.message.reply_html(
        response, reply_markup=util.build_multiple_buttons_markup(
            util.generate_button_details("Skip", backend.SKIP),
            util.generate_button_details("Cancel", backend.RESET)
        )
    )
    context.user_data.update({"title": title, "del": reply_message.message_id})
    return


def handle_polls(update: Update, context: CallbackContext) -> None:
    """Displays all recent polls created by user."""
    delete_chat_message(update.message)
    delete_old_chat_message(update, context)
    context.user_data.clear()

    if not is_registered(update.effective_user):
        handle_help(update, context)
        return

    uid = update.effective_user.id

    header = [util.make_html_bold("Your Polls")]

    recent_polls = User.get_user_by_id(uid).get_polls(limit=20)
    if recent_polls:
        body = [f"{i}. {poll.generate_linked_summary()}" for i, poll in enumerate(recent_polls, 1)]
    else:
        body = [util.make_html_italic("You have no polls! Use /poll to build a new poll.")]

    response = "\n\n".join(header + body)
    update.message.reply_html(response, reply_markup=util.build_single_button_markup("Close", backend.CLOSE))
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

    poll_id = re.match(r"^/poll_(\w+).*$", text).group(1)
    poll = Poll.get_poll_by_id(poll_id)
    if not poll:
        handle_help(update, context)
        return

    if poll.get_creator_id() == uid or User.get_user_by_id(uid).has_group_poll(poll_id):
        deliver_poll(update, poll)
        return

    handle_help(update, context)
    return


def handle_group(update: Update, context: CallbackContext) -> None:
    """Begins creating a new group."""
    delete_chat_message(update.message)
    delete_old_chat_message(update, context)

    if not is_registered(update.effective_user):
        handle_help(update, context)
        return

    user = User.get_user_by_id(update.effective_user.id)
    if not user.is_leader():
        handle_help(update, context)
        return

    context.user_data.clear()
    context.user_data.update({"action": "group", "name": "", "secret": ""})

    match = re.match(r"^\s*/group\s+(.+)$", update.message.text.strip())
    if not match:
        reply_message = update.message.reply_html(
            NEW_GROUP, reply_markup=util.build_single_button_markup("Cancel", backend.RESET)
        )
        context.user_data.update({"del": reply_message.message_id})
        return

    group_name = match.group(1).replace("\n", " ")

    if len(group_name) > MAX_GROUP_NAME_LENGTH:
        reply_message = update.message.reply_html(
            ERROR_GROUP_NAME_TOO_LONG, reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
        )
        context.user_data.update({"del": reply_message.message_id})
        return

    if User.get_user_by_id(update.effective_user.id).has_group_with_name(group_name):
        reply_message = update.message.reply_html(
            ERROR_GROUP_NAME_EXISTS, reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
        )
        context.user_data.update({"del": reply_message.message_id})
        return

    response = GROUP_PASSWORD_REQUEST.format(util.make_html_bold(group_name))
    reply_message = update.message.reply_html(
        response, reply_markup=util.build_single_button_markup("Cancel", backend.RESET)
    )
    context.user_data.update({"name": group_name, "del": reply_message.message_id})
    return


def handle_groups(update: Update, context: CallbackContext) -> None:
    """Views all the user's groups."""
    delete_chat_message(update.message)
    delete_old_chat_message(update, context)
    context.user_data.clear()

    if not is_registered(update.effective_user):
        handle_help(update, context)
        return

    uid = update.effective_user.id

    header = [util.make_html_bold("Your Groups")]

    user = User.get_user_by_id(uid)

    owned_groups_title = util.make_html_bold(f"Owned Groups {backend.EMOJI_CROWN}")
    owned_groups = user.get_owned_groups()
    if owned_groups:
        owned_groups_list = "\n\n".join(
            f"{i}. {group.generate_linked_summary()}" for i, group in enumerate(owned_groups, 1)
        )
    else:
        owned_groups_list = util.make_html_italic("You do not own any group!")
    owned_groups_summary = f"{owned_groups_title}\n{owned_groups_list}"

    joined_groups_title = util.make_html_bold(f"Joined Groups")
    joined_groups = user.get_joined_groups()
    if joined_groups:
        joined_groups_list = "\n\n".join(
            f"{i}. {group.generate_linked_summary()}" for i, group in enumerate(joined_groups, 1)
        )
    else:
        joined_groups_list = util.make_html_italic("You have not joined any group!")
    joined_groups_summary = f"{joined_groups_title}\n{joined_groups_list}"

    body = [owned_groups_summary] + [joined_groups_summary]

    response = "\n\n".join(header + body)
    update.message.reply_html(response, reply_markup=util.build_single_button_markup("Close", backend.CLOSE))
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
    user = User.get_user_by_id(uid)

    header = [util.make_html_bold("Available Bot Commands")]

    body = [START_GUIDE]
    if user:
        if user.is_leader():
            body += [POLL_GUIDE, POLLS_GUIDE, GROUP_GUIDE, GROUPS_GUIDE, INVITE_GUIDE]
        else:
            body += [POLL_GUIDE, POLLS_GUIDE, GROUPS_GUIDE, INVITE_GUIDE]
    body += [HELP_GUIDE]

    if not user:
        body += [util.make_html_italic(ACCESS_REQUEST)]

    response = "\n\n".join(header + body)
    update.message.reply_html(response, reply_markup=util.build_single_button_markup("Close", backend.CLOSE))
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

    user, is_leader, _ = get_user_permissions(update.effective_user.id)

    # Check if current action is poll
    action = context.user_data.get("action", "")
    if action == "bot_access":
        handle_bot_access_conversation(update, context)
        return
    elif action == "poll":
        handle_poll_conversation(update, context)
        return
    elif action == "vote":
        handle_vote_conversation(update, context)
        return
    elif action == "comment":
        handle_comment_conversation(update, context)
        return
    elif action == "group" and is_leader:
        handle_group_conversation(update, context)
        return
    elif action == "pass" and is_leader:
        handle_change_secret_conversation(update, context)
        return

    if is_private_chat(update.message):
        handle_help(update, context)
        return


def handle_bot_access_conversation(update: Update, context: CallbackContext) -> None:
    """Handles the conversation between the bot and the admin user to generate a bot access invitation."""
    uid = update.message.text.strip()

    delete_chat_message(update.message)
    delete_old_chat_message(update, context)

    _, _, is_admin = get_user_permissions(update.effective_user.id)

    if not is_admin:
        logger.warning("Illegal bot access callback")
        handle_help(update, context)
        return

    if not uid.isdigit():
        response = "You've entered an invalid user id. Please enter again."
        buttons = util.build_single_button_markup("Cancel", backend.RESET)
        reply_message = update.message.reply_html(response, reply_markup=buttons)
        context.user_data.update({"del": reply_message.message_id})
        return

    response, buttons = BotManager.build_bot_access_enrol_text_and_button(int(uid))
    update.message.reply_html(response, reply_markup=buttons)
    context.user_data.clear()
    return


def handle_poll_conversation(update: Update, context: CallbackContext) -> None:
    """Handles the conversation between the bot and the user to build a poll."""
    text = update.message.text.strip()
    title, description, options = \
        context.user_data.get("title", ""), context.user_data.get("descr", ""), context.user_data.get("options", [])

    delete_chat_message(update.message)
    delete_old_chat_message(update, context)

    # Handle title
    if not title:
        if len(text) > MAX_TITLE_LENGTH:
            reply_message = update.message.reply_html(
                ERROR_TITLE_TOO_LONG, reply_markup=util.build_single_button_markup("Cancel", backend.RESET)
            )
            context.user_data.update({"del": reply_message.message_id})
            return

        bold_title = util.make_html_bold_first_line(text)
        response = NEW_POLL_DESCRIPTION.format(bold_title)
        reply_message = update.message.reply_html(
            response, reply_markup=util.build_multiple_buttons_markup(
                util.generate_button_details("Skip", backend.SKIP),
                util.generate_button_details("Cancel", backend.RESET)
            )
        )
        context.user_data.update({"title": text, "del": reply_message.message_id})
        return
    if not description:
        response = NEW_OPTION.format("Awesome! Description added!")
        reply_message = update.message.reply_html(
            response, reply_markup=util.build_multiple_buttons_markup(
                util.generate_button_details("Cancel", backend.RESET)
            )
        )
        context.user_data.update({"descr": text, "del": reply_message.message_id})
        return

    # Handle option
    else:
        if not options:
            buttons = util.build_single_button_markup("Cancel", backend.RESET)
        else:
            buttons = util.build_multiple_buttons_markup(
                util.generate_button_details("Done", backend.DONE),
                util.generate_button_details("Cancel", backend.RESET)
            )

        if len(text) > MAX_OPTION_TITLE_LENGTH:
            reply_message = update.message.reply_html(ERROR_OPTION_TITLE_TOO_LONG, reply_markup=buttons)
            context.user_data.update({"del": reply_message.message_id})
            return

        options.append(text)

        if len(options) < 10:
            reply_message = update.message.reply_html(
                NEXT_OPTION.format(util.make_html_bold(text)), reply_markup=buttons
            )
            context.user_data.update({"options": options, "del": reply_message.message_id})
            return

        # Create poll
        poll, _ = User.get_user_by_id(update.effective_user.id).create_poll(title, description.strip(), options)

        update.message.reply_html(POLL_DONE, reply_markup=util.build_single_button_markup("Close", backend.CLOSE))
        deliver_poll(update, poll)

        # Clear user data
        context.user_data.clear()


def handle_vote_conversation(update: Update, context: CallbackContext) -> None:
    """Handles the conversation between the bot and the user to vote a poll option."""
    poll_id = context.user_data.get("pid", "")
    opt_id = int(context.user_data.get("opt", -1))
    uid, user_profile = extract_user_data(update.effective_user)

    delete_chat_message(update.message),
    delete_old_chat_message(update, context)
    context.user_data.clear()

    poll = Poll.get_poll_by_id(poll_id)
    if not poll:
        update.message.reply_html(DELETED_POLL, reply_markup=util.build_single_button_markup("Close", backend.CLOSE))
        logger.warning("Poll deleted before vote.")
        return

    if opt_id >= len(poll.get_options()) or opt_id < 0:
        update.message.reply_html(
            ERROR_INVALID_POLL_OPTION_REQUEST, reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
        )
        logger.warning("Invalid option selected from poll vote!")
        return

    if poll.get_options()[opt_id].is_voted_by_user(uid):
        update.message.reply_html(
            ERROR_ALREADY_VOTED, reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
        )
        logger.warning("Poll option already voted by user!")
        return

    response = poll.toggle(opt_id, uid, user_profile, update.message.text)

    reply_message = update.message.reply_html(
        util.make_html_bold(f"{response} {backend.EMOJI_HAPPY}"),
        reply_markup=util.build_single_switch_button_markup("Return To Chat", "")
    )

    reply_message.delete()
    refresh_polls(poll, context)
    return


def handle_comment_conversation(update: Update, context: CallbackContext) -> None:
    """Handles the conversation between the bot and the user to comment a poll option."""
    poll_id = context.user_data.get("pid", "")
    opt_id = int(context.user_data.get("opt", -1))
    uid, user_profile = extract_user_data(update.effective_user)

    delete_chat_message(update.message),
    delete_old_chat_message(update, context)
    context.user_data.clear()

    poll = Poll.get_poll_by_id(poll_id)
    if not poll:
        update.message.reply_html(DELETED_POLL, reply_markup=util.build_single_button_markup("Close", backend.CLOSE))
        logger.warning("Poll deleted before vote.")
        return

    if opt_id >= len(poll.get_options()) or opt_id < 0:
        update.message.reply_html(
            ERROR_INVALID_POLL_OPTION_REQUEST, reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
        )
        logger.warning("Invalid option selected from poll vote!")
        return

    if not poll.get_options()[opt_id].is_voted_by_user(uid):
        update.message.reply_html(
            ERROR_NOT_VOTED, reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
        )
        logger.warning("Poll option not voted by user!")
        return

    poll.edit_user_comment(opt_id, uid, update.message.text)

    reply_message = update.message.reply_html(
        util.make_html_bold(f"Comment updated successfully! {backend.EMOJI_HAPPY}"),
        reply_markup=util.build_single_switch_button_markup("Return To Chat", "")
    )

    reply_message.delete()
    refresh_polls(poll, context)
    return


def handle_group_conversation(update: Update, context: CallbackContext) -> None:
    """Handles the conversation between the bot and the user to create a group."""
    text = update.message.text.strip()
    group_name, secret = context.user_data.get("name", ""), context.user_data.get("secret", "")

    delete_chat_message(update.message)
    delete_old_chat_message(update, context)



    # Handle group name
    if not group_name:
        group_name = text.replace("\n", " ")
        if len(group_name) > MAX_GROUP_NAME_LENGTH:
            reply_message = update.message.reply_html(
                ERROR_GROUP_NAME_TOO_LONG, reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
            )
            context.user_data.update({"del": reply_message.message_id})
            return

        if User.get_user_by_id(update.effective_user.id).has_group_with_name(group_name):
            reply_message = update.message.reply_html(
                ERROR_GROUP_NAME_EXISTS, reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
            )
            context.user_data.update({"del": reply_message.message_id})
            return

        response = GROUP_PASSWORD_REQUEST.format(util.make_html_bold(group_name))
        reply_message = update.message.reply_html(
            response, reply_markup=util.build_single_button_markup("Cancel", backend.RESET)
        )
        context.user_data.update({"name": group_name, "del": reply_message.message_id})
        return
    # Handle secret
    if not re.match(r"^[A-Za-z0-9]{4,20}$", text):
        reply_message = update.message.reply_html(
            ERROR_INVALID_GROUP_PASS_FORMAT, reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
        )
        context.user_data.update({"del": reply_message.message_id})
        return

    # Create group
    group, _ = User.get_user_by_id(update.effective_user.id).create_group(group_name, text)

    update.message.reply_html(GROUP_DONE, reply_markup=util.build_single_button_markup("Close", backend.CLOSE))
    deliver_group(update, group)

    # Clear user data
    context.user_data.clear()
    return


def handle_change_secret_conversation(update: Update, context: CallbackContext) -> None:
    """Handles the conversation between the bot and the user to change the group secret."""
    gid = context.user_data.get("gid", "")

    delete_chat_message(update.message)
    delete_old_chat_message(update, context)

    group = Group.get_group_by_id(gid)
    if not group or group.get_owner() != update.effective_user.id:
        update.message.reply_html(
            util.make_html_bold(ERROR_ILLEGAL_SECRET_CHANGE),
            reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
        )
        logger.warning("Illegal password change!")
        return

    new_secret = update.message.text.strip()

    if not re.match(r"^[A-Za-z0-9]{4,20}$", new_secret):
        reply_message = update.message.reply_html(
            ERROR_INVALID_GROUP_PASS_FORMAT, reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
        )
        context.user_data.update({"del": reply_message.message_id})
        return

    # Change password
    group.edit_password(new_secret)
    update.message.reply_html(
        "Group password changed!", reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
    )

    # Clear user data
    context.user_data.clear()
    return


# endregion

# region CALLBACK QUERY HANDLERS


def handle_callback_query(update: Update, context: CallbackContext) -> None:
    """Handles a callback query."""
    query = update.callback_query

    match = re.match(r"^(\w+)\s+(\w+)\s+(\w+)$", query.data)
    if not match:
        handle_general_callback_query(query, update, context, query.data)
        return

    subject, action, identifier = match.group(1), match.group(2), match.group(3)

    if subject == backend.USER_SUBJECT:
        handle_user_callback_query(query, context, action, identifier)
    if subject == backend.POLL_SUBJECT:
        handle_poll_callback_query(query, context, action, identifier)
    elif subject == backend.GROUP_SUBJECT:
        handle_group_callback_query(query, context, action, identifier)
    else:
        logger.warning("Invalid callback query data.")
        query.answer(text="Invalid callback query data!")

    return


def handle_general_callback_query(query: CallbackQuery, update: Update, context: CallbackContext, action: str) -> None:
    """Handles a general callback query."""
    user, is_leader, is_admin = get_user_permissions(query.from_user.id)

    # Handle bot access button
    if action == backend.BOT_ACCESS and is_admin:
        query.answer(text=ACCESS_ENTER_USER_ID)
        reply_message = query.edit_message_text(
            ACCESS_ENTER_USER_ID, parse_mode=ParseMode.HTML,
            reply_markup=util.build_single_button_markup("Cancel", backend.RESET)
        )
        context.user_data.update({"action": "bot_access", "del": reply_message.message_id})
        return
    # Handle leader access button
    elif action == backend.PROMOTE and is_admin:
        response, buttons = BotManager.build_leader_promote_invite_text_and_button()
        query.answer(response)
        query.edit_message_text(response, parse_mode=ParseMode.HTML, reply_markup=buttons)
        return
    # Handle skip button
    elif action == backend.SKIP:
        user_action = context.user_data.get("action", "")
        if user_action == "poll":
            response = NEW_OPTION.format("")
            reply_message = query.edit_message_text(
                response, parse_mode=ParseMode.HTML, reply_markup=util.build_multiple_buttons_markup(
                    util.generate_button_details("Cancel", backend.RESET)
                )
            )
            context.user_data.update({"descr": " ", "del": reply_message.message_id})
            return
        elif user_action == "group":
            pass
        else:
            query.answer(text="Invalid callback query data!")
            logger.warning("Invalid callback query data.")
            return
        return
    # Handle done button
    elif action == backend.DONE:
        user_action = context.user_data.get("action", "")
        handle_done_callback_query(query, update, context, user_action)
        return
    # Handle close button
    elif action == backend.CLOSE:
        query.message.delete()
        query.answer(text=None)
        return
    # Handle reset button
    elif action == backend.RESET:
        query.message.delete()
        query.answer(text=None)
        context.user_data.clear()
        return
    else:
        query.answer(text="Invalid callback query data!")
        logger.warning("Invalid callback query data.")
        return


def handle_done_callback_query(query: CallbackQuery, update: Update, context: CallbackContext, action: str) -> None:
    """Handles done button callbacks."""
    if not is_registered(update.effective_user):
        query.message.delete()
        query.answer(text="Invalid callback query data!")
        logger.warning("Invalid callback query data.")
        return

    # Handle poll
    if action == "poll":
        title, description, options = \
            context.user_data.get("title", ""), context.user_data.get("descr", ""), context.user_data.get("options", [])

        # Check if there is a title
        if not title:
            reply_message = query.edit_message_text(
                ERROR_EARLY_DONE_TITLE, parse_mode=ParseMode.HTML,
                reply_markup=util.build_single_button_markup("Cancel", backend.RESET)
            )
            context.user_data.update({"del": reply_message.message_id})
            return

        # Check if there are options
        if not options:
            reply_message = query.edit_message_text(
                ERROR_EARLY_DONE_OPTION, parse_mode=ParseMode.HTML,
                reply_markup=util.build_single_button_markup("Cancel", backend.RESET)
            )
            context.user_data.update({"del": reply_message.message_id})
            return

        # Create poll
        poll, _ = User.get_user_by_id(update.effective_user.id).create_poll(title, description.strip(), options)

        query.message.reply_html(POLL_DONE, reply_markup=util.build_single_button_markup("Close", backend.CLOSE))
        deliver_poll(update, poll)

        # Clear user data
        context.user_data.clear()
        return
    # Handle group
    elif action == "group":
        group_name = context.user_data.setdefault("name", "")

        # Check if there is a group name
        if not group_name:
            reply_message = query.edit_message_text(
                ERROR_EARLY_DONE_GROUP_NAME, parse_mode=ParseMode.HTML,
                reply_markup=util.build_single_button_markup("Cancel", backend.RESET)
            )
            context.user_data.update({"del": reply_message.message_id})
            return

        # Create group
        group, _ = User.get_user_by_id(update.effective_user.id).create_group(group_name, "")

        query.message.reply_html(GROUP_DONE, reply_markup=util.build_single_button_markup("Close", backend.CLOSE))
        deliver_group(update, group)

        # Clear user data
        context.user_data.clear()
        return
    else:
        query.message.delete()
        query.answer(text="Invalid callback query data!")
        logger.warning("Invalid callback query data.")
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
    if action == backend.PROMOTE and is_pm and is_admin:
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
        query.edit_message_reply_markup(None)
        query.answer(text=DELETED_POLL)
        return

    uid, user_profile = extract_user_data(query.from_user)
    message = query.message
    is_pm = is_private_chat(message)

    # Handle poll option button
    if action.isdigit():
        status = poll.toggle(int(action), uid, user_profile)
        query.edit_message_text(poll.render_text(), parse_mode=ParseMode.HTML, reply_markup=poll.build_option_buttons())
        query.answer(text=status)
        refresh_polls(poll, context)
        return
    # Handle refresh option button
    elif action == backend.REFRESH_OPT:
        query.answer(text="Results updated!")
        query.edit_message_text(poll.render_text(), parse_mode=ParseMode.HTML, reply_markup=poll.build_option_buttons())
        return
    # Handle refresh button
    elif action == backend.REFRESH and is_pm:
        query.answer(text="Results updated!")
        query.edit_message_text(
            poll.render_text(), parse_mode=ParseMode.HTML, reply_markup=poll.build_admin_buttons(uid)
        )
        return
    # Handle customise button
    elif action == backend.CUSTOMISE and is_pm:
        query.edit_message_reply_markup(poll.build_customise_buttons())
        query.answer(text=None)
        return
    # Handle toggle response button
    elif action == backend.RESPONSE and is_pm:
        status = poll.toggle_response_type()
        query.answer(text=status)
        query.edit_message_reply_markup(poll.build_customise_buttons())
        return
    # Handle enforce comments button
    elif action == backend.COMMENT and is_pm:
        query.edit_message_reply_markup(poll.build_option_comment_required_buttons())
        query.answer(text=None)
        return
    # Handle toggle comments required button
    elif action.startswith(f"{backend.COMMENT}_") and is_pm:
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
    # Handle vote button
    elif action == backend.VOTE and is_pm:
        query.edit_message_reply_markup(poll.build_option_buttons())
        query.answer(text="You may now vote!")
        return
    # Handle edit comment button
    elif action.startswith(f"{backend.EDIT_COMMENT}_") and is_pm:
        _, opt_id = action.rsplit("_", 1)
        if not opt_id.isdigit():
            logger.warning("Invalid callback query data.")
            query.answer(text="Invalid callback query data!")
            return

        opt_id = int(opt_id)

        if opt_id >= len(poll.get_options()):
            query.answer(text=ERROR_INVALID_POLL_OPTION_REQUEST)
            logger.warning("Invalid option selected from poll vote!")
            return

        option = poll.get_options()[opt_id]

        reply_message = message.reply_html(
            REASON.format(util.make_html_bold(option.get_title())),
            reply_markup=util.build_single_button_markup("Close", backend.RESET),
        )
        context.user_data.update({"action": "comment", "pid": poll_id, "opt": opt_id, "del": reply_message.message_id})
        message.delete()
        delete_message_with_timer(reply_message, 900)
        query.answer(text="Please enter a reason/comment for your selected option.")
        return
    # Handle delete button
    elif action == backend.DELETE and is_pm:
        query.edit_message_reply_markup(poll.build_delete_confirmation_buttons())
        query.answer(text="Confirm delete?")
        return
    # Handle delete confirmation button
    elif action == backend.DELETE_YES and is_pm:
        User.get_user_by_id(uid).delete_poll(poll_id)
        message.delete()
        query.answer(text="Poll deleted!")
        for mid in poll.get_message_details():
            context.bot.edit_message_reply_markup(
                inline_message_id=mid, reply_markup=None
            )
        return
    # Handle back button
    elif action == backend.BACK and is_pm:
        query.edit_message_reply_markup(poll.build_admin_buttons(uid))
        query.answer(text=None)
        return
    # Handle close button
    elif action == backend.CLOSE:
        message.delete()
        query.answer(text=None)
        return
    # Handle other cases
    else:
        logger.warning("Invalid callback query data.")
        query.answer(text="Invalid callback query data!")
        query.edit_message_reply_markup(None)
        return


def handle_group_callback_query(query: CallbackQuery, context: CallbackContext, action: str, gid: str) -> None:
    """Handles a group callback query."""
    if not is_private_chat(query.message):
        return

    group = Group.get_group_by_id(gid)

    # Group is deleted or has error
    if not group:
        query.edit_message_reply_markup(None)
        query.answer(text=DELETED_GROUP)
        return

    uid, user_profile = extract_user_data(query.from_user)
    message = query.message
    is_owner = group.get_owner() == uid

    # User is no longer in the group
    if uid not in group.get_member_ids():
        query.edit_message_reply_markup(None)
        query.answer(text="You are not a member of this group.")
        return

    # Handle view members button
    if action == backend.VIEW_MEMBERS:
        query.edit_message_text(
            group.render_group_members_text(), parse_mode=ParseMode.HTML,
            reply_markup=group.build_members_view_buttons(back_action=backend.BACK, is_owner=is_owner)
        )
        query.answer(text=None)
        return
    # Handle remove member button
    elif action == backend.REMOVE_MEMBER and is_owner:
        query.edit_message_reply_markup(
            group.build_members_buttons(backend.REMOVE_MEMBER, back_action=backend.VIEW_MEMBERS)
        )
        query.answer(text="Select a member to remove.")
        return
    # Handle remove member choice button
    elif action.startswith(f"{backend.REMOVE_MEMBER}_") and is_owner:
        _, uid = action.rsplit("_", 1)
        member_name = User.get_user_by_id(uid).get_name()
        query.edit_message_reply_markup(
            group.build_delete_confirmation_buttons(
                delete_text="Remove", delete_action=action, back_action=backend.REMOVE_MEMBER
            )
        )
        query.answer(text=f"Confirm remove {member_name} from the group?")
        return
    # Handle delete confirmation button
    elif action.startswith(f"{backend.DELETE_YES}_"):
        match = re.match(r"^([^_\W]+)_([^_\W]+)_?([^_\W]+)?$", action)
        if not match:
            logger.warning("Invalid callback query data.")
            query.answer(text="Invalid callback query data!")
            query.edit_message_text(group.render_group_details_text(), parse_mode=ParseMode.HTML,
                                    reply_markup=group.build_group_details_buttons())

        sub_action, identifier = match.group(2), match.group(3)
        if sub_action == backend.REMOVE_MEMBER and is_owner:
            status = group.remove_member(identifier)
            query.answer(text=status)
            query.edit_message_text(group.render_group_members_text(), parse_mode=ParseMode.HTML,
                                    reply_markup=group.build_members_view_buttons(back_action=backend.BACK))
            return
        elif sub_action == backend.DELETE and is_owner:
            status = User.get_user_by_id(uid).delete_group(gid)
            query.answer(text=status)
            query.message.delete()
            return
        elif sub_action == backend.LEAVE_GROUP:
            group.remove_member(uid)
            query.answer("You have left the group.")
            query.edit_message_reply_markup(None)
            return
        else:
            logger.warning("Invalid callback query data.")
            query.answer(text="Invalid callback query data!")
            query.edit_message_text(group.render_group_details_text(), parse_mode=ParseMode.HTML,
                                    reply_markup=group.build_group_details_buttons())
            return
    # Handle view group polls button
    elif action == backend.VIEW_GROUP_POLLS:
        query.edit_message_text(group.render_group_polls_text(), parse_mode=ParseMode.HTML,
                                reply_markup=group.build_polls_view_buttons(back_action=backend.BACK))
        query.answer(text=None)
        return
    # Handle add poll button and add poll choice button
    elif action.startswith(backend.ADD_POLL):
        answered = False
        if "_" in action:
            _, poll_id = action.rsplit("_", 1)
            poll = Poll.get_poll_by_id(poll_id)
            if not poll:
                query.answer(text="Poll does not exist.")
            else:
                result = group.add_poll(poll_id)
                query.answer(text=result)
            answered = True

        user = User.get_user_by_id(uid)
        response, buttons = group.build_polls_text_and_buttons(
            user.get_polls(), filter_out=True, limit=30, action=backend.ADD_POLL, back_action=backend.VIEW_GROUP_POLLS
        )

        if not response:
            response = util.make_html_italic(
                "You do not have any more polls to add to this group. You can use /poll to create new polls."
            )
            query.edit_message_text(response, parse_mode=ParseMode.HTML, reply_markup=buttons)
            if not answered:
                query.answer(text="Sorry, no available polls to add.")
            return

        header = [util.make_html_bold("Select the poll you wish to add:")]
        response = "\n\n".join(header + [response])

        query.edit_message_text(response, parse_mode=ParseMode.HTML, reply_markup=buttons)
        if not answered:
            query.answer(text="Select a poll you wish to add.")
        return
    # Handle remove poll button an remove poll choice button
    elif action.startswith(backend.REMOVE_POLL):
        answered = False
        if "_" in action:
            _, poll_id = action.rsplit("_", 1)
            poll = Poll.get_poll_by_id(poll_id)
            if not poll:
                query.answer(text="Poll does not exist.")
            else:
                result = group.remove_poll(poll_id)
                query.answer(text=result)
            answered = True

        user = User.get_user_by_id(uid)
        filters = group.get_polls() if is_owner else user.get_polls()
        response, buttons = group.build_polls_text_and_buttons(
            filters, filter_out=False, limit=30, action=backend.REMOVE_POLL, back_action=backend.VIEW_GROUP_POLLS
        )

        if not response:
            response = util.make_html_italic(
                "There are no polls that you can remove."
            )
            query.edit_message_text(response, parse_mode=ParseMode.HTML, reply_markup=buttons)
            if not answered:
                query.answer(text="Sorry, no available polls to remove.")
            return

        header = [util.make_html_bold("Select the poll you wish to remove:")]
        response = "\n\n".join(header + [response])

        query.edit_message_text(response, parse_mode=ParseMode.HTML, reply_markup=buttons)
        if not answered:
            query.answer(text="Select a poll you wish to remove.")
        return
    # Handle settings button
    elif action == backend.GROUP_SETTINGS:
        query.edit_message_reply_markup(group.build_settings_buttons(is_owner=is_owner))
        query.answer(text=None)
        return
    # Handle delete group button
    elif action == backend.DELETE and is_owner:
        query.edit_message_reply_markup(group.build_delete_confirmation_buttons(
            delete_text="Delete", delete_action=action, back_action=backend.GROUP_SETTINGS)
        )
        query.answer(text="Confirm delete group?")
    # Handle leave group button
    elif action == backend.LEAVE_GROUP:
        query.edit_message_reply_markup(group.build_delete_confirmation_buttons(
            delete_text="Leave", delete_action=action, back_action=backend.GROUP_SETTINGS)
        )
        query.answer(text="Confirm leave group?")
    # Handle change password button
    elif action == backend.CHANGE_SECRET and is_owner:
        query.message.reply_html("Enter a new secret password for your group.")
        query.answer(text="Enter a new secret password.")
        context.user_data.clear()
        context.user_data.update({"action": "pass", "gid": gid})
        return
    # Handle back button
    elif action == backend.BACK:
        query.edit_message_text(group.render_group_details_text(), parse_mode=ParseMode.HTML,
                                reply_markup=group.build_group_details_buttons())
        query.answer(text=None)
        return
    # Handle close button
    elif action == backend.CLOSE:
        message.delete()
        query.answer(text=None)
        return
    # Handle other cases
    else:
        logger.warning("Invalid callback query data.")
        query.answer(text="Invalid callback query data!")
        query.edit_message_reply_markup(None)
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
    match = re.match(r"^/(vote|comment|join|access)\s+(\w+)$", text)
    if match:
        handle_inline_pm_query(query, match.group(1), match.group(2))
        return

    # Display incomplete commands
    match = re.match(r"^/([a-z]*)$", text)
    if match and is_sender:
        command = match.group(1)
        # Handle start query
        if "star".startswith(command):
            query_result = InlineQueryResultArticle(
                id="startcom", title="/start", description="View the bot's welcome message",
                input_message_content=InputTextMessageContent("/start")
            )
            results.append(query_result)
        # Handle poll query
        if "pol".startswith(command) and user:
            query_result = InlineQueryResultArticle(
                id="pollcom", title="/poll", description="Build a new poll",
                input_message_content=InputTextMessageContent("/poll")
            )
            results.append(query_result)
        # Handle polls query
        if "poll".startswith(command) and user:
            query_result = InlineQueryResultArticle(
                id="pollscom", title="/polls", description="View all the polls you have built",
                input_message_content=InputTextMessageContent("/polls")
            )
            results.append(query_result)
        # Handle group query
        if "grou".startswith(command) and is_leader:
            query_result = InlineQueryResultArticle(
                id="groupcom", title="/group", description="Create a new group",
                input_message_content=InputTextMessageContent("/group")
            )
            results.append(query_result)
        # Handle groups query
        if "group".startswith(command) and user:
            query_result = InlineQueryResultArticle(
                id="groupscom", title="/groups", description="View all the groups you are in",
                input_message_content=InputTextMessageContent("/groups")
            )
            results.append(query_result)
        # Handle invite query
        if "invit".startswith(command) and user:
            query_result = InlineQueryResultArticle(
                id="invitecom", title="/invite", description="Send a group invite to your friends",
                input_message_content=InputTextMessageContent("/invite")
            )
            results.append(query_result)
        # Handle access query
        if "acces".startswith(command) and is_admin:
            query_result = InlineQueryResultArticle(
                id="accesscom", title="/access", description="Manage access rights",
                input_message_content=InputTextMessageContent("/access")
            )
            results.append(query_result)
        # Handle invite access query
        if "enro".startswith(command) and is_admin:
            query_result = InlineQueryResultArticle(
                id="enrolcom", title="/enrol", description="Send a bot access invite to your friends",
                input_message_content=InputTextMessageContent("/enrol")
            )
            results.append(query_result)
        # Handle promote query
        if "promot".startswith(command) and is_admin:
            query_result = InlineQueryResultArticle(
                id="promotecom", title="/promote", description="Promote users to be bot leaders",
                input_message_content=InputTextMessageContent("/promote")
            )
            results.append(query_result)
        # Handle help query
        if "hel".startswith(command):
            query_result = InlineQueryResultArticle(
                id="helpcom", title="/help", description="View the help message",
                input_message_content=InputTextMessageContent("/help")
            )
            results.append(query_result)

    # Display complete commands as pm text
    match = re.match(r"^/(start|poll|polls|group|groups|invite|enrol|promote|help)(\s+.+)?$", text)
    if match:
        command, details = match.group(1), match.group(2)
        details = details.strip() if details else ""
        # Handle start query
        if command == "start" and is_sender:
            query.answer(results, switch_pm_text="Click to view the bot's welcome message", switch_pm_parameter=command)
            return
        # Handle poll query
        elif command == "poll" and user and is_sender:
            if details:
                context.user_data.update({"title": details})
                query.answer(
                    results, switch_pm_text="Click to build a new poll with the title", switch_pm_parameter=command
                )
            else:
                query.answer(results, switch_pm_text="Click to build a new poll", switch_pm_parameter=command)
            return
        # Handle polls query
        elif command == "polls" and user and is_sender:
            for poll in user.get_polls(details, limit=10):
                query_result = InlineQueryResultArticle(
                    id=f"poll_{poll.get_poll_id()}", title=poll.get_title(),
                    description=poll.generate_options_summary(),
                    input_message_content=InputTextMessageContent(f"/poll_{poll.get_poll_id()}")
                )
                results.append(query_result)
            query.answer(results, switch_pm_text="Click to view all your polls", switch_pm_parameter=command)
            return
        # Handle group query
        elif command == "group" and is_leader and is_sender:
            if details:
                context.user_data.update({"name": details})
                query.answer(
                    results, switch_pm_text="Click to create a new group with a name", switch_pm_parameter=command
                )
            else:
                query.answer(results, switch_pm_text="Click to create a new group", switch_pm_parameter=command)
            return
        # Handle groups query
        elif command == "groups" and user and is_sender:
            for group in user.get_all_groups(details, limit=30):
                query_result = InlineQueryResultArticle(
                    id=f"group_{group.get_gid()}", title=group.get_name(),
                    description=group.generate_group_description_summary(),
                    input_message_content=InputTextMessageContent(f"/group_{group.get_gid()}")
                )
                results.append(query_result)
            query.answer(results, switch_pm_text="Click to view all your joined groups", switch_pm_parameter=command)
            return
        # Handle invite query
        elif command == "invite" and user:
            if is_sender:
                query.answer(results, switch_pm_text="Click to send a group invite", switch_pm_parameter=command)
                return
            for group in user.get_owned_groups(details, limit=10):
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
        elif command == "enrol" and is_admin:
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
        elif command == "promote" and is_admin and is_sender:
            for user in User.get_users_by_name(details):
                if not user.is_leader():
                    query_result = InlineQueryResultArticle(
                        id=user.get_uid(), title=user.get_name(), description=f"@{user.get_username()}",
                        input_message_content=InputTextMessageContent(f"/promote {util.encode(user.get_uid())}"),
                    )
                    results.append(query_result)
            query.answer(
                results[:20], switch_pm_text="Click to promote a user to a bot leader", switch_pm_parameter=command
            )
            return
        # Handle help query
        elif command == "help" and is_sender:
            query.answer(results, switch_pm_text="Click to view the help message", switch_pm_parameter=command)
            return
        # Handle other query
        else:
            query.answer(results)
            return

    # Handle poll query
    if user:
        polls = user.get_polls(text, limit=10)
        for poll in polls:
            query_result = InlineQueryResultArticle(
                id=f"poll {poll.get_poll_id()}", title=poll.get_title(), description=poll.generate_options_summary(),
                input_message_content=InputTextMessageContent(poll.render_text(), parse_mode=ParseMode.HTML),
                reply_markup=poll.build_option_buttons(),
            )
            results.append(query_result)

    query.answer(results)
    return


def handle_inline_pm_query(query: InlineQuery, action: str, details: str) -> None:
    """Handles specific inline to pm queries."""
    if action == "vote":
        text = "Click here to toggle your vote."
    elif action == "comment":
        text = "Click here to add a comment to the poll."
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


# endregion


def handle_error(update: Update, context: CallbackContext) -> None:
    """Logs errors caused by Updates."""
    logger.warning(f"Update {update} caused error {context.error}")


def handle_save(update: Update, context: CallbackContext) -> None:
    """Saves data to database (Temporary)."""
    _, _, is_admin = get_user_permissions(update.effective_user.id)
    if not is_admin:
        handle_help(update, context)
        return
    status = BotManager.save_data()
    update.message.reply_html(status, reply_markup=util.build_single_button_markup("Close", backend.CLOSE))
    return


def handle_load(update: Update, context: CallbackContext) -> None:
    """Loads data from database (Temporary)."""
    _, _, is_admin = get_user_permissions(update.effective_user.id)
    if not is_admin:
        handle_help(update, context)
        return
    status = BotManager.load_data()
    update.message.reply_html(status, reply_markup=util.build_single_button_markup("Close", backend.CLOSE))
    return


# region HELPERS

def get_user_permissions(uid: int) -> tuple:
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
    update.message.reply_html(poll.render_text(), reply_markup=poll.build_admin_buttons(update.effective_user.id))
    return


def refresh_polls(poll: Poll, context: CallbackContext, only_buttons=False) -> None:
    """Refreshes all polls to update changes."""
    if only_buttons:
        for mid in poll.get_message_details():
            context.bot.edit_message_reply_markup(inline_message_id=mid, reply_markup=poll.build_option_buttons())
    else:
        for mid in poll.get_message_details():
            context.bot.edit_message_text(
                poll.render_text(), inline_message_id=mid, parse_mode=ParseMode.HTML,
                reply_markup=poll.build_option_buttons()
            )
    return


def deliver_group(update: Update, group: Group) -> None:
    """Delivers the group details."""
    update.message.reply_html(group.render_group_details_text(), reply_markup=group.build_group_details_buttons())
    return


def try_join_group_through_invitation(update: Update, invitation_code: str):
    """Authenticates group invitation code for user to join group."""
    match = re.match(r"^([^_\W]+)(_[^_\W]+)?$", invitation_code)
    if match:
        gid = match.group(1)
        group = Group.get_group_by_id(gid)

        if group and group.get_password_hash() == invitation_code:
            response = group.add_member(update.effective_user.id)
            update.message.reply_html(response, reply_markup=util.build_single_button_markup("Close", backend.CLOSE))
            return
        else:
            update.message.reply_html(
                ERROR_INVALID_GROUP_INVITE, reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
            )
        return

    update.message.reply_html(
        ERROR_INVALID_GROUP_INVITE, reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
    )
    return


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

    # Command handlers
    dispatcher.add_handler(CommandHandler("access", handle_access, filters=Filters.chat_type.private))
    dispatcher.add_handler(CommandHandler("enrol", handle_enrol, filters=Filters.chat_type.private))
    dispatcher.add_handler(CommandHandler("promote", handle_promote, filters=Filters.chat_type.private))
    dispatcher.add_handler(CommandHandler("start", handle_start, filters=Filters.chat_type.private))
    dispatcher.add_handler(CommandHandler("poll", handle_poll, filters=Filters.chat_type.private))
    dispatcher.add_handler(CommandHandler("group", handle_group, filters=Filters.chat_type.private))
    dispatcher.add_handler(CommandHandler("done", handle_done, filters=Filters.chat_type.private))
    dispatcher.add_handler(CommandHandler("polls", handle_polls, filters=Filters.chat_type.private))
    dispatcher.add_handler(CommandHandler("groups", handle_groups, filters=Filters.chat_type.private))
    dispatcher.add_handler(CommandHandler("invite", handle_invite, filters=Filters.chat_type.private))
    dispatcher.add_handler(CommandHandler("help", handle_help, filters=Filters.chat_type.private))
    dispatcher.add_handler(CommandHandler("save", handle_save, filters=Filters.chat_type.private))
    dispatcher.add_handler(CommandHandler("load", handle_load, filters=Filters.chat_type.private))

    # Message handlers
    dispatcher.add_handler(
        MessageHandler((Filters.regex(r"^\/poll_\w+.*$") & Filters.chat_type.private), handle_poll_view)
    )
    dispatcher.add_handler(
        MessageHandler((Filters.regex(r"^\/group_\w+.*$") & Filters.chat_type.private), handle_group_view)
    )
    dispatcher.add_handler(MessageHandler((Filters.text & Filters.chat_type.private), handle_message))

    # Callback query handlers
    dispatcher.add_handler(CallbackQueryHandler(handle_callback_query))

    # Inline query handlers
    dispatcher.add_handler(InlineQueryHandler(handle_inline_query))

    # Chosen inline result handlers
    dispatcher.add_handler(ChosenInlineResultHandler(handle_chosen_poll_result, pattern=r"^poll \w+$"))

    # Error handlers
    dispatcher.add_error_handler(handle_error)

    # Start database operations
    updater.job_queue.run_once(load_data, 0)
    updater.job_queue.run_repeating(save_data, 300, first=60)

    # Start the bot
    updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN, webhook_url=WEB_URL + TOKEN)
    updater.idle()


if __name__ == "__main__":
    main()
