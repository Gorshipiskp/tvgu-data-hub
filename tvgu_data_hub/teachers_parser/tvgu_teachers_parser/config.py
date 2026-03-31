import re
from typing import Final

TEACHERS_TvGU_PAGE_URL: Final[str] = "https://tversu.ru/sveden/employees/pps/index.html"

TEACHER_FULLNAME_PATTERN: Final[re.Pattern] = re.compile(r"([a-zA-Zёа-яА-Я\-]+(?:\s+[a-zA-Zёа-яА-Я\-]*)?)"
                                                         r"\s+([a-zA-Zёа-яА-Я\-]+)\s+([a-zA-Zёа-яА-Я\-]+)")
TEACHER_NAME_PARTS: Final[tuple[str, ...]] = ("surname", "name", "patronymic")
DIGITS_PATTERN: Final[re.Pattern] = re.compile(r"(\d+)")
NON_DIGITS_PATTERN: Final[re.Pattern] = re.compile(r"\D")
