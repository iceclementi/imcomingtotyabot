"""Schedules to schedule sending of messages and notifications"""
from __future__ import annotations

from abc import abstractmethod
from enum import StrEnum, unique
from typing import List, Tuple, Set, Union, Dict, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, ParseMode, ReplyKeyboardMarkup

from callbackcontext import CallbackContext, CallbackAction, CallbackTarget
import util

SCHEDULE = "sched"


@unique
class ScheduleType(StrEnum):
    DAILY = "D"
    WEEKLY = "W"
    MONTHLY = "M"
    YEARLY = "Y"


class Schedule(object):
    def __init__(self, tag: str):
        self._tag = tag
        self._name = ""
        self._recipients = []
        self._repeated = True

    # region Static Methods

    @staticmethod
    def show_schedule_type_options(header: str, subject: str, identifier: str, message: Message):
        def build_button(text: str, action: str) -> InlineKeyboardButton:
            return util.build_button(text, subject, f"{SCHEDULE}_{action}", identifier)
        daily_button = build_button("Daily", ScheduleType.DAILY.value)
        weekly_button = build_button("Weekly", ScheduleType.WEEKLY.value)
        monthly_button = build_button("Monthly", ScheduleType.MONTHLY.value)
        back_button = util.build_button("Back", subject, "Back", identifier)

        response = f"{header}\n\nWhat kind of <b>schedule</b> do you want?"
        buttons = InlineKeyboardMarkup([[daily_button], [weekly_button], [monthly_button], [back_button]])
        message.edit_text(response, parse_mode=ParseMode.HTML, reply_markup=buttons)
        return

    # endregion

    # region Properties

    @property
    @abstractmethod
    def schedule_type(self) -> ScheduleType:
        pass

    @property
    def tag(self) -> str:
        return self._tag

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

    @recipients.setter
    def recipients(self, new_recipients) -> None:
        self._recipients = new_recipients
        return

    @property
    def repeated(self) -> bool:
        return self._repeated

    @repeated.setter
    def repeated(self, repeated: bool) -> None:
        self._repeated = repeated
        return

    # endregion

    # region Class Methods

    @classmethod
    def load(cls, tag: str, name: str, recipients: List[str], repeated: bool) -> Schedule:
        schedule = cls(tag)
        schedule.name = name
        schedule.recipients = recipients
        schedule.repeated = repeated
        return schedule

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

    @abstractmethod
    def render_details(self) -> str:
        pass

    @abstractmethod
    def get_next_schedule_time_in_seconds(self) -> int:
        pass

    @abstractmethod
    def create_schedule(self) -> None:
        pass

    @abstractmethod
    def run_action(self, action: str) -> None:
        pass

    @abstractmethod
    def to_json(self) -> str:
        pass

    # endregion


class Time(object):
    def __init__(
            self,
            minute: int = 0,
            hour: int = 0,
            day: int = 0,
            week: int = 0,
            month: int = 0,
            year: int = 0
    ):
        self._minute = minute
        self._hour = hour
        self._day = day
        self._week = week
        self._month = month
        self._year = year
        self.verify_time_units()

    # region Properties

    @property
    def minute(self) -> int:
        return self._minute

    @minute.setter
    def minute(self, minute: int) -> None:
        self._minute = minute
        return

    @property
    def hour(self) -> int:
        return self._hour

    @hour.setter
    def hour(self, hour: int) -> None:
        self._hour = hour
        return

    @property
    def day(self) -> int:
        return self._day

    @day.setter
    def day(self, day: int) -> None:
        self._day = day
        return

    @property
    def week(self) -> int:
        return self._week

    @week.setter
    def week(self, week: int) -> None:
        self._week = week
        return

    @property
    def month(self) -> int:
        return self._month

    @month.setter
    def month(self, month: int) -> None:
        self._month = month
        return

    @property
    def year(self) -> int:
        return self._year

    @year.setter
    def year(self, year: int) -> None:
        self._year = year
        return

    # endregion

    def verify_time_units(self):
        self.minute = self.minute % 60
        self.hour = self.minute % 24

@unique
class DailyScheduleMode(StrEnum):
    INTERVAL = "I"
    SINGLE = "S"


class DailySchedule(Schedule):
    def __init__(self, tag: str):
        super().__init__(tag)
        self._mode = DailyScheduleMode.SINGLE
        self._trigger_time = Time()

    @property
    def schedule_type(self) -> ScheduleType:
        return ScheduleType.DAILY

    def render_details(self) -> str:
        pass

    def get_next_schedule_time_in_seconds(self) -> int:
        pass

    def show_schedule_modes(self, message: Message) -> None:

