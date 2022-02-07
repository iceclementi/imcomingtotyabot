"""Util methods"""
import string
import random
from datetime import datetime
from hashlib import blake2b as blake
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

ENCODE_KEY = string.digits + string.ascii_letters
NEGATIVE_SYMBOL = "Z"


def create_random_string(n: int) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))


def generate_random_id(n: int, preclusion: set) -> str:
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
        salt_bytes = bytes(f"{time_variance}{salt}", "ascii")
    else:
        salt_bytes = bytes(f"{salt}", "ascii")

    hasher = blake(key=salt_bytes, digest_size=16)
    hasher.update(bytes(text, "ascii"))

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


def build_multiple_buttons_markup(*button_details: tuple) -> InlineKeyboardMarkup:
    buttons = []
    for text, action, is_switch, to_self in button_details:
        if is_switch:
            button = InlineKeyboardButton(text, switch_inline_query_current_chat=action) if to_self \
                else InlineKeyboardButton(text, switch_inline_query=action)
        else:
            button = InlineKeyboardButton(text, callback_data=action)
        buttons.append([button])
    return InlineKeyboardMarkup(buttons)


def generate_button_details(text: str, action: str, is_switch=False, to_self=False) -> tuple:
    return text, action, is_switch, to_self


def build_single_link_button_markup(text: str, link: str) -> InlineKeyboardMarkup:
    button = InlineKeyboardButton(text, url=link)
    return InlineKeyboardMarkup([[button]])


def format_date(date: datetime, date_format="%B %d, %Y") -> str:
    return date.strftime(date_format)
