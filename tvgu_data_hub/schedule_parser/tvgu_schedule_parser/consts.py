import re
from typing import TypeAlias, Literal, Final

GroupType: TypeAlias = Literal["master", "regular", "aspirantes"]

GROUP_TYPE_ASPIRANTES: Final[GroupType] = "aspirantes"
GROUP_TYPE_MASTERS: Final[GroupType] = "master"
# regular - это бакалавриат и специалитет
GROUP_TYPE_REGULAR: Final[GroupType] = "regular"

# Паттерны могут быть неточными: через время логика названий групп уточнится
GROUP_NAME_PARTS_DEFAULT: Final[tuple[str, ...]] = (
    "is_master_1", "course", "group_number", "is_master_2", "subgroup_letter", "note"
)
GROUP_NAME_DEFAULT_PATTERN: re.Pattern = re.compile(r"(М)?([0-9])([0-9])(М)?([а-яА-ЯеёЕЁ])?(?:\((.+)\))?")

GROUP_NAME_PARTS_ASPIRANTES: Final[tuple[str, ...]] = (
    "course", "group_number", "note", "subgroup_letter"
)
GROUP_NAME_ASPIRANTES_PATTERN: re.Pattern = re.compile(r"([0-9])([0-9]{2})(?:\(([0-9а-яА-ЯеёЕЁ]+)\))?(?:-(\w+))?")

WeekMark = Literal["every", "minus", "plus", "none"]

WEEK_MARK_EVERY: Final[WeekMark] = "every"
WEEK_MARK_PLUS: Final[WeekMark] = "plus"
WEEK_MARK_MINUS: Final[WeekMark] = "minus"
WEEK_MARK_NONE: Final[WeekMark] = "none"

SubjectType = Literal["lecture", "labwork", "practice", "seminar", "unknown"]

# Возможные типы предметов и их возможные фразы в названии предмета
SUBJECT_TYPES: Final[dict[SubjectType, list[str]]] = {
    "lecture": ["Лекция"],
    "labwork": ["Лаб. работа"],
    "practice": ["Практика", "Практическое занятие"],
    "seminar": ["Семинар"],
    "unknown": [],
}
