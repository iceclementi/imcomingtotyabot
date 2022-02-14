"""Util methods"""
import string
import random
import re
import typing
from datetime import datetime
from hashlib import blake2b as blake
from typing import List, Tuple, Set, Union, Dict
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


def build_multiple_keyboard_buttons_markup(*button_texts: str, one_time=False, placeholder=None) -> ReplyKeyboardMarkup:
    buttons = []
    for button_text in button_texts:
        buttons.append([button_text])
    return ReplyKeyboardMarkup(buttons, one_time_keyboard=one_time, input_field_placeholder=placeholder)


def build_multiple_stacked_keyboard_buttons_markup(*button_texts: List[str], one_time=False, placeholder=None) \
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


def parse_format_string(format_string: str) -> Tuple[str, Union[Dict[str, Tuple[str, str]], None], bool]:
    format_results = dict()

    all_matches = re.findall(r"%([A-Za-z]+)(#\w+)?(\$\(.+\))?", format_string)
    for i, match in enumerate(all_matches, 1):
        format_type, label, default = match[0], match[1][1:], match[2][2:-1].strip()

        if not label:
            label = str(i)
        else:
            label_match = re.match(r"^[A-Za-z]\w{0,11}$", label)
            if not label_match:
                return f"<b>Format String Parse Error</b>\n" \
                       f"Invalid label <code>{label}</code> found.\n" \
                       f"<i>Labels must have up to 12 alphanumeric characters, including underscores, " \
                       f"and must start with a letter.</i>", \
                       None, False
            if label in format_results:
                return f"<b>Format String Parse Error</b>\n" \
                       f"Duplicated <code>{label}</code> found.\n" \
                       f"<i>Labels must be unique.</i>", \
                       None, False

        # Digit type
        if format_type == "d":
            default = default if default else "0"
            if not default.isdigit():
                return f"<b>Format String Parse Error</b>\nDefault value for <code>{label}</code> is not a digit.", \
                       None, False
            else:
                format_results[label] = (format_type, default)
        # String type
        elif format_type == "s":
            format_results[label] = (format_type, default)
        # Date type
        elif format_type == "dt":
            default = default if default else "1 %d/%m/%y"
            date_match = re.match(r"^([+|-]{0,3}[1-7])(\s+.+)?$", default)
            if not date_match:
                return f"<b>Format String Parse Error</b>\n" \
                       f"Default value for <code>{label}</code> is not in the correct date format.\n" \
                       f"<i>E.g. 1 %d/%m/%y</i>", \
                       None, False
            day, date_format = date_match.group(1), date_match.group(2)
            # Checks if all '+' or all '-'
            if len(day) > 1 and day[0] * (len(day) - 1) != day[:-1]:
                return f"<b>Format String Parse Error</b>\n" \
                       f"Default value for <code>{label}</code> is not in the correct date format.\n" \
                       f"<i>E.g. 1 %d/%m/%y</i>", \
                       None, False

            if not date_format:
                format_results[label] = (format_type, f"{day} %d/%m/%y")
            else:
                # Verify if date time format is valid
                try:
                    datetime.now().strftime(date_format.strip())
                except ValueError:
                    return f"<b>Format String Parse Error</b>\n" \
                           f"Default value for <code>{label}</code> is not in the correct date format.\n" \
                           f"<i>E.g. 1 %d/%m/%y</i>", \
                           None, False
                format_results[label] = (format_type, default)
        # Other types
        else:
            return f"<b>Format String Parse Error</b>\nInvalid format type found: %{format_type}", None, False

    # Create replaced text
    for label in format_results:
        format_string = re.sub(r"%([A-Za-z]+)(#\w+)?(\$\(.+\))?", f"<code>{label}</code>", format_string, count=1)

    return format_string, format_results, True
