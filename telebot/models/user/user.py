from __future__ import annotations

from typing import List, Set, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from telebot.database import database as db
from telebot.models import constant as const
from telebot.models.ballot.ballot import Ballot
from telebot.models.poll.poll import Poll
from telebot.models.template.ballot_template import BallotTemplate
from telebot.models.template.poll_template import PollTemplate
from telebot.models.template.template import Template
from telebot.models.user.group import Group
from telebot.utils import util
from telebot.utils.ui import PaginationTextGroup

user_storage = dict()


class User(object):
    def __init__(
        self, uid: int, first_name: str, last_name: str, username: str, is_leader: bool,
        owned_group_ids: Set[str], joined_group_ids: Set[str], poll_ids: Set[str], ballot_ids: Set[str],
        temp_poll_ids: Set[str], temp_ballot_ids: Set[str]
    ) -> None:
        self._uid = uid
        self._first_name = first_name
        self._last_name = last_name
        self._username = username
        self._leader = is_leader
        self._owned_group_ids = owned_group_ids
        self._joined_group_ids = joined_group_ids
        self._poll_ids = poll_ids
        self._ballot_ids = ballot_ids
        self._temp_poll_ids = temp_poll_ids
        self._temp_ballot_ids = temp_ballot_ids

    @staticmethod
    def get_user_by_id(uid: int) -> User:
        return user_storage.get(uid, None)

    @staticmethod
    def get_users_by_name(name="") -> List[User]:
        sorted_users = sorted(user_storage.values(), key=lambda user: user.get_name().lower())
        filtered_users = [user for user in sorted_users if name in user.get_name()]
        return filtered_users

    @classmethod
    def register(cls, uid: int, first_name: str, last_name="", username="") -> User:
        user = cls(uid, first_name, last_name, username, False, set(), set(), set(), set(), set(), set())
        user_storage[uid] = user
        return user

    @classmethod
    def load(
        cls, uid: int, first_name: str, last_name: str, username: str, is_leader: bool,
        owned_group_ids: List[str], joined_group_ids: List[str], poll_ids: List[str], ballot_ids: List[str],
        temp_poll_ids: List[str], temp_ballot_ids: List[str]
    ) -> None:
        user = cls(
            uid, first_name, last_name, username, is_leader, set(owned_group_ids), set(joined_group_ids),
            set(poll_ids), set(ballot_ids), set(temp_poll_ids), set(temp_ballot_ids)
        )
        user_storage[uid] = user
        return

    def get_uid(self) -> int:
        return self._uid

    def get_name(self) -> str:
        if self._last_name:
            return f"{self._first_name} {self._last_name}"
        return self._first_name

    def get_username(self) -> str:
        return self._username

    def is_leader(self) -> bool:
        return self._leader

    def promote_to_leader(self) -> None:
        self._leader = True

    def get_owned_group_ids(self) -> Set[str]:
        return self._owned_group_ids

    def get_owned_groups(self, filters="") -> List[Group]:
        owned_groups = Group.get_groups_by_ids(self._owned_group_ids, filters)
        return sorted(owned_groups, key=lambda group: group.get_name().lower())

    def has_group_with_name(self, name: str) -> bool:
        return any(group.get_name() == name for group in self.get_owned_groups())

    def create_group(self, name: str, password="") -> Tuple[Group | None, str]:
        if self.has_group_with_name(name):
            return None, "You already have a group with the same name."
        if len(self._owned_group_ids) >= const.MAX_GROUPS_PER_USER:
            return None, f"The maximum number of groups you can own ({const.MAX_GROUPS_PER_USER}) has been reached."
        group = Group.create_new(name, self._uid, password)
        self._owned_group_ids.add(group.get_gid())
        return group, f"Group {util.make_html_bold(name)} created!"

    def delete_group(self, gid: str) -> str:
        if gid not in self._owned_group_ids:
            return "You do not own that group."
        self._owned_group_ids.remove(gid)
        group = Group.get_group_by_id(gid)
        group.delete()
        return f"Group \"{group.get_name()}\" has been deleted."

    def get_joined_group_ids(self) -> Set[str]:
        return self._joined_group_ids

    def get_joined_groups(self, filters="") -> List[Group]:
        joined_groups = Group.get_groups_by_ids(self._joined_group_ids, filters)
        return sorted(joined_groups, key=lambda group: group.get_name().lower())

    def join_group(self, gid: str) -> str:
        if len(self._joined_group_ids) >= const.MAX_JOINED_GROUPS_PER_USER:
            return f"The maximum number of groups you can join ({const.MAX_JOINED_GROUPS_PER_USER}) has been reached."
        self._joined_group_ids.add(gid)
        group = Group.get_group_by_id(gid)
        return f"Group {util.make_html_bold(group.get_name())} joined!"

    def leave_group(self, gid: str) -> None:
        if gid in self._joined_group_ids:
            self._joined_group_ids.remove(gid)

    def get_all_group_ids(self) -> Set[str]:
        return set.union(self._owned_group_ids, self._joined_group_ids)

    def get_all_groups(self, filters="") -> List[Group]:
        all_user_groups = Group.get_groups_by_ids(self.get_all_group_ids(), filters)
        return sorted(all_user_groups, key=lambda group: group.get_name().lower())

    def get_poll_ids(self) -> Set[str]:
        return self._poll_ids

    def get_polls(self, filters="") -> List[Poll]:
        user_polls = Poll.get_polls_by_ids(self._poll_ids, filters)
        return sorted(user_polls, key=lambda poll: poll.get_created_date(), reverse=True)

    def get_group_poll_ids(self) -> Set[str]:
        group_poll_ids = set()
        for group in self.get_all_groups():
            group_poll_ids.update(group.get_poll_ids())
        return group_poll_ids

    def get_group_polls(self, filters="") -> List[Poll]:
        group_polls = Poll.get_polls_by_ids(self.get_group_poll_ids(), filters)
        return sorted(group_polls, key=lambda poll: poll.get_created_date(), reverse=True)

    def create_poll(self, title: str, description: str, options: list) -> Tuple[Poll, str]:
        poll = Poll.create_new(title, self._uid, description, options)
        self._poll_ids.add(poll.get_poll_id())
        return poll, f"Poll {util.make_html_bold(title)} created!"

    def delete_poll(self, poll_id: str) -> str:
        if poll_id not in self._poll_ids:
            return "No such poll exists."
        self._poll_ids.remove(poll_id)

        # Delete poll from all user groups
        for group in self.get_all_groups():
            if poll_id in group.get_poll_ids():
                group.remove_poll(poll_id)

        poll = Poll.get_poll_by_id(poll_id)
        poll.delete()

        return f"Poll {util.make_html_bold(poll.get_title())} has been deleted."

    def has_group_poll(self, poll_id: str) -> bool:
        return any(poll_id in group.get_poll_ids() for group in self.get_all_groups())

    def get_ballot_ids(self) -> Set[str]:
        return self._ballot_ids

    def get_ballots(self, filters="") -> List[Ballot]:
        user_ballots = Ballot.get_ballots_by_ids(self._ballot_ids, filters)
        return sorted(user_ballots, key=lambda ballot: ballot.get_created_date(), reverse=True)

    def get_group_ballot_ids(self) -> Set[str]:
        group_ballot_ids = set()
        for group in self.get_all_groups():
            group_ballot_ids.update(group.get_ballot_ids())
        return group_ballot_ids

    def get_group_ballots(self, filters="") -> List[Ballot]:
        group_ballots = Ballot.get_ballots_by_ids(self.get_group_ballot_ids(), filters)
        return sorted(group_ballots, key=lambda ballot: ballot.get_created_date(), reverse=True)

    def create_ballot(self, title: str, description: str, options: list, choices: list) -> Tuple[Ballot, str]:
        ballot = Ballot.create_new(title, self._uid, description, options, choices)
        self._ballot_ids.add(ballot.get_ballot_id())
        return ballot, f"Ballot {util.make_html_bold(title)} created!"

    def delete_ballot(self, ballot_id: str) -> str:
        if ballot_id not in self._ballot_ids:
            return "No such ballot exists."
        self._ballot_ids.remove(ballot_id)

        # Delete list from all user groups
        for group in self.get_all_groups():
            if ballot_id in group.get_ballot_ids():
                group.remove_ballot(ballot_id)

        ballot = Ballot.get_ballot_by_id(ballot_id)
        ballot.delete()

        return f"Ballot {util.make_html_bold(ballot.get_title())} has been deleted."

    def has_group_ballot(self, ballot_id: str) -> bool:
        return any(ballot_id in group.get_ballot_ids() for group in self.get_all_groups())

    def get_temp_poll_ids(self) -> Set[str]:
        return self._temp_poll_ids

    def get_temp_polls(self, filters="") -> List[PollTemplate]:
        user_temp_polls = PollTemplate.get_templates_by_ids(self._temp_poll_ids, filters)
        return sorted(user_temp_polls, key=lambda temp_poll: temp_poll._name.lower())

    def get_temp_poll_by_name(self, name: str) -> PollTemplate:
        return next(
            (temp_poll for temp_poll in self.get_temp_polls() if temp_poll._name.lower() == name.lower()), None
        )

    def create_temp_poll(
        self, name: str, description: str, format_title_string: str, description_format_string: str,
        options: list, is_single_response: bool
    ) -> Tuple[PollTemplate, str]:
        temp_poll = PollTemplate.create_new(
            name, description, format_title_string, description_format_string, options, is_single_response, self._uid
        )
        self._temp_poll_ids.add(temp_poll.temp_id)
        return temp_poll, f"Poll template {util.make_html_bold(name)} created!"

    def delete_temp_poll(self, temp_id: str) -> None:
        self._temp_poll_ids.remove(temp_id)
        temp_poll = PollTemplate.get_template_by_id(temp_id)
        temp_poll.delete()
        return

    def has_temp_poll_with_name(self, name: str) -> bool:
        return any(temp_poll._name.lower() == name.lower() for temp_poll in self.get_temp_polls())

    def create_poll_from_template(self, temp_id: str, title: str, description: str) -> Poll | None:
        if temp_id not in self._temp_poll_ids:
            return None
        temp_poll = PollTemplate.get_template_by_id(temp_id)
        poll, _ = self.create_poll(title, description, temp_poll._options)
        poll.set_single_response(temp_poll.is_single_response)
        return poll

    def get_temp_ballot_ids(self) -> Set[str]:
        return self._temp_ballot_ids

    def get_temp_ballots(self, filters="") -> List[BallotTemplate]:
        user_temp_ballots = BallotTemplate.get_templates_by_ids(self._temp_ballot_ids, filters)
        return sorted(user_temp_ballots, key=lambda temp_list: temp_list._name.lower())

    def get_temp_list_by_name(self, name: str) -> BallotTemplate:
        return next(
            (temp_list for temp_list in self.get_temp_ballots() if temp_list._name.lower() == name.lower()), None
        )

    def create_temp_list(
        self, name: str, description: str, title_format_string: str, description_format_string: str,
        options: List[str], choices: List[str], is_single_response: bool
    ) -> Tuple[BallotTemplate, str]:
        temp_list = BallotTemplate.create_new(
            name, description, title_format_string, description_format_string, options, choices,
            is_single_response, self._uid
        )
        self._temp_ballot_ids.add(temp_list.temp_id)
        return temp_list, f"Ballot template {util.make_html_bold(name)} created!"

    def delete_temp_list(self, temp_id: str) -> None:
        self._temp_ballot_ids.remove(temp_id)
        temp_list = BallotTemplate.get_template_by_id(temp_id)
        temp_list.delete()
        return

    def has_temp_list_with_name(self, name: str) -> bool:
        return any(temp_list._name.lower() == name.lower() for temp_list in self.get_temp_ballots())

    def create_ballot_from_template(self, temp_id: str, title: str, description: str) -> Ballot | None:
        if temp_id not in self._temp_ballot_ids:
            return None
        temp_ballot = BallotTemplate.get_template_by_id(temp_id)
        ballot, _ = self.create_ballot(title, description, temp_ballot._options, temp_ballot.choices)
        ballot.set_single_response(temp_ballot.is_single_response)
        return ballot

    def get_templates(self, filters="") -> List[Template]:
        temp_polls = self.get_temp_polls(filters)
        temp_ballots = self.get_temp_ballots(filters)
        return sorted(temp_polls + temp_ballots, key=lambda item: item._name.lower())

    def get_group_temp_ids(self) -> Set[str]:
        group_temp_ids = set()
        for group in self.get_all_groups():
            group_temp_ids.update(group.get_template_ids())
        return group_temp_ids

    def get_group_templates(self, filters="") -> List[Template]:
        group_templates = Template.get_templates_by_ids(self.get_group_temp_ids(), filters)
        return sorted(group_templates, key=lambda template: template._name.lower())

    def has_group_template(self, temp_id: str) -> bool:
        return any(temp_id in group.get_template_ids() for group in self.get_all_groups())

    def get_all_poll_ids(self) -> Set[str]:
        return self._poll_ids.union(self.get_group_poll_ids())

    def get_all_ballot_ids(self) -> Set[str]:
        return self._ballot_ids.union(self.get_group_ballot_ids())

    def get_everything(self, filters=""):
        all_polls = Poll.get_polls_by_ids(self.get_all_poll_ids(), filters)
        all_ballots = Ballot.get_ballots_by_ids(self.get_all_ballot_ids(), filters)
        return sorted(all_polls + all_ballots, key=lambda item: item.get_created_date(), reverse=True)

    def render_poll_list_with_buttons(self, page_number: int = 0) -> Tuple[str, InlineKeyboardMarkup]:
        header = "<b>Your Polls</b>"

        user_polls = self.get_polls()
        if user_polls:
            poll_linked_summaries = [poll.generate_linked_summary() for poll in user_polls]
            poll_text_group = PaginationTextGroup(
                poll_linked_summaries, ("", const.POLL, ""),
                items_per_page=5, is_horizontal_buttons=True, is_cyclic=False, hidden_enabled=True
            )

            page_contents, start_index = poll_text_group.get_page_contents(page_number)
            body = util.list_to_indexed_list_string(
                page_contents, start=start_index, line_spacing=2
            )
            buttons = poll_text_group.build_buttons(page_number)
            buttons.append([util.build_button("Close", action=const.CLOSE)])
        else:
            body = util.make_html_italic("You have no polls! Use /poll to build a new poll.")
            buttons = [[util.build_button("Close", action=const.CLOSE)]]

        poll_count = len(user_polls)
        footer = f"{const.EMOJI_POLL} {poll_count} poll{'' if poll_count == 1 else 's'} in total"

        return "\n\n".join([header] + [body] + [footer]), InlineKeyboardMarkup(buttons)

    def render_ballot_list_with_buttons(self, page_number: int = 0) -> Tuple[str, InlineKeyboardMarkup]:
        header = "<b>Your Ballots</b>"

        user_ballots = self.get_ballots()
        if user_ballots:
            ballot_linked_summaries = [ballot.generate_linked_summary() for ballot in user_ballots]
            ballot_text_group = PaginationTextGroup(
                ballot_linked_summaries, ("", const.BALLOT, ""),
                items_per_page=5, is_horizontal_buttons=True, is_cyclic=False, hidden_enabled=True
            )

            page_contents, start_index = ballot_text_group.get_page_contents(page_number)
            body = util.list_to_indexed_list_string(
                page_contents, start=start_index, line_spacing=2
            )
            buttons = ballot_text_group.build_buttons(page_number)
            buttons.append([util.build_button("Close", action=const.CLOSE)])
        else:
            body = util.make_html_italic("You have no ballots! Use /ballot to build a new ballot.")
            buttons = [[util.build_button("Close", action=const.CLOSE)]]

        ballot_count = len(user_ballots)
        footer = f"{const.EMOJI_BALLOT} {ballot_count} ballot{'' if ballot_count == 1 else 's'} in total"

        return "\n\n".join([header] + [body] + [footer]), InlineKeyboardMarkup(buttons)

    def render_template_list_with_buttons(self, page_number: int = 0) -> Tuple[str, InlineKeyboardMarkup]:
        header = "<b>Your Templates</b>"

        user_templates = self.get_templates()
        if user_templates:
            template_linked_summaries = [template.generate_linked_summary() for template in user_templates]
            template_text_group = PaginationTextGroup(
                template_linked_summaries, ("", const.TEMPLATE, ""),
                items_per_page=5, is_horizontal_buttons=True, is_cyclic=False, hidden_enabled=True
            )

            page_contents, start_index = template_text_group.get_page_contents(page_number)
            body = util.list_to_indexed_list_string(
                page_contents, start=start_index, line_spacing=2
            )
            buttons = template_text_group.build_buttons(page_number)
            buttons.append([util.build_button("Close", action=const.CLOSE)])
        else:
            body = "<i>You have no templates! Use /temp to create a new template.</i>"
            buttons = [[util.build_button("Close", action=const.CLOSE)]]

        template_count = len(user_templates)
        footer = f"{const.EMOJI_TEMPLATE} {template_count} template{'' if template_count == 1 else 's'} in total"

        return "\n\n".join([header] + [body] + [footer]), InlineKeyboardMarkup(buttons)

    def render_group_list_with_buttons(self, page_number: int = 0) -> Tuple[str, InlineKeyboardMarkup]:
        header = util.make_html_bold("Your Groups")

        all_groups = self.get_all_groups()
        if all_groups:
            group_linked_summaries = [group.generate_linked_summary(True) for group in all_groups]
            group_text_group = PaginationTextGroup(
                group_linked_summaries, ("", const.GROUP, ""),
                items_per_page=5, is_horizontal_buttons=True, is_cyclic=False, hidden_enabled=True
            )

            page_contents, start_index = group_text_group.get_page_contents(page_number)
            body = util.list_to_indexed_list_string(
                page_contents, start=start_index, line_spacing=2
            )
            buttons = group_text_group.build_buttons(page_number)
            buttons.append([util.build_button("Close", action=const.CLOSE)])
        else:
            body = f"<i><You are not in any group!/i>"
            buttons = [[util.build_button("Close", action=const.CLOSE)]]

        group_count = len(self.get_all_group_ids())
        footer = f"{const.EMOJI_GROUP} {group_count} group{'' if group_count == 1 else 's'} in total"

        return "\n\n".join([header] + [body] + [footer]), InlineKeyboardMarkup(buttons)

    def render_group_poll_list_with_buttons(self, page_number: int = 0) -> Tuple[str, InlineKeyboardMarkup]:
        header = "<b>Your Group Polls</b>"

        group_polls = self.get_group_polls()
        if group_polls:
            poll_linked_summaries = [poll.generate_linked_summary(True) for poll in group_polls]
            poll_text_group = PaginationTextGroup(
                poll_linked_summaries, ("", f"{const.GROUP}_{const.POLL}", ""),
                items_per_page=5, is_horizontal_buttons=True, is_cyclic=False, hidden_enabled=True
            )

            page_contents, start_index = poll_text_group.get_page_contents(page_number)
            body = util.list_to_indexed_list_string(
                page_contents, start=start_index, line_spacing=2
            )
            buttons = poll_text_group.build_buttons(page_number)
            buttons.append([util.build_button("Close", action=const.CLOSE)])
        else:
            body = "<i>You have no group polls!</i>"
            buttons = [[util.build_button("Close", action=const.CLOSE)]]

        poll_count = len(group_polls)
        footer = f"{const.EMOJI_POLL} {poll_count} group poll{'' if poll_count == 1 else 's'} in total"

        return "\n\n".join([header] + [body] + [footer]), InlineKeyboardMarkup(buttons)

    def render_group_ballot_list_with_buttons(self, page_number: int = 0) -> Tuple[str, InlineKeyboardMarkup]:
        header = "<b>Your Group Ballots</b>"

        group_ballots = self.get_group_ballots()
        if group_ballots:
            ballot_linked_summaries = [ballot.generate_linked_summary(True) for ballot in group_ballots]
            ballot_text_group = PaginationTextGroup(
                ballot_linked_summaries, ("", f"{const.GROUP}_{const.BALLOT}", ""),
                items_per_page=5, is_horizontal_buttons=True, is_cyclic=False, hidden_enabled=True
            )

            page_contents, start_index = ballot_text_group.get_page_contents(page_number)
            body = util.list_to_indexed_list_string(
                page_contents, start=start_index, line_spacing=2
            )
            buttons = ballot_text_group.build_buttons(page_number)
            buttons.append([util.build_button("Close", action=const.CLOSE)])
        else:
            body = "<i>You have no group ballots!</i>"
            buttons = [[util.build_button("Close", action=const.CLOSE)]]

        ballot_count = len(group_ballots)
        footer = f"{const.EMOJI_BALLOT} {ballot_count} group ballot{'' if ballot_count == 1 else 's'} in total"

        return "\n\n".join([header] + [body] + [footer]), InlineKeyboardMarkup(buttons)

    def render_group_template_list_with_buttons(self, page_number: int = 0) -> Tuple[str, InlineKeyboardMarkup]:
        header = "<b>Your Group Templates</b>"

        group_templates = self.get_group_templates()
        if group_templates:
            template_linked_summaries = [template.generate_linked_summary(True) for template in group_templates]
            template_text_group = PaginationTextGroup(
                template_linked_summaries, ("", f"{const.GROUP}_{const.TEMPLATE}", ""),
                items_per_page=5, is_horizontal_buttons=True, is_cyclic=False, hidden_enabled=True
            )

            page_contents, start_index = template_text_group.get_page_contents(page_number)
            body = util.list_to_indexed_list_string(
                page_contents, start=start_index, line_spacing=2
            )
            buttons = template_text_group.build_buttons(page_number)
            buttons.append([util.build_button("Close", action=const.CLOSE)])
        else:
            body = "<i>You have no group templates!</i>"
            buttons = [[util.build_button("Close", action=const.CLOSE)]]

        template_count = len(group_templates)
        footer = f"{const.EMOJI_TEMPLATE} {template_count} group template{'' if template_count == 1 else 's'} in total"

        return "\n\n".join([header] + [body] + [footer]), InlineKeyboardMarkup(buttons)

    def build_invite_text_and_buttons(self) -> tuple:
        close_button = InlineKeyboardButton("Close", callback_data=const.CLOSE)
        if not self._owned_group_ids:
            return "", InlineKeyboardMarkup.from_button(close_button)
        buttons = []
        for group in self.get_owned_groups():
            invite_button = util.build_switch_button(group.get_name(), f"/invite {group.get_name()}")
            buttons.append([invite_button])
        buttons.append([close_button])
        return "Which group's invite code do you want to send?", InlineKeyboardMarkup(buttons)

    def to_json(self) -> dict:
        return {
            db.USER_ID:               self._uid,
            db.USER_FIRST_NAME:       self._first_name,
            db.USER_LAST_NAME:        self._last_name,
            db.USER_USERNAME:         self._username,
            db.USER_IS_LEADER:        self._leader,
            db.USER_OWNED_GROUP_IDS:  list(self._owned_group_ids),
            db.USER_JOINED_GROUP_IDS: list(self._joined_group_ids),
            db.USER_POLL_IDS:         list(self._poll_ids),
            db.USER_BALLOT_IDS:       list(self._ballot_ids),
            db.USER_TEMP_POLL_IDS:    list(self._temp_poll_ids),
            db.USER_TEMP_BALLOT_IDS:  list(self._temp_ballot_ids)
        }
