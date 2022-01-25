import string
import random
from datetime import datetime
from collections import OrderedDict
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

# Settings
RANDOM_LENGTH = 4
EMOJI_PEOPLE = u"\U0001f465"
SESSION_EXPIRY = 1  # In hours
POLL_EXPIRY = 720

# Session Progress types
NONE = "none"
TITLE = "title"
OPTION = "option"

PUBLISH = "publish"
REFRESH = "refresh"
VOTE = "vote"
DELETE = "delete"
BACK = "back"

creators = set()
all_sessions = dict()
all_polls = dict()


class Session(object):
    def __init__(self, uid: int) -> None:
        self.uid = uid
        self.progress = TITLE
        self.poll_id = ""
        self.start_date = datetime.now()
        self.expiry = SESSION_EXPIRY

    def get_progress(self) -> str:
        return self.progress

    def set_progress(self, state: str) -> None:
        self.progress = state

    def get_poll_id(self) -> str:
        return self.poll_id

    def set_poll_id(self, poll_id: str) -> None:
        self.poll_id = poll_id

    def get_start_date(self) -> datetime:
        return self.start_date

    def get_expiry(self) -> int:
        return self.expiry

    def set_expiry(self, expiry: int) -> None:
        self.expiry = expiry

    def end_session(self) -> None:
        all_sessions.pop(self.uid)

    def reset_session(self):
        self.progress = TITLE
        self.start_date = datetime.now()
        poll = Poll.get_poll_by_id(self.poll_id)
        if poll:
            poll.reset_poll()
        else:
            self.poll_id = Poll.create_new_poll(self.uid)

    @staticmethod
    def start_new_session(uid: int) -> None:
        session = Session.get_session_by_id(uid)
        if not session:
            session = Session(uid)
            session.set_poll_id(Poll.create_new_poll(uid))
            all_sessions[uid] = session
        else:
            session.reset_session()

    @staticmethod
    def get_session_by_id(uid: int):
        return all_sessions.get(uid, None)


class Poll(object):
    def __init__(self, uid: int) -> None:
        self.creator_id = uid
        self.poll_id = create_random_string(RANDOM_LENGTH)
        self.title = ""
        self.options = []
        self.created_date = datetime.now()
        self.expiry = POLL_EXPIRY

    def get_creator_id(self) -> int:
        return self.creator_id

    def get_poll_id(self) -> str:
        return self.poll_id

    def get_title(self) -> str:
        return self.title

    def set_title(self, title: str) -> None:
        self.title = title

    def get_options(self) -> list:
        return self.options

    def add_option(self, option) -> None:
        self.options.append(option)

    def get_created_date(self) -> datetime:
        return self.created_date

    def get_expiry(self) -> int:
        return self.expiry

    def set_expiry(self, expiry: int) -> None:
        self.expiry = expiry

    def reset_poll(self):
        self.title = ""
        self.options = []
        self.created_date = datetime.now()

    @staticmethod
    def create_new_poll(uid: int) -> str:
        poll_id = create_random_string(RANDOM_LENGTH)
        while poll_id in all_polls:
            poll_id = create_random_string(RANDOM_LENGTH)
        all_polls[poll_id] = Poll(uid)
        return poll_id

    @staticmethod
    def get_poll_by_id(poll_id: str):
        return all_polls.get(poll_id, None)

    @staticmethod
    def toggle(poll_id: str, opt_id: int, uid: int, user_profile: dict):
        poll = all_polls.get(poll_id, None)
        if not poll:
            return None, "Sorry, this pole has been deleted."
        if opt_id >= len(poll.get_options()):
            return None, "Sorry, invalid option."
        status = poll.get_options()[opt_id].toggle(uid, user_profile)
        return poll, status

    def generate_respondents_summary(self) -> str:
        all_respondents_uid = set(uid for option in self.options for uid in option.respondents.key())
        respondents_count = len(all_respondents_uid)
        if respondents_count == 0:
            summary = "Nobody responded"
        elif respondents_count == 1:
            summary = "1 person responded"
        else:
            summary = f"{respondents_count} people responded"
        return summary

    def generate_options_summary(self) -> str:
        return " / ".join(option.title for option in self.options)

    def render_text(self) -> str:
        header = [make_html_bold_first_line(self.title)]
        body = [option.render_text() for option in self.options]
        # footer = [f"{EMOJI_PEOPLE} {self.generate_respondents_summary}"]
        # return "\n\n".join(header + body + footer)
        return "\n\n".join(header + body)

    def build_option_buttons(self, is_admin=False) -> InlineKeyboardMarkup:
        buttons = []
        for i, option in enumerate(self.options):
            option_data = f"{self.poll_id} {i}"
            option_button = InlineKeyboardButton(option.title, callback_data=option_data)
            buttons.append([option_button])
        if is_admin:
            back_data = f"{self.poll_id} {BACK}"
            back_button = InlineKeyboardButton("Back", callback_data=back_data)
            buttons.append([back_button])
        return InlineKeyboardMarkup(buttons)

    def build_admin_buttons(self) -> InlineKeyboardMarkup:
        publish_button = InlineKeyboardButton("Publish", switch_inline_query=self.title)
        refresh_data = f"{self.poll_id} {REFRESH}"
        refresh_button = InlineKeyboardButton("Refresh", callback_data=refresh_data)
        vote_data = f"{self.poll_id} {VOTE}"
        vote_button = InlineKeyboardButton("Vote", callback_data=vote_data)
        delete_data = f"{self.poll_id} {DELETE}"
        delete_button = InlineKeyboardButton("Delete", callback_data=delete_data)
        buttons = [[publish_button], [refresh_button], [vote_button, delete_button]]
        return InlineKeyboardMarkup(buttons)


class Option(object):
    def __init__(self, title: str, is_comment_required=False) -> None:
        self.title = title
        self.comment_required = is_comment_required
        self.respondents = OrderedDict()

    def comment_required(self) -> bool:
        return self.comment_required

    def toggle(self, uid: int, user_profile: dict) -> str:
        if uid in self.respondents:
            self.respondents.pop(uid, None)
            action = "removed from"
        else:
            self.respondents[uid] = user_profile.get("first_name", ""), user_profile.get("last_name", "")
            action = "added to"
        return f"You are {action} {self.title}!"

    def generate_namelist(self) -> str:
        return "\n".join(f"{first_name} {last_name}" for first_name, last_name in self.respondents.values())

    def render_text(self) -> str:
        title = make_html_bold(self.title)
        if self.respondents:
            title += f" ({len(self.respondents)} {EMOJI_PEOPLE})"
        namelist = strip_html_symbols(self.generate_namelist())
        return f"{title}\n{namelist}"


def to_id_string(uid: int) -> str:
    return str(uid).zfill(64)


def start_new_session(uid: int) -> None:
    all_sessions[uid] = Session(uid)


def create_random_string(n: int) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))


def strip_html_symbols(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def make_html_bold(text):
    return f"<b>{strip_html_symbols(text)}</b>"


def make_html_bold_first_line(text):
    text_split = text.split("\n", 1)
    output = make_html_bold(text_split[0])
    return output + "\n" + strip_html_symbols(text_split[1]) if len(text_split) > 1 else output
