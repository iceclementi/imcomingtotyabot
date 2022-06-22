import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Union

from telebot.database import database as db
from telebot.models import constant as const
from telebot.utils import util


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
    def load(cls, format_text: str, code: Dict[str, List[str]]):
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
                date_match = re.match(r"^((?:\+{0,3}|-{0,3})[0-7])(\s+(?:.|\n)*)?$", default)
                if not date_match:
                    return f"{FormatTextCode.FORMAT_TEXT_ERROR}\n" \
                           f"Default value for <u>{label}</u> is not in the correct date format.\n" \
                           f"<i>E.g. 1 %d/%m/%y</i>", \
                           None, False

                day, date_format = date_match.group(1), date_match.group(2)
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
            format_string = re.sub(
                r"%(st|dg|dt)(#\w+)?(\$\((?:.|\n)+?(?=\)\$)\)\$)?",
                f"<u>{label}</u>", format_string, count=1
            )

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
            date_match = re.match(r"^(\+{0,3}|-{0,3})([0-7])(\s+(?:.|\n)*)?$", format_input)
            if not date_match:
                return f"{self.FORMAT_TEXT_ERROR}\n" \
                       f"Format input for <u>{label}</u> is not in the correct date format.\n" \
                       f"<i>{format_input}</i>\n<i>E.g. 1 %d/%m/%y</i>", False
            week_offset_symbols, day, date_format = date_match.group(1), int(date_match.group(2)), date_match.group(3)

            # Get the default date format if not given
            if not date_format:
                date_format = \
                    re.match(r"^(?:\+{0,3}|-{0,3})[0-7](\s+(?:.|\n)*)?$", self.format_codes[label][1]).group(1).strip()

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
            day = datetime.now(tz=const.tz).isoweekday() if day == 0 else day
            days_offset = (day - datetime.now(tz=const.tz).isoweekday()) + week_offset * 7
            new_date = datetime.now(tz=const.tz) + timedelta(days_offset)
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
        body = util.list_to_indexed_list_string(
            [
                self.display_format_details(label, format_details) for label, format_details in
                self.format_codes.items()
            ]
        )

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
            db.FORMAT_TEXT:  self.format_text,
            db.FORMAT_CODES: self.format_codes
        }
