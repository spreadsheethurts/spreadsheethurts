from typing import Optional
import re

from .base import GsheetDateTimeAlikeBase, DatetimeDict, GsheetDateTime
from .date_alike import DateAlike
from .time_alike import TimeAlike

from wizard.utils.misc import roclassproperty


class DateTimeAlike(GsheetDateTimeAlikeBase):
    DATES: list[DateAlike] = DateAlike.find_leaf_classes().values()
    TIMES: list[TimeAlike] = TimeAlike.find_leaf_classes().values()

    @classmethod
    def is_space_at(cls, content: str, index: int) -> bool:
        """Checks if the character at a given index is a space."""
        if not (0 <= index < len(content)):
            return False

        return content[index] == " "

    @classmethod
    def is_comma_at(cls, content: str, index: int) -> bool:
        """Checks if the character at a given index is a comma."""
        if not (0 <= index < len(content)):
            return False

        return content[index] == ","

    @classmethod
    def is_valid_t_at(cls, content: str, index: int) -> bool:
        """Checks if 'T' at index is a valid separator (no surrounding spaces)."""
        return (
            0 < index < len(content)
            and content[index] == "T"
            and content[index - 1] != " "
            and (index + 1 < len(content) and content[index + 1] != " ")
        )

    @classmethod
    def maybe_iso8601(cls, content: str) -> Optional[DatetimeDict]:
        # The date features greedily capture letters for the month name, so this explicitly handles 'T' as a separator.
        if "T" in content:
            idxs = [i for i, c in enumerate(content) if c == "T"]
            for idx in idxs:
                if cls.is_valid_t_at(content, idx):
                    date_part, time_part = content[:idx], content[idx + 1 :]
                    for date in cls.DATES:
                        datedict = date.fullmatch(date_part)
                        if not datedict or not date.is_datetime_valid(**datedict):
                            continue

                        for time in cls.TIMES:
                            if (
                                timedict := time.fullmatch(time_part)
                            ) and time.is_datetime_valid(**timedict):
                                return datedict | timedict
        return None

    @classmethod
    def sep_is_comma_space(cls, content: str) -> Optional[DatetimeDict]:
        pat = re.compile(r", +")
        for matched in pat.finditer(content):
            date_part, time_part = (
                content[: matched.start()],
                content[matched.end() :],
            )
            # The required separator is a comma followed by a space (", ").
            # Formats like " , " (space-comma-space) or "," (comma alone) are invalid.
            if date_part.endswith(" "):
                continue

            for date in cls.DATES:
                datedict = date.fullmatch(date_part)
                if not datedict or not date.is_datetime_valid(**datedict):
                    continue
                for time in cls.TIMES:
                    if (
                        timedict := time.fullmatch(time_part)
                    ) and time.is_datetime_valid(**timedict):
                        return datedict | timedict
        return None

    @classmethod
    def sep_is_spaces(cls, content: str) -> Optional[DatetimeDict]:
        pat = re.compile(r" +")
        for matched in pat.finditer(content):
            date_part, time_part = (
                content[: matched.start()],
                content[matched.end() :],
            )

            for date in cls.DATES:
                datedict = date.fullmatch(date_part)
                if not datedict or not date.is_datetime_valid(**datedict):
                    continue
                for time in cls.TIMES:
                    if (
                        timedict := time.fullmatch(time_part)
                    ) and time.is_datetime_valid(**timedict):
                        return datedict | timedict
        return None

    @classmethod
    def fullmatch(cls, content: str) -> Optional[DatetimeDict]:

        if iso8601 := cls.maybe_iso8601(content):
            return iso8601

        if sep_is_comma_space := cls.sep_is_comma_space(content):
            return sep_is_comma_space

        if sep_is_spaces := cls.sep_is_spaces(content):
            return sep_is_spaces

        return None

    @classmethod
    def is_datetime_valid(cls, **kwargs: DatetimeDict) -> Optional[GsheetDateTime]:
        if not (date := DateAlike.is_datetime_valid(**kwargs)):
            return None
        if not (time := TimeAlike.is_datetime_valid(**kwargs)):
            return None
        return date + cls.to_delta(time)

    @roclassproperty
    def EXAMPLES(cls) -> list[str]:
        return (
            [
                f"{de} {te}"
                for date in cls.DATES
                for time in cls.TIMES
                for de in date.EXAMPLES
                for te in time.EXAMPLES
            ]
            + [
                f"{de.rstrip()}T{te.lstrip()}"
                for date in cls.DATES
                for time in cls.TIMES
                for de in date.EXAMPLES
                for te in time.EXAMPLES
            ]
            + [
                f"{de}, {te}"
                for date in cls.DATES
                for time in cls.TIMES
                for de in date.EXAMPLES
                for te in time.EXAMPLES
            ]
        )
