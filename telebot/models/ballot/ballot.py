from __future__ import annotations

from datetime import datetime
from typing import List, Set

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from telebot.database import database as db
from telebot.models import constant as const
from telebot.models.user.user import User
from telebot.utils import util
from telebot.utils.ui import PaginationButtonGroup

ballot_storage = dict()


class Ballot(object):
    def __init__(
        self, ballot_id: str, title: str, uid: int, description: str, options: List[BallotOption],
        choices: List[str], single_response: bool, message_details: set, expiry: int, created_date: datetime
    ) -> None:
        self.ballot_id = ballot_id
        self.title = title
        self.creator_id = uid
        self.description = description
        self.options = options
        self.choices = choices
        self.single_response = single_response
        self.message_details = message_details
        self.expiry = expiry
        self.created_date = created_date

    @staticmethod
    def get_ballot_by_id(ballot_id: str) -> Ballot:
        return ballot_storage.get(ballot_id, None)

    @staticmethod
    def get_ballots_by_ids(ballot_ids: Set[str], filters="") -> List[Ballot]:
        ballot_lists = [Ballot.get_ballot_by_id(ballot_id) for ballot_id in ballot_ids]
        return [ballot for ballot in ballot_lists if filters.lower() in ballot.get_title().lower()]

    @classmethod
    def create_new(
        cls, title: str, uid: int, description: str, option_titles: List[str], choices: List[str]
    ) -> Ballot:
        ballot_id = util.generate_random_id(const.BALLOT_ID_LENGTH, set(ballot_storage.keys()))
        ballot = cls(
            ballot_id, title, uid, description, list(), choices, True, set(), const.EXPIRY, datetime.now(tz=const.tz)
        )

        for option_title in option_titles:
            ballot.add_option(BallotOption.create_new(option_title))

        ballot_storage[ballot_id] = ballot
        return ballot

    @classmethod
    def load(
        cls, ballot_id: str, title: str, uid: int, description: str, options: List[dict], choices: List[str],
        single_response: bool, message_details: List[str], expiry: int, created_date: str
    ) -> None:
        ballot = cls(
            ballot_id, title, uid, description, list(), choices, single_response, set(message_details), expiry,
            datetime.fromisoformat(created_date)
        )

        for option_data in options:
            option = BallotOption.load(option_data.get(db.BALLOT_OPTION_TITLE, ""))
            for choice_id in option_data.get(db.BALLOT_OPTION_ALLOCATIONS, []):
                if ballot.is_valid_choice(choice_id):
                    option.add_allocation(choice_id, ballot.get_choice(choice_id))
            ballot.add_option(option)

        ballot_storage[ballot_id] = ballot
        return

    def delete(self) -> None:
        ballot_storage.pop(self.ballot_id, None)

    def get_creator_id(self) -> int:
        return self.creator_id

    def get_ballot_id(self) -> str:
        return self.ballot_id

    def get_title(self) -> str:
        return self.title

    def set_title(self, title: str) -> None:
        self.title = title

    def get_description(self) -> str:
        return self.description

    def set_description(self, description: str) -> None:
        self.description = description

    def get_options(self) -> List[BallotOption]:
        return self.options

    def get_option(self, opt_id) -> BallotOption:
        return self.options[opt_id] if self.is_valid_option(opt_id) else None

    def add_option(self, option) -> None:
        self.options.append(option)

    def is_valid_option(self, opt_id: int) -> bool:
        return 0 <= opt_id < len(self.options)

    def get_choices(self) -> List[str]:
        return self.choices

    def get_choice(self, choice_id: int) -> str:
        return self.choices[choice_id] if self.is_valid_choice(choice_id) else ""

    def is_valid_choice(self, choice_id: int) -> bool:
        return 0 <= choice_id < len(self.choices)

    def get_message_details(self) -> Set[str]:
        return self.message_details

    def add_message_details(self, mid: str) -> None:
        self.message_details.add(mid)

    def has_message_details(self, mid: str) -> bool:
        return mid in self.message_details

    def is_single_response(self) -> bool:
        return self.single_response

    def set_single_response(self, single_response: bool) -> None:
        self.single_response = single_response

    def toggle_response_type(self) -> str:
        # if any(option.is_allocated() for option in self.options):
        #     return "Cannot change response type for non-empty list."
        self.single_response = not self.single_response
        status = "single response" if self.single_response else "multi-response"
        return f"Response type is changed to {status}."

    def get_created_date(self) -> datetime:
        return self.created_date

    def get_expiry(self) -> int:
        return self.expiry

    def set_expiry(self, expiry: int) -> None:
        self.expiry = expiry

    def get_ballot_hash(self) -> str:
        return f"{self.ballot_id}_{util.simple_hash(self.title, self.ballot_id, variance=False)}"

    def toggle(self, opt_id: int, choice_id: int) -> str:
        if not self.is_valid_option(opt_id) or not self.is_valid_choice(choice_id):
            return "Sorry, invalid option or choice."

        if self.single_response:
            for i, option in enumerate(self.options):
                if i != opt_id:
                    option.remove_allocation(choice_id)
        return self.options[opt_id].toggle(choice_id, self.get_choice(choice_id))

    def contains(self, opt_id: int, choice_id: int):
        if opt_id < len(self.options):
            return self.options[opt_id].contains(choice_id)
        return False

    def get_allocation_count(self) -> int:
        all_allocations_id = set(choice_id for option in self.options for choice_id in option.get_allocations())
        return len(all_allocations_id)

    def generate_allocations_summary(self) -> str:
        allocation_count = self.get_allocation_count()
        if allocation_count in (0, 1):
            summary = f"{allocation_count} person allocated out of {len(self.choices)}"
        else:
            summary = f"{allocation_count} people allocated out of {len(self.choices)}"
        return summary

    def generate_linked_summary(self, include_creator=False) -> str:
        short_bold_title = util.make_html_bold(self.title)[:60]
        header = f"{short_bold_title} ({self.get_allocation_count()} {const.EMOJI_PEOPLE})"
        link = f"/ballot_{self.ballot_id}"
        creator = f"{const.EMOJI_CROWN} {User.get_user_by_id(self.creator_id).get_name()}"
        return "\n".join([header] + [f"{link} {creator}"]) if include_creator else "\n".join([header] + [link])

    def generate_options_summary(self) -> str:
        return " / ".join(option.get_title() for option in self.options)

    def render_text(self) -> str:
        title = util.make_html_bold(self.title)
        description = util.make_html_italic(self.description)
        header = [f"{const.EMOJI_BALLOT} {title}\n{description}" if description else title]
        body = [option.render_text() for option in self.options]
        footer = [f"{const.EMOJI_PEOPLE} {self.generate_allocations_summary()}"]
        return "\n\n".join(header + body + footer)

    def build_update_buttons(self) -> InlineKeyboardMarkup:
        update_button = util.build_switch_button("Update", f"/update {self.get_ballot_hash()}", to_self=True)
        refresh_button = self.build_button("Refresh", const.USER_REFRESH)
        buttons = [[update_button, refresh_button]]
        return InlineKeyboardMarkup(buttons)

    def build_option_buttons(self) -> InlineKeyboardMarkup:
        buttons = []
        for i, option in enumerate(self.options):
            option_button = self.build_button(option.get_title(), f"{const.OPTION}_{i}")
            buttons.append([option_button])
        refresh_button = self.build_button("Refresh", const.REFRESH_OPT)
        done_button = self.build_button("Done", const.RETURN)
        buttons.append([refresh_button, done_button])
        return InlineKeyboardMarkup(buttons)

    def build_admin_buttons(self) -> InlineKeyboardMarkup:
        publish_button = util.build_switch_button("Publish", self.title)
        settings_button = self.build_button("Settings", const.SETTINGS)
        refresh_button = self.build_button("Refresh", const.REFRESH)
        close_button = self.build_button("Close", const.CLOSE)
        buttons = [[publish_button], [settings_button], [refresh_button, close_button]]
        return InlineKeyboardMarkup(buttons)

    def build_settings_buttons(self, is_creator=False) -> InlineKeyboardMarkup:
        response_text = "Multi-Response" if self.single_response else "Single Response"
        toggle_response_button = self.build_button(f"Change to {response_text}", const.RESPONSE)
        back_button = self.build_button("Back", const.BACK)
        buttons = [[toggle_response_button], [back_button]]
        if is_creator:
            delete_button = self.build_button("Delete ReversePoll", const.DELETE)
            buttons.insert(-1, [delete_button])
        return InlineKeyboardMarkup(buttons)

    def build_choice_buttons(self, opt_id: int, page_number: int = 0, index: int = 0) -> InlineKeyboardMarkup:
        choice_button_group = PaginationButtonGroup(
            self.choices, (const.BALLOT_SUBJECT, f"{const.CHOICE}_{opt_id}", self.ballot_id), items_per_page=5,
            is_horizontal_buttons=True, is_cyclic=True, hidden_enabled=True
        )
        buttons = choice_button_group.build_buttons(page_number, index)
        back_button = self.build_button("Back", const.OPTIONS)
        buttons.append([back_button])
        return InlineKeyboardMarkup(buttons)

    def build_delete_confirm_buttons(
        self, delete_action: str, back_action: str, delete_text="Delete", back_text="No"
    ) -> InlineKeyboardMarkup:
        delete_button = self.build_button(delete_text, f"{const.DELETE_YES}_{delete_action}")
        back_button = self.build_button(back_text, back_action)
        buttons = [[delete_button, back_button]]
        return InlineKeyboardMarkup(buttons)

    def build_button(self, text: str, action: str) -> InlineKeyboardButton:
        return util.build_button(text, const.BALLOT_SUBJECT, action, self.ballot_id)

    def to_json(self) -> dict:
        return {
            db.BALLOT_ID:              self.ballot_id,
            db.BALLOT_TITLE:           self.title,
            db.BALLOT_CREATOR_ID:      self.creator_id,
            db.BALLOT_DESCRIPTION:     self.description,
            db.BALLOT_OPTIONS:         [option.to_json() for option in self.options],
            db.BALLOT_CHOICES:         self.choices,
            db.BALLOT_SINGLE_RESPONSE: self.single_response,
            db.BALLOT_MESSAGE_DETAILS: list(self.message_details),
            db.BALLOT_EXPIRY:          self.expiry,
            db.BALLOT_CREATED_DATE:    self.created_date.isoformat()
        }


class BallotOption(object):
    def __init__(self, title: str) -> None:
        self.title = title
        self.allocations = dict()

    @classmethod
    def create_new(cls, title: str):
        return cls(title)

    @classmethod
    def load(cls, title: str):
        return cls(title)

    def get_title(self) -> str:
        return self.title

    def contains(self, choice_id: int) -> bool:
        return choice_id in self.allocations

    def get_allocations(self) -> dict:
        return self.allocations

    def is_allocated(self) -> bool:
        return len(self.allocations) > 0

    def add_allocation(self, choice_id: int, name: str) -> None:
        self.allocations[choice_id] = name

    def remove_allocation(self, choice_id: int) -> None:
        if choice_id in self.allocations:
            self.allocations.pop(choice_id)

    def toggle(self, choice_id: int, choice_name: str) -> str:
        if choice_id in self.allocations:
            self.allocations.pop(choice_id, None)
            action = "removed from"
        else:
            self.allocations[choice_id] = choice_name
            action = "added to"
        return f"{choice_name} is {action} {self.title}!"

    def generate_namelist(self) -> str:
        return "\n".join(self.allocations.values())

    def render_text(self) -> str:
        title = util.make_html_bold(self.title)
        if self.allocations:
            title += f" ({len(self.allocations)} {const.EMOJI_PEOPLE})"
        namelist = util.strip_html_symbols(self.generate_namelist())
        return f"{title}\n{namelist}"

    def to_json(self) -> dict:
        return {
            db.BALLOT_OPTION_TITLE:       self.title,
            db.BALLOT_OPTION_ALLOCATIONS: list(self.allocations)
        }
