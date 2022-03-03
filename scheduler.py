"""Schedulers to schedule sending of messages and notifications"""
from abc import abstractmethod
from typing import List, Tuple, Set, Union, Dict, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

import util


class Scheduler(object):
    TYPE_DAILY = "D"
    TYPE_WEEKLY = "W"
    TYPE_YEARLY = "M"
    TYPE_MONTHLY = "Y"

    def __init__(self, name: str, repeated: bool = True):
        self._name = name
        self._recipients = []
        self._repeated = repeated

    @property
    @abstractmethod
    def scheduler_type(self) -> str:
        pass

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, new_name: str) -> None:
        self._name = new_name
        return

    @property
    def recipients(self) -> List[str]:
        return self._recipients

    def add_recipient(self, new_recipient: str) -> bool:
        if new_recipient in self.recipients:
            return False
        self.recipients.append(new_recipient)
        return True

    def remove_recipient(self, recipient: str) -> bool:
        if recipient not in self.recipients:
            return False
        self.recipients.remove(recipient)
        return True

    @property
    def repeated(self) -> bool:
        return self._repeated

    @repeated.setter
    def repeated(self, repeated: bool) -> None:
        self._repeated = repeated
        return

    @abstractmethod
    def render_details(self) -> str:
        pass

    @abstractmethod
    def get_next_schedule_time_in_seconds(self) -> int:
        pass


class DailyScheduler(Scheduler):
    def __init__(self, name: str, repeated: bool = True):
        super().__init__(name, repeated)

    @property
    def scheduler_type(self) -> str:
        return self.TYPE_DAILY

    def render_details(self) -> str:
        pass

    def get_next_schedule_time_in_seconds(self) -> int:
        pass
