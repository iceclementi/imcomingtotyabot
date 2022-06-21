from __future__ import annotations

from collections import OrderedDict
from datetime import datetime
from typing import List, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from database import database as db
from models import constant as const
from models.user.user import User
from utils import util

poll_storage = dict()


class Poll(object):
    def __init__(
        self, poll_id: str, title: str, uid: int, description: str, options: list, single_response: bool,
        message_details: set, expiry: int, created_date: datetime
    ) -> None:
        self._poll_id = poll_id
        self._creator_id = uid
        self._title = title
        self._description = description
        self._options = options
        self._single_response = single_response
        self._message_details = message_details
        self._expiry = expiry
        self._created_date = created_date

    @staticmethod
    def get_poll_by_id(poll_id: str) -> Poll:
        return poll_storage.get(poll_id, None)

    @staticmethod
    def get_polls_by_ids(poll_ids: set, filters="") -> List[Poll]:
        poll_lists = [Poll.get_poll_by_id(poll_id) for poll_id in poll_ids]
        return [poll for poll in poll_lists if filters.lower() in poll.get_title().lower()]

    @classmethod
    def create_new(cls, title: str, uid: int, description: str, option_titles: list) -> Poll:
        poll_id = util.generate_random_id(const.POLL_ID_LENGTH, set(poll_storage.keys()))
        poll = cls(poll_id, title, uid, description, list(), True, set(), const.EXPIRY, datetime.now(tz=const.tz))

        for option_title in option_titles:
            poll.add_option(Option.create_new(option_title))

        poll_storage[poll_id] = poll
        return poll

    @classmethod
    def load(
        cls, poll_id: str, title: str, uid: int, description: str, options: list, single_response: bool,
        message_details: list, expiry: int, created_date: str
    ) -> None:
        poll = cls(
            poll_id, title, uid, description, list(), single_response, set(message_details),
            expiry, datetime.fromisoformat(created_date)
        )

        for option_data in options:
            poll.add_option(
                Option.load(
                    option_data.get(db.OPTION_TITLE, ""),
                    option_data.get(db.OPTION_COMMENT_REQUIRED, False),
                    option_data.get(db.OPTION_RESPONDENTS, [])
                )
            )

        poll_storage[poll_id] = poll
        return

    def delete(self) -> None:
        poll_storage.pop(self._poll_id, None)

    def get_creator_id(self) -> int:
        return self._creator_id

    def get_poll_id(self) -> str:
        return self._poll_id

    def get_title(self) -> str:
        return self._title

    def set_title(self, title: str) -> None:
        self._title = title

    def get_description(self) -> str:
        return self._description

    def set_description(self, description: str) -> None:
        self._description = description

    def get_options(self) -> List[Option]:
        return self._options

    def add_option(self, option) -> None:
        self._options.append(option)

    def get_message_details(self) -> set:
        return self._message_details

    def add_message_details(self, mid: str) -> None:
        self._message_details.add(mid)

    def has_message_details(self, mid: str) -> bool:
        return mid in self._message_details

    def is_single_response(self) -> bool:
        return self._single_response

    def set_single_response(self, single_response: bool) -> None:
        self._single_response = single_response

    def toggle_response_type(self) -> str:
        # if any(option.has_votes() for option in self.options):
        #     return "Cannot change response type for non-empty poll."
        self._single_response = not self._single_response
        status = "single response" if self._single_response else "multi-response"
        return f"Response type is changed to {status}."

    def get_created_date(self) -> datetime:
        return self._created_date

    def get_expiry(self) -> int:
        return self._expiry

    def set_expiry(self, expiry: int) -> None:
        self._expiry = expiry

    def get_poll_hash(self) -> str:
        return f"{self._poll_id}_{util.simple_hash(self._title, self._poll_id, variance=False)}"

    def toggle(self, opt_id: int, uid: int, user_profile: dict, comment="") -> str:
        if opt_id >= len(self._options):
            return "Sorry, invalid option."

        if self._single_response:
            for i, option in enumerate(self._options):
                if i != opt_id:
                    option.remove_user(uid)
        return self._options[opt_id].toggle(uid, user_profile, comment)

    def is_voted_by_user(self, opt_id: int, uid: int) -> bool:
        if opt_id < len(self._options):
            return self._options[opt_id].is_voted_by_user(uid)
        return False

    def edit_user_comment(self, opt_id: int, uid: int, comment: str) -> str:
        if opt_id >= len(self._options):
            return "Sorry, invalid option."
        option = self._options[opt_id]
        if not option.is_voted_by_user(uid):
            return "You need to vote for this option first before adding comments."
        option.edit_user_comment(uid, comment)
        return ""

    def toggle_comment_requirement(self, opt_id: int) -> str:
        if opt_id >= len(self._options):
            return "Sorry, invalid option."
        return self._options[opt_id].toggle_comment_requirement()

    def is_user_comment_required(self, opt_id: int, uid: int) -> bool:
        if opt_id >= len(self._options):
            return False
        return self._options[opt_id].is_user_comment_required(uid)

    def get_respondent_count(self) -> int:
        all_respondents_uid = set(uid for option in self._options for uid in option.get_respondents())
        return len(all_respondents_uid)

    def generate_respondents_summary(self) -> str:
        respondents_count = self.get_respondent_count()
        if respondents_count == 0:
            summary = "Nobody responded"
        elif respondents_count == 1:
            summary = "1 person responded"
        else:
            summary = f"{respondents_count} people responded"
        return summary

    def generate_linked_summary(self, include_creator=False) -> str:
        short_bold_title = util.make_html_bold(self._title)[:60]
        header = f"{short_bold_title} ({self.get_respondent_count()} {const.EMOJI_PEOPLE})"
        link = f"/poll_{self._poll_id}"
        creator = f"{const.EMOJI_CROWN} {User.get_user_by_id(self._creator_id).get_name()}"
        return "\n".join([header] + [f"{link} {creator}"]) if include_creator else "\n".join([header] + [link])

    def generate_options_summary(self) -> str:
        return " / ".join(option.get_title() for option in self._options)

    def render_text(self) -> str:
        title = util.make_html_bold(self._title)
        description = util.make_html_italic(self._description)
        header = [f"{const.EMOJI_POLL} {title}\n{description}" if description else title]
        body = [option.render_text() for option in self._options]
        footer = [f"{const.EMOJI_PEOPLE} {self.generate_respondents_summary()}"]
        return "\n\n".join(header + body + footer)

    def build_option_buttons(self) -> InlineKeyboardMarkup:
        buttons = []
        for i, option in enumerate(self._options):
            if option.is_comment_required():
                option_button = util.build_switch_button(
                    option.get_title(), f"/vote {self.get_poll_hash()}_{i}", to_self=True
                )
            else:
                option_button = self.build_button(option.get_title(), str(i))
            buttons.append([option_button])
        edit_comments_button = util.build_switch_button(
            "Comment", f"/comment {self.get_poll_hash()}", to_self=True
        )
        refresh_button = self.build_button("Refresh", const.REFRESH_OPT)
        buttons.append([edit_comments_button, refresh_button])
        return InlineKeyboardMarkup(buttons)

    def build_admin_buttons(self) -> InlineKeyboardMarkup:
        publish_button = util.build_switch_button("Publish", self._title)
        settings_button = self.build_button("Settings", const.SETTINGS)
        refresh_button = self.build_button("Refresh", const.REFRESH)
        close_button = self.build_button("Close", const.CLOSE)
        buttons = [[publish_button], [settings_button], [refresh_button, close_button]]
        return InlineKeyboardMarkup(buttons)

    def build_settings_buttons(self, is_creator=False) -> InlineKeyboardMarkup:
        response_text = "Multi-Response" if self._single_response else "Single Response"
        toggle_response_button = self.build_button(f"Change to {response_text}", const.RESPONSE)
        enforce_comments_button = self.build_button("Change Comment Requirements", const.COMMENT)
        back_button = self.build_button("Back", const.BACK)
        buttons = [[toggle_response_button], [enforce_comments_button], [back_button]]
        if is_creator:
            delete_button = self.build_button("Delete Poll", const.DELETE)
            buttons.insert(-1, [delete_button])
        return InlineKeyboardMarkup(buttons)

    def build_option_comment_required_buttons(self) -> InlineKeyboardMarkup:
        buttons = []
        for i, option in enumerate(self._options):
            button_text = option.get_title() + (" (required)" if option.is_comment_required() else "")
            option_button = self.build_button(button_text, f"{const.COMMENT}_{i}")
            buttons.append([option_button])
        back_button = self.build_button("Back", const.BACK)
        buttons.append([back_button])
        return InlineKeyboardMarkup(buttons)

    def build_option_comment_text_and_buttons(self, uid: int) -> Tuple[str, InlineKeyboardMarkup]:
        buttons = []
        for i, option in enumerate(self._options):
            if option.is_voted_by_user(uid):
                option_button = self.build_button(option.get_title(), f"{const.EDIT_COMMENT}_{i}")
                buttons.append([option_button])

        if buttons:
            response = "Select the option to add or change your comment."
        else:
            response = util.make_html_italic("You have to vote first before you can enter a comment.")

        return_button = self.build_button("Cancel", const.RETURN)
        buttons.append([return_button])

        return response, InlineKeyboardMarkup(buttons)

    def build_comment_complete_buttons(self) -> InlineKeyboardMarkup:
        back_button = self.build_button("Back", const.EDIT_COMMENT)
        return_button = self.build_button("Return to Chat", const.RETURN)
        buttons = [[back_button, return_button]]
        return InlineKeyboardMarkup(buttons)

    def build_delete_confirm_buttons(
        self, delete_action: str, back_action: str, delete_text="Delete", back_text="No"
    ) -> InlineKeyboardMarkup:
        delete_button = self.build_button(delete_text, f"{const.DELETE_YES}_{delete_action}")
        back_button = self.build_button(back_text, back_action)
        buttons = [[delete_button, back_button]]
        return InlineKeyboardMarkup(buttons)

    def build_button(self, text: str, action: str) -> InlineKeyboardButton:
        return util.build_button(text, const.POLL_SUBJECT, action, self._poll_id)

    def to_json(self) -> dict:
        return {
            db.POLL_ID:              self._poll_id,
            db.POLL_TITLE:           self._title,
            db.POLL_CREATOR_ID:      self._creator_id,
            db.POLL_DESCRIPTION:     self._description,
            db.POLL_OPTIONS:         [option.to_json() for option in self._options],
            db.POLL_SINGLE_RESPONSE: self._single_response,
            db.POLL_MESSAGE_DETAILS: list(self._message_details),
            db.POLL_EXPIRY:          self._expiry,
            db.POLL_CREATED_DATE:    self._created_date.isoformat()
        }


class Option(object):
    def __init__(self, title: str, is_comment_required: bool, respondents: list) -> None:
        self.title = title
        self.comment_required = is_comment_required
        self.respondents = OrderedDict(respondents)

    @classmethod
    def create_new(cls, title: str, is_comment_required=False):
        return cls(title, is_comment_required, list())

    @classmethod
    def load(cls, title: str, is_comment_required: bool, respondents: list):
        return cls(title, is_comment_required, respondents)

    def get_title(self) -> str:
        return self.title

    def is_comment_required(self) -> bool:
        return self.comment_required

    def is_user_comment_required(self, uid: int) -> bool:
        return self.comment_required and uid not in self.respondents

    def is_voted_by_user(self, uid: int) -> bool:
        return uid in self.respondents

    def get_respondents(self) -> OrderedDict:
        return self.respondents

    def has_votes(self) -> bool:
        return len(self.respondents) > 0

    def get_user_comment(self, uid: int) -> str:
        if uid not in self.respondents:
            return "No comment."
        _, _, comment = self.respondents[uid]
        return comment if comment else "No comment."

    def edit_user_comment(self, uid: int, comment: str) -> None:
        if uid not in self.respondents:
            return
        first_name, last_name, _ = self.respondents[uid]
        self.respondents[uid] = first_name, last_name, comment

    def toggle(self, uid: int, user_profile: dict, comment="") -> str:
        if uid in self.respondents:
            self.respondents.pop(uid, None)
            action = "removed from"
        else:
            self.respondents[uid] = user_profile.get("first_name", ""), user_profile.get("last_name", ""), comment
            action = "added to"
        return f"You are {action} {self.title}!"

    def remove_user(self, uid: int) -> None:
        if uid in self.respondents:
            self.respondents.pop(uid)

    def toggle_comment_requirement(self) -> str:
        self.comment_required = not self.comment_required
        action = "now requires comments" if self.comment_required else "no longer requires comments"
        return f"Option '{self.title}' {action}."

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
            title += f" ({len(self.respondents)} {const.EMOJI_PEOPLE})"
        namelist = util.strip_html_symbols(self.generate_namelist())
        return f"{title}\n{namelist}"

    def to_json(self) -> dict:
        return {
            db.OPTION_TITLE:            self.title,
            db.OPTION_COMMENT_REQUIRED: self.comment_required,
            db.OPTION_RESPONDENTS:      list(self.respondents.items())
        }
