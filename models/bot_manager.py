import json

from models.models import group_storage, list_storage, poll_storage, temp_list_storage, temp_poll_storage, user_storage
from utils import util

from database import database as db


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
            db.save(list_storage, db.BALLOT_SHEET)
            db.save(temp_poll_storage, db.TEMP_POLL_SHEET)
            db.save(temp_list_storage, db.TEMP_BALLOT_SHEET)
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
                List.load(
                    list_data[db.REVERSE_POLL_ID],
                    list_data[db.REVERSE_POLL_TITLE],
                    list_data[db.REVERSE_POLL_CREATOR_ID],
                    list_data[db.REVERSE_POLL_DESCRIPTION],
                    list_data[db.REVERSE_POLL_OPTIONS],
                    list_data[db.REVERSE_POLL_CHOICES],
                    list_data[db.REVERSE_POLL_SINGLE_RESPONSE],
                    list_data[db.REVERSE_POLL_MESSAGE_DETAILS],
                    list_data[db.REVERSE_POLL_EXPIRY],
                    list_data[db.REVERSE_POLL_CREATED_DATE],
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
                ListTemplate.load(
                    temp_list_data[db.TEMP_REVERSE_POLL_ID],
                    temp_list_data[db.TEMP_REVERSE_POLL_NAME],
                    temp_list_data[db.TEMP_REVERSE_POLL_DESCRIPTION],
                    temp_list_data[db.TEMP_REVERSE_POLL_TITLE_FORMAT],
                    temp_list_data[db.TEMP_REVERSE_POLL_DESCRIPTION_FORMAT],
                    temp_list_data[db.TEMP_REVERSE_POLL_OPTIONS],
                    temp_list_data[db.TEMP_REVERSE_POLL_CHOICES],
                    temp_list_data[db.TEMP_REVERSE_POLL_SINGLE_RESPONSE],
                    temp_list_data[db.TEMP_REVERSE_POLL_CREATOR_ID]
                )

            return "Data loaded successfully."
        except (TypeError, json.JSONDecodeError) as error:
            return f"Error loading data: {error}"

    @staticmethod
    def build_access_request_text_and_buttons() -> tuple:
        response = f"Which access to you want to grant?"
        buttons = util.build_multiple_buttons_markup(
            util.generate_button_details("Bot Access", BOT_ACCESS),
            util.generate_button_details("Bot Leader Access", PROMOTE),
            util.generate_button_details("Close", CLOSE)
        )
        return response, buttons

    @staticmethod
    def build_bot_access_enrol_text_and_button(uid: int) -> tuple:
        response = f"Click the button below to send a unique invitation to your friend to access the bot."
        buttons = util.build_multiple_buttons_markup(
            util.generate_button_details("Send Bot Invite", f"/enrol {uid}", True),
            util.generate_button_details("Close", CLOSE)
        )
        return response, buttons

    @staticmethod
    def build_invite_text_and_button(token: str, uid: int) -> tuple:
        invitation = f"You are invited to have access to <b>@{BOT_NAME}</b>!"
        buttons = util.build_multiple_buttons_markup(
            util.generate_button_details(
                "Get Access",  f"/access {BotManager.get_bot_token_hash(token, uid)}", is_switch=True, to_self=True
            ),
            util.generate_button_details("Close", CLOSE)
        )
        return invitation, buttons

    @staticmethod
    def build_leader_promote_invite_text_and_button() -> tuple:
        response = f"Who do you want to promote to a bot leader?"

        buttons = []
        for user in sorted(user_storage.values(), key=lambda u: u.get_name().lower()):
            if not user.is_leader():
                invite_button = util.build_button(user.get_name(), USER_SUBJECT, PROMOTE, util.encode(user.get_uid()))
                buttons.append([invite_button])
        close_button = InlineKeyboardButton("Close", callback_data=CLOSE)
        buttons.append([close_button])
        return response, InlineKeyboardMarkup(buttons)