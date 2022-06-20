from __future__ import annotations

import re
from typing import Dict, List, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from database import database as db
from models import models
from models.format_text_code import FormatTextCode
from models.template import Template
from models.user import User
from utils import util

temp_poll_storage = dict()


class PollTemplate(Template):
    def __init__(
        self, temp_id: str, name: str, description: str, title_format: FormatTextCode,
        description_format: FormatTextCode, options: List[str], single_response: bool,
        creator_id: int
    ) -> None:
        super().__init__(temp_id, name, description, title_format, description_format, creator_id)
        self._options = options
        self._is_single_response = single_response

    @staticmethod
    def get_template_by_id(temp_id: str) -> PollTemplate:
        return temp_poll_storage.get(temp_id, None)

    @staticmethod
    def get_templates_by_ids(temp_ids: set, filters="") -> List[PollTemplate]:
        template_lists = [PollTemplate.get_template_by_id(temp_id) for temp_id in temp_ids]
        return [template for template in template_lists if filters.lower() in template.name.lower()]

    @classmethod
    def create_new(
        cls, name: str, description: str, title_format_string: str, description_format_string: str,
        options: List[str], single_response: bool, creator_id: int
    ) -> PollTemplate:
        temp_id = "P" + util.generate_random_id(models.POLL_ID_LENGTH, set(temp_poll_storage.keys()))
        title_format = FormatTextCode.create_new(title_format_string)
        description_format = FormatTextCode.create_new(description_format_string)
        template = cls(
            temp_id, name, description, title_format, description_format, options, single_response, creator_id
        )
        temp_poll_storage[temp_id] = template
        return template

    @classmethod
    def load(
        cls, temp_id: str, name: str, description: str, title_format_data: Dict[str, Dict[str, List[str]]],
        description_format_data: Dict[str, Dict[str, List[str]]], options: List[str], single_response: bool,
        creator_id: int
    ) -> None:
        title_format = FormatTextCode.load(
            title_format_data.get(db.FORMAT_TEXT, ""),
            title_format_data.get(db.FORMAT_CODES, dict())
        )
        description_format = FormatTextCode.load(
            description_format_data.get(db.FORMAT_TEXT, ""),
            description_format_data.get(db.FORMAT_CODES, dict())
        )

        template = cls(
            temp_id, name, description, title_format, description_format, options, single_response, creator_id
        )
        temp_poll_storage[temp_id] = template
        return

    def delete(self) -> None:
        temp_poll_storage.pop(self._temp_id, None)

    @property
    def options(self) -> List[str]:
        return self._options

    @property
    def is_single_response(self) -> bool:
        return self._is_single_response

    @is_single_response.setter
    def is_single_response(self, new_response_type: bool) -> None:
        self._is_single_response = new_response_type
        return

    def toggle_response_type(self) -> str:
        self.is_single_response = not self.is_single_response
        status = "single response" if self.is_single_response else "multi-response"
        return f"Response type is changed to {status}."

    def generate_linked_summary(self, include_creator=False) -> str:
        header = f"<b>{self.name} {models.EMOJI_POLL}</b>"
        if self.description:
            header += f"\n<i>{self.description}</i>"
        link = f"/temp_{self.temp_id}"
        creator = f"{models.EMOJI_CROWN} {User.get_user_by_id(self.creator_id).get_name()}"
        return "\n".join([header] + [f"{link} {creator}"]) if include_creator else "\n".join([header] + [link])

    def render_text(self) -> str:
        header = f"<b>{models.EMOJI_POLL} {self.name} (Template)</b>"
        if self.description:
            header += f"\n<i>{self.description}</i>"
        title_body = f"<b>Title</b>\n{self.title_format.render_details()}"
        description_body = f"<b>Description</b>\n{self.description_format.render_details()}"
        options_body = f"<b>Options</b>\n{util.list_to_indexed_list_string(self.options)}"
        response_type_body = f"<b>Response Type</b> - {'Single' if self.is_single_response else 'Multiple'}"
        return "\n\n".join([header] + [title_body] + [description_body] + [options_body] + [response_type_body])

    def render_title_code(self, header="") -> str:
        return (
            f"<b>{header}</b>\n{self.title_format.render_details()}"
            if header
            else f"<b>Title Format</b>\n{self.title_format.render_details()}"
        )

    def render_description_code(self, header="") -> str:
        return (
            f"<b>{header}</b>\n{self.description_format.render_details()}"
            if header
            else f"<b>Description Format</b>\n{self.description_format.render_details()}"
        )

    def render_title(self, format_inputs="") -> Tuple[str, bool]:
        return self.title_format.render_format_text(format_inputs)

    def render_description(self, format_inputs="") -> Tuple[str, bool]:
        return self.description_format.render_format_text(format_inputs)

    def render_title_and_description(self, format_inputs="") -> Tuple[str, str, bool]:
        offset = len(self.title_format.format_codes)

        # Separate title and description format inputs using ".." as separator
        match = re.match(r"^((?:.|\n)*)(?:(?<=^)|(?<=\n))\.\.(?=$|\n)((?:.|\n)*)$", format_inputs)
        if not match:
            title_result, is_title_valid = self.title_format.render_format_text(format_inputs.strip())
            description_result, is_description_valid = self.description_format.render_format_text()
        else:
            title_result, is_title_valid = self.title_format.render_format_text(match.group(1).strip())
            description_result, is_description_valid = self.description_format.render_format_text(
                match.group(2).strip(), offset=offset
            )

        if not is_title_valid:
            return title_result, "", False
        elif not is_description_valid:
            return description_result, "", False
        else:
            return title_result, description_result, True

    def build_main_buttons(self) -> InlineKeyboardMarkup:
        generate_poll_button = self.build_button("Generate Poll", models.POLL)
        settings_buttons = self.build_button("Settings", models.SETTINGS)
        refresh_button = self.build_button("Refresh", models.REFRESH)
        close_button = self.build_button("Close", models.CLOSE)
        buttons = [[generate_poll_button], [settings_buttons], [refresh_button, close_button]]
        return InlineKeyboardMarkup(buttons)

    def build_format_title_buttons(self) -> InlineKeyboardMarkup:
        title_code_button = self.build_button("View Title Format Details", models.TEMP_TITLE_CODE)
        continue_button = self.build_button("Continue", models.DONE)
        cancel_button = self.build_button("Cancel", models.RESET)
        buttons = [[title_code_button], [cancel_button, continue_button]]
        return InlineKeyboardMarkup(buttons)

    def build_format_description_buttons(self) -> InlineKeyboardMarkup:
        description_code_button = self.build_button("View Description Format Details", models.TEMP_DESCRIPTION_CODE)
        build_button = self.build_button("Create", models.DONE)
        cancel_button = self.build_button("Cancel", models.RESET)
        skip_button = self.build_button("Skip", models.SKIP)
        buttons = [[description_code_button], [skip_button], [cancel_button, build_button]]
        return InlineKeyboardMarkup(buttons)

    def build_settings_buttons(self, is_creator=False) -> InlineKeyboardMarkup:
        edit_template_details_button = self.build_button("Edit Template Details", f"{models.EDIT}_{models.TEMPLATE}")
        edit_title_button = self.build_button("Edit Title Format", f"{models.EDIT}_{models.TITLE}")
        edit_description_button = self.build_button("Edit Description Format", f"{models.EDIT}_{models.DESCRIPTION}")
        edit_options_button = self.build_button("Edit Options", f"{models.EDIT}_{models.OPTIONS}")
        response_text = "Multi-Response" if self.is_single_response else "Single Response"
        toggle_response_button = self.build_button(f"Change to {response_text}", f"{models.EDIT}_{models.RESPONSE}")
        back_button = self.build_button("Back", models.BACK)
        buttons = [
            [edit_template_details_button], [edit_title_button], [edit_description_button], [edit_options_button],
            [toggle_response_button], [back_button]
        ]

        if is_creator:
            delete_template_button = self.build_button("Delete Template", models.DELETE)
            buttons.insert(-1, [delete_template_button])

        return InlineKeyboardMarkup(buttons)

    def build_edit_template_details_buttons(self) -> InlineKeyboardMarkup:
        change_name_button = self.build_button(
            "Change Template Name", f"{models.RENAME}_{models.TEMPLATE}_{models.NAME}"
        )
        change_descr_button = self.build_button(
            "Change Template Description", f"{models.RENAME}_{models.TEMPLATE}_{models.DESCRIPTION}"
        )
        remove_descr_button = self.build_button(
            "Remove Template Description", f"{models.DELETE}_{models.TEMPLATE}_{models.DESCRIPTION}"
        )
        add_descr_button = self.build_button(
            "Add Template Description", f"{models.ADD}_{models.TEMPLATE}_{models.DESCRIPTION}"
        )
        back_button = self.build_button("Back", models.SETTINGS)
        if self.description:
            buttons = [[change_name_button], [change_descr_button], [remove_descr_button], [back_button]]
        else:
            buttons = [[change_name_button], [add_descr_button], [back_button]]
        return InlineKeyboardMarkup(buttons)

    def build_edit_title_buttons(self) -> InlineKeyboardMarkup:
        change_title_button = self.build_button("Change Format Title", f"{models.RENAME}_{models.TITLE}")
        back_button = self.build_button("Back", models.SETTINGS)
        buttons = [[change_title_button], [back_button]]
        return InlineKeyboardMarkup(buttons)

    def build_edit_description_buttons(self) -> InlineKeyboardMarkup:
        if self.description_format.format_text:
            change_description_button = self.build_button(
                "Change Format Description", f"{models.RENAME}_{models.DESCRIPTION}"
            )
            remove_description_button = self.build_button(
                "Remove Format Description", f"{models.DELETE}_{models.DESCRIPTION}"
            )
            buttons = [[change_description_button], [remove_description_button]]
        else:
            add_description_button = self.build_button("Add Format Description", f"{models.ADD}_{models.DESCRIPTION}")
            buttons = [[add_description_button]]
        back_button = self.build_button("Back", models.SETTINGS)
        buttons.append([back_button])
        return InlineKeyboardMarkup(buttons)

    def build_format_back_buttons(self, back_action: str) -> InlineKeyboardMarkup:
        back_button = self.build_button("Back", back_action)
        cancel_button = self.build_button("Cancel", models.RESET)
        buttons = [[cancel_button, back_button]]
        return InlineKeyboardMarkup(buttons)

    def build_edit_confirm_buttons(self, back_action: str) -> InlineKeyboardMarkup:
        confirm_button = self.build_button("Confirm", models.DONE)
        back_button = self.build_button("Back", back_action)
        buttons = [[back_button, confirm_button]]
        return InlineKeyboardMarkup(buttons)

    def build_single_back_button(self, back_action: str, back_text="Back") -> InlineKeyboardMarkup:
        back_button = self.build_button(back_text, back_action)
        return InlineKeyboardMarkup([[back_button]])

    def build_delete_confirm_buttons(
        self, delete_action: str, back_action: str, delete_text="Delete", back_text="No"
    ) -> InlineKeyboardMarkup:
        delete_button = self.build_button(delete_text, f"{models.DELETE_YES}_{delete_action}")
        back_button = self.build_button(back_text, back_action)
        buttons = [[delete_button, back_button]]
        return InlineKeyboardMarkup(buttons)

    def build_button(self, text: str, action: str) -> InlineKeyboardButton:
        return util.build_button(text, models.TEMP_POLL_SUBJECT, action, self.temp_id)

    def to_json(self) -> dict:
        return {
            db.TEMP_POLL_ID:                 self.temp_id,
            db.TEMP_POLL_NAME:               self.name,
            db.TEMP_POLL_DESCRIPTION:        self.description,
            db.TEMP_POLL_TITLE_FORMAT:       self.title_format.to_json(),
            db.TEMP_POLL_DESCRIPTION_FORMAT: self.description_format.to_json(),
            db.TEMP_POLL_OPTIONS:            self.options,
            db.TEMP_POLL_SINGLE_RESPONSE:    self.is_single_response,
            db.TEMP_POLL_CREATOR_ID:         self.creator_id,
        }
