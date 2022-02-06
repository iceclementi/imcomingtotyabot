"""Main Interface"""
import os
import logging
import re
import backend
from backend import User, Group, Poll, Option, BotManager
import util
from telegram import (
    Update, ParseMode, User as TeleUser, Message, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup,
    InlineQueryResultArticle, InputTextMessageContent, ForceReply, CallbackQuery
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
ACCESS_KEYS = os.environ["ACCESS_KEY"].split("_")
PORT = int(os.environ.get("PORT", 8443))
updater = Updater(TOKEN, use_context=True)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot settings
BOT_NAME = "tyacountmeintbot"
MAX_TITLE_LENGTH = 100
MAX_OPTION_TITLE_LENGTH = 50
MAX_GROUP_NAME_LENGTH = 50
MIN_GROUP_PASS_LENGTH = 4
MAX_GROUP_PASS_LENGTH = 20
ACCESS_REQUIRED = False  # Set to False if access is not required to build polls

# Responses
ACCESS_DECLINED = "Sorry, wrong access key."
ACCESS_GRANTED = "Congratulations, you now have access to the bot! Use /start to begin building a poll."
ACCESS_REQUEST = "In order to use this bot, you need to have access.\n" \
                 "Enter <b>>/access &lt;key&gt;</b> to request for access."

NEW_POLL = "Let's create a new poll! First, send me the title."
NEW_OPTION = "New poll:\n{}\n\nNow send me the first answer option."
NEXT_OPTION = "Nice! Now send me another answer option, or /done to finish."
POLL_DONE = "\U0001f44d Poll created! You may now publish it to a group or send it to your friends."
DELETED_POLL = "Sorry, the poll has been deleted."

NEW_GROUP = "Let's create a new group! To begin, send me the group name."
GROUP_PASSWORD_REQUEST = "New group:\n{}\n\nNow enter a secret password for your group. " \
                         "Alternatively, enter /done to skip this step."
GROUP_DONE = "\U0001f44d Group created! You are now the owner of the group. " \
             "Use /invite to invite your friends to join the group."
DELETED_GROUP = "Sorry, the group has been deleted."
GROUP_INVITATION = "Which group's invite code do you want to send?"

REASON = "You've selected {}.\nPlease enter a reason/comment for your selected option."
HELP = "This bot will help you create polls where people can leave their names. " + \
           "Use /poll to create a poll here, then publish it to groups or send it to " + \
           "individual friends.\n\nSend /polls to manage your existing polls."

ERROR_ACCESS_FORMAT = "Invalid access request format. Please use <b>/access &lt;key&gt;</b>."
ERROR_ACCESS_ALREADY_GRANTED = "You already have access to the bot! Use /poll to begin building a poll."
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

# endregion


def handle_start(update: Update, context: CallbackContext) -> None:
    """Manages implicit references to the bot."""
    if not validate_and_register_user(update.effective_user):
        update.message.reply_html(ACCESS_REQUEST)
        return

    arguments = context.args
    if not arguments:
        update.message.reply_html(HELP)
        return

    update.message.delete()

    match = re.match(r"^(\w+)-(\w+)$", arguments[0])
    if not match:
        update.message.reply_html(HELP)
        return

    uid, user_profile = extract_user_data(update.effective_user)

    action = match.group(1)
    # Handle join
    if action == "join":
        invitation_code = match.group(2)
        try_join_group_through_invitation(update, invitation_code)
        return
    # Handle comment
    elif action == "comment":
        poll_details = match.group(2)
        comment_match = re.match(r"^([^_\W]+_[^_\W]+)$", poll_details)
        if not comment_match:
            update.message.reply_html(
                ERROR_INVALID_POLL_COMMENT_REQUEST, reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
            )
            logger.warning("Invalid poll comment request!")
            return

        poll_hash = comment_match.group(1)
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
    # Handle vote
    elif action == "vote":
        poll_details = match.group(2)
        vote_match = re.match(r"^([^_\W]+_[^_\W]+)_(\d+)$", poll_details)
        if not vote_match:
            update.message.reply_html(
                ERROR_INVALID_POLL_VOTE_REQUEST, reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
            )
            logger.warning("Invalid poll vote request!")
            return

        poll_hash, opt_id = vote_match.group(1), int(vote_match.group(2))
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
            update.message.reply_html(
                response, reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
            )

            refresh_polls(poll, context)
            return

        reply_message = update.message.reply_html(
            REASON.format(util.make_html_bold(option.get_title())),
            reply_markup=util.build_single_button_markup("Close", backend.RESET),
        )
        context.user_data.update({"action": "vote", "pid": poll_id, "opt": opt_id, "del": reply_message.message_id})
        delete_message_with_timer(reply_message, 900)
        return
    else:
        update.message.reply_html(HELP)
        return


def handle_access(update: Update, context: CallbackContext) -> None:
    """Grants access to the user to build the poll."""
    # Access command only work in private chat or when access is required
    if not ACCESS_REQUIRED:
        return

    context.user_data.clear()

    uid, user_profile = extract_user_data(update.effective_user)

    if User.get_user_by_id(uid):
        update.message.reply_html(ERROR_ACCESS_ALREADY_GRANTED)
        return

    arguments = context.args
    if not arguments:
        update.message.reply_html(ERROR_ACCESS_FORMAT)
        return

    access_key = arguments[0]
    if access_key in ACCESS_KEYS:
        User.register(uid, user_profile["first_name"], user_profile["last_name"], user_profile["username"])
        update.message.reply_html(ACCESS_GRANTED)
        return
    else:
        update.message.reply_html(ACCESS_DECLINED)


def handle_poll(update: Update, context: CallbackContext) -> None:
    """Begins building a new poll."""
    if not validate_and_register_user(update.effective_user):
        update.message.reply_html(ACCESS_REQUEST)
        return

    # Create user data
    context.user_data.clear()
    context.user_data.update({"action": "poll", "title": "", "options": []})

    update.message.reply_html(NEW_POLL)


def handle_done(update: Update, context: CallbackContext) -> None:
    """Finishes building the poll."""
    if not validate_and_register_user(update.effective_user):
        update.message.reply_html(ACCESS_REQUEST)
        return

    action = context.user_data.setdefault("action", "")

    # Handle poll
    if action == "poll":
        title, options = context.user_data.setdefault("title", ""), context.user_data.setdefault("options", [])

        # Check if there is a title
        if not title:
            update.message.reply_html(ERROR_EARLY_DONE_TITLE)
            return

        # Check if there are options
        if not options:
            update.message.reply_html(ERROR_EARLY_DONE_OPTION)
            return

        # Create poll
        poll, _ = User.get_user_by_id(update.effective_user.id).create_poll(title, options)

        update.message.reply_html(POLL_DONE)
        deliver_poll(update, poll)

        # Clear user data
        context.user_data.clear()
        return
    # Handle group
    elif action == "group":
        group_name = context.user_data.setdefault("name", "")

        # Check if there is a group name
        if not group_name:
            update.message.reply_html(ERROR_EARLY_DONE_GROUP_NAME)

        # Create group
        group, _ = User.get_user_by_id(update.effective_user.id).create_group(group_name, "")

        update.message.reply_html(GROUP_DONE.format(util.make_html_bold(group.get_gid())))
        deliver_group(update, group)

        # Clear user data
        context.user_data.clear()
        return
    else:
        update.message.reply_html(HELP)
        return


def handle_polls(update: Update, context: CallbackContext) -> None:
    """Displays all recent polls created by user."""
    if not validate_and_register_user(update.effective_user):
        update.message.reply_html(ACCESS_REQUEST)
        return

    update.message.delete()
    context.user_data.clear()

    uid = update.effective_user.id

    header = [util.make_html_bold("Your Polls")]

    recent_polls = User.get_user_by_id(uid).get_polls(limit=20)
    if recent_polls:
        body = [f"{i}. {poll.generate_linked_summary()}" for i, poll in enumerate(recent_polls, 1)]
    else:
        body = [util.make_html_italic("You have no polls! Use /poll to build a new poll.")]

    response = "\n\n".join(header + body)
    update.message.reply_html(response, reply_markup=util.build_single_button_markup("Close", backend.CLOSE))


def handle_poll_view(update: Update, context: CallbackContext) -> None:
    """Displays the master poll identified by its poll id"""
    if not validate_and_register_user(update.effective_user):
        update.message.reply_html(ACCESS_REQUEST)
        return

    update.message.delete()
    context.user_data.clear()

    uid = update.effective_user.id
    text = update.message.text

    poll_id = re.match(r"^/poll_(\w+).*$", text).group(1)
    poll = Poll.get_poll_by_id(poll_id)
    if not poll:
        update.message.reply_html(HELP)
        return

    if User.get_user_by_id(uid).has_group_poll(poll_id):
        deliver_poll(update, poll)
        return
    else:
        update.message.reply_html(HELP)
        return


def handle_group(update: Update, context: CallbackContext) -> None:
    """Begins creating a new group."""
    if not validate_and_register_user(update.effective_user):
        update.message.reply_html(ACCESS_REQUEST)
        return

    # Create user data
    context.user_data.clear()
    context.user_data.update({"action": "group", "name": "", "secret": ""})

    match = re.match(r"^\s*/group\s+(.*)$", update.message.text)
    if not match:
        update.message.reply_html(NEW_GROUP)
        return

    group_name = match.group(1).strip().replace("\n", " ")

    if len(group_name) > MAX_GROUP_NAME_LENGTH:
        update.message.reply_html(ERROR_GROUP_NAME_TOO_LONG)
        return

    if User.get_user_by_id(update.effective_user.id).has_group_with_name(group_name):
        update.message.reply_html(ERROR_GROUP_NAME_EXISTS)
        return

    context.user_data["name"] = group_name
    response = GROUP_PASSWORD_REQUEST.format(util.make_html_bold(group_name))
    update.message.reply_html(response)


def handle_groups(update: Update, context: CallbackContext) -> None:
    """Views all the user's groups."""
    if not validate_and_register_user(update.effective_user):
        update.message.reply_html(ACCESS_REQUEST)
        return

    context.user_data.clear()
    update.message.delete()

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


def handle_group_view(update: Update, context: CallbackContext) -> None:
    """Views details of a group."""
    if not validate_and_register_user(update.effective_user):
        update.message.reply_html(ACCESS_REQUEST)
        return

    context.user_data.clear()
    update.message.delete()

    uid = update.effective_user.id
    text = update.message.text

    gid = re.match(r"^/group_(\w+).*$", text).group(1)
    group = Group.get_group_by_id(gid)
    if group and uid in group.get_member_ids():
        deliver_group(update, group)
        return
    else:
        update.message.reply_html(HELP)


def handle_invite(update: Update, context: CallbackContext) -> None:
    """Sends group invitation code."""
    if not validate_and_register_user(update.effective_user):
        update.message.reply_html(ACCESS_REQUEST)
        return

    context.user_data.clear()
    uid = update.effective_user.id

    response, buttons = User.get_user_by_id(uid).build_invite_text_and_buttons()
    if buttons:
        update.message.reply_html(response, reply_markup=buttons)
    else:
        update.message.reply_html(response)


def handle_join(update: Update, context: CallbackContext) -> None:
    """Joins a group from a group invite code."""
    if not validate_and_register_user(update.effective_user):
        update.message.reply_html(ACCESS_REQUEST)
        return

    context.user_data.clear()

    arguments = context.args
    if not arguments:
        context.user_data.update({"action": "join"})
        update.message.reply_html("Enter the group invitation code.")
        return

    invitation_code = arguments[0]
    try_join_group_through_invitation(update, invitation_code)
    return


def handle_help(update: Update, context: CallbackContext) -> None:
    """Displays a help message."""
    update.message.reply_html(HELP)


def handle_message(update: Update, context: CallbackContext) -> None:
    """Handles a message from the user."""
    if not update.message:
        return

    text = update.message.text
    if not text:
        return

    if not validate_and_register_user(update.effective_user):
        update.message.reply_html(ACCESS_REQUEST)
        return

    # Check if current action is poll
    action = context.user_data.get("action", "")
    if action == "poll":
        handle_poll_conversation(update, context)
        return
    elif action == "vote":
        handle_vote_conversation(update, context)
        return
    elif action == "comment":
        handle_comment_conversation(update, context)
        return
    elif action == "group":
        handle_group_conversation(update, context)
        return
    elif action == "join":
        handle_join_conversation(update, context)
        return
    elif action == "pass":
        handle_change_secret_conversation(update, context)
        return

    if is_private_chat(update.message):
        update.message.reply_html(HELP)
        return


def handle_poll_conversation(update: Update, context: CallbackContext) -> None:
    """Handles the conversation between the bot and the user to build a poll."""
    text = update.message.text.strip()
    title, options = context.user_data.get("title", ""), context.user_data.get("options", [])

    # Handle title
    if not title:
        if len(text) > MAX_TITLE_LENGTH:
            update.message.reply_html(ERROR_TITLE_TOO_LONG)
            return

        bold_title = util.make_html_bold_first_line(text)
        response = NEW_OPTION.format(bold_title)
        update.message.reply_html(response)

        context.user_data["title"] = text
        return
    # Handle option
    else:
        if len(text) > MAX_OPTION_TITLE_LENGTH:
            update.message.reply_html(ERROR_OPTION_TITLE_TOO_LONG)
            return

        options.append(text)

        if len(options) < 10:
            update.message.reply_html(NEXT_OPTION)
            context.user_data["options"] = options
            return

        # Create poll
        poll, _ = User.get_user_by_id(update.effective_user.id).create_poll(title, options)

        update.message.reply_html(POLL_DONE)
        deliver_poll(update, poll)

        # Clear user data
        context.user_data.clear()


def handle_vote_conversation(update: Update, context: CallbackContext) -> None:
    """Handles the conversation between the bot and the user to vote a poll option."""
    poll_id = context.user_data.get("pid", "")
    opt_id = int(context.user_data.get("opt", -1))
    from_mid = context.user_data.get("del", "")
    cid = update.effective_chat.id
    uid, user_profile = extract_user_data(update.effective_user)

    context.user_data.clear()

    delete_message_and_response = lambda: (update.message.delete(), context.bot.delete_message(cid, from_mid))

    poll = Poll.get_poll_by_id(poll_id)
    if not poll:
        update.message.reply_html(DELETED_POLL, reply_markup=util.build_single_button_markup("Close", backend.CLOSE))
        delete_message_and_response()
        logger.warning("Poll deleted before vote.")
        return

    if opt_id >= len(poll.get_options()) or opt_id < 0:
        update.message.reply_html(
            ERROR_INVALID_POLL_OPTION_REQUEST, reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
        )
        delete_message_and_response()
        logger.warning("Invalid option selected from poll vote!")
        return

    if poll.get_options()[opt_id].is_voted_by_user(uid):
        update.message.reply_html(
            ERROR_ALREADY_VOTED, reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
        )
        delete_message_and_response()
        logger.warning("Poll option already voted by user!")
        return

    response = poll.toggle(opt_id, uid, user_profile, update.message.text)

    update.message.reply_html(
        util.make_html_bold(f"{response} {backend.EMOJI_HAPPY}"),
        reply_markup=util.build_single_button_markup("Close", backend.CLOSE),
    )
    update.message.reply_html(
        poll.render_text(),
        reply_markup=util.build_single_button_markup("Close", backend.CLOSE),
    )
    delete_message_and_response()
    refresh_polls(poll, context)
    return


def handle_comment_conversation(update: Update, context: CallbackContext) -> None:
    """Handles the conversation between the bot and the user to comment a poll option."""
    poll_id = context.user_data.get("pid", "")
    opt_id = int(context.user_data.get("opt", -1))
    from_mid = context.user_data.get("del", "")
    cid = update.effective_chat.id
    uid, user_profile = extract_user_data(update.effective_user)

    context.user_data.clear()

    delete_message_and_response = lambda: (update.message.delete(), context.bot.delete_message(cid, from_mid))

    poll = Poll.get_poll_by_id(poll_id)
    if not poll:
        update.message.reply_html(DELETED_POLL, reply_markup=util.build_single_button_markup("Close", backend.CLOSE))
        delete_message_and_response()
        logger.warning("Poll deleted before vote.")
        return

    if opt_id >= len(poll.get_options()) or opt_id < 0:
        update.message.reply_html(
            ERROR_INVALID_POLL_OPTION_REQUEST, reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
        )
        delete_message_and_response()
        logger.warning("Invalid option selected from poll vote!")
        return

    if not poll.get_options()[opt_id].is_voted_by_user(uid):
        update.message.reply_html(
            ERROR_NOT_VOTED, reply_markup=util.build_single_button_markup("Close", backend.CLOSE)
        )
        delete_message_and_response()
        logger.warning("Poll option not voted by user!")
        return

    poll.edit_user_comment(opt_id, uid, update.message.text)

    update.message.reply_html(
        util.make_html_bold(f"Comment updated successfully! {backend.EMOJI_HAPPY}"),
        reply_markup=util.build_single_button_markup("Close", backend.CLOSE),
    )
    update.message.reply_html(
        poll.render_text(),
        reply_markup=util.build_single_button_markup("Close", backend.CLOSE),
    )
    delete_message_and_response()
    refresh_polls(poll, context)
    return


def handle_group_conversation(update: Update, context: CallbackContext) -> None:
    """Handles the conversation between the bot and the user to create a group."""
    text = update.message.text.strip()
    group_name, secret = context.user_data.get("name", ""), context.user_data.get("secret", "")

    # Handle group name
    if not group_name:
        group_name = text.replace("\n", " ")
        if len(group_name) > MAX_GROUP_NAME_LENGTH:
            update.message.reply_html(ERROR_GROUP_NAME_TOO_LONG)
            return

        if User.get_user_by_id(update.effective_user.id).has_group_with_name(group_name):
            update.message.reply_html(ERROR_GROUP_NAME_EXISTS)
            return

        response = GROUP_PASSWORD_REQUEST.format(util.make_html_bold(group_name))
        update.message.reply_html(response)

        context.user_data["name"] = group_name
        return
    # Handle secret
    else:
        if not re.match(r"^[A-Za-z0-9]{4,20}$", text):
            update.message.reply_html(ERROR_INVALID_GROUP_PASS_FORMAT)
            return

        update.message.delete()

        # Create group
        group, _ = User.get_user_by_id(update.effective_user.id).create_group(group_name, text)

        code = f"{group.get_gid()}_{util.simple_hash(text, salt=group.get_gid())}"

        update.message.reply_html(GROUP_DONE.format(util.make_html_bold(code)))
        deliver_group(update, group)

        # Clear user data
        context.user_data.clear()


def handle_join_conversation(update: Update, context: CallbackContext) -> None:
    """Handles the conversation between the bot and the user to join a group."""
    invitation_code = update.message.text.strip()
    try_join_group_through_invitation(update, invitation_code)
    return


def handle_change_secret_conversation(update: Update, context: CallbackContext) -> None:
    """Handles the conversation between the bot and the user to change the group secret."""
    gid = context.user_data.get("gid", "")

    group = Group.get_group_by_id(gid)
    if not group or group.get_owner() != update.effective_user.id:
        update.message.reply_html(util.make_html_bold(ERROR_ILLEGAL_SECRET_CHANGE))
        logger.warning("Illegal password change!")
        return

    new_secret = update.message.text.strip()

    if not re.match(r"^[A-Za-z0-9]{4,20}$", new_secret):
        update.message.reply_html(ERROR_INVALID_GROUP_PASS_FORMAT)
        return

    update.message.delete()

    # Change password
    group.edit_password(new_secret)
    update.message.reply_html("Group password changed!")

    # Clear user data
    context.user_data.clear()
    return


def handle_callback_query(update: Update, context: CallbackContext) -> None:
    """Handles a callback query."""
    query = update.callback_query

    match = re.match(r"^(\w+)\s+(\w+)\s+(\w+)$", query.data)
    if not match:
        handle_general_callback_query(query, context, query.data)
        return

    subject, action, identifier = match.group(1), match.group(2), match.group(3)

    if subject == backend.POLL_SUBJECT:
        handle_poll_callback_query(query, context, action, identifier)
    elif subject == backend.GROUP_SUBJECT:
        handle_group_callback_query(query, context, action, identifier)
    else:
        logger.warning("Invalid callback query data.")
        query.answer(text="Invalid callback query data!")
        return


def handle_general_callback_query(query: CallbackQuery, context: CallbackContext, action: str) -> None:
    # Handle close button
    if action == backend.CLOSE:
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


def handle_poll_callback_query(query: CallbackQuery, context: CallbackContext, action: str, poll_id: str) -> None:
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
        return
    # Handle vote button
    elif action == backend.VOTE and is_pm:
        query.edit_message_reply_markup(poll.build_option_buttons())
        query.answer(text="You may now vote!")
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
    group = Group.get_group_by_id(gid)

    # Group is deleted or has error
    if not group:
        query.edit_message_reply_markup(None)
        query.answer(text=DELETED_GROUP)
        return

    uid, user_profile = extract_user_data(query.from_user)
    message = query.message
    is_admin = is_private_chat(message)
    is_owner = group.get_owner() == uid

    if not is_admin:
        return

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
    else:
        logger.warning("Invalid callback query data.")
        query.answer(text="Invalid callback query data!")
        query.edit_message_reply_markup(None)
        return


def handle_inline_query(update: Update, context: CallbackContext) -> None:
    """Handles an inline query."""
    inline_query = update.inline_query
    text = inline_query.query
    uid = update.effective_user.id
    user = User.get_user_by_id(uid)

    results = []

    # Handle vote query
    match = re.match(r"^\s*/vote\s+(\w+)\s*$", text)
    if match:
        poll_details = match.group(1)
        inline_query.answer(
            results, switch_pm_text="Click here to toggle your vote.",
            switch_pm_parameter=f"vote-{poll_details}"
        )
        return
    # Handle comment query
    match = re.match(r"^\s*/comment\s+(\w+)\s*$", text)
    if match:
        poll_details = match.group(1)
        inline_query.answer(
            results, switch_pm_text="Click here to add a comment to the poll",
            switch_pm_parameter=f"comment-{poll_details}"
        )
        return
    # Handle invite query
    match = re.match(r"^\s*/invite\s*(.*)$", text)
    if match:
        group_name = match.group(1).strip()
        for group in user.get_owned_groups(group_name, limit=10):
            invitation, join_button = group.build_invite_text_and_button(update.effective_user.first_name)
            query_result = InlineQueryResultArticle(
                id=group.get_gid(), title=group.get_name(), description="Send group invitation",
                input_message_content=InputTextMessageContent(invitation), reply_markup=join_button
            )
            results.append(query_result)
        inline_query.answer(results)
        return

    # Handle join query
    match = re.match(r"^\s*/join\s+(\w+)\s*$", text)
    if match:
        invite_code = match.group(1)
        inline_query.answer(
            results, switch_pm_text="Click here to join group", switch_pm_parameter=f"join-{invite_code}"
        )
        return

    # Handle poll query
    polls = user.get_polls(text, limit=10)
    for poll in polls:
        query_result = InlineQueryResultArticle(
            id=f"poll {poll.get_poll_id()}", title=poll.get_title(), description=poll.generate_options_summary(),
            input_message_content=InputTextMessageContent(poll.render_text(), parse_mode=ParseMode.HTML),
            reply_markup=poll.build_option_buttons(),
        )
        results.append(query_result)

    inline_query.answer(results)
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


def handle_error(update: Update, context: CallbackContext) -> None:
    """Logs errors caused by Updates."""
    logger.warning(f"Update {update} caused error {context.error}")


def handle_save(update: Update, context: CallbackContext) -> None:
    """Saves data to database (Temporary)."""
    status = BotManager.save_data()
    update.message.reply_html(status)
    return


def handle_load(update: Update, context: CallbackContext) -> None:
    """Loads data from database (Temporary)."""
    status = BotManager.load_data()
    update.message.reply_html(status)
    return


def validate_and_register_user(user: TeleUser) -> bool:
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


def delete_message_with_timer(message: Message, countdown: int):
    """Deletes a message after a given countdown"""
    updater.job_queue.run_once(delete_message, countdown, context=message)


def delete_message(context: CallbackContext) -> None:
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


def refresh_polls(poll: Poll, context: CallbackContext):
    """Refreshes all polls to update changes."""
    for mid in poll.get_message_details():
        context.bot.edit_message_text(
            poll.render_text(), inline_message_id=mid, parse_mode=ParseMode.HTML,
            reply_markup=poll.build_option_buttons()
        )
    return


def deliver_group(update: Update, group: Group) -> None:
    """Delivers the group details."""
    update.message.reply_html(group.render_group_details_text(),
                              reply_markup=group.build_group_details_buttons())
    return


def try_join_group_through_invitation(update: Update, invitation_code: str):
    """Authenticates group invitation code for user to join group."""
    match = re.match(r"^([^_\W]+)(_[^_\W]+)?$", invitation_code)
    if match:
        gid = match.group(1)
        group = Group.get_group_by_id(gid)

        if group and group.get_password_hash() == invitation_code:
            response = group.add_member(update.effective_user.id)
            update.message.reply_html(response)
            return
        else:
            update.message.reply_html(ERROR_INVALID_GROUP_INVITE)
        return

    update.message.reply_html(ERROR_INVALID_GROUP_INVITE)
    return


def save_data(context: CallbackContext) -> None:
    """Saves data to database."""
    status = BotManager.save_data()
    logger.info(status)


def load_data(context: CallbackContext) -> None:
    """Loads data from database."""
    status = BotManager.load_data()
    logger.info(status)


def main():
    """Starts the bot."""
    # Dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Command handlers
    dispatcher.add_handler(CommandHandler("access", handle_access, filters=Filters.chat_type.private))
    dispatcher.add_handler(CommandHandler("start", handle_start, filters=Filters.chat_type.private))
    dispatcher.add_handler(CommandHandler("poll", handle_poll, filters=Filters.chat_type.private))
    dispatcher.add_handler(CommandHandler("group", handle_group, filters=Filters.chat_type.private))
    dispatcher.add_handler(CommandHandler("done", handle_done, filters=Filters.chat_type.private))
    dispatcher.add_handler(CommandHandler("polls", handle_polls, filters=Filters.chat_type.private))
    dispatcher.add_handler(CommandHandler("groups", handle_groups, filters=Filters.chat_type.private))
    dispatcher.add_handler(CommandHandler("invite", handle_invite, filters=Filters.chat_type.private))
    dispatcher.add_handler(CommandHandler("join", handle_join, filters=Filters.chat_type.private))
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
    updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN,
                          webhook_url=WEB_URL + TOKEN)
    updater.idle()


if __name__ == "__main__":
    main()
