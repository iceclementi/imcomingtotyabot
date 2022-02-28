"""UI Elements"""
from abc import abstractmethod
from typing import List, Tuple, Set, Union, Dict
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

import util

EMOJI_UP = "︿"
EMOJI_DOWN = "﹀"
ICON_LEFT = "<<"
ICON_RIGHT = ">>"


class Pagination(object):
    def __init__(self, button_data: Tuple[str, str, str], items_per_page: int = 5, is_horizontal_buttons: bool = True,
                 is_cyclic: bool = True) -> None:
        self._button_data = button_data
        self._items_per_page = items_per_page
        self._is_horizontal_buttons = is_horizontal_buttons
        self._is_cyclic = is_cyclic

    @property
    def button_data(self) -> Tuple[str, str, str]:
        return self._button_data

    @property
    def items_per_page(self) -> int:
        return self._items_per_page

    @items_per_page.setter
    def items_per_page(self, new_items_per_page: int) -> None:
        self._items_per_page = new_items_per_page
        return

    @property
    def is_horizontal_buttons(self) -> bool:
        return self._is_horizontal_buttons

    @is_horizontal_buttons.setter
    def is_horizontal_buttons(self, is_horizontal_buttons: bool) -> None:
        self._is_horizontal_buttons = is_horizontal_buttons
        return

    @property
    def is_cyclic(self) -> bool:
        return self._is_cyclic


class PaginationButtonGroup(Pagination):
    def __init__(self, button_titles: List[str], button_data: Tuple[str, str, str], items_per_page: int = 5,
                 is_horizontal_buttons: bool = True, is_cyclic: bool = True) -> None:
        super().__init__(button_data, items_per_page, is_horizontal_buttons, is_cyclic)
        self._button_titles = button_titles

    @property
    def button_titles(self):
        return self._button_titles

    @property
    def page_count(self) -> int:
        return (len(self.button_titles) + self.items_per_page - 1) // self.items_per_page

    def build_next_button(self, current_page_number: int) -> InlineKeyboardButton:
        next_page_number = (current_page_number + 1) % self.page_count
        next_symbol = ICON_RIGHT if self.is_horizontal_buttons else EMOJI_DOWN
        if self.is_cyclic:
            return self.build_navigation_button(next_symbol, next_page_number)
        else:
            return self.build_navigation_button(next_symbol, next_page_number) if next_page_number != 0 \
                else self.build_navigation_button(" ", current_page_number)

    def build_previous_button(self, current_page_number: int) -> InlineKeyboardButton:
        prev_page_number = (current_page_number - 1) % self.page_count
        prev_symbol = ICON_LEFT if self.is_horizontal_buttons else EMOJI_UP
        if self.is_cyclic:
            return self.build_navigation_button(prev_symbol, prev_page_number)
        else:
            return self.build_navigation_button(prev_symbol, prev_page_number) \
                if prev_page_number != self.page_count - 1 else self.build_navigation_button(" ", current_page_number)

    def build_buttons(self, current_page_number: int = 0, index: int = 0) -> List[List[InlineKeyboardButton]]:
        if index:
            current_page_number = index % self.items_per_page

        lower_item_index = current_page_number * self.items_per_page
        upper_item_index = lower_item_index + self.items_per_page

        current_titles = self.button_titles[lower_item_index:upper_item_index]
        buttons = [[self.build_item_button(title, lower_item_index + i)] for i, title in enumerate(current_titles)]

        if self.is_horizontal_buttons:
            buttons.append(
                [self.build_previous_button(current_page_number), self.build_next_button(current_page_number)]
            )
        else:
            buttons.insert(0, [self.build_previous_button(current_page_number)])
            buttons.append([self.build_next_button(current_page_number)])
        return buttons

    def build_navigation_button(self, text: str, page_number: int) -> InlineKeyboardButton:
        subject, action, identifier = self.button_data
        return util.build_button(text, subject, f"page{page_number}_{action}", identifier)

    def build_item_button(self, text: str, item_index: int) -> InlineKeyboardButton:
        subject, action, identifier = self.button_data
        return util.build_button(text, subject, f"{action}_{item_index}", identifier)
