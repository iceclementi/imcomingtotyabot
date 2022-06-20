from __future__ import annotations

from datetime import datetime
from typing import List, Set, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from database import database as db
from models import models
from models.poll import Poll
from models.ballot import Ballot
from models.template import Template
from models.user import User
from utils import util

group_storage = dict()


class Group(object):
    def __init__(
        self, gid: str, name: str, uid: int, password: str, member_ids: Set[int],
        poll_ids: Set[str], list_ids: Set[str], template_ids: Set[str], created_date: datetime
    ) -> None:
        self._gid = gid
        self._name = name
        self._owner = uid
        self._password = password
        self._member_ids = member_ids
        self._poll_ids = poll_ids
        self._ballot_ids = list_ids
        self._template_ids = template_ids
        self._created_date = created_date

    @staticmethod
    def get_group_by_id(gid: str) -> Group:
        return group_storage.get(gid, None)

    @staticmethod
    def get_groups_by_ids(gids: set, filters="") -> List[Group]:
        group_lists = [Group.get_group_by_id(gid) for gid in gids]
        return [group for group in group_lists if filters.lower() in group.get_name().lower()]

    @classmethod
    def create_new(cls, name: str, uid: int, password="") -> Group:
        gid = util.generate_random_id(models.GROUP_ID_LENGTH, set(group_storage.keys()))
        group = cls(gid, name, uid, password, {uid}, set(), set(), set(), datetime.now(tz=models.tz))
        group_storage[gid] = group
        return group

    @classmethod
    def load(
        cls, gid: str, name: str, owner: int, password: str, member_ids: List[int],
        poll_ids: List[str], ballot_ids: List[str], template_ids: List[str], created_date: str
    ) -> None:
        group = cls(
            gid, name, owner, password, set(member_ids),
            set(poll_ids), set(ballot_ids), set(template_ids), datetime.fromisoformat(created_date)
        )
        group_storage[gid] = group
        return

    def delete(self) -> None:
        for uid in list(self.get_member_ids()):
            self.remove_member(uid)
        group_storage.pop(self._gid, None)

    def get_gid(self) -> str:
        return self._gid

    def get_name(self) -> str:
        return self._name

    def edit_name(self, new_name: str) -> None:
        self._name = new_name

    def get_password_hash(self) -> str:
        return f"{self._gid}_{util.simple_hash(self._password, self._gid)}" if self._password else self._gid

    def edit_password(self, new_password: str) -> None:
        self._password = new_password

    def get_owner(self) -> int:
        return self._owner

    def get_member_ids(self) -> Set[int]:
        return self._member_ids

    def get_members(self) -> List[User]:
        members = [User.get_user_by_id(uid) for uid in self._member_ids]
        return sorted(members, key=lambda member: member.get_name().lower())

    def add_member(self, uid: int) -> str:
        if uid in self._member_ids:
            return "You are already in the group!"
        if len(self._member_ids) >= models.MAX_GROUP_SIZE:
            return f"The group size limit ({models.MAX_GROUP_SIZE}) has been reached."
        self._member_ids.add(uid)
        User.get_user_by_id(uid).join_group(self._gid)
        return f"You have joined {util.make_html_bold(self._name)}!"

    def remove_member(self, uid: int) -> str:
        if uid not in self._member_ids:
            return "The user is not in the group."
        self._member_ids.remove(uid)
        user = User.get_user_by_id(uid)
        user.leave_group(self._gid)
        for poll_id in list(self.get_poll_ids()):
            if Poll.get_poll_by_id(poll_id).get_creator_id() == uid:
                self._poll_ids.remove(poll_id)
        return f"{user.get_name()} has been removed from the group."

    def get_poll_ids(self) -> Set[str]:
        return self._poll_ids

    def get_polls(self, filters="") -> List[Poll]:
        group_polls = Poll.get_polls_by_ids(self._poll_ids, filters)
        return sorted(group_polls, key=lambda poll: poll.get_created_date(), reverse=True)

    def add_poll(self, poll_id: str) -> str:
        if poll_id in self._poll_ids:
            return "The poll already exists in the group."
        self._poll_ids.add(poll_id)
        return f"Poll \"{Poll.get_poll_by_id(poll_id).get_title()}\" added into the group."

    def remove_poll(self, poll_id: str) -> str:
        if poll_id not in self._poll_ids:
            return "The poll is not in the group."
        self._poll_ids.remove(poll_id)
        title = Poll.get_poll_by_id(poll_id).get_title()
        return f"Poll \"{title}\" has been removed from the group."

    def get_ballot_ids(self) -> Set[str]:
        return self._ballot_ids

    def get_ballots(self, filters="") -> List[Ballot]:
        group_lists = Ballot.get_ballots_by_ids(self._ballot_ids, filters)
        return sorted(group_lists, key=lambda _list: _list.get_created_date(), reverse=True)

    def add_ballot(self, ballot_id: str) -> str:
        if ballot_id in self._ballot_ids:
            return "The list already exists in the group."
        self._ballot_ids.add(ballot_id)
        return f"Ballot \"{Ballot.get_ballot_by_id(ballot_id).get_title()}\" added into the group."

    def remove_ballot(self, ballot_id: str) -> str:
        if ballot_id not in self._ballot_ids:
            return "The list is not in the group."
        self._ballot_ids.remove(ballot_id)
        title = Ballot.get_ballot_by_id(ballot_id).get_title()
        return f"Ballot \"{title}\" has been removed from the group."

    def get_template_ids(self) -> Set[str]:
        return self._template_ids

    def get_templates(self, filters="") -> List[Template]:
        group_templates = Template.get_templates_by_ids(self._template_ids, filters)
        return sorted(group_templates, key=lambda template: template._name.lower())

    def add_template(self, temp_id: str) -> str:
        template = Template.get_template_by_id(temp_id)
        if temp_id in self._template_ids:
            return f"The {template.temp_type} template already exists in the group."
        self._template_ids.add(temp_id)
        return f"{template.temp_type.capitalize()} template \"{template.name}\" is added to the group."

    def remove_template(self, temp_id: str) -> str:
        if temp_id not in self._template_ids:
            return "The template does not exist in the group."
        self._template_ids.remove(temp_id)
        template = Template.get_template_by_id(temp_id)
        return f"{template.temp_type.capitalize()} template \"{template.name}\" has been removed from the group."

    def generate_linked_summary(self, include_creator=False) -> str:
        header = f"<b>{self._name[:60]}</b> ({len(self._member_ids)} {models.EMOJI_PEOPLE})"
        link = f"/group_{self._gid}"
        creator = f"{models.EMOJI_CROWN} {User.get_user_by_id(self._owner).get_name()}"
        return "\n".join([header] + [f"{link} {creator}"]) if include_creator else "\n".join([header] + [link])

    def generate_group_members_list(self) -> str:
        members_list = []
        for member in self.get_members():
            if member.get_uid() == self._owner:
                member_name = f"{util.make_html_bold(member.get_name())} {models.EMOJI_CROWN}"
            else:
                member_name = member.get_name()
            members_list.append(member_name)

        if len(self.get_members()) == 1:
            response = util.make_html_italic("You're the only member in the group. Go ahead and add some more members!")
            members_list.append(f"\n{response}")

        return "\n".join(members_list)

    def generate_group_polls_list(self) -> str:
        if not self._poll_ids:
            return util.make_html_italic("You have no group polls. Go ahead and add a poll into the group!")

        return util.list_to_indexed_list_string(
            [poll.generate_linked_summary(include_creator=True) for poll in self.get_polls()], line_spacing=2
        )

    def generate_group_ballots_list(self) -> str:
        if not self._ballot_ids:
            return util.make_html_italic("You have no group ballots. Go ahead and add a ballot into the group!")

        return util.list_to_indexed_list_string(
            [_list.generate_linked_summary(include_creator=True) for _list in self.get_ballots()], line_spacing=2
        )

    def generate_group_templates_list(self) -> str:
        if not self._template_ids:
            return util.make_html_italic("You have no group templates. Go ahead and add a template into the group!")

        return util.list_to_indexed_list_string(
            [template.generate_linked_summary(True) for template in self.get_templates()], line_spacing=2
        )

    def generate_group_description_summary(self) -> str:
        owner = [f"{models.EMOJI_CROWN} {User.get_user_by_id(self._owner).get_name()}"]
        member_count = [f"{models.EMOJI_PEOPLE} {len(self._member_ids)}"]
        poll_count = [f"{models.EMOJI_POLL} {len(self._poll_ids)}"]
        list_count = [f"{models.EMOJI_BALLOT} {len(self._ballot_ids)}"]
        return " / ".join(owner + member_count + poll_count + list_count)

    def render_group_details_text(self) -> str:
        title = util.make_html_bold(self._name)
        owner = f"{models.EMOJI_CROWN} {User.get_user_by_id(self._owner).get_name()}"
        header = f"{title}\n{owner}"

        member_count = f"{models.EMOJI_PEOPLE} {len(self._member_ids)}"
        poll_count = f"{models.EMOJI_POLL} {len(self._poll_ids)}"
        list_count = f"{models.EMOJI_BALLOT} {len(self._ballot_ids)}"
        template_count = f"{models.EMOJI_TEMPLATE} {len(self._template_ids)}"
        body = f"{member_count: <8}{poll_count: <8}{list_count: <8}{template_count: <8}"

        footer = util.make_html_italic(f"Created on: {util.format_date(self._created_date)}")
        return "\n\n".join([header] + [body] + [footer])

    def render_group_members_text(self) -> str:
        header = util.make_html_bold(f"Group Members ({self._name})")
        body = self.generate_group_members_list()

        if len(self._member_ids) == 0:
            footer_description = "No group members"
        elif len(self._member_ids) == 1:
            footer_description = "1 group member"
        else:
            footer_description = f"{len(self._member_ids)} group members"

        footer = f"{models.EMOJI_PEOPLE} {footer_description}"

        return "\n\n".join([header] + [body] + [footer])

    def render_group_polls_text(self) -> str:
        header = util.make_html_bold(f"{self._name} Polls")
        body = self.generate_group_polls_list()

        if len(self._poll_ids) == 0:
            footer_description = "No group polls"
        elif len(self._poll_ids) == 1:
            footer_description = "1 group poll"
        else:
            footer_description = f"{len(self._poll_ids)} group polls"

        footer = f"{models.EMOJI_POLL} {footer_description}"

        return "\n\n".join([header] + [body] + [footer])

    def render_group_ballots_text(self) -> str:
        header = util.make_html_bold(f"{self._name} Ballots")
        body = self.generate_group_ballots_list()

        if len(self._ballot_ids) == 0:
            footer_description = "No group ballots"
        elif len(self._ballot_ids) == 1:
            footer_description = "1 group ballot"
        else:
            footer_description = f"{len(self._ballot_ids)} group ballots"

        footer = f"{models.EMOJI_BALLOT} {footer_description}"

        return "\n\n".join([header] + [body] + [footer])

    def render_group_templates_text(self) -> str:
        header = f"<b>{self._name} Templates</b>"
        body = self.generate_group_templates_list()

        if len(self._template_ids) == 0:
            footer_description = "No group templates"
        elif len(self._template_ids) == 1:
            footer_description = "1 group template"
        else:
            footer_description = f"{len(self._template_ids)} group templates"

        footer = f"{models.EMOJI_TEMPLATE} {footer_description}"

        return "\n\n".join([header] + [body] + [footer])

    def build_invite_text_and_button(self, owner_name: str) -> Tuple[str, InlineKeyboardMarkup]:
        invitation = f"You are invited to join {owner_name}'s <b>{self._name}</b> group!"
        join_button = util.build_switch_button("Join Group", f"/join {self.get_password_hash()}", to_self=True)
        return invitation, InlineKeyboardMarkup([[join_button]])

    def build_main_buttons(self) -> InlineKeyboardMarkup:
        view_button = self.build_button("View", models.VIEW)
        settings_button = self.build_button("Settings", models.SETTINGS)
        refresh_button = self.build_button("Refresh", models.REFRESH)
        close_button = self.build_button("Close", models.CLOSE)
        buttons = [[view_button], [settings_button], [refresh_button, close_button]]
        return InlineKeyboardMarkup(buttons)

    def build_view_buttons(self) -> InlineKeyboardMarkup:
        view_members_button = self.build_button("View Members", models.MEMBER)
        view_polls_button = self.build_button("View Polls", models.POLL)
        view_ballots_button = self.build_button("View Ballots", models.BALLOT)
        view_templates_button = self.build_button("View Templates", models.TEMPLATE)
        back_button = self.build_button("Back", models.BACK)
        buttons = [
            [view_members_button], [view_polls_button], [view_ballots_button], [view_templates_button], [back_button]
        ]
        return InlineKeyboardMarkup(buttons)

    def build_view_members_buttons(self, is_owner=False) -> InlineKeyboardMarkup:
        back_button = self.build_button("Back", models.VIEW)
        if not is_owner:
            return InlineKeyboardMarkup([[back_button]])

        buttons = []
        group_invite_button = util.build_switch_button("Send Group Invite", f"/invite {self._name}")
        buttons.append([group_invite_button])

        if len(self._member_ids) > 1:
            remove_member_button = self.build_button("Remove Member", f"{models.DELETE}_{models.MEMBER}")
            buttons.append([remove_member_button])

        buttons.append([back_button])
        return InlineKeyboardMarkup(buttons)

    def build_members_buttons(self, member_action: str, back_action=models.MEMBER) -> InlineKeyboardMarkup:
        buttons = []
        for member in self.get_members():
            if member.get_uid() != self._owner:
                member_button = self.build_button(member.get_name(), f"{member_action}_{member.get_uid()}")
                buttons.append([member_button])
        if back_action:
            back_button = self.build_button("Back", back_action)
            buttons.append([back_button])
        return InlineKeyboardMarkup(buttons)

    def build_view_polls_buttons(self, user_polls: List[Poll], is_owner=False) -> InlineKeyboardMarkup:
        add_group_poll_button = self.build_button("Add Group Poll", f"{models.ADD}_{models.POLL}")
        remove_group_poll_button = self.build_button("Remove Group Poll", f"{models.DELETE}_{models.POLL}")
        back_button = self.build_button("Back", models.VIEW)
        show_remove_button = len(self._poll_ids) and (
                    is_owner or any(poll.get_poll_id() in self.get_poll_ids() for poll in user_polls))
        buttons = (
            [[add_group_poll_button], [remove_group_poll_button], [back_button]]
            if show_remove_button
            else [[add_group_poll_button], [back_button]]
        )
        return InlineKeyboardMarkup(buttons)

    def build_polls_text_and_buttons(self, filters: list, filter_out=False, action="", back_action="") -> tuple:
        if filter_out:
            polls = [poll for poll in filters if poll.get_poll_id() not in self.get_poll_ids()]
        else:
            polls = [poll for poll in filters if poll.get_poll_id() in self.get_poll_ids()]

        back_button = self.build_button("Back", back_action)

        if not polls:
            return "", InlineKeyboardMarkup([[back_button]])

        response = "\n\n".join(f"{i}. {poll.generate_linked_summary(True)}" for i, poll in enumerate(polls, 1))
        buttons = [[self.build_button(
            poll.get_title(),
            f"{action}_{poll.get_poll_id()}"
        )] for poll in polls]
        buttons.append([back_button])

        return response, InlineKeyboardMarkup(buttons)

    def build_add_polls_buttons(self, user_polls: List[Poll]) -> InlineKeyboardMarkup:
        polls = [poll for poll in user_polls if poll.get_poll_id() not in self.get_poll_ids()]

        if not polls:
            return self.build_single_back_button(models.POLL)

        buttons = [[self.build_button(poll.get_title(), f"{models.ADD}_{models.POLL}_{poll.get_poll_id()}")]
                   for poll in polls]
        back_button = self.build_button("Back", models.POLL)
        buttons.append([back_button])
        return InlineKeyboardMarkup(buttons)

    def build_remove_polls_buttons(self, user_polls: List[Poll], is_owner=False) -> InlineKeyboardMarkup:
        if is_owner:
            polls = self.get_polls()
        else:
            polls = [poll for poll in user_polls if poll.get_poll_id() in self.get_poll_ids()]

        if not polls:
            return self.build_single_back_button(models.POLL)

        buttons = [[self.build_button(poll.get_title(), f"{models.DELETE}_{models.POLL}_{poll.get_poll_id()}")]
                   for poll in polls]
        back_button = self.build_button("Back", models.POLL)
        buttons.append([back_button])
        return InlineKeyboardMarkup(buttons)

    def build_view_ballots_buttons(self, user_lists: List[Ballot], is_owner=False) -> InlineKeyboardMarkup:
        add_group_ballot_button = self.build_button("Add Group Ballot", f"{models.ADD}_{models.BALLOT}")
        remove_group_ballot_button = self.build_button("Remove Group Ballot", f"{models.DELETE}_{models.BALLOT}")
        back_button = self.build_button("Back", models.VIEW)
        show_remove_button = len(self._ballot_ids) and (
                    is_owner or any(ballot.get_ballot_id() in self.get_ballot_ids() for ballot in user_lists))
        buttons = [[add_group_ballot_button], [remove_group_ballot_button], [back_button]] if show_remove_button else [
            [add_group_ballot_button], [back_button]]
        return InlineKeyboardMarkup(buttons)

    def build_add_ballots_buttons(self, user_lists: List[Ballot]) -> InlineKeyboardMarkup:
        ballots = [ballot for ballot in user_lists if ballot.get_ballot_id() not in self.get_ballot_ids()]

        if not ballots:
            return self.build_single_back_button(models.BALLOT)

        buttons = [[self.build_button(ballot.get_title(), f"{models.ADD}_{models.BALLOT}_{ballot.get_ballot_id()}")]
                   for ballot in ballots]
        back_button = self.build_button("Back", models.BALLOT)
        buttons.append([back_button])
        return InlineKeyboardMarkup(buttons)

    def build_remove_lists_buttons(self, user_lists: List[Ballot], is_owner=False) -> InlineKeyboardMarkup:
        if is_owner:
            ballots = self.get_ballots()
        else:
            ballots = [ballot for ballot in user_lists if ballot.get_ballot_id() in self.get_ballot_ids()]

        if not ballots:
            return self.build_single_back_button(models.BALLOT)

        buttons = [[self.build_button(ballot.get_title(), f"{models.DELETE}_{models.BALLOT}_{ballot.get_ballot_id()}")]
                   for ballot in ballots]
        back_button = self.build_button("Back", models.BALLOT)
        buttons.append([back_button])
        return InlineKeyboardMarkup(buttons)

    def build_view_templates_buttons(self, user_templates: List[Template], is_owner=False) -> InlineKeyboardMarkup:
        add_group_template_button = self.build_button("Add Group Template", f"{models.ADD}_{models.TEMPLATE}")
        remove_group_template_button = self.build_button("Remove Group Template", f"{models.DELETE}_{models.TEMPLATE}")
        back_button = self.build_button("Back", models.VIEW)
        show_remove_button = len(self._template_ids) and (
                is_owner or any(template.temp_id in self.get_template_ids() for template in user_templates)
        )
        buttons = (
            [[add_group_template_button], [remove_group_template_button], [back_button]]
            if show_remove_button
            else [[add_group_template_button], [back_button]]
        )
        return InlineKeyboardMarkup(buttons)

    def build_add_templates_buttons(self, user_templates: List[Template]) -> InlineKeyboardMarkup:
        templates = [template for template in user_templates if template.temp_id not in self.get_template_ids()]

        if not templates:
            return self.build_single_back_button(models.TEMPLATE)

        buttons = [
            [self.build_button(
                f"{template.icon} {template.name}", f"{models.ADD}_{models.TEMPLATE}_{template.temp_id}"
            )]
            for template in templates
        ]

        back_button = self.build_button("Back", models.TEMPLATE)
        buttons.append([back_button])
        return InlineKeyboardMarkup(buttons)

    def build_remove_templates_buttons(self, user_templates: List[Template], is_owner=False) -> InlineKeyboardMarkup:
        if is_owner:
            templates = self.get_templates()
        else:
            templates = [template for template in user_templates if template.temp_id in self.get_template_ids()]

        if not templates:
            return self.build_single_back_button(models.TEMPLATE)

        buttons = [
            [self.build_button(
                f"{template.icon} {template.name}", f"{models.DELETE}_{models.TEMPLATE}_{template.temp_id}"
            )]
            for template in templates
        ]
        back_button = self.build_button("Back", models.TEMPLATE)
        buttons.append([back_button])
        return InlineKeyboardMarkup(buttons)

    def build_settings_buttons(self, is_owner=False) -> InlineKeyboardMarkup:
        if is_owner:
            change_name_button = self.build_button("Change Group Name", f"{models.RENAME}_{models.NAME}")
            change_password_button = self.build_button("Change Password", models.SECRET)
            delete_group_button = self.build_button("Delete Group", models.DELETE)
            buttons = [[change_name_button], [change_password_button], [delete_group_button]]
        else:
            leave_group_button = self.build_button("Leave Group", models.LEAVE_GROUP)
            buttons = [[leave_group_button]]
        back_button = self.build_button("Back", models.BACK)
        buttons.append([back_button])
        return InlineKeyboardMarkup(buttons)

    def build_single_back_button(self, back_action: str, back_text="Back") -> InlineKeyboardMarkup:
        back_button = self.build_button(back_text, back_action)
        return InlineKeyboardMarkup([[back_button]])

    def build_delete_confirm_buttons(
        self, delete_action: str, back_action: str, delete_text="Delete", back_text="No"
    ) -> InlineKeyboardMarkup:
        delete_button = self.build_button(delete_text, f"{models.DELETE_YES}_{delete_action}")
        back_button = self.build_button(back_text, back_action)
        buttons = [[delete_button, back_button]]
        return InlineKeyboardMarkup(buttons)

    def build_button(self, text: str, action: str) -> InlineKeyboardButton:
        return util.build_button(text, models.GROUP_SUBJECT, action, self._gid)

    def to_json(self) -> dict:
        return {
            db.GROUP_ID:           self._gid,
            db.GROUP_NAME:         self._name,
            db.GROUP_OWNER:        self._owner,
            db.GROUP_PASSWORD:     self._password,
            db.GROUP_MEMBER_IDS:   list(self._member_ids),
            db.GROUP_POLL_IDS:     list(self._poll_ids),
            db.GROUP_BALLOT_IDS:   list(self._ballot_ids),
            db.GROUP_TEMP_IDS:     list(self._template_ids),
            db.GROUP_CREATED_DATE: self._created_date.isoformat()
        }
