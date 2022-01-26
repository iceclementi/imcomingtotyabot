"""Backend models"""
from datetime import datetime
from collections import OrderedDict
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
import util

# Settings
POLL_ID_LENGTH = 4
EMOJI_PEOPLE = "\U0001f465"
SESSION_EXPIRY = 1  # In hours
POLL_EXPIRY = 720

# Session Progress types
NONE = "none"
TITLE = "title"
OPTION = "option"

# Button actions
PUBLISH = "publish"
REFRESH = "refresh"
CUSTOMISE = "custom"
RESPONSE = "response"
COMMENT = "comment"
VOTE = "vote"
DELETE = "delete"
DELETE_YES = "delete-yes"
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
    def __init__(self, uid: int, poll_id: str) -> None:
        self.creator_id = uid
        self.poll_id = poll_id
        self.title = ""
        self.options = []
        self.single_response = True
        self.inline_ids = []
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

    def is_single_response(self) -> bool:
        return self.single_response

    def toggle_response_type(self) -> str:
        if any(option.has_votes() for option in self.options):
            return "Cannot change response type for non-empty poll."
        self.single_response = not self.single_response
        status = "single response" if self.single_response else "multi-response"
        return f"Response type is changed to {status}."

    def get_inline_ids(self) -> list:
        return self.inline_ids

    def add_inline_id(self, inline_id: str) -> None:
        if inline_id not in self.inline_ids:
            self.inline_ids.append(inline_id)

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

    def delete_poll(self) -> None:
        all_polls.pop(self.poll_id)

    @staticmethod
    def create_new_poll(uid: int) -> str:
        poll_id = util.create_random_string(POLL_ID_LENGTH)
        while poll_id in all_polls:
            poll_id = util.create_random_string(POLL_ID_LENGTH)
        all_polls[poll_id] = Poll(uid, poll_id)
        return poll_id

    @staticmethod
    def get_poll_by_id(poll_id: str):
        return all_polls.get(poll_id, None)

    @staticmethod
    def get_polls_created_by_user(uid: int, filters="", limit=50) -> list:
        all_user_polls = [poll for poll in all_polls.values()
                          if poll.get_creator_id() == uid and filters.lower() in poll.get_title().lower()]
        return sorted(all_user_polls, key=lambda poll: poll.get_created_date(), reverse=True)[:limit]

    def toggle(self, opt_id: int, uid: int, user_profile: dict, comment="") -> str:
        if opt_id >= len(self.options):
            return "Sorry, invalid option."

        if self.single_response:
            for i, option in enumerate(self.options):
                if i != opt_id:
                    option.remove_user(uid)
        return self.options[opt_id].toggle(uid, user_profile, comment)

    def toggle_comment_requirement(self, opt_id: int) -> str:
        if opt_id >= len(self.options):
            return "Sorry, invalid option."
        return self.options[opt_id].toggle_comment_requirement(opt_id)

    def generate_respondents_summary(self) -> str:
        all_respondents_uid = set(uid for option in self.options for uid in option.respondents)
        respondents_count = len(all_respondents_uid)
        if respondents_count == 0:
            summary = "Nobody responded"
        elif respondents_count == 1:
            summary = "1 person responded"
        else:
            summary = f"{respondents_count} people responded"
        return summary

    def generate_linked_summary(self) -> str:
        short_bold_title = [util.make_html_bold(self.title)[:60]]
        respondents_summary = [f"({self.generate_respondents_summary()})"]
        link = [f"/poll_{self.poll_id}"]
        return "\n".join(short_bold_title + respondents_summary + link)

    def generate_options_summary(self) -> str:
        return " / ".join(option.title for option in self.options)

    def render_text(self) -> str:
        header = [util.make_html_bold_first_line(self.title)]
        body = [option.render_text() for option in self.options]
        footer = [f"{EMOJI_PEOPLE} {self.generate_respondents_summary()}"]
        return "\n\n".join(header + body + footer)

    def build_option_buttons(self, is_admin=False) -> InlineKeyboardMarkup:
        buttons = []
        for i, option in enumerate(self.options):
            option_button = util.build_button(option.get_title(), self.poll_id, str(i))
            buttons.append([option_button])
        if is_admin:
            back_button = util.build_button("Back", self.poll_id, BACK)
            buttons.append([back_button])
        return InlineKeyboardMarkup(buttons)

    def build_admin_buttons(self) -> InlineKeyboardMarkup:
        publish_button = InlineKeyboardButton("Publish", switch_inline_query=self.title)
        refresh_button = util.build_button("Refresh", self.poll_id, REFRESH)
        customise_button = util.build_button("Customise", self.poll_id, CUSTOMISE)
        vote_button = util.build_button("Vote", self.poll_id, VOTE)
        delete_button = util.build_button("Delete", self.poll_id, DELETE)
        buttons = [[publish_button], [refresh_button], [customise_button], [vote_button, delete_button]]
        return InlineKeyboardMarkup(buttons)

    def build_customise_buttons(self) -> InlineKeyboardMarkup:
        response_text = "Multi-Response" if self.single_response else "Single Response"
        toggle_response_button = util.build_button(f"Change to {response_text}", self.poll_id, RESPONSE)
        enforce_comments_button = util.build_button("Change Comment Requirements", self.poll_id, COMMENT)
        back_button = util.build_button("Back", self.poll_id, BACK)
        buttons = [[toggle_response_button], [enforce_comments_button], [back_button]]
        return InlineKeyboardMarkup(buttons)

    def build_option_comment_buttons(self) -> InlineKeyboardMarkup:
        buttons = []
        for i, option in enumerate(self.options):
            button_text = option.get_title() + (" (required)" if option.is_comment_required() else "")
            option_button = util.build_button(button_text, self.poll_id, f"{COMMENT}-{i}")
            buttons.append([option_button])
        back_button = util.build_button("Back", self.poll_id, BACK)
        buttons.append(back_button)
        return InlineKeyboardMarkup(buttons)

    def build_delete_confirmation_buttons(self) -> InlineKeyboardMarkup:
        yes_button = util.build_button("Delete", self.poll_id, DELETE_YES)
        no_button = util.build_button("No", self.poll_id, BACK)
        buttons = [[yes_button, no_button]]
        return InlineKeyboardMarkup(buttons)


class Option(object):
    def __init__(self, title: str, is_comment_required=False) -> None:
        self.title = title
        self.comment_required = is_comment_required
        self.respondents = OrderedDict()

    def get_title(self) -> str:
        return self.title

    def is_comment_required(self) -> bool:
        return self.comment_required

    def has_votes(self) -> bool:
        return len(self.respondents) > 0

    def remove_user(self, uid: int) -> None:
        if uid in self.respondents:
            self.respondents.pop(uid)

    def toggle(self, uid: int, user_profile: dict, comment="") -> str:
        if uid in self.respondents:
            self.respondents.pop(uid, None)
            action = "removed from"
        else:
            self.respondents[uid] = user_profile.get("first_name", ""), user_profile.get("last_name", ""), comment
            action = "added to"
        return f"You are {action} {self.title}!"

    def toggle_comment_requirement(self) -> str:
        self.comment_required = not self.comment_required
        action = "now requires comments" if self.comment_required else "no longer requires comments"
        return f"Option '{self.title}' {action}"

    def generate_namelist(self) -> str:
        namelist = []
        for first_name, last_name, comment in self.respondents.values():
            name = first_name
            if last_name:
                name += f" {last_name}"
            if comment:
                name += f" ({comment})"
            namelist.append(name)
        return "\n".join(namelist)

    def render_text(self) -> str:
        title = util.make_html_bold(self.title)
        if self.respondents:
            title += f" ({len(self.respondents)} {EMOJI_PEOPLE})"
        namelist = util.strip_html_symbols(self.generate_namelist())
        return f"{title}\n{namelist}"
