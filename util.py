"""Util methods"""
import string
import random
from telegram import InlineKeyboardButton

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


def simple_hash(text: str, limit=16) -> str:
    n = len(text) + 12
    return "".join(encode(ord(c), n) for c in text)[:16]


def build_button(text: str, poll_id: str, action: str) -> InlineKeyboardButton:
    data = f"{poll_id} {action}"
    return InlineKeyboardButton(text, callback_data=data)


def build_switch_button(text: str, placeholder: str, to_self=False) -> InlineKeyboardButton:
    return InlineKeyboardButton(text, switch_inline_query_current_chat=placeholder) if to_self \
        else InlineKeyboardButton(text, switch_inline_query=placeholder)

