"""Backend models"""
from datetime import datetime
from collections import OrderedDict
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
import util

# Settings
POLL_ID_LENGTH = 4
GROUP_ID_LENGTH = 3
MAX_GROUPS_PER_USER = 10
MAX_GROUP_SIZE = 50
EMOJI_PEOPLE = "\U0001f465"
SESSION_EXPIRY = 1  # In hours
POLL_EXPIRY = 720
BOT_NAME = "tyacountmeintbot"

# Session Progress types
NONE = "none"
TITLE = "title"
OPTION = "option"

# Button actions
PUBLISH = "publish"
REFRESH = "refresh"
REFRESH_OPT = "refresh-opt"
CUSTOMISE = "custom"
RESPONSE = "response"
COMMENT = "comment"
VOTE = "vote"
DELETE = "delete"
DELETE_YES = "delete-yes"
BACK = "back"

all_users = dict()
all_groups = dict()
all_sessions = dict()
temp_polls = dict()
all_polls = dict()


class User(object):
    def __init__(self, uid: int, first_name: str, last_name: str, username: str) -> None:
        self.uid = uid
        self.first_name = first_name
        self.last_name = last_name
        self.username = username
        self.is_group_owner = True
        self.group_ids = set()
        self.poll_ids = set()

    @staticmethod
    def get_user_by_id(uid: int):
        return all_users.get(uid, None)

    @classmethod
    def register(cls, uid: int, first_name: str, last_name="", username=""):
        user = cls(uid, first_name, last_name, username)
        all_users[uid] = user
        return user

    def get_name(self):
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name

    def get_group_ids(self) -> set:
        return self.groups

    def get_groups(self, filters="", limit=10) -> list:
        user_groups = [Group.get_group_by_id(gid) for gid in self.group_ids]
        filtered_groups = [group for group in user_groups if filters.lower() in group.get_name().lower()]
        return sorted(filtered_groups, key=lambda group: group.get_name().lower(), reverse=True)[:limit]

    def create_group(self, name: str) -> str:
        if any(group.get_name() == name for group in self.get_groups(limit=MAX_GROUPS_PER_USER)):
            return "You already have a group with the same name."
        if len(self.group_ids) >= MAX_GROUPS_PER_USER:
            return f"The maximum number of groups per user ({MAX_GROUPS_PER_USER}) has been reached."
        group = Group.create_new(name, self.uid)
        self.group_ids.add(group.get_gid())
        return f"Group {util.make_html_bold(name)} created!"

    def delete_group(self, gid: str) -> str:
        if gid not in self.group_ids:
            return "You do not own that group."
        self.group_ids.remove(gid)
        group = Group.get_group_by_id(gid)
        group.delete()
        return f"Group {util.make_html_bold(group.get_name())} has been deleted."

    def get_polls(self, filters="", limit=50) -> list:
        user_polls = [Poll.get_poll_by_id(poll_id) for poll_id in self.poll_ids]
        filtered_polls = [poll for poll in user_polls if filters.lower() in poll.get_title.lower()]
        return sorted(filtered_polls, key=lambda poll: poll.get_title.lower(), reverse=True)[:limit]

    def create_poll(self, title: str, options: list) -> tuple:
        poll = Poll.create_new(self.uid, title, options)
        self.poll_ids.add(poll.get_poll_id())
        return poll, f"Poll {util.make_html_bold(title)} created!"

    def delete_poll(self, poll_id: str) -> str:
        if poll_id not in self.poll_ids:
            return "No such poll exists."
        self.poll_ids.remove(poll_id)
        poll = Poll.get_poll_by_id(poll_id)
        poll.delete()
        return f"Poll {util.make_html_bold(poll.get_title())} has been deleted."


class Group(object):
    def __init__(self, gid: str, name: str, uid: int, password: str) -> None:
        self.gid = gid
        self.name = name
        self.owner = uid
        self.password = password
        self.member_ids = set()
        self.poll_ids = set()

    @staticmethod
    def get_group_by_id(gid: str):
        return all_groups.get(gid, None)

    @classmethod
    def create_new(cls, name: str, uid: int, password=""):
        gid = util.generate_random_id(GROUP_ID_LENGTH, set(all_groups.keys()))
        group = cls(gid, name, uid, password)
        all_groups[gid] = group
        return group

    def delete(self) -> None:
        all_groups.pop(self.gid, None)

    def get_gid(self) -> str:
        return self.gid

    def edit_name(self, new_name: str) -> None:
        self.name = new_name

    def edit_password(self, new_password: str) -> None:
        self.password = new_password

    def get_member_ids(self) -> set:
        return self.member_ids

    def add_member(self, uid: int) -> str:
        if uid in self.members:
            return "You are already in the group."
        if len(self.members) >= MAX_GROUP_SIZE:
            return f"The group size limit ({MAX_GROUP_SIZE}) has been reached."
        self.member_ids.add(uid)
        return f"You have joined {util.make_html_bold(self.name)}."

    def remove_member(self, uid: int) -> str:
        if uid not in self.members:
            return "The user is not in the group."
        self.member_ids.remove(uid)
        name = User.get_user_by_id(uid).get_name()
        return f"{name} has been removed from the group."

    def get_poll_ids(self) -> set:
        return self.polls

    def add_poll(self, poll_id: str, poll_title: str) -> str:
        if poll_id in self.poll_ids:
            return "The poll already exists in the group."
        self.poll_ids.add(poll_id)
        return f"Poll \"{poll_title}\" added into the group."

    def remove_poll(self, poll_id: str) -> str:
        if poll_id in self.poll_ids:
            return "The poll is not in the group."
        self.poll_ids.remove(poll_id)
        title = Poll.get_poll_by_id(poll_id).get_title()
        return f"Poll \"{title}\" has been removed from the group."

    def generate_group_summary(self):
        pass

    def generate_group_members_summary(self):
        pass

    def generate_group_polls_summary(self):
        pass


class Session(object):
    def __init__(self, uid: int) -> None:
        self.uid = uid
        self.progress = TITLE
        self.poll_id = ""
        self.start_date = datetime.now()
        self.expiry = SESSION_EXPIRY

    def get_progress(self) -> str:
        return self.progress

    def set_progress(self, state: str) -> None:
        self.progress = state

    def get_poll_id(self) -> str:
        return self.poll_id

    def set_poll_id(self, poll_id: str) -> None:
        self.poll_id = poll_id

    def get_start_date(self) -> datetime:
        return self.start_date

    def get_expiry(self) -> int:
        return self.expiry

    def set_expiry(self, expiry: int) -> None:
        self.expiry = expiry

    def end_session(self) -> None:
        all_sessions.pop(self.uid)
        all_polls[self.poll_id] = temp_polls.pop(self.poll_id)

    def reset_session(self):
        self.progress = TITLE
        self.start_date = datetime.now()
        poll = Poll.get_temp_poll_by_id(self.poll_id)
        if poll:
            poll.reset_poll()
        else:
            self.poll_id = Poll.create_new_temp_poll(self.uid)

    @staticmethod
    def start_new_session(uid: int) -> None:
        session = Session.get_session_by_id(uid)
        if not session:
            session = Session(uid)
            session.set_poll_id(Poll.create_new_temp_poll(uid))
            all_sessions[uid] = session
        else:
            session.reset_session()

    @staticmethod
    def get_session_by_id(uid: int):
        return all_sessions.get(uid, None)


class Poll(object):
    def __init__(self, uid: int, poll_id: str, title: str) -> None:
        self.creator_id = uid
        self.poll_id = poll_id
        self.title = title
        self.options = []
        self.message_details = set()
        self.single_response = True
        self.created_date = datetime.now()
        self.expiry = POLL_EXPIRY

    @staticmethod
    def get_poll_by_id(poll_id: str):
        return all_polls.get(poll_id, None)

    @classmethod
    def create_new(cls, uid: int, title: str, option_titles: list):
        poll_id = util.generate_random_id(POLL_ID_LENGTH, set(all_polls.keys()))
        poll = cls(uid, poll_id, title)

        for option_title in option_titles:
            poll.add_option(Option.create_new(option_title))

        all_polls[poll_id] = poll
        return poll

    def delete(self) -> None:
        all_polls.pop(self.poll_id, None)

    def get_creator_id(self) -> int:
        return self.creator_id

    def get_poll_id(self) -> str:
        return self.poll_id

    def get_title(self) -> str:
        return self.title

    def set_title(self, title: str) -> None:
        self.title = title

    def get_options(self) -> list:
        return self.options

    def add_option(self, option) -> None:
        self.options.append(option)

    def get_all_message_details(self) -> set:
        return self.message_details

    def add_message_details(self, mid: str, cid: str) -> None:
        self.message_details.add((mid, cid))

    def has_message_details(self, mid: str) -> bool:
        return any(mid == message_id for message_id, _ in self.message_details)

    def is_single_response(self) -> bool:
        return self.single_response

    def toggle_response_type(self) -> str:
        if any(option.has_votes() for option in self.options):
            return "Cannot change response type for non-empty poll."
        self.single_response = not self.single_response
        status = "single response" if self.single_response else "multi-response"
        return f"Response type is changed to {status}."

    def get_created_date(self) -> datetime:
        return self.created_date

    def get_expiry(self) -> int:
        return self.expiry

    def set_expiry(self, expiry: int) -> None:
        self.expiry = expiry

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

    def generate_respondents_summary(self) -> str:
        all_respondents_uid = set(uid for option in self.options for uid in option.respondents)
        respondents_count = len(all_respondents_uid)
        if respondents_count == 0:
            summary = "Nobody responded"
        elif respondents_count == 1:
            summary = "1 person responded"
        else:
            summary = f"{respondents_count} people responded"
        return summary

    def generate_linked_summary(self) -> str:
        short_bold_title = [util.make_html_bold(self.title)[:60]]
        respondents_summary = [f"({self.generate_respondents_summary()})"]
        link = [f"/poll_{self.poll_id}"]
        return "\n".join(short_bold_title + respondents_summary + link)

    def generate_options_summary(self) -> str:
        return " / ".join(option.title for option in self.options)

    def render_text(self) -> str:
        header = [util.make_html_bold_first_line(self.title)]
        body = [option.render_text() for option in self.options]
        footer = [f"{EMOJI_PEOPLE} {self.generate_respondents_summary()}"]
        return "\n\n".join(header + body + footer)

    def build_option_buttons(self, mid: int, is_admin=False) -> InlineKeyboardMarkup:
        buttons = []
        for i, option in enumerate(self.options):
            option_button = util.build_button(option.get_title(), self.poll_id, str(i))
            buttons.append([option_button])
        edit_comments_button = util.build_switch_button(
            "Comment", f"/comment_{self.poll_id}_{util.encode(mid)} ", to_self=True
        )
        refresh_button = util.build_button("Refresh", self.poll_id, REFRESH_OPT)
        buttons.append([edit_comments_button, refresh_button])
        test_button = util.build_button("Test", self.poll_id, "test")  # TESTING ONLY!!!
        buttons.append([test_button])  # TESTING ONLY!!!
        if is_admin:
            back_button = util.build_button("Back", self.poll_id, BACK)
            buttons.append([back_button])
        return InlineKeyboardMarkup(buttons)

    def build_admin_buttons(self) -> InlineKeyboardMarkup:
        publish_button = util.build_switch_button("Publish", self.title)
        refresh_button = util.build_button("Refresh", self.poll_id, REFRESH)
        customise_button = util.build_button("Customise", self.poll_id, CUSTOMISE)
        vote_button = util.build_button("Vote", self.poll_id, VOTE)
        delete_button = util.build_button("Delete", self.poll_id, DELETE)
        buttons = [[publish_button], [refresh_button], [customise_button], [vote_button, delete_button]]
        return InlineKeyboardMarkup(buttons)

    def build_customise_buttons(self) -> InlineKeyboardMarkup:
        response_text = "Multi-Response" if self.single_response else "Single Response"
        toggle_response_button = util.build_button(f"Change to {response_text}", self.poll_id, RESPONSE)
        enforce_comments_button = util.build_button("Change Comment Requirements", self.poll_id, COMMENT)
        back_button = util.build_button("Back", self.poll_id, BACK)
        buttons = [[toggle_response_button], [enforce_comments_button], [back_button]]
        return InlineKeyboardMarkup(buttons)

    def build_option_comment_buttons(self) -> InlineKeyboardMarkup:
        buttons = []
        for i, option in enumerate(self.options):
            button_text = option.get_title() + (" (required)" if option.is_comment_required() else "")
            option_button = util.build_button(button_text, self.poll_id, f"{COMMENT}-{i}")
            buttons.append([option_button])
        back_button = util.build_button("Back", self.poll_id, BACK)
        buttons.append([back_button])
        return InlineKeyboardMarkup(buttons)

    def build_delete_confirmation_buttons(self) -> InlineKeyboardMarkup:
        yes_button = util.build_button("Delete", self.poll_id, DELETE_YES)
        no_button = util.build_button("No", self.poll_id, BACK)
        buttons = [[yes_button, no_button]]
        return InlineKeyboardMarkup(buttons)


class Option(object):
    def __init__(self, title: str, is_comment_required: bool) -> None:
        self.title = title
        self.comment_required = is_comment_required
        self.respondents = OrderedDict()

    @classmethod
    def create_new(cls, title: str, is_comment_required=False):
        return cls(title, is_comment_required)

    def get_title(self) -> str:
        return self.title

    def is_comment_required(self) -> bool:
        return self.comment_required

    def is_user_comment_required(self, uid: int) -> bool:
        return self.comment_required and uid not in self.respondents

    def is_voted_by_user(self, uid: int) -> bool:
        return uid in self.respondents

    def has_votes(self) -> bool:
        return len(self.respondents) > 0

    def remove_user(self, uid: int) -> None:
        if uid in self.respondents:
            self.respondents.pop(uid)

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
