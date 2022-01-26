"""Util methods"""
import string
import random
from telegram import InlineKeyboardButton


def create_random_string(n: int) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))


def strip_html_symbols(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def make_html_bold(text):
    return f"<b>{strip_html_symbols(text)}</b>"


def make_html_bold_first_line(text):
    text_split = text.split("\n", 1)
    output = make_html_bold(text_split[0])
    return output + "\n" + strip_html_symbols(text_split[1]) if len(text_split) > 1 else output


def build_button(text: str, poll_id: str, action: str) -> InlineKeyboardButton:
    data = f"{poll_id} {action}"
    return InlineKeyboardButton(text, callback_data=data)


def build_switch_button(text: str, placeholder: str, to_self=False) -> InlineKeyboardButton:
    return InlineKeyboardButton(text, switch_inline_query_current_chat=placeholder) if to_self \
        else InlineKeyboardButton(text, switch_inline_query=placeholder)

