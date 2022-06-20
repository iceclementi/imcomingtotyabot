"""Backend models"""
from __future__ import annotations

import pytz

# region SETTINGS

# Settings
POLL_ID_LENGTH = 4
BALLOT_ID_LENGTH = 4
GROUP_ID_LENGTH = 3
MAX_GROUPS_PER_USER = 10
MAX_JOINED_GROUPS_PER_USER = 30
MAX_GROUP_SIZE = 50
EMOJI_PEOPLE = "\U0001f465"
EMOJI_GROUP = "\U0001fac2"
EMOJI_POLL = "\U0001f4ca"
EMOJI_BALLOT = "\U0001f4dd"
EMOJI_TEMPLATE = "\U0001f4c3"
EMOJI_CROWN = "\U0001f451"
EMOJI_HAPPY = "\U0001f60a"
SESSION_EXPIRY = 1  # In hours
EXPIRY = 720
BOT_NAME = "imcomingtotyabot"
tz = pytz.timezone("Asia/Singapore")

# Button Actions
USER_SUBJECT = "u"
POLL_SUBJECT = "p"
BALLOT_SUBJECT = "b"
GROUP_SUBJECT = "g"
TEMP_POLL_SUBJECT = "tp"
TEMP_BALLOT_SUBJECT = "tb"
POLL = "poll"
BALLOT = "ballot"
GROUP = "group"
PUBLISH = "publish"
REFRESH = "refresh"
TITLE = "title"
DESCRIPTION = "descr"
OPTION = "opt"
OPTIONS = "opts"
CHOICE = "choice"
CHOICES = "choices"
NAME = "name"
USER_REFRESH = "userRefresh"
REFRESH_OPT = "refreshOpt"
RESPONSE = "response"
COMMENT = "comment"
EDIT_COMMENT = "editComment"
VOTE = "vote"
BACK = "back"
MEMBER = "mem"
SETTINGS = "set"
SECRET = "pass"
GROUP_INVITE = "invite"
LEAVE_GROUP = "leave"
BOT_ACCESS = "bot"
PROMOTE = "promote"
CLOSE = "close"
RESET = "reset"
DONE = "done"
SKIP = "skip"
SHOW = "show"
HIDE = "hide"
TEMPLATE = "temp"
TEMP_POLL = "tPoll"
TEMP_BALLOT = "tBallot"
TEMP_GUIDE = "guide"
TEMP_TITLE = "tTitle"
TEMP_DESCRIPTION = "tDescr"
TEMP_TITLE_CODE = "tTitleCode"
TEMP_DESCRIPTION_CODE = "tDescrCode"
EDIT = "edit"
RENAME = "rename"
ADD = "add"
VIEW = "view"
DELETE = "del"
DELETE_YES = "delYes"
RETURN = "return"
PAGE = "page"

# endregion
