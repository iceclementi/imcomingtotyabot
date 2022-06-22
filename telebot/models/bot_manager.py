import json

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from telebot.database import database as db
from telebot.models import constant as const
from telebot.models.ballot.ballot import Ballot, ballot_storage
from telebot.models.poll.poll import Poll, poll_storage
from telebot.models.template.ballot_template import BallotTemplate, temp_ballot_storage
from telebot.models.template.poll_template import PollTemplate, temp_poll_storage
from telebot.models.user.group import Group, group_storage
from telebot.models.user.user import User, user_storage
from telebot.utils import util


class BotManager(object):
    @staticmethod
    def is_admin(uid: int, admin_keys: list) -> bool:
        return util.encode(uid) in admin_keys

    @staticmethod
    def get_bot_token_hash(token: str, uid: int) -> str:
        return util.simple_hash(token, util.encode(uid), 32)

    @staticmethod
    def get_leader_token_hash(token: str, uid: int, name: str) -> str:
        return util.simple_hash(token, f"{util.encode(uid)}{name}", 32)

    @staticmethod
    def save_data() -> str:
        try:
            db.save(user_storage, db.USER_SHEET)
            db.save(group_storage, db.GROUP_SHEET)
            db.save(poll_storage, db.POLL_SHEET)
            db.save(ballot_storage, db.BALLOT_SHEET)
            db.save(temp_poll_storage, db.TEMP_POLL_SHEET)
            db.save(temp_ballot_storage, db.TEMP_BALLOT_SHEET)
            return "Data saved successfully."
        except (TypeError, json.JSONDecodeError) as error:
            return f"Error saving data: {error}"

    @staticmethod
    def load_data() -> str:
        try:
            users_data = db.load(db.USER_SHEET)
            for user_data in users_data:
                User.load(
                    user_data[db.USER_ID],
                    user_data[db.USER_FIRST_NAME],
                    user_data[db.USER_LAST_NAME],
                    user_data[db.USER_USERNAME],
                    user_data[db.USER_IS_LEADER],
                    user_data[db.USER_OWNED_GROUP_IDS],
                    user_data[db.USER_JOINED_GROUP_IDS],
                    user_data[db.USER_POLL_IDS],
                    user_data[db.USER_BALLOT_IDS],
                    user_data[db.USER_TEMP_POLL_IDS],
                    user_data[db.USER_TEMP_BALLOT_IDS]
                )

            groups_data = db.load(db.GROUP_SHEET)
            for group_data in groups_data:
                Group.load(
                    group_data[db.GROUP_ID],
                    group_data[db.GROUP_NAME],
                    group_data[db.GROUP_OWNER],
                    group_data[db.GROUP_PASSWORD],
                    group_data[db.GROUP_MEMBER_IDS],
                    group_data[db.GROUP_POLL_IDS],
                    group_data[db.GROUP_BALLOT_IDS],
                    group_data[db.GROUP_TEMP_IDS],
                    group_data[db.GROUP_CREATED_DATE],
                )

            polls_data = db.load(db.POLL_SHEET)
            for poll_data in polls_data:
                Poll.load(
                    poll_data[db.POLL_ID],
                    poll_data[db.POLL_TITLE],
                    poll_data[db.POLL_CREATOR_ID],
                    poll_data[db.POLL_DESCRIPTION],
                    poll_data[db.POLL_OPTIONS],
                    poll_data[db.POLL_SINGLE_RESPONSE],
                    poll_data[db.POLL_MESSAGE_DETAILS],
                    poll_data[db.POLL_EXPIRY],
                    poll_data[db.POLL_CREATED_DATE],
                )

            lists_data = db.load(db.BALLOT_SHEET)
            for list_data in lists_data:
                Ballot.load(
                    list_data[db.BALLOT_ID],
                    list_data[db.BALLOT_TITLE],
                    list_data[db.BALLOT_CREATOR_ID],
                    list_data[db.BALLOT_DESCRIPTION],
                    list_data[db.BALLOT_OPTIONS],
                    list_data[db.BALLOT_CHOICES],
                    list_data[db.BALLOT_SINGLE_RESPONSE],
                    list_data[db.BALLOT_MESSAGE_DETAILS],
                    list_data[db.BALLOT_EXPIRY],
                    list_data[db.BALLOT_CREATED_DATE],
                )

            temp_polls_data = db.load(db.TEMP_POLL_SHEET)
            for temp_poll_data in temp_polls_data:
                PollTemplate.load(
                    temp_poll_data[db.TEMP_POLL_ID],
                    temp_poll_data[db.TEMP_POLL_NAME],
                    temp_poll_data[db.TEMP_POLL_DESCRIPTION],
                    temp_poll_data[db.TEMP_POLL_TITLE_FORMAT],
                    temp_poll_data[db.TEMP_POLL_DESCRIPTION_FORMAT],
                    temp_poll_data[db.TEMP_POLL_OPTIONS],
                    temp_poll_data[db.TEMP_POLL_SINGLE_RESPONSE],
                    temp_poll_data[db.TEMP_POLL_CREATOR_ID]
                )

            temp_lists_data = db.load(db.TEMP_BALLOT_SHEET)
            for temp_list_data in temp_lists_data:
                BallotTemplate.load(
                    temp_list_data[db.TEMP_BALLOT_ID],
                    temp_list_data[db.TEMP_BALLOT_NAME],
                    temp_list_data[db.TEMP_BALLOT_DESCRIPTION],
                    temp_list_data[db.TEMP_BALLOT_TITLE_FORMAT],
                    temp_list_data[db.TEMP_BALLOT_DESCRIPTION_FORMAT],
                    temp_list_data[db.TEMP_BALLOT_OPTIONS],
                    temp_list_data[db.TEMP_BALLOT_CHOICES],
                    temp_list_data[db.TEMP_BALLOT_SINGLE_RESPONSE],
                    temp_list_data[db.TEMP_BALLOT_CREATOR_ID]
                )

            return "Data loaded successfully."
        except (TypeError, json.JSONDecodeError) as error:
            return f"Error loading data: {error}"

    @staticmethod
    def build_access_request_text_and_buttons() -> tuple:
        response = f"Which access to you want to grant?"
        buttons = util.build_multiple_buttons_markup(
            util.generate_button_details("Bot Access", const.BOT_ACCESS),
            util.generate_button_details("Bot Leader Access", const.PROMOTE),
            util.generate_button_details("Close", const.CLOSE)
        )
        return response, buttons

    @staticmethod
    def build_bot_access_enrol_text_and_button(uid: int) -> tuple:
        response = f"Click the button below to send a unique invitation to your friend to access the bot."
        buttons = util.build_multiple_buttons_markup(
            util.generate_button_details("Send Bot Invite", f"/enrol {uid}", True),
            util.generate_button_details("Close", const.CLOSE)
        )
        return response, buttons

    @staticmethod
    def build_invite_text_and_button(token: str, uid: int) -> tuple:
        invitation = f"You are invited to have access to <b>@{const.BOT_NAME}</b>!"
        buttons = util.build_multiple_buttons_markup(
            util.generate_button_details(
                "Get Access", f"/access {BotManager.get_bot_token_hash(token, uid)}", is_switch=True, to_self=True
            ),
            util.generate_button_details("Close", const.CLOSE)
        )
        return invitation, buttons

    @staticmethod
    def build_leader_promote_invite_text_and_button() -> tuple:
        response = f"Who do you want to promote to a bot leader?"

        buttons = []
        for user in sorted(user_storage.values(), key=lambda u: u.get_name().lower()):
            if not user.is_leader():
                invite_button = util.build_button(
                    user.get_name(), const.USER_SUBJECT, const.PROMOTE, util.encode(user.get_uid())
                )
                buttons.append([invite_button])
        close_button = InlineKeyboardButton("Close", callback_data=const.CLOSE)
        buttons.append([close_button])
        return response, InlineKeyboardMarkup(buttons)
