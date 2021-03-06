import os
import json
import gspread
from gspread import Worksheet
from oauth2client.service_account import ServiceAccountCredentials

# region DATABASE SETTINGS

# Scope of application
scopes = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
          "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
json_creds = os.getenv("GOOGLE_SHEETS_CREDS_JSON")

creds_dict = json.loads(json_creds)
creds_dict["private_key"] = creds_dict["private_key"].replace("\\\\n", "\n")
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scopes)
client = gspread.authorize(creds)

# endregion

# region SHEET SETTINGS

# Spreadsheets
database_spreadsheet = client.open_by_key("1Qd__kBpgbE6CqxbX30q4QulHAl0hiiRoEeTJxhmyQXI")
users_sheet = database_spreadsheet.worksheet("User Data")
groups_sheet = database_spreadsheet.worksheet("Group Data")
polls_sheet = database_spreadsheet.worksheet("Poll Data")
lists_sheet = database_spreadsheet.worksheet("List Data")
temp_polls_sheet = database_spreadsheet.worksheet("Poll Template Data")
temp_lists_sheet = database_spreadsheet.worksheet("List Template Data")

# User database fields
USER_SHEET = "user"
USER_ID = "uid"
USER_FIRST_NAME = "first_name"
USER_LAST_NAME = "last_name"
USER_USERNAME = "username"
USER_IS_LEADER = "is_leader"
USER_OWNED_GROUP_IDS = "owned_group_ids"
USER_JOINED_GROUP_IDS = "joined_group_ids"
USER_POLL_IDS = "poll_ids"
USER_LIST_IDS = "list_ids"
USER_TEMP_POLL_IDS = "temp_poll_ids"
USER_TEMP_LIST_IDS = "temp_list_ids"
USER_FIELDS = [
    USER_ID, USER_FIRST_NAME, USER_LAST_NAME, USER_USERNAME, USER_IS_LEADER, USER_OWNED_GROUP_IDS,
    USER_JOINED_GROUP_IDS, USER_POLL_IDS, USER_LIST_IDS, USER_TEMP_POLL_IDS, USER_TEMP_LIST_IDS
]

# Group database fields
GROUP_SHEET = "group"
GROUP_ID = "gid"
GROUP_NAME = "name"
GROUP_OWNER = "owner"
GROUP_PASSWORD = "password"
GROUP_MEMBER_IDS = "member_ids"
GROUP_POLL_IDS = "poll_ids"
GROUP_LIST_IDS = "list_ids"
GROUP_TEMP_IDS = "temp_ids"
GROUP_CREATED_DATE = "created_date"
GROUP_FIELDS = [
    GROUP_ID, GROUP_NAME, GROUP_OWNER, GROUP_PASSWORD, GROUP_MEMBER_IDS,
    GROUP_POLL_IDS, GROUP_LIST_IDS, GROUP_TEMP_IDS, GROUP_CREATED_DATE
]

# Poll database fields
POLL_SHEET = "poll"
POLL_ID = "poll_id"
POLL_TITLE = "title"
POLL_CREATOR_ID = "creator_id"
POLL_DESCRIPTION = "description"
POLL_OPTIONS = "options"
POLL_SINGLE_RESPONSE = "is_single_response"
POLL_MESSAGE_DETAILS = "message_details"
POLL_EXPIRY = "expiry"
POLL_CREATED_DATE = "created_date"
POLL_FIELDS = [
    POLL_ID, POLL_TITLE, POLL_CREATOR_ID, POLL_DESCRIPTION, POLL_OPTIONS, POLL_SINGLE_RESPONSE,
    POLL_MESSAGE_DETAILS, POLL_EXPIRY, POLL_CREATED_DATE
]

# Option fields
OPTION_TITLE = "title"
OPTION_COMMENT_REQUIRED = "comment_required"
OPTION_RESPONDENTS = "respondents"
OPTION_FIELDS = [OPTION_TITLE, OPTION_COMMENT_REQUIRED, OPTION_RESPONDENTS]

# List database fields
LIST_SHEET = "list"
LIST_ID = "list_id"
LIST_TITLE = "title"
LIST_CREATOR_ID = "creator_id"
LIST_DESCRIPTION = "description"
LIST_OPTIONS = "options"
LIST_CHOICES = "choices"
LIST_SINGLE_RESPONSE = "is_single_response"
LIST_MESSAGE_DETAILS = "message_details"
LIST_EXPIRY = "expiry"
LIST_CREATED_DATE = "created_date"
LIST_FIELDS = [
    LIST_ID, LIST_TITLE, LIST_CREATOR_ID, LIST_DESCRIPTION, LIST_OPTIONS, LIST_CHOICES,
    LIST_SINGLE_RESPONSE, LIST_MESSAGE_DETAILS, LIST_EXPIRY, LIST_CREATED_DATE
]

# List option fields
LIST_OPTION_TITLE = "title"
LIST_OPTION_ALLOCATIONS = "allocations"
LIST_OPTION_FIELDS = [LIST_OPTION_TITLE, LIST_OPTION_ALLOCATIONS]

# Poll template database fields
TEMP_POLL_SHEET = "temp_poll"
TEMP_POLL_ID = "temp_id"
TEMP_POLL_NAME = "name"
TEMP_POLL_DESCRIPTION = "description"
TEMP_POLL_TITLE_FORMAT = "title_format"
TEMP_POLL_DESCRIPTION_FORMAT = "description_format"
TEMP_POLL_OPTIONS = "options"
TEMP_POLL_SINGLE_RESPONSE = "is_single_response"
TEMP_POLL_CREATOR_ID = "creator_id"
TEMP_POLL_FIELDS = [
    TEMP_POLL_ID, TEMP_POLL_NAME, TEMP_POLL_DESCRIPTION, TEMP_POLL_TITLE_FORMAT, TEMP_POLL_DESCRIPTION_FORMAT,
    TEMP_POLL_OPTIONS, TEMP_POLL_SINGLE_RESPONSE, TEMP_POLL_CREATOR_ID
]

# List template database fields
TEMP_LIST_SHEET = "temp_list"
TEMP_LIST_ID = "temp_id"
TEMP_LIST_NAME = "name"
TEMP_LIST_DESCRIPTION = "description"
TEMP_LIST_TITLE_FORMAT = "title_format"
TEMP_LIST_DESCRIPTION_FORMAT = "description_format"
TEMP_LIST_OPTIONS = "options"
TEMP_LIST_CHOICES = "choices"
TEMP_LIST_SINGLE_RESPONSE = "is_single_response"
TEMP_LIST_CREATOR_ID = "creator_id"
TEMP_LIST_FIELDS = [
    TEMP_LIST_ID, TEMP_LIST_NAME, TEMP_LIST_DESCRIPTION, TEMP_LIST_TITLE_FORMAT, TEMP_LIST_DESCRIPTION_FORMAT,
    TEMP_LIST_OPTIONS, TEMP_LIST_CHOICES, TEMP_LIST_SINGLE_RESPONSE, TEMP_LIST_CREATOR_ID
]

# Format text code fields
FORMAT_TEXT = "format_text"
FORMAT_CODES = "format_codes"
FORMAT_TEXT_CODE_FIELDS = [FORMAT_TEXT, FORMAT_CODES]


# endregion


# Currently implementing lazy saving and loading
def save(data: dict, sheet_name: str) -> None:
    """Saves data to be stored into the database"""
    if sheet_name == USER_SHEET:
        return save_to_sheet(data, users_sheet, USER_FIELDS)
    elif sheet_name == GROUP_SHEET:
        return save_to_sheet(data, groups_sheet, GROUP_FIELDS)
    elif sheet_name == POLL_SHEET:
        return save_to_sheet(data, polls_sheet, POLL_FIELDS)
    elif sheet_name == LIST_SHEET:
        return save_to_sheet(data, lists_sheet, LIST_FIELDS)
    elif sheet_name == TEMP_POLL_SHEET:
        return save_to_sheet(data, temp_polls_sheet, TEMP_POLL_FIELDS)
    elif sheet_name == TEMP_LIST_SHEET:
        return save_to_sheet(data, temp_lists_sheet, TEMP_LIST_FIELDS)
    else:
        return


def save_to_sheet(data: dict, sheet: Worksheet, headers: list) -> None:
    all_values = [headers]
    for data_values in data.values():
        row_data = data_values.to_json()
        row_values = [json.dumps(row_data.get(field, "")) for field in headers]
        all_values.append(row_values)
    # Clear rows
    sheet.clear()
    sheet.insert_rows(all_values, row=1, value_input_option="RAW")
    sheet.resize(rows=len(all_values))
    return


def load(sheet_name: str) -> list:
    """Loads stored data from the database as a list of dictionary."""
    if sheet_name == USER_SHEET:
        return load_from_sheet(users_sheet, USER_FIELDS)
    elif sheet_name == GROUP_SHEET:
        return load_from_sheet(groups_sheet, GROUP_FIELDS)
    elif sheet_name == POLL_SHEET:
        return load_from_sheet(polls_sheet, POLL_FIELDS)
    elif sheet_name == LIST_SHEET:
        return load_from_sheet(lists_sheet, LIST_FIELDS)
    elif sheet_name == TEMP_POLL_SHEET:
        return load_from_sheet(temp_polls_sheet, TEMP_POLL_FIELDS)
    elif sheet_name == TEMP_LIST_SHEET:
        return load_from_sheet(temp_lists_sheet, TEMP_LIST_FIELDS)
    else:
        return list()


def load_from_sheet(sheet: Worksheet, headers: list) -> list:
    all_values = sheet.get_all_records(numericise_ignore=["all"])
    data = []
    for row_values in all_values:
        row_data = {field: json.loads(row_values[field]) for field in headers}
        data.append(row_data)
    return data
