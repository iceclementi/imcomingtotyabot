"""Encapsulates callback data for inline keyboard buttons"""
from __future__ import annotations

from collections import namedtuple
from enum import StrEnum, unique

@unique
class CallbackAction(StrEnum):
    SCHEDULE = "SC"
    ADD = "add"
    DELETE = "del"
    DELETE_YES = "delYes"
    EDIT = "edit"
    VIEW = "view"
    BACK = "back"
    CLOSE = "close"
    RESET = "reset"
    DONE = "done"
    SKIP = "skip"


@unique
class CallbackTarget(StrEnum):
    NAME = "name"


CallbackContextBase = namedtuple(
    "CallbackContextBase",
    ("module_id", "module", "action", "target", "sub_target", "sub_target_2", "sub_target_3"),
    defaults=(None,) * 7
)


class CallbackContext(CallbackContextBase):
    def create_new(self, **kwargs) -> CallbackContext:
        return self._replace(**kwargs)
