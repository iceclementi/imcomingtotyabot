"""Util methods"""
import string
import random
from datetime import datetime
from hashlib import blake2b as blake
from typing import List, Tuple, Set
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

ENCODE_KEY = string.digits + string.ascii_letters
NEGATIVE_SYMBOL = "Z"


def create_random_string(n: int) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))


def generate_random_id(n: int, preclusion: Set[str]) -> str:
    random_id = create_random_string(n)
    while random_id in preclusion:
        random_id = create_random_string(n)
    return random_id


def strip_html_symbols(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def make_html_bold(text: str) -> str:
    return f"<b>{strip_html_symbols(text)}</b>"


def make_html_italic(text: str) -> str:
    return f"<i>{strip_html_symbols(text)}</i>"


def make_html_bold_first_line(text: str) -> str:
    text_split = text.split("\n", 1)
    output = make_html_bold(text_split[0])
    return output + "\n" + strip_html_symbols(text_split[1]) if len(text_split) > 1 else output


def encode(num: int, base=32) -> str:
    if num == 0:
        return "0"
    num, code = (num, "") if num > 0 else (-num, NEGATIVE_SYMBOL)
    while num > 0:
        num, i = divmod(num, base)
        code += ENCODE_KEY[i]
    return code


def decode(code: str, base=32) -> int:
    if code.startswith(NEGATIVE_SYMBOL):
        code, factor = code[1:], -1
    else:
        factor = 1
    num = 0
    for i, value in enumerate(code):
        num += ENCODE_KEY.find(value) * base ** i
    return num * factor


def simple_hash(text: str, salt="", length=16, variance=True) -> str:
    if variance:
        time_variance = datetime.now().strftime("%H%d%m%y")
        salt_bytes = bytes(f"{time_variance}{salt}", "utf-8")
    else:
        salt_bytes = bytes(f"{salt}", "utf-8")

    hasher = blake(key=salt_bytes, digest_size=16)
    hasher.update(bytes(text, "utf-8"))

    digest = hasher.hexdigest()
    encoded_digest = encode(int(digest, 16), base=62)

    return encoded_digest[:length]


def build_button(text: str, subject: str, action: str, identifier: str) -> InlineKeyboardButton:
    data = f"{subject} {action} {identifier}"
    return InlineKeyboardButton(text, callback_data=data)


def build_switch_button(text: str, placeholder: str, to_self=False) -> InlineKeyboardButton:
    return InlineKeyboardButton(text, switch_inline_query_current_chat=placeholder) if to_self \
        else InlineKeyboardButton(text, switch_inline_query=placeholder)


def build_single_button_markup(text: str, action: str) -> InlineKeyboardMarkup:
    button = InlineKeyboardButton(text, callback_data=action)
    return InlineKeyboardMarkup([[button]])


def build_single_switch_button_markup(text: str, placeholder: str) -> InlineKeyboardMarkup:
    button = InlineKeyboardButton(text, switch_inline_query=placeholder)
    return InlineKeyboardMarkup([[button]])


def build_multiple_buttons_markup(*button_details: Tuple[str, str, bool, bool]) -> InlineKeyboardMarkup:
    buttons = []
    for text, action, is_switch, to_self in button_details:
        if is_switch:
            button = InlineKeyboardButton(text, switch_inline_query_current_chat=action) if to_self \
                else InlineKeyboardButton(text, switch_inline_query=action)
        else:
            button = InlineKeyboardButton(text, callback_data=action)
        buttons.append([button])
    return InlineKeyboardMarkup(buttons)


def build_multiple_stacked_buttons_markup(*button_details: List[Tuple[str, str, bool, bool]]) -> InlineKeyboardMarkup:
    buttons = []
    for button_row_details in button_details:
        button_row = []
        for text, action, is_switch, to_self in button_row_details:
            if is_switch:
                button = InlineKeyboardButton(text, switch_inline_query_current_chat=action) if to_self \
                    else InlineKeyboardButton(text, switch_inline_query=action)
            else:
                button = InlineKeyboardButton(text, callback_data=action)
            button_row.append(button)
        buttons.append(button_row)
    return InlineKeyboardMarkup(buttons)


def generate_button_details(text: str, action: str, is_switch=False, to_self=False) -> Tuple[str, str, bool, bool]:
    return text, action, is_switch, to_self


def build_single_link_button_markup(text: str, link: str) -> InlineKeyboardMarkup:
    button = InlineKeyboardButton(text, url=link)
    return InlineKeyboardMarkup([[button]])


def build_multiple_keyboard_buttons(*button_texts: str, one_time=False, placeholder=None) -> ReplyKeyboardMarkup:
    buttons = []
    for button_text in button_texts:
        buttons.append([button_text])
    return ReplyKeyboardMarkup(buttons, one_time_keyboard=one_time, input_field_placeholder=placeholder)


def build_multiple_stacked_keyboard_buttons(*button_texts: List[str], one_time=False, placeholder=None) \
        -> ReplyKeyboardMarkup:
    buttons = []
    for button_row_texts in button_texts:
        button_row = []
        for button_text in button_row_texts:
            button_row.append(button_text)
        buttons.append(button_row)
    return ReplyKeyboardMarkup(buttons, one_time_keyboard=one_time, input_field_placeholder=placeholder)


def format_date(date: datetime, date_format="%B %d, %Y") -> str:
    return date.strftime(date_format)


def list_to_dict(_list: List[str]) -> dict:
    return {i: item for i, item in enumerate(_list)}


def list_to_indexed_list_string(_list: List[str], start=1) -> str:
    indexed_list = [f"{i}. {item}" for i, item in enumerate(_list, start)]
    return "\n".join(indexed_list)

