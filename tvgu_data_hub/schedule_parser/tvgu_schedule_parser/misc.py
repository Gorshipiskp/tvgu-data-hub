import re
from dataclasses import dataclass
from json import JSONEncoder
from typing import Optional, TypeAlias

from aiohttp import ClientSession

from .config import REQUEST_TIMEOUT, SKIP_ASPIRANTES
from .consts import GROUP_TYPE_ASPIRANTES, GROUP_NAME_PARTS_ASPIRANTES, GroupType, GROUP_TYPE_MASTERS, \
    GROUP_TYPE_REGULAR, GROUP_NAME_ASPIRANTES_PATTERN, GROUP_NAME_DEFAULT_PATTERN, GROUP_NAME_PARTS_DEFAULT, WeekMark, \
    SubjectType, SUBJECT_TYPES


class SkipLessonException(Exception):
    pass


class UnHandlingGroupException(Exception):
    pass


class SkipAspirantesException(Exception):
    pass


class TimetableNotFoundException(Exception):
    pass


@dataclass(frozen=True, kw_only=True)
class GroupBase:
    """Базовый датакласс группы для хранения независимой информации"""

    origin_name: str
    note: Optional[str]
    course: Optional[int]
    type: GroupType
    number: int
    subgroup_letter: Optional[str]

    def _identify(self) -> tuple[str, int, GroupType, str]:
        return (
            self.origin_name,
            self.number,
            self.type,
            self.subgroup_letter
        )

    def __hash__(self) -> int:
        return hash(self._identify())

    def __eq__(self, other) -> bool:
        if isinstance(other, Group):
            return self._identify() == other._identify()
        return NotImplemented


@dataclass(frozen=True, kw_only=True)
class Group(GroupBase):
    """Датакласс группы с кодом (аббревиатурой) структуры (факультета/института)"""

    faculty_code: str


@dataclass(frozen=True, kw_only=True)
class LessonTime:
    """Датакласс для хранения времени пар (используется лишь в одном месте)"""

    start: int
    end: int


@dataclass(frozen=True, kw_only=True)
class TeacherSmall:
    """Датакласс для малого объёма информации о преподавателях"""

    initials: str
    role: str

    def _identify(self) -> tuple[str, str]:
        return (
            self.initials,
            self.role
        )

    def __hash__(self) -> int:
        return hash(self._identify())

    def __eq__(self, other) -> bool:
        if isinstance(other, TeacherSmall):
            return self._identify() == other._identify()
        return NotImplemented


@dataclass(frozen=True, kw_only=True)
class LessonBase:
    """Базовый датакласс пары для хранения независимой информации"""

    lesson_number: int
    week_day: int
    week_mark: WeekMark
    time_start: int
    time_end: int
    subgroup: Optional[str]


@dataclass(frozen=True, kw_only=True)
class Lesson(LessonBase):
    """Датакласс пары с указанием преподавателей, названия и типа предмета и места проведения"""

    teachers: tuple[TeacherSmall, ...]
    subject_name: Optional[str]
    subject_type: SubjectType
    place: str

    def _identify(self) -> tuple[WeekMark, int, int, SubjectType, Optional[str], Optional[str]]:
        return (
            self.week_mark,
            self.week_day,
            self.lesson_number,
            self.subject_type,
            self.subject_name,
            self.place
        )

    def __hash__(self) -> int:
        return hash(self._identify())

    def __eq__(self, other) -> bool:
        if isinstance(other, Lesson):
            return self._identify() == other._identify()
        return NotImplemented


AllGroupsSchedules = dict[str, dict[Group, Optional[tuple[Lesson]]]]


def group_type_checker(faculty_code: str, name_parts: dict[str, str]) -> GroupType:
    """Функция для проверки типа группы на основе частей названия"""

    if len(name_parts) == len(GROUP_NAME_PARTS_ASPIRANTES) or faculty_code == "АСП":
        return GROUP_TYPE_ASPIRANTES
    if name_parts.get("is_master_1") or name_parts.get("is_master_2"):
        return GROUP_TYPE_MASTERS
    return GROUP_TYPE_REGULAR


def parse_group_name(pattern: re.Pattern, pattern_parts: tuple[str, ...], faculty_code: str, group_body: str) -> Group:
    """Функция для разбора названия группы на части"""

    try:
        found: tuple[str, ...] = re.findall(pattern, group_body)[0]
    except IndexError as _:
        raise UnHandlingGroupException(f"Неизвестный шаблон группы: {group_body}")

    if len(found) != len(pattern_parts):
        raise ValueError(f"Неверный шаблон для группы: ({found=}; {pattern_parts=}; {group_body=})")

    parsed: dict[str, str] = dict(zip(pattern_parts, found))

    note: str = parsed["note"]

    return Group(
        origin_name=f"{faculty_code}-{group_body}",
        faculty_code=faculty_code,
        course=int(parsed.get("course")) if parsed.get("course") else None,
        number=int(parsed["group_number"]),
        note=note if note else None,
        type=group_type_checker(faculty_code, parsed),
        subgroup_letter=parsed.get("subgroup_letter") if parsed.get("subgroup_letter") else None,
    )


def parse_group_by_name(group_name: str) -> Group:
    """Автоматический парсер названия группы (без необходимости указывания паттерна)"""

    faculty_code, group_body = group_name.split("-", 1)

    if not faculty_code:
        raise ValueError(f"Факультет не определён для {group_name}")

    if faculty_code == "АСП":
        if SKIP_ASPIRANTES:
            raise SkipAspirantesException
        return parse_group_name(GROUP_NAME_ASPIRANTES_PATTERN, GROUP_NAME_PARTS_ASPIRANTES, faculty_code, group_body)
    else:
        return parse_group_name(GROUP_NAME_DEFAULT_PATTERN, GROUP_NAME_PARTS_DEFAULT, faculty_code, group_body)


async def fetch_json(session: ClientSession, url: str) -> dict:
    async with session.get(url, timeout=REQUEST_TIMEOUT) as response:
        return await response.json()


def determine_subject_type(subject_str: Optional[str]) -> SubjectType:
    """Функция для определения типа предмета"""

    if subject_str is not None:
        for subject_type, type_phrases in SUBJECT_TYPES.items():
            for phrase in type_phrases:
                if phrase.lower() in subject_str.lower():
                    return subject_type
    return "unknown"


def clean_subject_name(subject_str: Optional[str], subject_type: Optional[SubjectType]) -> Optional[str]:
    """Функция для очистки названия предмета от его типа"""

    if subject_str is None or subject_type is None:
        return None

    for subject_type_phrase in SUBJECT_TYPES[subject_type]:
        subject_str = re.sub(
            rf"\s*\({re.escape(subject_type_phrase)}\)\s*", "", subject_str,
            flags=re.IGNORECASE
        )

    return subject_str


def parse_teacher_name(teacher_str: str) -> list[tuple[str, str]]:
    """Функция для парсинга имен и ролей преподавателей"""

    teachers = re.findall(r'([^,(]+?)\s*\(([^()]*(?:\(.*?\)[^()]*)*)\)', teacher_str)

    return [(teacher_name.strip(), teacher_role.strip()) for teacher_name, teacher_role in teachers]


class CustomEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__
