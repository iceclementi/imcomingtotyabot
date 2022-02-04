import os
import json
import gspread
from gspread import Worksheet
from oauth2client.service_account import ServiceAccountCredentials

from backend import User, Group, Poll

# region Database Settings

# Scope of application
scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
json_creds = os.getenv("GOOGLE_SHEETS_CREDS_JSON")

creds_dict = json.loads(json_creds)
creds_dict["private_key"] = creds_dict["private_key"].replace("\\\\n", "\n")
creds = ServiceAccountCredentials.from_json_keyfile_name(creds_dict, scopes)
client = gspread.authorize(creds)

# endregion

# region Sheet Settings

# Spreadsheets
users_sheet = client.open_by_key("1Qd__kBpgbE6CqxbX30q4QulHAl0hiiRoEeTJxhmyQXI").worksheet("User Data")

# User database fields
USER_SHEET = "user"
USER_ID = "uid"
USER_FIRST_NAME = "first_name"
USER_LAST_NAME = "last_name"
USER_USERNAME = "username"
USER_IS_GROUP_OWNER = "is_group_owner"
USER_OWNED_GROUP_IDS = "owned_group_ids"
USER_JOINED_GROUP_IDS = "joined_group_ids"
USER_POLL_IDS = "poll_ids"
USER_FIELDS = [
    USER_ID, USER_FIRST_NAME, USER_LAST_NAME, USER_USERNAME, USER_IS_GROUP_OWNER,
    USER_OWNED_GROUP_IDS, USER_JOINED_GROUP_IDS, USER_POLL_IDS
]

# endregion


# Currently implementing lazy saving and loading
def save(data: dict, sheet: str) -> None:
    if sheet == USER_SHEET:
        return save_users(data)
    else:
        return


def save_users(users: dict) -> None:
    all_values = [USER_FIELDS]
    for user in users.values():
        user_data = user.to_json()
        row_values = [json.dumps(user_data.get(field, "")) for field in USER_FIELDS]
        all_values.append(row_values)
    users_sheet.clear()
    users_sheet.insert_rows(all_values, row=1, value_input_option="RAW")
    return


def save_groups(data: dict) -> None:
    pass


def save_polls(data: dict) -> None:
    pass


def load(sheet: str) -> None:
    if sheet == USER_SHEET:
        return load_users()
    else:
        return


def load_users() -> None:
    all_values = users_sheet.get_all_records()
    for user_data in all_values:
        User.load(
            json.loads(user_data.get(USER_ID, "-1")),
            json.loads(user_data.get(USER_FIRST_NAME, "")),
            json.loads(user_data.get(USER_LAST_NAME, "")),
            json.loads(user_data.get(USER_USERNAME, "")),
            json.loads(user_data.get(USER_IS_GROUP_OWNER, "False")),
            json.loads(user_data.get(USER_OWNED_GROUP_IDS, "[]")),
            json.loads(user_data.get(USER_JOINED_GROUP_IDS, "[]")),
            json.loads(user_data.get(USER_POLL_IDS, "[]"))
        )
    return


def load_groups() -> None:
    pass


def load_polls() -> None:
    pass
