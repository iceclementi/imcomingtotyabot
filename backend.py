"""Backend models"""
from datetime import datetime
from collections import OrderedDict
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
import util

# Settings
POLL_ID_LENGTH = 4
GROUP_ID_LENGTH = 3
MAX_GROUPS_PER_USER = 10
MAX_JOINED_GROUPS_PER_USER = 30
MAX_GROUP_SIZE = 50
EMOJI_PEOPLE = "\U0001f465"
EMOJI_POLL = "\U0001f4ca"
EMOJI_CROWN = "\U0001f451"
SESSION_EXPIRY = 1  # In hours
POLL_EXPIRY = 720
BOT_NAME = "tyacountmeintbot"

# Button Actions
POLL_SUBJECT = "p"
GROUP_SUBJECT = "g"
PUBLISH = "publish"
REFRESH = "refresh"
REFRESH_OPT = "refreshOpt"
CUSTOMISE = "custom"
RESPONSE = "response"
COMMENT = "comment"
VOTE = "vote"
DELETE = "delete"
DELETE_YES = "delYes"
BACK = "back"
VIEW_MEMBERS = "members"
REMOVE_MEMBER = "delMember"
VIEW_GROUP_POLLS = "polls"
ADD_POLL = "poll"
REMOVE_POLL = "delPoll"
GROUP_SETTINGS = "set"
CHANGE_SECRET = "pass"
GROUP_INVITE = "invite"


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
        self.owned_group_ids = set()
        self.joined_group_ids = set()
        self.poll_ids = set()

    @staticmethod
    def get_user_by_id(uid: int):
        return all_users.get(uid, None)

    @classmethod
    def register(cls, uid: int, first_name: str, last_name="", username=""):
        user = cls(uid, first_name, last_name, username)
        all_users[uid] = user
        return user

    def get_uid(self) -> int:
        return self.uid

    def get_name(self) -> str:
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name

    def get_username(self) -> str:
        return self.username

    def get_owned_group_ids(self) -> set:
        return self.groups

    def get_owned_groups(self, filters="", limit=MAX_GROUPS_PER_USER) -> list:
        user_groups = [Group.get_group_by_id(gid) for gid in self.owned_group_ids]
        filtered_groups = [group for group in user_groups if filters.lower() in group.get_name().lower()]
        return sorted(filtered_groups, key=lambda group: group.get_name().lower())[:limit]

    def has_group_with_name(self, name: str) -> bool:
        return any(group.get_name() == name for group in self.get_owned_groups(limit=MAX_GROUPS_PER_USER))

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
        return f"Group {util.make_html_bold(group.get_name())} has been deleted."

    def get_joined_group_ids(self) -> set:
        return self.joined_group_ids

    def get_joined_groups(self, filters="", limit=MAX_JOINED_GROUPS_PER_USER) -> list:
        user_groups = [Group.get_group_by_id(gid) for gid in self.joined_group_ids]
        filtered_groups = [group for group in user_groups if filters.lower() in group.get_name().lower()]
        return sorted(filtered_groups, key=lambda group: group.get_name().lower())[:limit]

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

    def get_all_groups(self, filters="", limit=50) -> list:
        user_groups = [Group.get_group_by_id(gid) for gid in self.get_all_group_ids()]
        filtered_groups = [group for group in user_groups if filters.lower() in group.get_name().lower()]
        return sorted(filtered_groups, key=lambda group: group.get_name().lower())[:limit]

    def get_poll_ids(self) -> set:
        return self.poll_ids

    def get_polls(self, filters="", limit=50) -> list:
        user_polls = [Poll.get_poll_by_id(poll_id) for poll_id in self.poll_ids]
        filtered_polls = [poll for poll in user_polls if filters.lower() in poll.get_title().lower()]
        return sorted(filtered_polls, key=lambda poll: poll.get_created_date(), reverse=True)[:limit]

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

        # Delete poll from all user groups
        for group in self.get_all_groups():
            if poll_id in group.get_poll_ids():
                group.remove_poll(poll_id)

        return f"Poll {util.make_html_bold(poll.get_title())} has been deleted."

    def has_group_poll(self, poll_id: str) -> bool:
        return any(poll_id in group.get_poll_ids() for group in self.get_all_groups())

    def build_invite_text_and_buttons(self) -> tuple:
        if not self.owned_group_ids:
            return util.make_html_italic("You do not own any groups!"), None
        buttons = []
        for group in self.get_owned_groups():
            invite_button = util.build_switch_button(group.get_name(), f"/invite {group.get_name()}")
            buttons.append([invite_button])
        return "Which group's invite code do you want to send?", InlineKeyboardMarkup(buttons)

    def build_polls_text_and_buttons(self, filters=None, is_filter_away=False, limit=20,
                                     subject="", action="", identifier="", back_action="") -> tuple:
        if filters:
            polls = [poll for poll in self.get_polls() if poll.get_poll_id() not in filters][:limit] if is_filter_away \
                else [poll for poll in self.get_polls() if poll.get_poll_id() in filters][:limit]
        else:
            polls = self.get_polls()[:limit]

        back_button = util.build_button("Back", subject, back_action, identifier)

        if not polls:
            return util.make_html_italic(
                "You do not have any more polls to add to this group. You can use /poll to create new polls."
            ), InlineKeyboardMarkup([[back_button]])

        response = "\n\n".join(f"{i}. {poll.generate_linked_summary()}" for i, poll in enumerate(polls, 1))
        buttons = [[util.build_button(poll.get_title(), subject,
                                      f"{action}_{poll.get_poll_id()}", identifier)] for poll in polls]
        buttons.append([back_button])

        return response, InlineKeyboardMarkup(buttons)


class Group(object):
    def __init__(self, gid: str, name: str, uid: int, password: str) -> None:
        self.gid = gid
        self.name = name
        self.owner = uid
        self.password = password
        self.member_ids = {uid}
        self.poll_ids = set()
        self.created_date = datetime.now()

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
        if uid in self.members:
            return "You are already in the group."
        if len(self.members) >= MAX_GROUP_SIZE:
            return f"The group size limit ({MAX_GROUP_SIZE}) has been reached."
        self.member_ids.add(uid)
        User.get_user_by_id(uid).join_group(self.gid)
        return f"You have joined {util.make_html_bold(self.name)}."

    def remove_member(self, uid: int) -> str:
        if uid not in self.members:
            return "The user is not in the group."
        self.member_ids.remove(uid)
        user = User.get_user_by_id(uid)
        user.leave_group(self.gid)
        return f"{user.get_name()} has been removed from the group."

    def get_poll_ids(self) -> set:
        return self.poll_ids

    def get_polls(self, filters="", limit=50) -> list:
        group_polls = [Poll.get_poll_by_id(poll_id) for poll_id in self.poll_ids]
        filtered_polls = [poll for poll in group_polls if filters.lower() in poll.get_title().lower()]
        return sorted(filtered_polls, key=lambda poll: poll.get_created_date(), reverse=True)[:limit]

    def add_poll(self, poll_id: str, poll_title: str) -> str:
        if poll_id in self.poll_ids:
            return "The poll already exists in the group."
        self.poll_ids.add(poll_id)
        return f"Poll \"{poll_title}\" added into the group."

    def remove_poll(self, poll_id: str) -> str:
        if poll_id not in self.poll_ids:
            return "The poll is not in the group."
        self.poll_ids.remove(poll_id)
        title = Poll.get_poll_by_id(poll_id).get_title()
        return f"Poll \"{title}\" has been removed from the group."

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

    def generate_group_polls_list(self, limit=50) -> str:
        if not self.poll_ids:
            return util.make_html_italic("You have no group polls. Go ahead and add a poll into the group!")

        return "\n\n".join(poll.generate_linked_summary() for poll in self.get_polls(limit=limit))

    def render_group_details_text(self) -> str:
        title = util.make_html_bold(self.name)
        owner = f"{EMOJI_CROWN} {User.get_user_by_id(self.owner).get_name()}"
        header = [f"{title}\n{owner}"]

        member_count = f"{EMOJI_PEOPLE} {len(self.member_ids)}"
        poll_count = f"{EMOJI_POLL} {len(self.poll_ids)}"
        body = [f"{member_count: <8}{poll_count}"]

        footer = [util.make_html_italic(f"Created on: {util.format_date(self.created_date)}")]
        return "\n\n".join(header + body + footer)

    def render_group_members_text(self) -> str:
        title = util.make_html_bold(f"{self.name} Members")
        header = [f"{title} ({len(self.member_ids)} {EMOJI_PEOPLE})"]

        body = [self.generate_group_members_list()]
        return "\n\n".join(header + body)

    def render_group_polls_text(self) -> str:
        title = util.make_html_bold(f"{self.name} Polls")
        header = [f"{title} ({len(self.poll_ids)} {EMOJI_POLL})"]

        body = [self.generate_group_polls_list()]
        return "\n\n".join(header + body)

    def build_invite_text_and_button(self, owner_username: str) -> tuple:
        invitation = f"You are invited to join {owner_username}'s \"{self.name}\" group!"
        join_button = util.build_switch_button("Join Group", f"/join {self.get_password_hash()}", to_self=True)
        return invitation, InlineKeyboardMarkup([[join_button]])

    def build_group_details_buttons(self) -> InlineKeyboardMarkup:
        view_members_button = util.build_button("View Members", GROUP_SUBJECT, VIEW_MEMBERS, self.gid)
        view_polls_button = util.build_button("View Polls", GROUP_SUBJECT, VIEW_GROUP_POLLS, self.gid)
        settings_button = util.build_button("Settings", GROUP_SUBJECT, GROUP_SETTINGS, self.gid)
        buttons = [[view_members_button], [view_polls_button], [settings_button]]
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

    def build_delete_confirmation_buttons(self, delete_text="Delete", delete_action="", back_action="") \
            -> InlineKeyboardMarkup:
        yes_button = util.build_button(delete_text, GROUP_SUBJECT, f"{DELETE_YES}_{delete_action}", self.gid)
        no_button = util.build_button("No", GROUP_SUBJECT, back_action, self.gid)
        buttons = [[yes_button, no_button]]
        return InlineKeyboardMarkup(buttons)


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
            option_button = util.build_button(option.get_title(), POLL_SUBJECT, str(i), self.poll_id)
            buttons.append([option_button])
        edit_comments_button = util.build_switch_button(
            "Comment", f"/comment_{self.poll_id}_{util.encode(mid)} ", to_self=True
        )
        refresh_button = util.build_button("Refresh", POLL_SUBJECT, REFRESH_OPT, self.poll_id)
        buttons.append([edit_comments_button, refresh_button])
        test_button = util.build_button("Test", POLL_SUBJECT, "test", self.poll_id)  # TESTING ONLY!!!
        buttons.append([test_button])  # TESTING ONLY!!!
        if is_admin:
            back_button = util.build_button("Back", POLL_SUBJECT, BACK, self.poll_id)
            buttons.append([back_button])
        return InlineKeyboardMarkup(buttons)

    def build_admin_buttons(self) -> InlineKeyboardMarkup:
        publish_button = util.build_switch_button("Publish", self.title)
        refresh_button = util.build_button("Refresh", POLL_SUBJECT, REFRESH, self.poll_id)
        customise_button = util.build_button("Customise", POLL_SUBJECT, CUSTOMISE, self.poll_id)
        vote_button = util.build_button("Vote", POLL_SUBJECT, VOTE, self.poll_id)
        delete_button = util.build_button("Delete", POLL_SUBJECT, DELETE, self.poll_id)
        buttons = [[publish_button], [refresh_button], [customise_button], [vote_button, delete_button]]
        return InlineKeyboardMarkup(buttons)

    def build_customise_buttons(self) -> InlineKeyboardMarkup:
        response_text = "Multi-Response" if self.single_response else "Single Response"
        toggle_response_button = util.build_button(f"Change to {response_text}", POLL_SUBJECT, RESPONSE, self.poll_id)
        enforce_comments_button = util.build_button("Change Comment Requirements", POLL_SUBJECT, COMMENT, self.poll_id)
        back_button = util.build_button("Back", POLL_SUBJECT, BACK, self.poll_id)
        buttons = [[toggle_response_button], [enforce_comments_button], [back_button]]
        return InlineKeyboardMarkup(buttons)

    def build_option_comment_buttons(self) -> InlineKeyboardMarkup:
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
