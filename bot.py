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
    RegexHandler, Filters, Updater, JobQueue
)
import telegram.error

# region SETTINGS

# Environment settings
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

REASON = "Please enter a reason/comment."
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

# endregion


def handle_start(update: Update, context: CallbackContext) -> None:
    """Manages implicit references to the bot."""
    # Start command only work in private chat
    if not is_user_admin(update.message):
        return

    if not validate_and_register_user(update.effective_user):
        update.message.reply_html(ACCESS_REQUEST)
        return

    arguments = context.args
    if not arguments:
        update.message.reply_html(HELP)
        return

    match = re.match(r"^(\w+)-(\w+)$", arguments[0])
    if not match:
        update.message.reply_html(HELP)
        return

    action = match.group(1)
    # Handle join
    if action == "join":
        invitation_code = match.group(2)
        try_join_group_through_invitation(update, invitation_code)
        return
    else:
        update.message.reply_html(HELP)
        return


def handle_access(update: Update, context: CallbackContext) -> None:
    """Grants access to the user to build the poll."""
    # Access command only work in private chat or when access is required
    if not is_user_admin(update.message) or not ACCESS_REQUIRED:
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
    # Poll command only work in private chat and when access is granted
    if not is_user_admin(update.message):
        return

    if not validate_and_register_user(update.effective_user):
        update.message.reply_html(ACCESS_REQUEST)
        return

    # Create user data
    context.user_data.clear()
    context.user_data.update({"action": "poll", "title": "", "options": []})

    update.message.reply_html(NEW_POLL)


def handle_done(update: Update, context: CallbackContext) -> None:
    """Finishes building the poll."""
    # Done command only work in private chat
    if not is_user_admin(update.message):
        return

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
        deliver_poll(update, poll, is_admin=True)

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
    # Polls command only work in private chat
    if not is_user_admin(update.message):
        return

    if not validate_and_register_user(update.effective_user):
        update.message.reply_html(ACCESS_REQUEST)
        return

    context.user_data.clear()

    uid = update.effective_user.id

    header = [util.make_html_bold("Your Polls")]

    recent_polls = User.get_user_by_id(uid).get_polls(limit=20)
    if recent_polls:
        body = [f"{i + 1}. {poll.generate_linked_summary()}" for i, poll in enumerate(recent_polls)]
    else:
        body = [util.make_html_italic("You have no polls! Use /poll to build a new poll.")]

    response = "\n\n".join(header + body)
    update.message.reply_html(response)


def handle_poll_view(update: Update, context: CallbackContext) -> None:
    """Displays the master poll identified by its poll id"""
    # Poll view command only work in private chat
    if not is_user_admin(update.message):
        return

    if not validate_and_register_user(update.effective_user):
        update.message.reply_html(ACCESS_REQUEST)
        return

    context.user_data.clear()

    uid = update.effective_user.id
    text = update.message.text

    poll_id = re.match(r"^/poll_(\w+).*$", text).group(1)
    poll = Poll.get_poll_by_id(poll_id)
    if not poll:
        update.message.reply_html(HELP)
        return

    if poll.get_creator_id() == uid:
        deliver_poll(update, poll, is_admin=True)
        return
    elif User.get_user_by_id(uid).has_group_poll(poll_id):
        deliver_poll(update, poll, is_admin=False)
        return
    else:
        update.message.reply_html(HELP)
        return


def handle_group(update: Update, context: CallbackContext) -> None:
    """Begins creating a new group."""
    # Group command only work in private chat
    if not is_user_admin(update.message):
        return

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
    # Groups command only work in private chat
    if not is_user_admin(update.message):
        return

    if not validate_and_register_user(update.effective_user):
        update.message.reply_html(ACCESS_REQUEST)
        return

    context.user_data.clear()

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
    update.message.reply_html(response)


def handle_group_view(update: Update, context: CallbackContext) -> None:
    """Views details of a group."""
    # Group view command only work in private chat
    if not is_user_admin(update.message):
        return

    if not validate_and_register_user(update.effective_user):
        update.message.reply_html(ACCESS_REQUEST)
        return

    context.user_data.clear()

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
    # Invite command only work in private chat
    if not is_user_admin(update.message):
        return

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
    # Join command only work in private chat
    if not is_user_admin(update.message):
        return

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


def handle_show(update: Update, context: CallbackContext) -> None:
    """Displays the standard poll identified by its poll id"""
    text = update.message.text

    poll_id = re.match(r"^/show_(\w+).*$", text).group(1)
    poll = Poll.get_poll_by_id(poll_id)

    if poll and poll.get_creator_id() == update.effective_user.id:
        deliver_poll(update, poll)


def handle_comment(update: Update, context: CallbackContext) -> None:
    message = update.message
    text = message.text

    match = re.match(r"^\s*/comment_([^_\W]+)_(\d+)_([^_\W]+).*$", text)
    if not match:
        return

    poll_id, opt_id, mid_code = match.group(1), match.group(2), match.group(3)
    reply_message = message.reply_html(
        f"@{update.effective_user.username} {REASON} #comment_{poll_id}_{opt_id}_{mid_code}",
        reply_markup=ForceReply(), disable_notification=True
    )

    # Delete reply message after 10 minutes
    updater.job_queue.run_once(delete_message, 600, context=reply_message)

    # Delete user message
    update.message.delete()


def handle_help(update: Update, context: CallbackContext) -> None:
    """Displays a help message."""
    # Help command only work in private chat
    if not is_user_admin(update.message):
        return
    update.message.reply_html(HELP)


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

    if not validate_and_register_user(update.effective_user):
        update.message.reply_html(ACCESS_REQUEST)
        return

    # Check if current action is poll
    action = context.user_data.get("action", "")
    if action == "poll":
        handle_poll_conversation(update, context)
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

    if is_user_admin(update.message):
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
        deliver_poll(update, poll, is_admin=True)

        # Clear user data
        context.user_data.clear()


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

        code = f"{group.get_gid()}_{util.time_hash(text, salt=group.get_gid())}"

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
        query.answer(text="Invalid callback query data!")
        logger.warning("Invalid callback query data.")
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


def handle_poll_callback_query(query: CallbackQuery, context: CallbackContext, action: str, poll_id: str) -> None:
    poll = Poll.get_poll_by_id(poll_id)

    # Poll is deleted or has error
    if not poll:
        query.edit_message_reply_markup(None)
        query.answer(text=DELETED_POLL)
        return

    uid, user_profile = extract_user_data(query.from_user)
    message = query.message
    is_admin = is_user_admin(message)

    # Handle poll option button
    if action.isdigit():
        if poll.is_user_comment_required(int(action), uid):
            query.answer(text=REASON)
            reply_message = query.message.reply_html(
                f"@{user_profile['username']} {REASON} #vote_{poll_id}_{action}_{util.encode(message.message_id)}",
                reply_markup=ForceReply(), disable_notification=True
            )

            # Delete reply message after 10 minutes
            updater.job_queue.run_once(delete_message, 600, context=reply_message)
            return
        status = poll.toggle(int(action), uid, user_profile)
        query.edit_message_text(poll.render_text(), parse_mode=ParseMode.HTML,
                                reply_markup=poll.build_option_buttons(message.message_id, is_admin=is_admin))
        query.answer(text=status)
        return
    # Handle refresh option button
    elif action == backend.REFRESH_OPT:
        query.answer(text="Results updated!")
        query.edit_message_text(poll.render_text(), parse_mode=ParseMode.HTML,
                                reply_markup=poll.build_option_buttons(message.message_id, is_admin=is_admin))
        return
    # Handle refresh button
    elif action == backend.REFRESH and is_admin:
        query.answer(text="Results updated!")
        query.edit_message_text(poll.render_text(), parse_mode=ParseMode.HTML, reply_markup=poll.build_admin_buttons())
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
    elif action.startswith(f"{backend.COMMENT}_") and is_admin:
        _, opt_id = action.rsplit("_", 1)
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
        query.edit_message_reply_markup(poll.build_option_buttons(message.message_id, is_admin=True))
        query.answer(text="You may now vote!")
        return
    # Handle delete button
    elif action == backend.DELETE and is_admin:
        query.edit_message_reply_markup(poll.build_delete_confirmation_buttons())
        query.answer(text="Confirm delete?")
        return
    # Handle delete confirmation button
    elif action == backend.DELETE_YES and is_admin:
        User.get_user_by_id(uid).delete_poll(poll_id)
        for mid, cid in poll.get_all_message_details():
            try:
                query.bot.delete_message(util.decode(cid), util.decode(mid))
            except telegram.error.TelegramError:
                pass
        query.answer(text="Poll deleted!")
        return
    # Handle back button
    elif action == backend.BACK and is_admin:
        query.edit_message_reply_markup(poll.build_admin_buttons())
        query.answer(text=None)
        return
    # TESTING ONLY!!!
    elif action == "test":
        query.answer(text="")
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
    is_admin = is_user_admin(message)
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

    # Handle comment query
    match = re.match(r"^\s*/comment_([^_\W]+)_([^_\W]+)\s*(\S*)\s*$", text)
    if match:
        poll_id, mid_code, opt_title = match.group(1), match.group(2), match.group(3)
        poll = Poll.get_poll_by_id(poll_id)

        if not poll or not poll.has_message_details(mid_code):
            inline_query.answer(results)
            return

        for i, option in enumerate(poll.get_options()):
            if opt_title.lower() in option.get_title().lower() and option.is_voted_by_user(uid):
                query_result = InlineQueryResultArticle(
                    id=f"{poll_id}_{i}_{mid_code}", title=option.get_title(), description=option.get_user_comment(uid),
                    input_message_content=InputTextMessageContent(f"/comment_{poll_id}_{i}_{mid_code} @{BOT_NAME}")
                )
                results.append(query_result)
        inline_query.answer(results)
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
            id=poll.get_poll_id(), title=poll.get_title(), description=poll.generate_options_summary(),
            input_message_content=InputTextMessageContent(f"/show_{poll.get_poll_id()} @{BOT_NAME}")
        )
        results.append(query_result)

    inline_query.answer(results)
    return


def handle_reply_message(update: Update, context: CallbackContext) -> None:
    """Handles a reply message to the bot."""
    uid, user_profile = extract_user_data(update.effective_user)
    comment = update.message.text

    text = update.message.reply_to_message.text

    delete_message_and_response = lambda message: (message.reply_to_message.delete(), message.delete())

    # Verify reply message format
    match = re.match(r"^@(\w+) [^#]+#([^_\W]+)_([^_\W]+)_(\d+)_([^_\W]+)$", text)
    if not match:
        update.message.reply_html("Invalid reply message format!", disable_notification=True)
        logger.warning("Invalid reply message format.")
        delete_message_and_response(update.message)
        return

    username, action, poll_id, opt_id, message_id = \
        match.group(1), match.group(2), match.group(3), int(match.group(4)), util.decode(match.group(5))

    # Check if username matches
    if username != user_profile["username"]:
        return

    poll = Poll.get_poll_by_id(poll_id)
    if not poll:
        update.message.reply_html(DELETED_POLL, disable_notification=True)
        delete_message_and_response(update.message)
        return

    if opt_id >= len(poll.get_options()):
        update.message.reply_html("Invalid poll option.", disable_notification=True)
        logger.warning("Invalid poll option from reply message.")
        delete_message_and_response(update.message)
        return

    if action == "vote":
        poll.toggle(opt_id, uid, user_profile, comment)
    elif action == "comment":
        status = poll.edit_user_comment(opt_id, uid, comment)
        if status:
            update.message.reply_html(status, disable_notification=True)

    delete_message_and_response(update.message)

    # Edit the poll
    is_admin = is_user_admin(update.message)
    chat_id = update.message.chat_id
    context.bot.edit_message_text(
        poll.render_text(), message_id=message_id, chat_id=chat_id,
        parse_mode=ParseMode.HTML, reply_markup=poll.build_option_buttons(message_id, is_admin=is_admin)
    )


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


def is_user_admin(message: Message) -> bool:
    """Verifies if a user is an admin."""
    return message and message.chat.type == "private"


def extract_user_data(user: TeleUser) -> tuple:
    """Extracts user data from User object."""
    return user.id, {"first_name": user.first_name, "last_name": user.last_name or "", "username": user.username or ""}


def delete_message(context: CallbackContext) -> None:
    """Deletes a message from the job queue."""
    try:
        message = context.job.context
        message.delete()
    except telegram.error.TelegramError:
        logger.info("Message has been deleted.")


def deliver_poll(update: Update, poll: Poll, is_admin=False) -> None:
    """Delivers the poll."""
    if is_admin:
        reply = update.message.reply_html(poll.render_text(), reply_markup=poll.build_admin_buttons())
    else:
        reply = update.message.reply_html(poll.render_text(), reply_to_message_id=-1)
        reply.edit_reply_markup(poll.build_option_buttons(reply.message_id))
    poll.add_message_details(util.encode(reply.message_id), util.encode(update.message.chat_id))


def deliver_group(update: Update, group: Group) -> None:
    """Delivers the group details."""
    update.message.reply_html(group.render_group_details_text(),
                              reply_markup=group.build_group_details_buttons())


def try_join_group_through_invitation(update: Update, invitation_code: str):
    """Authenticates group invitation code for user to join group."""
    match = re.match(r"^([^_\W]+)(_[^_\W]+)?$", invitation_code)
    if match:
        gid = match.group(1)
        group = Group.get_group_by_id(gid)

        if group and group.get_password_hash() == invitation_code:
            user = User.get_user_by_id(update.effective_user.id)

            if gid in user.get_all_group_ids():
                update.message.reply_html(ERROR_ALREADY_IN_GROUP)
                return
            response = user.join_group(gid)
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
    dispatcher.add_handler(CommandHandler("access", handle_access))
    dispatcher.add_handler(CommandHandler("start", handle_start))
    dispatcher.add_handler(CommandHandler("poll", handle_poll))
    dispatcher.add_handler(CommandHandler("group", handle_group))
    dispatcher.add_handler(CommandHandler("done", handle_done))
    dispatcher.add_handler(CommandHandler("polls", handle_polls))
    dispatcher.add_handler(CommandHandler("groups", handle_groups))
    dispatcher.add_handler(CommandHandler("invite", handle_invite))
    dispatcher.add_handler(CommandHandler("join", handle_join))
    dispatcher.add_handler(CommandHandler("help", handle_help))
    dispatcher.add_handler(CommandHandler("save", handle_save))
    dispatcher.add_handler(CommandHandler("load", handle_load))

    # Message handlers
    dispatcher.add_handler(MessageHandler(Filters.regex(r"^\/poll_\w+.*$"), handle_poll_view))
    dispatcher.add_handler(MessageHandler(Filters.regex(r"^\/show_\w+.*$"), handle_show))
    dispatcher.add_handler(MessageHandler(Filters.regex(r"^\/comment_\w+.*$"), handle_comment))
    dispatcher.add_handler(MessageHandler(Filters.regex(r"^\/group_\w+.*$"), handle_group_view))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_message))

    # Callback query handlers
    dispatcher.add_handler(CallbackQueryHandler(handle_callback_query))

    # Inline query handlers
    dispatcher.add_handler(InlineQueryHandler(handle_inline_query))

    # Error handlers
    dispatcher.add_error_handler(handle_error)

    # Start database operations
    updater.job_queue.run_once(load_data, 0)
    updater.job_queue.run_repeating(save_data, 60, first=60)

    # Start the bot
    updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN,
                          webhook_url="https://tya-countmein.herokuapp.com/" + TOKEN)
    updater.idle()


if __name__ == "__main__":
    main()
