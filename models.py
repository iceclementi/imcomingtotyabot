"""Backend models"""
import json
from datetime import datetime, timedelta
from collections import OrderedDict
import re
from typing import Tuple, Dict, List as Lst, Union
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

import database as db
import util

# region SETTINGS

# Settings
POLL_ID_LENGTH = 4
LIST_ID_LENGTH = 4
GROUP_ID_LENGTH = 3
MAX_GROUPS_PER_USER = 10
MAX_JOINED_GROUPS_PER_USER = 30
MAX_GROUP_SIZE = 50
EMOJI_PEOPLE = "\U0001f465"
EMOJI_GROUP = "\U0001fac2"
EMOJI_POLL = "\U0001f4ca"
EMOJI_LIST = "\U0001f4dd"
EMOJI_TEMPLATE = "\U0001f4c3"
EMOJI_CROWN = "\U0001f451"
EMOJI_HAPPY = "\U0001f60a"
SESSION_EXPIRY = 1  # In hours
EXPIRY = 720
BOT_NAME = "imcomingtotyabot"

# Button Actions
USER_SUBJECT = "u"
POLL_SUBJECT = "p"
LIST_SUBJECT = "l"
GROUP_SUBJECT = "g"
TEMP_POLL_SUBJECT = "tp"
TEMP_LIST_SUBJECT = "tl"
POLL = "poll"
LIST = "list"
GROUP = " group"
PUBLISH = "publish"
REFRESH = "refresh"
TITLE = "title"
OPTION = "opt"
OPTIONS = "opts"
CHOICE = "choice"
USER_REFRESH = "userRefresh"
REFRESH_OPT = "refreshOpt"
CUSTOMISE = "custom"
RESPONSE = "response"
COMMENT = "comment"
EDIT_COMMENT = "editComment"
VOTE = "vote"
DELETE = "delete"
DELETE_YES = "delYes"
BACK = "back"
VIEW_MEMBERS = "members"
REMOVE_MEMBER = "delMember"
VIEW_GROUP_POLLS = "polls"
ADD_POLL = "poll"
REMOVE_POLL = "delPoll"
SETTINGS = "set"
CHANGE_SECRET = "pass"
GROUP_INVITE = "invite"
LEAVE_GROUP = "leave"
BOT_ACCESS = "bot"
PROMOTE = "promote"
CLOSE = "close"
RESET = "reset"
DONE = "done"
SKIP = "skip"
UPDATE_DONE = "updateDone"
SHOW = "show"
HIDE = "hide"
PRESET = "preset"
TEMP_POLL = "tPoll"
TEMP_LIST = "tList"
PRESET_GUIDE = "preGuide"
TEMP_TITLE = "tTitle"
TEMP_DESCRIPTION = "tDescr"
TEMP_TITLE_CODE = "tTitleCode"
TEMP_DESCRIPTION_CODE = "tDescrCode"
EDIT = "edit"

# endregion

user_storage = dict()
group_storage = dict()
poll_storage = dict()
list_storage = dict()
temp_poll_storage = dict()
temp_list_storage = dict()


class User(object):
    def __init__(self, uid: int, first_name: str, last_name: str, username: str, is_leader: bool,
                 owned_group_ids: set, joined_group_ids: set, poll_ids: set, list_ids: set, temp_poll_ids: set) -> None:
        self.uid = uid
        self.first_name = first_name
        self.last_name = last_name
        self.username = username
        self.leader = is_leader
        self.owned_group_ids = owned_group_ids
        self.joined_group_ids = joined_group_ids
        self.poll_ids = poll_ids
        self.list_ids = list_ids
        self._temp_poll_ids = temp_poll_ids

    @staticmethod
    def get_user_by_id(uid: int):
        return user_storage.get(uid, None)

    @staticmethod
    def get_users_by_name(name="") -> list:
        sorted_users = sorted(user_storage.values(), key=lambda user: user.get_name().lower())
        filtered_users = [user for user in sorted_users if name in user.get_name()]
        return filtered_users

    @classmethod
    def register(cls, uid: int, first_name: str, last_name="", username=""):
        user = cls(uid, first_name, last_name, username, False, set(), set(), set(), set(), set())
        user_storage[uid] = user
        return user

    @classmethod
    def load(cls, uid: int, first_name: str, last_name: str, username: str, is_leader: bool,
             owned_group_ids: list, joined_group_ids: list, poll_ids: list, list_ids: list,
             temp_poll_ids: list) -> None:
        user = cls(uid, first_name, last_name, username, is_leader,
                   set(owned_group_ids), set(joined_group_ids), set(poll_ids), set(list_ids), set(temp_poll_ids))
        user_storage[uid] = user
        return

    def get_uid(self) -> int:
        return self.uid

    def get_name(self) -> str:
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name

    def get_username(self) -> str:
        return self.username

    def is_leader(self) -> bool:
        return self.leader

    def promote_to_leader(self) -> None:
        self.leader = True

    def get_owned_group_ids(self) -> set:
        return self.groups

    def get_owned_groups(self, filters="") -> list:
        owned_groups = Group.get_groups_by_ids(self.owned_group_ids, filters)
        return sorted(owned_groups, key=lambda group: group.get_name().lower())

    def has_group_with_name(self, name: str) -> bool:
        return any(group.get_name() == name for group in self.get_owned_groups())

    def create_group(self, name: str, password="") -> tuple:
        if self.has_group_with_name(name):
            return None, "You already have a group with the same name."
        if len(self.owned_group_ids) >= MAX_GROUPS_PER_USER:
            return None, f"The maximum number of groups you can own ({MAX_GROUPS_PER_USER}) has been reached."
        group = Group.create_new(name, self.uid, password)
        self.owned_group_ids.add(group.get_gid())
        return group, f"Group {util.make_html_bold(name)} created!"

    def delete_group(self, gid: str) -> str:
        if gid not in self.owned_group_ids:
            return "You do not own that group."
        self.owned_group_ids.remove(gid)
        group = Group.get_group_by_id(gid)
        group.delete()
        return f"Group \"{group.get_name()}\" has been deleted."

    def get_joined_group_ids(self) -> set:
        return self.joined_group_ids

    def get_joined_groups(self, filters="") -> list:
        joined_groups = Group.get_groups_by_ids(self.joined_group_ids, filters)
        return sorted(joined_groups, key=lambda group: group.get_name().lower())

    def join_group(self, gid: str) -> str:
        if len(self.joined_group_ids) >= MAX_JOINED_GROUPS_PER_USER:
            return f"The maximum number of groups you can join ({MAX_JOINED_GROUPS_PER_USER}) has been reached."
        self.joined_group_ids.add(gid)
        group = Group.get_group_by_id(gid)
        return f"Group {util.make_html_bold(group.get_name())} joined!"

    def leave_group(self, gid: str) -> None:
        if gid in self.joined_group_ids:
            self.joined_group_ids.remove(gid)

    def get_all_group_ids(self) -> set:
        return set.union(self.owned_group_ids, self.joined_group_ids)

    def get_all_groups(self, filters="") -> list:
        all_user_groups = Group.get_groups_by_ids(self.get_all_group_ids(), filters)
        return sorted(all_user_groups, key=lambda group: group.get_name().lower())

    def get_poll_ids(self) -> set:
        return self.poll_ids

    def get_polls(self, filters="") -> list:
        user_polls = Poll.get_polls_by_ids(self.poll_ids, filters)
        return sorted(user_polls, key=lambda poll: poll.get_created_date(), reverse=True)

    def get_group_poll_ids(self) -> set:
        group_poll_ids = set()
        for group in self.get_all_groups():
            group_poll_ids.update(group.get_poll_ids())
        return group_poll_ids

    def get_group_polls(self, filters="") -> list:
        group_polls = Poll.get_polls_by_ids(self.get_group_poll_ids(), filters)
        return sorted(group_polls, key=lambda poll: poll.get_created_date(), reverse=True)

    def create_poll(self, title: str, description: str, options: list) -> tuple:
        poll = Poll.create_new(title, self.uid, description, options)
        self.poll_ids.add(poll.get_poll_id())
        return poll, f"Poll {util.make_html_bold(title)} created!"

    def delete_poll(self, poll_id: str) -> str:
        if poll_id not in self.poll_ids:
            return "No such poll exists."
        self.poll_ids.remove(poll_id)

        # Delete poll from all user groups
        for group in self.get_all_groups():
            if poll_id in group.get_poll_ids():
                group.remove_poll(poll_id)

        poll = Poll.get_poll_by_id(poll_id)
        poll.delete()

        return f"Poll {util.make_html_bold(poll.get_title())} has been deleted."

    def has_group_poll(self, poll_id: str) -> bool:
        return any(poll_id in group.get_poll_ids() for group in self.get_all_groups())

    def get_list_ids(self) -> set:
        return self.list_ids

    def get_lists(self, filters="") -> list:
        user_lists = List.get_lists_by_ids(self.list_ids, filters)
        return sorted(user_lists, key=lambda _list: _list.get_created_date(), reverse=True)

    def get_group_list_ids(self) -> set:
        group_list_ids = set()
        for group in self.get_all_groups():
            group_list_ids.update(group.get_list_ids())
        return group_list_ids

    def get_group_lists(self, filters="") -> list:
        group_lists = List.get_lists_by_ids(self.get_group_list_ids(), filters)
        return sorted(group_lists, key=lambda _list: _list.get_created_date(), reverse=True)

    def create_list(self, title: str, description: str, options: list, choices: list) -> tuple:
        _list = List.create_new(title, self.uid, description, options, choices)
        self.list_ids.add(_list.get_list_id())
        return _list, f"List {util.make_html_bold(title)} created!"

    def delete_list(self, list_id: str) -> str:
        if list_id not in self.list_ids:
            return "No such list exists."
        self.list_ids.remove(list_id)

        # Delete list from all user groups
        for group in self.get_all_groups():
            if list_id in group.get_list_ids():
                group.remove_list(list_id)

        _list = List.get_list_by_id(list_id)
        _list.delete()

        return f"Poll {util.make_html_bold(list.get_title())} has been deleted."

    def has_group_list(self, list_id: str) -> bool:
        return any(list_id in group.get_list_ids() for group in self.get_all_groups())

    def get_temp_poll_ids(self) -> set:
        return self._temp_poll_ids

    def get_temp_polls(self, filters="") -> list:
        user_temp_polls = PollTemplate.get_templates_by_ids(self._temp_poll_ids, filters)
        return sorted(user_temp_polls, key=lambda temp_poll: temp_poll.name.lower())

    def get_temp_poll_by_name(self, name: str):
        return next((temp_poll for temp_poll in self.get_temp_polls() if temp_poll.name.lower() == name.lower()), None)

    def create_temp_poll(self, name: str, title: str, description: str, options: list,
                         is_single_response: bool) -> tuple:
        temp_poll = PollTemplate.create_new(name, title, description, options, is_single_response, self.uid)
        self._temp_poll_ids.add(temp_poll.temp_id)
        return temp_poll, f"Poll template {util.make_html_bold(name)} created!"

    def delete_temp_poll(self, temp_poll_id: str) -> str:
        if temp_poll_id not in self._temp_poll_ids:
            return "No such poll template exists."
        self._temp_poll_ids.remove(temp_poll_id)

        temp_poll = PollTemplate.get_template_by_id(temp_poll_id)
        temp_poll.delete()

        return f"Poll {util.make_html_bold(temp_poll.get_title())} has been deleted."

    def has_temp_poll_with_name(self, name: str) -> bool:
        return any(temp_poll.name.lower() == name.lower() for temp_poll in self.get_temp_polls())

    def create_poll_from_template(self, temp_id: str, title: str, description: str):
        if temp_id not in self._temp_poll_ids:
            return None
        temp_poll = PollTemplate.get_template_by_id(temp_id)
        poll, _ = self.create_poll(title, description, temp_poll.options)
        poll.set_single_response(temp_poll.is_single_response)
        return poll

    def get_templates(self, filters="") -> list:
        temp_polls = self.get_temp_polls(filters)
        return sorted(temp_polls, key=lambda item: item.name.lower())

    def get_all_poll_ids(self) -> set:
        return self.poll_ids.union(self.get_group_poll_ids())

    def get_all_list_ids(self) -> set:
        return self.list_ids.union(self.get_group_list_ids())

    def get_everything(self, filters=""):
        all_polls = Poll.get_polls_by_ids(self.get_all_poll_ids(), filters)
        all_lists = List.get_lists_by_ids(self.get_all_list_ids(), filters)
        return sorted(all_polls + all_lists, key=lambda item: item.get_created_date(), reverse=True)

    def render_poll_list(self) -> str:
        header = [util.make_html_bold("Your Polls")]

        user_polls = self.get_polls()
        if user_polls:
            body = [f"{i}. {poll.generate_linked_summary()}" for i, poll in enumerate(user_polls, 1)]
        else:
            body = [util.make_html_italic("You have no polls! Use /poll to build a new poll.")]

        poll_count = len(user_polls)
        footer = [f"{EMOJI_POLL} {poll_count} poll{'' if poll_count == 1 else 's'} in total"]

        return "\n\n".join(header + body + footer)

    def render_list_list(self) -> str:
        header = [util.make_html_bold("Your Lists")]

        user_lists = self.get_lists()
        if user_lists:
            body = [f"{i}. {_list.generate_linked_summary()}" for i, _list in enumerate(user_lists, 1)]
        else:
            body = [util.make_html_italic("You have no lists! Use /list to build a new list.")]

        list_count = len(user_lists)
        footer = [f"{EMOJI_LIST} {list_count} list{'' if list_count == 1 else 's'} in total"]

        return "\n\n".join(header + body + footer)

    def render_group_poll_list(self) -> str:
        header = [util.make_html_bold("Your Group Polls")]

        group_polls = self.get_group_polls()
        if group_polls:
            body = [f"{i}. {poll.generate_linked_summary(True)}" for i, poll in enumerate(group_polls, 1)]
        else:
            body = [util.make_html_italic("You have no group polls!")]

        poll_count = len(group_polls)
        footer = [f"{EMOJI_POLL} {poll_count} group poll{'' if poll_count == 1 else 's'} in total"]

        return "\n\n".join(header + body + footer)

    def render_group_list_list(self) -> str:
        header = [util.make_html_bold("Your Group Lists")]

        group_lists = self.get_group_lists()
        if group_lists:
            body = [f"{i}. {_list.generate_linked_summary(True)}" for i, _list in enumerate(group_lists, 1)]
        else:
            body = [util.make_html_italic("You have no group lists!")]

        list_count = len(group_lists)
        footer = [f"{EMOJI_LIST} {list_count} group list{'' if list_count == 1 else 's'} in total"]

        return "\n\n".join(header + body + footer)

    def render_group_list(self) -> str:
        header = [util.make_html_bold("Your Groups")]

        owned_groups_list = self.render_owned_groups_list()
        joined_groups_list = self.render_joined_groups_list()
        body = [owned_groups_list] + [joined_groups_list]

        group_count = len(self.owned_group_ids) + len(self.joined_group_ids)
        footer = [f"{EMOJI_GROUP} {group_count} group{'' if group_count == 1 else 's'} in total"]

        return "\n\n".join(header + body + footer)

    def render_owned_groups_list(self) -> str:
        owned_groups_title = util.make_html_bold("Owned Groups") + f" ({len(self.owned_group_ids)} {EMOJI_CROWN})"
        owned_groups = self.get_owned_groups()
        if owned_groups:
            owned_groups_list = "\n\n".join(
                f"{i}. {group.generate_linked_summary()}" for i, group in enumerate(owned_groups, 1)
            )
        else:
            owned_groups_list = util.make_html_italic("You do not own any group!")
        return f"{owned_groups_title}\n{owned_groups_list}"

    def render_joined_groups_list(self) -> str:
        joined_groups_title = util.make_html_bold("Joined Groups") + f" ({len(self.joined_group_ids)} {EMOJI_GROUP})"
        joined_groups = self.get_joined_groups()
        if joined_groups:
            joined_groups_list = "\n\n".join(
                f"{i}. {group.generate_linked_summary()}" for i, group in enumerate(joined_groups, 1)
            )
        else:
            joined_groups_list = util.make_html_italic("You have not joined any group!")
        return f"{joined_groups_title}\n{joined_groups_list}"

    def render_template_list(self) -> str:
        header = "<b>Your Templates</b>"

        user_templates = self.get_temp_polls()
        if user_templates:
            body = [f"{i}. {template.generate_linked_summary()}" for i, template in enumerate(user_templates, 1)]
        else:
            body = ["<i>You have no templates! Use /temp to create a new template.</i>"]

        template_count = len(user_templates)
        footer = f"{EMOJI_TEMPLATE} {template_count} template{'' if template_count == 1 else 's'} in total"

        return "\n\n".join([header] + body + [footer])

    def build_invite_text_and_buttons(self) -> tuple:
        close_button = InlineKeyboardButton("Close", callback_data=CLOSE)
        if not self.owned_group_ids:
            return "", InlineKeyboardMarkup.from_button(close_button)
        buttons = []
        for group in self.get_owned_groups():
            invite_button = util.build_switch_button(group.get_name(), f"/invite {group.get_name()}")
            buttons.append([invite_button])
        buttons.append([close_button])
        return "Which group's invite code do you want to send?", InlineKeyboardMarkup(buttons)

    def to_json(self) -> dict:
        return {
            db.USER_ID: self.uid,
            db.USER_FIRST_NAME: self.first_name,
            db.USER_LAST_NAME: self.last_name,
            db.USER_USERNAME: self.username,
            db.USER_IS_LEADER: self.leader,
            db.USER_OWNED_GROUP_IDS: list(self.owned_group_ids),
            db.USER_JOINED_GROUP_IDS: list(self.joined_group_ids),
            db.USER_POLL_IDS: list(self.poll_ids),
            db.USER_LIST_IDS: list(self.list_ids),
            db.USER_TEMP_POLL_IDS: list(self._temp_poll_ids)
        }


class Group(object):
    def __init__(self, gid: str, name: str, uid: int, password: str, member_ids: set,
                 poll_ids: set, list_ids: set, created_date: datetime) -> None:
        self.gid = gid
        self.name = name
        self.owner = uid
        self.password = password
        self.member_ids = member_ids
        self.poll_ids = poll_ids
        self.list_ids = list_ids
        self.created_date = created_date

    @staticmethod
    def get_group_by_id(gid: str):
        return group_storage.get(gid, None)

    @staticmethod
    def get_groups_by_ids(gids: set, filters="") -> list:
        group_lists = [Group.get_group_by_id(gid) for gid in gids]
        return [group for group in group_lists if filters.lower() in group.get_name().lower()]

    @classmethod
    def create_new(cls, name: str, uid: int, password=""):
        gid = util.generate_random_id(GROUP_ID_LENGTH, set(group_storage.keys()))
        group = cls(gid, name, uid, password, {uid}, set(), set(), datetime.now())
        group_storage[gid] = group
        return group

    @classmethod
    def load(cls, gid: str, name: str, owner: int, password: str, member_ids: list,
             poll_ids: list, list_ids: list, created_date: str) -> None:
        group = cls(gid, name, owner, password, set(member_ids),
                    set(poll_ids), set(list_ids), datetime.fromisoformat(created_date))
        group_storage[gid] = group
        return

    def delete(self) -> None:
        for uid in list(self.get_member_ids()):
            self.remove_member(uid)
        group_storage.pop(self.gid, None)

    def get_gid(self) -> str:
        return self.gid

    def get_name(self) -> str:
        return self.name

    def edit_name(self, new_name: str) -> None:
        self.name = new_name

    def get_password_hash(self) -> str:
        return f"{self.gid}_{util.simple_hash(self.password, self.gid)}" if self.password else self.gid

    def edit_password(self, new_password: str) -> None:
        self.password = new_password

    def get_owner(self) -> int:
        return self.owner

    def get_member_ids(self) -> set:
        return self.member_ids

    def get_members(self) -> list:
        members = [User.get_user_by_id(uid) for uid in self.member_ids]
        return sorted(members, key=lambda member: member.get_name().lower())

    def add_member(self, uid: int) -> str:
        if uid in self.member_ids:
            return "You are already in the group."
        if len(self.member_ids) >= MAX_GROUP_SIZE:
            return f"The group size limit ({MAX_GROUP_SIZE}) has been reached."
        self.member_ids.add(uid)
        User.get_user_by_id(uid).join_group(self.gid)
        return f"You have joined {util.make_html_bold(self.name)}."

    def remove_member(self, uid: int) -> str:
        if uid not in self.member_ids:
            return "The user is not in the group."
        self.member_ids.remove(uid)
        user = User.get_user_by_id(uid)
        user.leave_group(self.gid)
        for poll_id in list(self.get_poll_ids()):
            if Poll.get_poll_by_id(poll_id).get_creator_id() == uid:
                self.poll_ids.remove(poll_id)
        return f"{user.get_name()} has been removed from the group."

    def get_poll_ids(self) -> set:
        return self.poll_ids

    def get_polls(self, filters="") -> list:
        group_polls = [Poll.get_poll_by_id(poll_id) for poll_id in self.poll_ids]
        filtered_polls = [poll for poll in group_polls if filters.lower() in poll.get_title().lower()]
        return sorted(filtered_polls, key=lambda poll: poll.get_created_date(), reverse=True)

    def add_poll(self, poll_id: str) -> str:
        if poll_id in self.poll_ids:
            return "The poll already exists in the group."
        self.poll_ids.add(poll_id)
        return f"Poll \"{Poll.get_poll_by_id(poll_id).get_title()}\" added into the group."

    def remove_poll(self, poll_id: str) -> str:
        if poll_id not in self.poll_ids:
            return "The poll is not in the group."
        self.poll_ids.remove(poll_id)
        title = Poll.get_poll_by_id(poll_id).get_title()
        return f"Poll \"{title}\" has been removed from the group."

    def get_list_ids(self) -> set:
        return self.list_ids

    def get_lists(self, filters="") -> list:
        group_lists = [Poll.get_list_by_id(list_id) for list_id in self.list_ids]
        filtered_lists = [_list for _list in group_lists if filters.lower() in _list.get_title().lower()]
        return sorted(filtered_lists, key=lambda _list: _list.get_created_date(), reverse=True)

    def add_list(self, list_id: str) -> str:
        if list_id in self.list_ids:
            return "The list already exists in the group."
        self.list_ids.add(list_id)
        return f"List \"{List.get_list_by_id(list_id).get_title()}\" added into the group."

    def remove_list(self, list_id: str) -> str:
        if list_id not in self.list_ids:
            return "The list is not in the group."
        self.list_ids.remove(list_id)
        title = List.get_list_by_id(list_id).get_title()
        return f"List \"{title}\" has been removed from the group."

    def generate_linked_summary(self) -> str:
        short_bold_title = util.make_html_bold(self.name)[:60]
        link = f"/group_{self.gid}"
        return f"{short_bold_title} ({len(self.member_ids)} {EMOJI_PEOPLE})\n{link}"

    def generate_group_members_list(self) -> str:
        members_list = []
        for member in self.get_members():
            if member.get_uid() == self.owner:
                member_name = f"{util.make_html_bold(member.get_name())} {EMOJI_CROWN}"
            else:
                member_name = member.get_name()
            members_list.append(member_name)

        if len(self.get_members()) == 1:
            response = util.make_html_italic("You're the only member in the group. Go ahead and add some more members!")
            members_list.append(f"\n{response}")

        return "\n".join(members_list)

    def generate_group_polls_list(self) -> str:
        if not self.poll_ids:
            return util.make_html_italic("You have no group polls. Go ahead and add a poll into the group!")

        return "\n\n".join(poll.generate_linked_summary(include_creator=True) for poll in self.get_polls())

    def generate_group_description_summary(self) -> str:
        owner = [f"{EMOJI_CROWN} {User.get_user_by_id(self.owner).get_name()}"]
        member_count = [f"{EMOJI_PEOPLE} {len(self.member_ids)}"]
        poll_count = [f"{EMOJI_POLL} {len(self.poll_ids)}"]
        list_count = [f"{EMOJI_LIST} {len(self.list_ids)}"]
        return " / ".join(owner + member_count + poll_count + list_count)

    def render_group_details_text(self) -> str:
        title = util.make_html_bold(self.name)
        owner = f"{EMOJI_CROWN} {User.get_user_by_id(self.owner).get_name()}"
        header = [f"{title}\n{owner}"]

        member_count = f"{EMOJI_PEOPLE} {len(self.member_ids)}"
        poll_count = f"{EMOJI_POLL} {len(self.poll_ids)}"
        list_count = f"{EMOJI_LIST} {len(self.list_ids)}"
        body = [f"{member_count: <8}{poll_count: <8}{list_count}"]

        footer = [util.make_html_italic(f"Created on: {util.format_date(self.created_date)}")]
        return "\n\n".join(header + body + footer)

    def render_group_members_text(self) -> str:
        header = [util.make_html_bold(f"{self.name} Members")]
        body = [self.generate_group_members_list()]

        if len(self.member_ids) == 0:
            footer_description = "No group members"
        elif len(self.member_ids) == 1:
            footer_description = "1 group member"
        else:
            footer_description = f"{len(self.member_ids)} group members"

        footer = [f"{EMOJI_PEOPLE} {footer_description}"]

        return "\n\n".join(header + body + footer)

    def render_group_polls_text(self) -> str:
        header = [util.make_html_bold(f"{self.name} Polls")]
        body = [self.generate_group_polls_list()]

        if len(self.poll_ids) == 0:
            footer_description = "No group polls"
        elif len(self.poll_ids) == 1:
            footer_description = "1 group poll"
        else:
            footer_description = f"{len(self.poll_ids)} group polls"

        footer = [f"{EMOJI_POLL} {footer_description}"]

        return "\n\n".join(header + body + footer)

    def build_invite_text_and_button(self, owner_name: str) -> tuple:
        invitation = f"You are invited to join {owner_name}'s <b>{self.name}</b> group!"
        join_button = util.build_switch_button("Join Group", f"/join {self.get_password_hash()}", to_self=True)
        return invitation, InlineKeyboardMarkup([[join_button]])

    def build_group_details_buttons(self) -> InlineKeyboardMarkup:
        view_members_button = util.build_button("View Members", GROUP_SUBJECT, VIEW_MEMBERS, self.gid)
        view_polls_button = util.build_button("View Polls", GROUP_SUBJECT, VIEW_GROUP_POLLS, self.gid)
        settings_button = util.build_button("Settings", GROUP_SUBJECT, SETTINGS, self.gid)
        close_button = util.build_button("Close", GROUP_SUBJECT, CLOSE, self.gid)
        buttons = [[view_members_button], [view_polls_button], [settings_button, close_button]]
        return InlineKeyboardMarkup(buttons)

    def build_members_view_buttons(self, back_action="", is_owner=False) -> InlineKeyboardMarkup:
        buttons = []
        if is_owner:
            group_invite_button = util.build_switch_button("Send Group Invite", f"/invite {self.name}")
            remove_member_button = util.build_button("Remove Member", GROUP_SUBJECT, REMOVE_MEMBER, self.gid)
            buttons.append([group_invite_button])
            buttons.append([remove_member_button])
        if back_action:
            back_button = util.build_button("Back", GROUP_SUBJECT, back_action, self.gid)
            buttons.append([back_button])
        return InlineKeyboardMarkup(buttons)

    def build_members_buttons(self, member_action: str, back_action="") -> InlineKeyboardMarkup:
        buttons = []
        for member in self.get_members():
            if member.get_uid() != self.owner:
                member_button = util.build_button(
                    member.get_name(), GROUP_SUBJECT, f"{member_action}_{member.get_uid()}", self.gid
                )
                buttons.append([member_button])
        if back_action:
            back_button = util.build_button("Back", GROUP_SUBJECT, back_action, self.gid)
            buttons.append([back_button])
        return InlineKeyboardMarkup(buttons)

    def build_polls_view_buttons(self, back_action="") -> InlineKeyboardMarkup:
        add_group_poll_button = util.build_button("Add Group Poll", GROUP_SUBJECT, ADD_POLL, self.gid)
        remove_group_poll_button = util.build_button("Remove Group Poll", GROUP_SUBJECT, REMOVE_POLL, self.gid)
        buttons = [[add_group_poll_button], [remove_group_poll_button]]
        if back_action:
            back_button = util.build_button("Back", GROUP_SUBJECT, back_action, self.gid)
            buttons.append([back_button])
        return InlineKeyboardMarkup(buttons)

    def build_polls_text_and_buttons(self, filters: list, filter_out=False, action="", back_action="") -> tuple:
        if filter_out:
            polls = [poll for poll in filters if poll.get_poll_id() not in self.get_poll_ids()]
        else:
            polls = [poll for poll in filters if poll.get_poll_id() in self.get_poll_ids()]

        back_button = util.build_button("Back", GROUP_SUBJECT, back_action, self.gid)

        if not polls:
            return "", InlineKeyboardMarkup([[back_button]])

        response = "\n\n".join(f"{i}. {poll.generate_linked_summary(True)}" for i, poll in enumerate(polls, 1))
        buttons = [[util.build_button(poll.get_title(), GROUP_SUBJECT,
                                      f"{action}_{poll.get_poll_id()}", self.gid)] for poll in polls]
        buttons.append([back_button])

        return response, InlineKeyboardMarkup(buttons)

    def build_settings_buttons(self, is_owner=False) -> InlineKeyboardMarkup:
        if is_owner:
            change_password_button = util.build_button("Change Password", GROUP_SUBJECT, CHANGE_SECRET, self.gid)
            delete_group_button = util.build_button("Delete Group", GROUP_SUBJECT, DELETE, self.gid)
            buttons = [[change_password_button], [delete_group_button]]
        else:
            leave_group_button = util.build_button("Leave Group", GROUP_SUBJECT, LEAVE_GROUP, self.gid)
            buttons = [[leave_group_button]]
        back_button = util.build_button("Back", GROUP_SUBJECT, BACK, self.gid)
        buttons.append([back_button])
        return InlineKeyboardMarkup(buttons)

    def build_delete_confirmation_buttons(self, delete_text="Delete", delete_action="", back_action="") \
            -> InlineKeyboardMarkup:
        yes_button = util.build_button(delete_text, GROUP_SUBJECT, f"{DELETE_YES}_{delete_action}", self.gid)
        no_button = util.build_button("No", GROUP_SUBJECT, back_action, self.gid)
        buttons = [[yes_button, no_button]]
        return InlineKeyboardMarkup(buttons)

    def to_json(self) -> dict:
        return {
            db.GROUP_ID: self.gid,
            db.GROUP_NAME: self.name,
            db.GROUP_OWNER: self.owner,
            db.GROUP_PASSWORD: self.password,
            db.GROUP_MEMBER_IDS: list(self.member_ids),
            db.GROUP_POLL_IDS: list(self.poll_ids),
            db.GROUP_LIST_IDS: list(self.list_ids),
            db.GROUP_CREATED_DATE: self.created_date.isoformat()
        }


class Poll(object):
    def __init__(self, poll_id: str, title: str, uid: int, description: str, options: list, single_response: bool,
                 message_details: set, expiry: int, created_date: datetime) -> None:
        self.poll_id = poll_id
        self.creator_id = uid
        self.title = title
        self.description = description
        self.options = options
        self.single_response = single_response
        self.message_details = message_details
        self.expiry = expiry
        self.created_date = created_date

    @staticmethod
    def get_poll_by_id(poll_id: str):
        return poll_storage.get(poll_id, None)

    @staticmethod
    def get_polls_by_ids(poll_ids: set, filters="") -> list:
        poll_lists = [Poll.get_poll_by_id(poll_id) for poll_id in poll_ids]
        return [poll for poll in poll_lists if filters.lower() in poll.get_title().lower()]

    @classmethod
    def create_new(cls, title: str, uid: int, description: str, option_titles: list):
        poll_id = util.generate_random_id(POLL_ID_LENGTH, set(poll_storage.keys()))
        poll = cls(poll_id, title, uid, description, list(), True, set(), EXPIRY, datetime.now())

        for option_title in option_titles:
            poll.add_option(Option.create_new(option_title))

        poll_storage[poll_id] = poll
        return poll

    @classmethod
    def load(cls, poll_id: str, title: str, uid: int, description: str, options: list, single_response: bool,
             message_details: list, expiry: int, created_date: str) -> None:
        poll = cls(poll_id, title, uid, description, list(), single_response, set(message_details),
                   expiry, datetime.fromisoformat(created_date))

        for option_data in options:
            poll.add_option(Option.load(
                option_data.get(db.OPTION_TITLE, ""),
                option_data.get(db.OPTION_COMMENT_REQUIRED, False),
                option_data.get(db.OPTION_RESPONDENTS, [])
            ))

        poll_storage[poll_id] = poll
        return

    def delete(self) -> None:
        poll_storage.pop(self.poll_id, None)

    def get_creator_id(self) -> int:
        return self.creator_id

    def get_poll_id(self) -> str:
        return self.poll_id

    def get_title(self) -> str:
        return self.title

    def set_title(self, title: str) -> None:
        self.title = title

    def get_description(self) -> str:
        return self.description

    def set_description(self, description: str) -> None:
        self.description = description

    def get_options(self) -> list:
        return self.options

    def add_option(self, option) -> None:
        self.options.append(option)

    def get_message_details(self) -> set:
        return self.message_details

    def add_message_details(self, mid: str) -> None:
        self.message_details.add(mid)

    def has_message_details(self, mid: str) -> bool:
        return mid in self.message_details

    def is_single_response(self) -> bool:
        return self.single_response

    def set_single_response(self, single_response: bool) -> None:
        self.single_response = single_response

    def toggle_response_type(self) -> str:
        # if any(option.has_votes() for option in self.options):
        #     return "Cannot change response type for non-empty poll."
        self.single_response = not self.single_response
        status = "single response" if self.single_response else "multi-response"
        return f"Response type is changed to {status}."

    def get_created_date(self) -> datetime:
        return self.created_date

    def get_expiry(self) -> int:
        return self.expiry

    def set_expiry(self, expiry: int) -> None:
        self.expiry = expiry

    def get_poll_hash(self) -> str:
        return f"{self.poll_id}_{util.simple_hash(self.title, self.poll_id, variance=False)}"

    def toggle(self, opt_id: int, uid: int, user_profile: dict, comment="") -> str:
        if opt_id >= len(self.options):
            return "Sorry, invalid option."

        if self.single_response:
            for i, option in enumerate(self.options):
                if i != opt_id:
                    option.remove_user(uid)
        return self.options[opt_id].toggle(uid, user_profile, comment)

    def is_voted_by_user(self, opt_id: int, uid: int):
        if opt_id < len(self.options):
            return self.options[opt_id].is_voted_by_user(uid)
        return False

    def edit_user_comment(self, opt_id: int, uid: int, comment: str) -> str:
        if opt_id >= len(self.options):
            return "Sorry, invalid option."
        option = self.options[opt_id]
        if not option.is_voted_by_user(uid):
            return "You need to vote for this option first before adding comments."
        option.edit_user_comment(uid, comment)
        return ""

    def toggle_comment_requirement(self, opt_id: int) -> str:
        if opt_id >= len(self.options):
            return "Sorry, invalid option."
        return self.options[opt_id].toggle_comment_requirement()

    def is_user_comment_required(self, opt_id: int, uid: int) -> bool:
        if opt_id >= len(self.options):
            return False
        return self.options[opt_id].is_user_comment_required(uid)

    def get_respondent_count(self) -> int:
        all_respondents_uid = set(uid for option in self.options for uid in option.get_respondents())
        return len(all_respondents_uid)

    def generate_respondents_summary(self) -> str:
        respondents_count = self.get_respondent_count()
        if respondents_count == 0:
            summary = "Nobody responded"
        elif respondents_count == 1:
            summary = "1 person responded"
        else:
            summary = f"{respondents_count} people responded"
        return summary

    def generate_linked_summary(self, include_creator=False) -> str:
        short_bold_title = util.make_html_bold(self.title)[:60]
        header = [f"{short_bold_title} ({self.get_respondent_count()} {EMOJI_PEOPLE})"]
        creator = [f"{EMOJI_CROWN} {User.get_user_by_id(self.creator_id).get_name()}"]
        link = [f"/poll_{self.poll_id}"]
        return "\n".join(header + creator + link) if include_creator else "\n".join(header + link)

    def generate_options_summary(self) -> str:
        return " / ".join(option.get_title() for option in self.options)

    def render_text(self) -> str:
        title = util.make_html_bold(self.title)
        description = util.make_html_italic(self.description)
        header = [f"{title}\n{description}" if description else title]
        body = [option.render_text() for option in self.options]
        footer = [f"{EMOJI_PEOPLE} {self.generate_respondents_summary()}"]
        return "\n\n".join(header + body + footer)

    def build_option_buttons(self) -> InlineKeyboardMarkup:
        buttons = []
        for i, option in enumerate(self.options):
            if option.is_comment_required():
                option_button = util.build_switch_button(
                    option.get_title(), f"/vote {self.get_poll_hash()}_{i}", to_self=True
                )
            else:
                option_button = util.build_button(option.get_title(), POLL_SUBJECT, str(i), self.poll_id)
            buttons.append([option_button])
        edit_comments_button = util.build_switch_button(
            "Comment", f"/comment {self.get_poll_hash()}", to_self=True
        )
        refresh_button = util.build_button("Refresh", POLL_SUBJECT, REFRESH_OPT, self.poll_id)
        buttons.append([edit_comments_button, refresh_button])
        return InlineKeyboardMarkup(buttons)

    def build_admin_buttons(self, uid: int) -> InlineKeyboardMarkup:
        publish_button = util.build_switch_button("Publish", self.title)
        customise_button = util.build_button("Customise", POLL_SUBJECT, CUSTOMISE, self.poll_id)
        refresh_button = util.build_button("Refresh", POLL_SUBJECT, REFRESH, self.poll_id)
        close_button = util.build_button("Close", POLL_SUBJECT, CLOSE, self.poll_id)

        if uid == self.creator_id:
            delete_button = util.build_button("Delete", POLL_SUBJECT, DELETE, self.poll_id)
            buttons = [[publish_button], [customise_button], [delete_button], [refresh_button, close_button]]
        else:
            buttons = [[publish_button], [customise_button], [refresh_button, close_button]]
        return InlineKeyboardMarkup(buttons)

    def build_customise_buttons(self) -> InlineKeyboardMarkup:
        response_text = "Multi-Response" if self.single_response else "Single Response"
        toggle_response_button = util.build_button(f"Change to {response_text}", POLL_SUBJECT, RESPONSE, self.poll_id)
        enforce_comments_button = util.build_button("Change Comment Requirements", POLL_SUBJECT, COMMENT, self.poll_id)
        back_button = util.build_button("Back", POLL_SUBJECT, BACK, self.poll_id)
        buttons = [[toggle_response_button], [enforce_comments_button], [back_button]]
        return InlineKeyboardMarkup(buttons)

    def build_option_comment_required_buttons(self) -> InlineKeyboardMarkup:
        buttons = []
        for i, option in enumerate(self.options):
            button_text = option.get_title() + (" (required)" if option.is_comment_required() else "")
            option_button = util.build_button(button_text, POLL_SUBJECT, f"{COMMENT}_{i}", self.poll_id)
            buttons.append([option_button])
        back_button = util.build_button("Back", POLL_SUBJECT, BACK, self.poll_id)
        buttons.append([back_button])
        return InlineKeyboardMarkup(buttons)

    def build_delete_confirmation_buttons(self) -> InlineKeyboardMarkup:
        yes_button = util.build_button("Delete", POLL_SUBJECT, DELETE_YES, self.poll_id)
        no_button = util.build_button("No", POLL_SUBJECT, BACK, self.poll_id)
        buttons = [[yes_button, no_button]]
        return InlineKeyboardMarkup(buttons)

    def build_option_comment_text_and_buttons(self, uid: int) -> tuple:
        buttons = []
        for i, option in enumerate(self.options):
            if option.is_voted_by_user(uid):
                option_button = util.build_button(
                    option.get_title(), POLL_SUBJECT, f"{EDIT_COMMENT}_{i}", self.poll_id
                )
                buttons.append([option_button])

        if buttons:
            response = util.make_html_bold("Select the option to add or change your comment.")
        else:
            response = util.make_html_italic("You have to vote first before you can enter a comment.")

        close_button = util.build_button("Close", POLL_SUBJECT, CLOSE, self.poll_id)
        buttons.append([close_button])

        return response, InlineKeyboardMarkup(buttons)

    def build_single_button(self, text: str, action: str):
        button = util.build_button(text, POLL_SUBJECT, action, self.poll_id)
        return InlineKeyboardMarkup([[button]])

    def to_json(self) -> dict:
        return {
            db.POLL_ID: self.poll_id,
            db.POLL_TITLE: self.title,
            db.POLL_CREATOR_ID: self.creator_id,
            db.POLL_DESCRIPTION: self.description,
            db.POLL_OPTIONS: [option.to_json() for option in self.options],
            db.POLL_SINGLE_RESPONSE: self.single_response,
            db.POLL_MESSAGE_DETAILS: list(self.message_details),
            db.POLL_EXPIRY: self.expiry,
            db.POLL_CREATED_DATE: self.created_date.isoformat()
        }


class Option(object):
    def __init__(self, title: str, is_comment_required: bool, respondents: list) -> None:
        self.title = title
        self.comment_required = is_comment_required
        self.respondents = OrderedDict(respondents)

    @classmethod
    def create_new(cls, title: str, is_comment_required=False):
        return cls(title, is_comment_required, list())

    @classmethod
    def load(cls, title: str, is_comment_required: bool, respondents: list):
        return cls(title, is_comment_required, respondents)

    def get_title(self) -> str:
        return self.title

    def is_comment_required(self) -> bool:
        return self.comment_required

    def is_user_comment_required(self, uid: int) -> bool:
        return self.comment_required and uid not in self.respondents

    def is_voted_by_user(self, uid: int) -> bool:
        return uid in self.respondents

    def get_respondents(self) -> OrderedDict:
        return self.respondents

    def has_votes(self) -> bool:
        return len(self.respondents) > 0

    def get_user_comment(self, uid: int) -> str:
        if uid not in self.respondents:
            return "No comment."
        _, _, comment = self.respondents[uid]
        return comment if comment else "No comment."

    def edit_user_comment(self, uid: int, comment: str) -> None:
        if uid not in self.respondents:
            return
        first_name, last_name, _ = self.respondents[uid]
        self.respondents[uid] = first_name, last_name, comment

    def toggle(self, uid: int, user_profile: dict, comment="") -> str:
        if uid in self.respondents:
            self.respondents.pop(uid, None)
            action = "removed from"
        else:
            self.respondents[uid] = user_profile.get("first_name", ""), user_profile.get("last_name", ""), comment
            action = "added to"
        return f"You are {action} {self.title}!"
    
    def remove_user(self, uid: int) -> None:
        if uid in self.respondents:
            self.respondents.pop(uid)

    def toggle_comment_requirement(self) -> str:
        self.comment_required = not self.comment_required
        action = "now requires comments" if self.comment_required else "no longer requires comments"
        return f"Option '{self.title}' {action}."

    def generate_namelist(self) -> str:
        namelist = []
        for first_name, last_name, comment in self.respondents.values():
            name = first_name
            if last_name:
                name += f" {last_name}"
            if comment:
                name += f" ({comment})"
            namelist.append(name)
        return "\n".join(namelist)

    def render_text(self) -> str:
        title = util.make_html_bold(self.title)
        if self.respondents:
            title += f" ({len(self.respondents)} {EMOJI_PEOPLE})"
        namelist = util.strip_html_symbols(self.generate_namelist())
        return f"{title}\n{namelist}"

    def to_json(self) -> dict:
        return {
            db.OPTION_TITLE: self.title,
            db.OPTION_COMMENT_REQUIRED: self.comment_required,
            db.OPTION_RESPONDENTS: list(self.respondents.items())
        }


class List(object):
    def __init__(self, list_id: str, title: str, uid: int, description: str, options: list, choices: list,
                 single_response: bool, message_details: set, expiry: int, created_date: datetime) -> None:
        self.list_id = list_id
        self.title = title
        self.creator_id = uid
        self.description = description
        self.options = options
        self.choices = choices
        self.single_response = single_response
        self.message_details = message_details
        self.expiry = expiry
        self.created_date = created_date

    @staticmethod
    def get_list_by_id(list_id: str):
        return list_storage.get(list_id, None)

    @staticmethod
    def get_lists_by_ids(list_ids: set, filters="") -> list:
        list_lists = [List.get_list_by_id(list_id) for list_id in list_ids]
        return [_list for _list in list_lists if filters.lower() in _list.get_title().lower()]

    @classmethod
    def create_new(cls, title: str, uid: int, description: str, option_titles: list, choices: list):
        list_id = util.generate_random_id(LIST_ID_LENGTH, set(list_storage.keys()))
        _list = cls(list_id, title, uid, description, list(), choices, True, set(), EXPIRY, datetime.now())

        for option_title in option_titles:
            _list.add_option(ListOption.create_new(option_title))

        list_storage[list_id] = _list
        return _list

    @classmethod
    def load(cls, list_id: str, title: str, uid: int, description: str, options: list, choices: list,
             single_response: bool, message_details: list, expiry: int, created_date: str) -> None:
        _list = cls(list_id, title, uid, description, list(), choices, single_response, set(message_details),
                    expiry, datetime.fromisoformat(created_date))

        for option_data in options:
            option = ListOption.load(option_data.get(db.LIST_OPTION_TITLE, ""))
            for choice_id in option_data.get(db.LIST_OPTION_ALLOCATIONS, []):
                if _list.is_valid_choice(choice_id):
                    option.add_allocation(choice_id, _list.get_choice(choice_id))
            _list.add_option(option)

        list_storage[list_id] = _list
        return

    def delete(self) -> None:
        list_storage.pop(self.list_id, None)

    def get_creator_id(self) -> int:
        return self.creator_id

    def get_list_id(self) -> str:
        return self.list_id

    def get_title(self) -> str:
        return self.title

    def set_title(self, title: str) -> None:
        self.title = title

    def get_description(self) -> str:
        return self.description

    def set_description(self, description: str) -> None:
        self.description = description

    def get_options(self) -> list:
        return self.options

    def get_option(self, opt_id):
        return self.options[opt_id] if self.is_valid_option(opt_id) else None

    def add_option(self, option) -> None:
        self.options.append(option)

    def is_valid_option(self, opt_id: int) -> bool:
        return 0 <= opt_id < len(self.options)

    def get_choices(self) -> list:
        return self.choices

    def get_choice(self, choice_id: int) -> str:
        return self.choices[choice_id] if self.is_valid_choice(choice_id) else ""

    def is_valid_choice(self, choice_id: int) -> bool:
        return 0 <= choice_id < len(self.choices)

    def get_message_details(self) -> set:
        return self.message_details

    def add_message_details(self, mid: str) -> None:
        self.message_details.add(mid)

    def has_message_details(self, mid: str) -> bool:
        return mid in self.message_details

    def is_single_response(self) -> bool:
        return self.single_response

    def toggle_response_type(self) -> str:
        # if any(option.is_allocated() for option in self.options):
        #     return "Cannot change response type for non-empty list."
        self.single_response = not self.single_response
        status = "single response" if self.single_response else "multi-response"
        return f"Response type is changed to {status}."

    def get_created_date(self) -> datetime:
        return self.created_date

    def get_expiry(self) -> int:
        return self.expiry

    def set_expiry(self, expiry: int) -> None:
        self.expiry = expiry

    def get_list_hash(self) -> str:
        return f"{self.list_id}_{util.simple_hash(self.title, self.list_id, variance=False)}"

    def toggle(self, opt_id: int, choice_id: int) -> str:
        if not self.is_valid_option(opt_id) or not self.is_valid_choice(choice_id):
            return "Sorry, invalid option or choice."

        if self.single_response:
            for i, option in enumerate(self.options):
                if i != opt_id:
                    option.remove_allocation(choice_id)
        return self.options[opt_id].toggle(choice_id, self.get_choice(choice_id))

    def contains(self, opt_id: int, choice_id: int):
        if opt_id < len(self.options):
            return self.options[opt_id].contains(choice_id)
        return False

    def get_allocation_count(self) -> int:
        all_allocations_id = set(choice_id for option in self.options for choice_id in option.get_allocations())
        return len(all_allocations_id)

    def generate_allocations_summary(self) -> str:
        allocation_count = self.get_allocation_count()
        if allocation_count in (0, 1):
            summary = f"{allocation_count} person allocated out of {len(self.choices)}"
        else:
            summary = f"{allocation_count} people allocated out of {len(self.choices)}"
        return summary

    def generate_linked_summary(self, include_creator=False) -> str:
        short_bold_title = util.make_html_bold(self.title)[:60]
        header = [f"{short_bold_title} ({self.get_allocation_count()} {EMOJI_PEOPLE})"]
        creator = [f"{EMOJI_CROWN} {User.get_user_by_id(self.creator_id).get_name()}"]
        link = [f"/list_{self.list_id}"]
        return "\n".join(header + creator + link) if include_creator else "\n".join(header + link)

    def generate_options_summary(self) -> str:
        return " / ".join(option.get_title() for option in self.options)

    def render_text(self) -> str:
        title = util.make_html_bold(self.title)
        description = util.make_html_italic(self.description)
        header = [f"{title}\n{description}" if description else title]
        body = [option.render_text() for option in self.options]
        footer = [f"{EMOJI_PEOPLE} {self.generate_allocations_summary()}"]
        return "\n\n".join(header + body + footer)

    def build_update_buttons(self) -> InlineKeyboardMarkup:
        update_button = util.build_switch_button("Update", f"/update {self.get_list_hash()}", to_self=True)
        refresh_button = util.build_button("Refresh", LIST_SUBJECT, USER_REFRESH, self.list_id)
        buttons = [[update_button, refresh_button]]
        return InlineKeyboardMarkup(buttons)

    def build_option_buttons(self) -> InlineKeyboardMarkup:
        buttons = []
        for i, option in enumerate(self.options):
            option_button = util.build_button(option.get_title(), LIST_SUBJECT, f"{OPTION}_{i}", self.list_id)
            buttons.append([option_button])
        refresh_button = util.build_button("Refresh", LIST_SUBJECT, REFRESH_OPT, self.list_id)
        done_button = util.build_button("Done", LIST_SUBJECT, UPDATE_DONE, self.list_id)
        buttons.append([refresh_button, done_button])
        return InlineKeyboardMarkup(buttons)

    def build_admin_buttons(self, uid: int) -> InlineKeyboardMarkup:
        publish_button = util.build_switch_button("Publish", self.title)
        customise_button = util.build_button("Customise", LIST_SUBJECT, CUSTOMISE, self.list_id)
        refresh_button = util.build_button("Refresh", LIST_SUBJECT, REFRESH, self.list_id)
        close_button = util.build_button("Close", LIST_SUBJECT, CLOSE, self.list_id)

        if uid == self.creator_id:
            delete_button = util.build_button("Delete", LIST_SUBJECT, DELETE, self.list_id)
            buttons = [[publish_button], [customise_button], [delete_button], [refresh_button, close_button]]
        else:
            buttons = [[publish_button], [customise_button], [refresh_button, close_button]]
        return InlineKeyboardMarkup(buttons)

    def build_customise_buttons(self) -> InlineKeyboardMarkup:
        response_text = "Multi-Response" if self.single_response else "Single Response"
        toggle_response_button = util.build_button(f"Change to {response_text}", LIST_SUBJECT, RESPONSE, self.list_id)
        back_button = util.build_button("Back", LIST_SUBJECT, BACK, self.list_id)
        buttons = [[toggle_response_button], [back_button]]
        return InlineKeyboardMarkup(buttons)

    def build_choice_buttons(self, opt_id: int) -> InlineKeyboardMarkup:
        buttons = []
        for i, choice in enumerate(self.choices):
            choice_button = util.build_button(choice, LIST_SUBJECT, f"{CHOICE}_{opt_id}_{i}", self.list_id)
            buttons.append([choice_button])
        back_button = util.build_button("Back", LIST_SUBJECT, OPTIONS, self.list_id)
        buttons.append([back_button])
        return InlineKeyboardMarkup(buttons)

    def build_delete_confirmation_buttons(self) -> InlineKeyboardMarkup:
        yes_button = util.build_button("Delete", LIST_SUBJECT, DELETE_YES, self.list_id)
        no_button = util.build_button("No", LIST_SUBJECT, BACK, self.list_id)
        buttons = [[yes_button, no_button]]
        return InlineKeyboardMarkup(buttons)

    def build_single_button(self, text: str, action: str):
        button = util.build_button(text, LIST_SUBJECT, action, self.list_id)
        return InlineKeyboardMarkup([[button]])

    def to_json(self) -> dict:
        return {
            db.LIST_ID: self.list_id,
            db.LIST_TITLE: self.title,
            db.LIST_CREATOR_ID: self.creator_id,
            db.LIST_DESCRIPTION: self.description,
            db.LIST_OPTIONS: [option.to_json() for option in self.options],
            db.LIST_CHOICES: self.choices,
            db.LIST_SINGLE_RESPONSE: self.single_response,
            db.LIST_MESSAGE_DETAILS: list(self.message_details),
            db.LIST_EXPIRY: self.expiry,
            db.LIST_CREATED_DATE: self.created_date.isoformat()
        }


class ListOption(object):
    def __init__(self, title: str) -> None:
        self.title = title
        self.allocations = dict()

    @classmethod
    def create_new(cls, title: str):
        return cls(title)

    @classmethod
    def load(cls, title: str):
        return cls(title)

    def get_title(self) -> str:
        return self.title

    def contains(self, choice_id: int) -> bool:
        return choice_id in self.allocations

    def get_allocations(self) -> dict:
        return self.allocations

    def is_allocated(self) -> bool:
        return len(self.allocations) > 0

    def add_allocation(self, choice_id: int, name: str) -> None:
        self.allocations[choice_id] = name

    def remove_allocation(self, choice_id: int) -> None:
        if choice_id in self.allocations:
            self.allocations.pop(choice_id)

    def toggle(self, choice_id: int, choice_name: str) -> str:
        if choice_id in self.allocations:
            self.allocations.pop(choice_id, None)
            action = "removed from"
        else:
            self.allocations[choice_id] = choice_name
            action = "added to"
        return f"{choice_name} is {action} {self.title}!"

    def generate_namelist(self) -> str:
        return "\n".join(self.allocations.values())

    def render_text(self) -> str:
        title = util.make_html_bold(self.title)
        if self.allocations:
            title += f" ({len(self.allocations)} {EMOJI_PEOPLE})"
        namelist = util.strip_html_symbols(self.generate_namelist())
        return f"{title}\n{namelist}"

    def to_json(self) -> dict:
        return {
            db.LIST_OPTION_TITLE: self.title,
            db.LIST_OPTION_ALLOCATIONS: list(self.allocations)
        }


class FormatTextCode(object):
    FORMAT_TYPES = {"dg": "digit", "st": "string", "dt": "date"}
    FORMAT_TEXT_ERROR = "<b>Format Code Parse Error</b>"

    def __init__(self, format_text: str, format_codes: Dict[str, Tuple[str, str]]):
        self._format_text = format_text
        self._format_codes = format_codes

    @classmethod
    def create_new(cls, text: str):
        format_text, code, is_valid = FormatTextCode.parse_format_text(text)
        if not is_valid:
            return cls("", dict())
        return cls(format_text, code)

    @classmethod
    def load(cls, format_text: str, code: Dict[str, Lst[str]]):
        formatted_code = {label: tuple(format_details) for label, format_details in code.items()}
        return cls(format_text, formatted_code)

    @staticmethod
    def parse_format_text(format_string: str) -> Tuple[str, Union[Dict[str, Tuple[str, str]], None], bool]:
        format_codes = dict()

        all_matches = re.findall(r"%(st|dg|dt)(#\w+)?(\$\((?:.|\n)+?(?=\)\$)\)\$)?", format_string)
        for i, match in enumerate(all_matches, 1):
            format_type, label, default = match[0], match[1][1:], match[2][2:-2].strip()

            if not label:
                label = str(i)
            else:
                label_match = re.match(r"^[A-Za-z]\w{0,11}$", label)
                if not label_match:
                    return f"{FormatTextCode.FORMAT_TEXT_ERROR}\n" \
                           f"Invalid label <u>{label}</u> found.\n" \
                           f"<i>Labels must have up to 12 alphanumeric characters, including underscores, " \
                           f"and must start with a letter.</i>", \
                           None, False
                if label in format_codes:
                    return f"{FormatTextCode.FORMAT_TEXT_ERROR}\n" \
                           f"Duplicated <u>{label}</u> found.\n" \
                           f"<i>Labels must be unique.</i>", \
                           None, False

            # Digit type
            if format_type == "dg":
                default = default if default else "0"
                if not bool(re.match(r"^[+|-]?\d+$", default)):
                    return f"{FormatTextCode.FORMAT_TEXT_ERROR}\nDefault value for <u>{label}</u> is not a digit.", \
                           None, False
                else:
                    format_codes[label] = (format_type, default)
            # String type
            elif format_type == "st":
                format_codes[label] = (format_type, default)
            # Date type
            elif format_type == "dt":
                default = default if default else "0 %d/%m/%y"
                date_match = re.match(r"^([+|-]{0,3}[0-7])(\s+.+)?$", default)
                if not date_match:
                    return f"{FormatTextCode.FORMAT_TEXT_ERROR}\n" \
                           f"Default value for <u>{label}</u> is not in the correct date format.\n" \
                           f"<i>E.g. 1 %d/%m/%y</i>", \
                           None, False
                day, date_format = date_match.group(1), date_match.group(2)
                # Checks if all '+' or all '-'
                if len(day) > 1 and day[0] * (len(day) - 1) != day[:-1]:
                    return f"{FormatTextCode.FORMAT_TEXT_ERROR}\n" \
                           f"Default value for <u>{label}</u> is not in the correct date format.\n" \
                           f"<i>E.g. 1 %d/%m/%y</i>", \
                           None, False

                if not date_format:
                    format_codes[label] = (format_type, f"{day} %d/%m/%y")
                else:
                    # Verify if date time format is valid
                    try:
                        datetime.now().strftime(date_format.strip())
                    except ValueError:
                        return f"{FormatTextCode.FORMAT_TEXT_ERROR}\n" \
                               f"Default value for <u>{label}</u> is not in the correct date format.\n" \
                               f"<i>E.g. 1 %d/%m/%y</i>", \
                               None, False
                    format_codes[label] = (format_type, default)
            # Other types
            else:
                return f"{FormatTextCode.FORMAT_TEXT_ERROR}\nInvalid format type found: %{format_type}", None, False

        # Create replaced text
        for label in format_codes:
            format_string = re.sub(r"%(st|dg|dt)(#\w+)?(\$\((?:.|\n)+?(?=\)\$)\)\$)?",
                                   f"<u>{label}</u>", format_string, count=1)

        return format_string, format_codes, True

    @property
    def format_text(self) -> str:
        return self._format_text

    @property
    def format_codes(self) -> Dict[str, Tuple[str, str]]:
        return self._format_codes

    def display_format_details(self, label: str, format_details: Tuple[str, str]) -> str:
        format_type, default = format_details
        return f"<u>{label}</u> - <b>type</b> {self.FORMAT_TYPES.get(format_type, '')}\n<b>default</b> {default}"

    def convert_format_input(self, label: str, format_type: str, format_input: str) -> Tuple[str, bool]:
        if format_type == "dg":
            if not bool(re.match(r"^[+|-]?\d+$", format_input)):
                return f"{self.FORMAT_TEXT_ERROR}\nFormat input for <u>{label}</u> is not a digit.\n" \
                       f"<i>{format_input}</i>", False
            return format_input, True
        elif format_type == "st":
            return format_input, True
        elif format_type == "dt":
            date_match = re.match(r"^([+|-]{0,3})([0-7])(\s+.+)?$", format_input)
            if not date_match:
                return f"{self.FORMAT_TEXT_ERROR}\n" \
                       f"Format input for <u>{label}</u> is not in the correct date format.\n" \
                       f"<i>{format_input}</i>\n<i>E.g. 1 %d/%m/%y</i>", False
            week_offset_symbols, day, date_format = date_match.group(1), int(date_match.group(2)), date_match.group(3)
            # Checks if all '+' or all '-'
            if week_offset_symbols and week_offset_symbols[0] * len(week_offset_symbols) != week_offset_symbols:
                return f"{self.FORMAT_TEXT_ERROR}\n" \
                       f"Format input for <u>{label}</u> is not in the correct date format.\n" \
                       f"<i>{format_input}</i>\n<i>E.g. 1 %d/%m/%y</i>", False

            if not date_format:
                date_format = "%d/%m/%y"

            # Verify if date time format is valid
            try:
                datetime.now().strftime(date_format.strip())
            except ValueError:
                return f"{self.FORMAT_TEXT_ERROR}\n" \
                       f"Format input for <u>{label}</u> is not in the correct date format.\n" \
                       f"<i>{format_input}</i>\n<i>E.g. 1 %d/%m/%y</i>", False

            # Get the date offset
            week_offset = len(week_offset_symbols) * (1 if week_offset_symbols[0] == "+" else -1) \
                if week_offset_symbols else 0
            day = datetime.now().isoweekday() if day == 0 else day
            days_offset = (day - datetime.now().isoweekday()) + week_offset * 7
            new_date = datetime.now() + timedelta(days_offset)
            return new_date.strftime(date_format.strip()), True
        # Handle other format types as string for now
        else:
            return format_input, True

    def parse_single_format_input(self, label: str, format_input: str) -> Tuple[str, bool]:
        format_type, default = self.format_codes.get(label, ("", ""))

        # Handle non-existent label
        if not format_type:
            return f"{self.FORMAT_TEXT_ERROR}\nLabel <u>{label}</u> does not exist.", False

        # Checks if format input is multi-line
        multi_line_match = re.match(r"^(.*?)\$\(((?:.|\n)*?)(?=\)\$)\)\$(.*)$", format_input)
        if multi_line_match:
            head, middle, tail = multi_line_match.group(1), multi_line_match.group(2), multi_line_match.group(3)

            # Handle incorrect format
            if head or tail:
                return f"{self.FORMAT_TEXT_ERROR}\nMulti-line format input for <u>{label}</u> has excess " \
                       f"wrapping characters.\n<i>{format_input}</i>", False

            return self.convert_format_input(label, format_type, format_input)

        if not format_input:
            format_input = default

        return self.convert_format_input(label, format_type, format_input)

    def parse_format_inputs(self, format_inputs="", offset=0) -> Tuple[Union[Dict[str, str], str], bool]:
        labels = list(self.format_codes)

        # Find all single line, or multi-line demarcated by $(...)$
        all_matches = re.findall(r"(?:(?<=^)|(?<=\n))(.*?(?:\$\((?:.|\n)+?(?=\)\$)\)\$)?) *(?=$|\n)", format_inputs)
        all_matches = [match for match in all_matches if match]

        if len(all_matches) > len(labels):
            return f"{self.FORMAT_TEXT_ERROR}\nToo many format inputs. Only {len(labels)} required.", False

        # Parse each format input
        parsed_formats = dict()
        for i, match in enumerate(all_matches):
            # Removing leading and trailing spaces
            match = match.strip()

            # Use default value
            if match == ".":
                label, format_input = labels[i], self.format_codes[labels[i]][1]
            else:
                # Check for labels
                format_match = re.match(r"^(\w+)\s*=\s*((?:.|\n)*)$", match)
                # No label
                if not format_match:
                    label, format_input = labels[i], match
                # Have label
                else:
                    label, format_input = format_match.group(1), format_match.group(2)
                    # Convert label index to label name
                    if label.isdigit():
                        if 1 <= int(label) - offset <= len(labels):
                            label = labels[int(label) - offset - 1]
                        else:
                            return f"{self.FORMAT_TEXT_ERROR}\nLabel index out of range: <i>{label}</i>.", False

            # Handle any errors
            if label in parsed_formats:
                return f"{self.FORMAT_TEXT_ERROR}\nDuplicate values for <u>{label}</u> given.", False
            parsed_format, is_valid = self.parse_single_format_input(label, format_input)
            if not is_valid:
                return parsed_format, is_valid

            # Store parsed format into dictionary
            parsed_formats[label] = parsed_format
            continue

        # Parse remaining format inputs that were not given
        for label in labels:
            if label not in parsed_formats:
                parsed_format, is_valid = self.parse_single_format_input(label, self.format_codes[label][1])
                if not is_valid:
                    return parsed_format, is_valid
                parsed_formats[label] = parsed_format

        return parsed_formats, True

    def render_details(self):
        title = self.format_text
        body = util.list_to_indexed_list_string([
            self.display_format_details(label, format_details) for label, format_details in self.format_codes.items()
        ])

        if not title:
            return f"<i>None</i>"

        response = "\n\n".join([title] + [f"<b>Details</b>\n{body}"]) if body \
            else "\n\n".join([title] + [f"<b>Details</b>\n<i>None</i>"])
        return response

    def render_format_text(self, format_inputs="", offset=0) -> Tuple[str, bool]:
        parsed_format, is_valid = self.parse_format_inputs(format_inputs, offset)

        # Error parsing format input
        if not is_valid:
            return parsed_format, is_valid

        new_text = self.format_text

        # Replace label with corresponding values
        for label, value in parsed_format.items():
            new_text = re.sub(f"<u>{label}</u>", value, new_text, count=1)

        return new_text, True

    def to_json(self) -> dict:
        return {
            db.FORMAT_TEXT: self.format_text,
            db.FORMAT_CODES: self.format_codes
        }


class PollTemplate(object):
    def __init__(self, temp_id: str, name: str, formatted_title: FormatTextCode, formatted_description: FormatTextCode,
                 options: list, single_response: bool, creator_id: int) -> None:
        self._temp_id = temp_id
        self._name = name
        self._formatted_title = formatted_title
        self._formatted_description = formatted_description
        self._options = options
        self._is_single_response = single_response
        self._creator_id = creator_id

    @staticmethod
    def get_template_by_id(temp_id: str):
        return temp_poll_storage.get(temp_id, None)

    @staticmethod
    def get_templates_by_ids(temp_ids: set, filters="") -> list:
        template_lists = [PollTemplate.get_template_by_id(temp_id) for temp_id in temp_ids]
        return [template for template in template_lists if filters.lower() in template.name.lower()]

    @classmethod
    def create_new(cls, name: str, format_title: str, format_description: str, options: list, single_response: bool,
                   creator_id: int):
        temp_id = util.generate_random_id(POLL_ID_LENGTH, set(temp_poll_storage.keys()))
        formatted_title = FormatTextCode.create_new(format_title)
        formatted_description = FormatTextCode.create_new(format_description)
        template = cls(temp_id, name, formatted_title, formatted_description, options, single_response, creator_id)
        temp_poll_storage[temp_id] = template
        return template

    @classmethod
    def load(cls, temp_id: str, name: str, title: Dict[str, Dict[str, Lst[str]]],
             description: Dict[str, Dict[str, Lst[str]]], options: list, single_response: bool,
             creator_id: int) -> None:
        formatted_title = FormatTextCode.load(
            title.get(db.FORMAT_TEXT, ""),
            title.get(db.FORMAT_CODES, dict())
        )
        formatted_description = FormatTextCode.load(
            description.get(db.FORMAT_TEXT, ""),
            description.get(db.FORMAT_CODES, dict())
        )

        template = cls(temp_id, name, formatted_title, formatted_description, options, single_response, creator_id)
        temp_poll_storage[temp_id] = template
        return

    def delete(self) -> None:
        temp_poll_storage.pop(self._temp_id, None)

    @property
    def temp_id(self) -> str:
        return self._temp_id

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, new_name: str) -> None:
        self._name = new_name
        return

    @property
    def formatted_title(self) -> FormatTextCode:
        return self._formatted_title

    @formatted_title.setter
    def formatted_title(self, new_title: FormatTextCode) -> None:
        self._formatted_title = new_title
        return

    @property
    def formatted_description(self) -> FormatTextCode:
        return self._formatted_description

    @formatted_description.setter
    def formatted_description(self, new_description: FormatTextCode) -> None:
        self._formatted_description = new_description
        return

    @property
    def options(self) -> list:
        return self._options

    @property
    def is_single_response(self) -> bool:
        return self._is_single_response

    @property
    def creator_id(self) -> int:
        return self._creator_id

    def generate_linked_summary(self, include_creator=False) -> str:
        title = f"<b>{self.name} {EMOJI_POLL}</b>"
        creator = f"{EMOJI_CROWN} {User.get_user_by_id(self.creator_id).get_name()}"
        link = f"/ptemp_{self.temp_id}"
        return "\n".join([title] + [creator] + [link]) if include_creator else "\n".join([title] + [link])

    def render_text(self) -> str:
        header = f"<b>Poll Template ({self.name})</b>"
        title_body = f"<b>Title</b>\n{self.formatted_title.render_details()}"
        description_body = f"<b>Description</b>\n{self.formatted_description.render_details()}"
        options_body = f"<b>Options</b>\n{util.list_to_indexed_list_string(self.options)}"
        response_type_body = f"<b>Response Type</b> - {'Single' if self.is_single_response else 'Multiple'}"
        return "\n\n".join([header] + [title_body] + [description_body] + [options_body] + [response_type_body])

    def render_title_code(self) -> str:
        return f"<b>Title</b>\n{self.formatted_title.render_details()}"

    def render_description_code(self) -> str:
        return f"<b>Description</b>\n{self.formatted_description.render_details()}"

    def render_title(self, format_inputs="") -> Tuple[str, bool]:
        return self.formatted_title.render_format_text(format_inputs)

    def render_description(self, format_inputs="") -> Tuple[str, bool]:
        return self.formatted_description.render_format_text(format_inputs)

    def render_title_and_description(self, format_inputs="") -> Tuple[str, str, bool]:
        offset = len(self.formatted_title.format_codes)

        # Separate title and description format inputs using ".." as separator
        match = re.match(r"^((?:.|\n)*)(?:(?<=^)|(?<=\n))\.\.(?=$|\n)((?:.|\n)*)$", format_inputs)
        if not match:
            title_result, is_title_valid = self.formatted_title.render_format_text(format_inputs.strip())
            description_result, is_description_valid = self.formatted_description.render_format_text()
        else:
            title_result, is_title_valid = self.formatted_title.render_format_text(match.group(1).strip())
            description_result, is_description_valid = \
                self.formatted_description.render_format_text(match.group(2).strip(), offset=offset)

        if not is_title_valid:
            return title_result, "", False
        elif not is_description_valid:
            return description_result, "", False
        else:
            return title_result, description_result, True

    def build_main_buttons(self) -> InlineKeyboardMarkup:
        generate_poll_button = util.build_button("Generate Poll", TEMP_POLL_SUBJECT, POLL, self.temp_id)
        settings_buttons = util.build_button("Settings", TEMP_POLL_SUBJECT, SETTINGS, self.temp_id)
        close_button = util.build_button("Close", TEMP_POLL_SUBJECT, CLOSE, self.temp_id)
        buttons = [[generate_poll_button], [settings_buttons], [close_button]]
        return InlineKeyboardMarkup(buttons)

    def build_format_title_buttons(self) -> InlineKeyboardMarkup:
        title_code_button = util.build_button(
            "View Title Format Details", TEMP_POLL_SUBJECT, TEMP_TITLE_CODE, self.temp_id
        )
        continue_button = util.build_button("Continue", TEMP_POLL_SUBJECT, DONE, self.temp_id)
        cancel_button = util.build_button("Cancel", TEMP_POLL_SUBJECT, RESET, self.temp_id)
        buttons = [[title_code_button], [cancel_button, continue_button]]
        return InlineKeyboardMarkup(buttons)

    def build_format_description_buttons(self) -> InlineKeyboardMarkup:
        description_code_button = util.build_button(
            "View Description Format Details", TEMP_POLL_SUBJECT, TEMP_DESCRIPTION_CODE, self.temp_id
        )
        build_button = util.build_button("Create", TEMP_POLL_SUBJECT, DONE, self.temp_id)
        cancel_button = util.build_button("Cancel", TEMP_POLL_SUBJECT, RESET, self.temp_id)
        skip_button = util.build_button("Skip", TEMP_POLL_SUBJECT, SKIP, self.temp_id)
        buttons = [[description_code_button], [skip_button], [cancel_button, build_button]]
        return InlineKeyboardMarkup(buttons)

    def build_format_back_buttons(self, back_action: str):
        back_button = util.build_button("Back", TEMP_POLL_SUBJECT, back_action, self.temp_id)
        cancel_button = util.build_button("Cancel", TEMP_POLL_SUBJECT, RESET, self.temp_id)
        buttons = [[cancel_button, back_button]]
        return InlineKeyboardMarkup(buttons)

    def to_json(self) -> dict:
        return {
            db.TEMP_POLL_ID: self.temp_id,
            db.TEMP_POLL_NAME: self.name,
            db.TEMP_POLL_FORMATTED_TITLE: self.formatted_title.to_json(),
            db.TEMP_POLL_FORMATTED_DESCRIPTION: self.formatted_description.to_json(),
            db.TEMP_POLL_OPTIONS: self.options,
            db.TEMP_POLL_SINGLE_RESPONSE: self.is_single_response,
            db.TEMP_POLL_CREATOR_ID: self.creator_id,
        }


class BotManager(object):
    @staticmethod
    def is_admin(uid: int, admin_keys: list) -> bool:
        return util.encode(uid) in admin_keys

    @staticmethod
    def get_bot_token_hash(token: str, uid: int) -> str:
        return util.simple_hash(token, util.encode(uid), 32)

    @staticmethod
    def get_leader_token_hash(token: str, uid: int, name: str) -> str:
        return util.simple_hash(token, f"{util.encode(uid)}{name}", 32)

    @staticmethod
    def save_data() -> str:
        try:
            db.save(user_storage, db.USER_SHEET)
            db.save(group_storage, db.GROUP_SHEET)
            db.save(poll_storage, db.POLL_SHEET)
            db.save(list_storage, db.LIST_SHEET)
            db.save(temp_poll_storage, db.TEMP_POLL_SHEET)
            return "Data saved successfully."
        except (TypeError, json.JSONDecodeError) as error:
            return f"Error saving data: {error}"

    @staticmethod
    def load_data() -> str:
        try:
            users_data = db.load(db.USER_SHEET)
            for user_data in users_data:
                User.load(
                    user_data[db.USER_ID],
                    user_data[db.USER_FIRST_NAME],
                    user_data[db.USER_LAST_NAME],
                    user_data[db.USER_USERNAME],
                    user_data[db.USER_IS_LEADER],
                    user_data[db.USER_OWNED_GROUP_IDS],
                    user_data[db.USER_JOINED_GROUP_IDS],
                    user_data[db.USER_POLL_IDS],
                    user_data[db.USER_LIST_IDS],
                    user_data[db.USER_TEMP_POLL_IDS]
                )

            groups_data = db.load(db.GROUP_SHEET)
            for group_data in groups_data:
                Group.load(
                    group_data[db.GROUP_ID],
                    group_data[db.GROUP_NAME],
                    group_data[db.GROUP_OWNER],
                    group_data[db.GROUP_PASSWORD],
                    group_data[db.GROUP_MEMBER_IDS],
                    group_data[db.GROUP_POLL_IDS],
                    group_data[db.GROUP_LIST_IDS],
                    group_data[db.GROUP_CREATED_DATE],
                )

            polls_data = db.load(db.POLL_SHEET)
            for poll_data in polls_data:
                Poll.load(
                    poll_data[db.POLL_ID],
                    poll_data[db.POLL_TITLE],
                    poll_data[db.POLL_CREATOR_ID],
                    poll_data[db.POLL_DESCRIPTION],
                    poll_data[db.POLL_OPTIONS],
                    poll_data[db.POLL_SINGLE_RESPONSE],
                    poll_data[db.POLL_MESSAGE_DETAILS],
                    poll_data[db.POLL_EXPIRY],
                    poll_data[db.POLL_CREATED_DATE],
                )

            lists_data = db.load(db.LIST_SHEET)
            for list_data in lists_data:
                List.load(
                    list_data[db.LIST_ID],
                    list_data[db.LIST_TITLE],
                    list_data[db.LIST_CREATOR_ID],
                    list_data[db.LIST_DESCRIPTION],
                    list_data[db.LIST_OPTIONS],
                    list_data[db.LIST_CHOICES],
                    list_data[db.LIST_SINGLE_RESPONSE],
                    list_data[db.LIST_MESSAGE_DETAILS],
                    list_data[db.LIST_EXPIRY],
                    list_data[db.LIST_CREATED_DATE],
                )

            temp_polls_data = db.load(db.TEMP_POLL_SHEET)
            for temp_poll_data in temp_polls_data:
                PollTemplate.load(
                    temp_poll_data[db.TEMP_POLL_ID],
                    temp_poll_data[db.TEMP_POLL_NAME],
                    temp_poll_data[db.TEMP_POLL_FORMATTED_TITLE],
                    temp_poll_data[db.TEMP_POLL_FORMATTED_DESCRIPTION],
                    temp_poll_data[db.TEMP_POLL_OPTIONS],
                    temp_poll_data[db.TEMP_POLL_SINGLE_RESPONSE],
                    temp_poll_data[db.TEMP_POLL_CREATOR_ID]
                )

            return "Data loaded successfully."
        except (TypeError, json.JSONDecodeError) as error:
            return f"Error loading data: {error}"

    @staticmethod
    def build_access_request_text_and_buttons() -> tuple:
        response = f"Which access to you want to grant?"
        buttons = util.build_multiple_buttons_markup(
            util.generate_button_details("Bot Access", BOT_ACCESS),
            util.generate_button_details("Bot Leader Access", PROMOTE),
            util.generate_button_details("Close", CLOSE)
        )
        return response, buttons

    @staticmethod
    def build_bot_access_enrol_text_and_button(uid: int) -> tuple:
        response = f"Click the button below to send a unique invitation to your friend to access the bot."
        buttons = util.build_multiple_buttons_markup(
            util.generate_button_details("Send Bot Invite", f"/enrol {uid}", True),
            util.generate_button_details("Close", CLOSE)
        )
        return response, buttons

    @staticmethod
    def build_invite_text_and_button(token: str, uid: int) -> tuple:
        invitation = f"You are invited to have access to <b>@{BOT_NAME}</b>!"
        buttons = util.build_multiple_buttons_markup(
            util.generate_button_details(
                "Get Access",  f"/access {BotManager.get_bot_token_hash(token, uid)}", is_switch=True, to_self=True
            ),
            util.generate_button_details("Close", CLOSE)
        )
        return invitation, buttons

    @staticmethod
    def build_leader_promote_invite_text_and_button() -> tuple:
        response = f"Who do you want to promote to a bot leader?"

        buttons = []
        for user in sorted(user_storage.values(), key=lambda u: u.get_name().lower()):
            if not user.is_leader():
                invite_button = util.build_button(user.get_name(), USER_SUBJECT, PROMOTE, util.encode(user.get_uid()))
                buttons.append([invite_button])
        close_button = InlineKeyboardButton("Close", callback_data=CLOSE)
        buttons.append([close_button])
        return response, InlineKeyboardMarkup(buttons)
