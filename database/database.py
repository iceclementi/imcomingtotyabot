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
ballots_sheet = database_spreadsheet.worksheet("Ballot Data")
temp_polls_sheet = database_spreadsheet.worksheet("Poll Template Data")
temp_ballots_sheet = database_spreadsheet.worksheet("Ballot Template Data")

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
USER_BALLOT_IDS = "ballot_ids"
USER_TEMP_POLL_IDS = "temp_poll_ids"
USER_TEMP_BALLOT_IDS = "temp_ballot_ids"
USER_FIELDS = [
    USER_ID, USER_FIRST_NAME, USER_LAST_NAME, USER_USERNAME, USER_IS_LEADER, USER_OWNED_GROUP_IDS,
    USER_JOINED_GROUP_IDS, USER_POLL_IDS, USER_BALLOT_IDS, USER_TEMP_POLL_IDS, USER_TEMP_BALLOT_IDS
]

# Group database fields
GROUP_SHEET = "group"
GROUP_ID = "gid"
GROUP_NAME = "name"
GROUP_OWNER = "owner"
GROUP_PASSWORD = "password"
GROUP_MEMBER_IDS = "member_ids"
GROUP_POLL_IDS = "poll_ids"
GROUP_BALLOT_IDS = "ballot_ids"
GROUP_TEMP_IDS = "temp_ids"
GROUP_CREATED_DATE = "created_date"
GROUP_FIELDS = [
    GROUP_ID, GROUP_NAME, GROUP_OWNER, GROUP_PASSWORD, GROUP_MEMBER_IDS,
    GROUP_POLL_IDS, GROUP_BALLOT_IDS, GROUP_TEMP_IDS, GROUP_CREATED_DATE
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
BALLOT_SHEET = "ballot"
BALLOT_ID = "list_id"
BALLOT_TITLE = "title"
BALLOT_CREATOR_ID = "creator_id"
BALLOT_DESCRIPTION = "description"
BALLOT_OPTIONS = "options"
BALLOT_CHOICES = "choices"
BALLOT_SINGLE_RESPONSE = "is_single_response"
BALLOT_MESSAGE_DETAILS = "message_details"
BALLOT_EXPIRY = "expiry"
BALLOT_CREATED_DATE = "created_date"
BALLOT_FIELDS = [
    BALLOT_ID, BALLOT_TITLE, BALLOT_CREATOR_ID, BALLOT_DESCRIPTION, BALLOT_OPTIONS, BALLOT_CHOICES,
    BALLOT_SINGLE_RESPONSE, BALLOT_MESSAGE_DETAILS, BALLOT_EXPIRY, BALLOT_CREATED_DATE
]

# List option fields
BALLOT_OPTION_TITLE = "title"
BALLOT_OPTION_ALLOCATIONS = "allocations"
BALLOT_OPTION_FIELDS = [BALLOT_OPTION_TITLE, BALLOT_OPTION_ALLOCATIONS]

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
TEMP_BALLOT_SHEET = "temp_list"
TEMP_BALLOT_ID = "temp_id"
TEMP_BALLOT_NAME = "name"
TEMP_BALLOT_DESCRIPTION = "description"
TEMP_BALLOT_TITLE_FORMAT = "title_format"
TEMP_BALLOT_DESCRIPTION_FORMAT = "description_format"
TEMP_BALLOT_OPTIONS = "options"
TEMP_BALLOT_CHOICES = "choices"
TEMP_BALLOT_SINGLE_RESPONSE = "is_single_response"
TEMP_BALLOT_CREATOR_ID = "creator_id"
TEMP_BALLOT_FIELDS = [
    TEMP_BALLOT_ID, TEMP_BALLOT_NAME, TEMP_BALLOT_DESCRIPTION, TEMP_BALLOT_TITLE_FORMAT, TEMP_BALLOT_DESCRIPTION_FORMAT,
    TEMP_BALLOT_OPTIONS, TEMP_BALLOT_CHOICES, TEMP_BALLOT_SINGLE_RESPONSE, TEMP_BALLOT_CREATOR_ID
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
    elif sheet_name == BALLOT_SHEET:
        return save_to_sheet(data, ballots_sheet, BALLOT_FIELDS)
    elif sheet_name == TEMP_POLL_SHEET:
        return save_to_sheet(data, temp_polls_sheet, TEMP_POLL_FIELDS)
    elif sheet_name == TEMP_BALLOT_SHEET:
        return save_to_sheet(data, temp_ballots_sheet, TEMP_BALLOT_FIELDS)
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
    elif sheet_name == BALLOT_SHEET:
        return load_from_sheet(ballots_sheet, BALLOT_FIELDS)
    elif sheet_name == TEMP_POLL_SHEET:
        return load_from_sheet(temp_polls_sheet, TEMP_POLL_FIELDS)
    elif sheet_name == TEMP_BALLOT_SHEET:
        return load_from_sheet(temp_ballots_sheet, TEMP_BALLOT_FIELDS)
    else:
        return list()


def load_from_sheet(sheet: Worksheet, headers: list) -> list:
    all_values = sheet.get_all_records(numericise_ignore=["all"])
    data = []
    for row_values in all_values:
        row_data = {field: json.loads(row_values[field]) for field in headers}
        data.append(row_data)
    return data
