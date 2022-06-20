from __future__ import annotations

from abc import abstractmethod
from typing import List

from telegram import InlineKeyboardMarkup

from models import models
from models.format_text_code import FormatTextCode
from models.poll_template import PollTemplate
from models.ballot_template import BallotTemplate


class Template(object):
    TEMPLATE_TYPES = {"P": "poll", "L": "list"}
    TEMPLATE_ICONS = {"poll": models.EMOJI_POLL, "list": models.EMOJI_BALLOT}

    def __init__(self, temp_id: str, name: str, description: str,
                 title_format: FormatTextCode, description_format: FormatTextCode, creator_id: int) -> None:
        self._temp_id = temp_id
        self._name = name
        self._description = description
        self._title_format = title_format
        self._description_format = description_format
        self._creator_id = creator_id

    @staticmethod
    @abstractmethod
    def get_template_by_id(temp_id: str) -> Template | None:
        if temp_id.startswith("P"):
            return PollTemplate.get_template_by_id(temp_id)
        elif temp_id.startswith("L"):
            return BallotTemplate.get_template_by_id(temp_id)
        else:
            return None

    @staticmethod
    @abstractmethod
    def get_templates_by_ids(temp_ids: set, filters="") -> List[Template]:
        template_lists = [Template.get_template_by_id(temp_id) for temp_id in temp_ids]
        return [template for template in template_lists if filters.lower() in template.name.lower()]

    @property
    def temp_id(self) -> str:
        return self._temp_id

    @property
    def temp_type(self) -> str:
        return self.TEMPLATE_TYPES.get(self.temp_id[0], "")

    @property
    def icon(self) -> str:
        return self.TEMPLATE_ICONS.get(self.temp_type, "")

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, new_name: str) -> None:
        self._name = new_name
        return

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, new_description: str) -> None:
        self._description = new_description
        return

    @property
    def title_format(self) -> FormatTextCode:
        return self._title_format

    @title_format.setter
    def title_format(self, new_title: str) -> None:
        self._title_format = FormatTextCode.create_new(new_title)
        return

    @property
    def description_format(self) -> FormatTextCode:
        return self._description_format

    @description_format.setter
    def description_format(self, new_description: str) -> None:
        self._description_format = FormatTextCode.create_new(new_description)
        return

    @property
    def creator_id(self) -> int:
        return self._creator_id

    @abstractmethod
    def generate_linked_summary(self, include_creator=False) -> str:
        pass

    @abstractmethod
    def render_text(self) -> str:
        pass

    @abstractmethod
    def build_main_buttons(self) -> InlineKeyboardMarkup:
        pass