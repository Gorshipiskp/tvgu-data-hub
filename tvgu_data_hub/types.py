from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Any

from .schedule_parser.tvgu_schedule_parser.consts import WeekMark, SubjectType
from .schedule_parser.tvgu_schedule_parser.misc import GroupBase, LessonBase, Lesson, Group, TeacherSmall
from .structs_parser.tvgu_structs_parser.normalizer import TvGUStructBase
from .structs_parser.tvgu_structs_parser.parsers.parser_structs import DepartmentBase
from .teachers_parser.tvgu_teachers_parser.misc import Teacher


class NeedPK(ABC):
    @abstractmethod
    def get_pk(self) -> Any:
        raise NotImplementedError


@dataclass(frozen=True, kw_only=True)
class GroupAggregated(GroupBase, NeedPK):
    id: int
    struct_id: int
    has_schedule: bool

    def get_pk(self) -> str:
        return self.origin_name


@dataclass(frozen=True, kw_only=True)
class StructAggregated(TvGUStructBase, NeedPK):
    id: int
    boss_id: Optional[int]
    groups_ids: tuple[int]
    departments_ids: tuple[int]

    def get_pk(self) -> str:
        return self.name


@dataclass(frozen=True, kw_only=True)
class DepartmentAggregated(DepartmentBase, NeedPK):
    id: int
    boss_id: Optional[int]
    boss_jobs: Optional[list[str]]
    struct_id: int

    def get_pk(self) -> str:
        return self.name


@dataclass(frozen=True, kw_only=True)
class LessonAggregated(LessonBase):
    id: int
    groups_ids: tuple[int]
    teachers_ids: tuple[int]
    subject_id: int
    place_id: int

    def _identify(self) -> tuple[WeekMark, int, int, int, int]:
        return (
            self.week_mark,
            self.week_day,
            self.lesson_number,
            self.subject_id,
            self.place_id,
        )

    def __hash__(self) -> int:
        return hash(self._identify())

    def __eq__(self, other) -> bool:
        if isinstance(other, LessonAggregated):
            return self._identify() == other._identify()
        return NotImplemented


@dataclass(frozen=True, kw_only=True)
class LessonWithGroups(Lesson):
    groups: tuple[Group, ...]


@dataclass(frozen=True, kw_only=True)
class LessonWithID(LessonWithGroups):
    id: int


@dataclass(frozen=True, kw_only=True)
class SubjectAggregated(NeedPK):
    id: int
    name: str
    type: SubjectType

    def _identify(self) -> tuple[str, SubjectType]:
        return (
            self.name,
            self.type
        )

    def get_pk(self) -> tuple[str, SubjectType]:
        return self._identify()

    def __hash__(self) -> int:
        return hash(self._identify())

    def __eq__(self, other) -> bool:
        if isinstance(other, SubjectAggregated):
            return self._identify() == other._identify()
        return NotImplemented


@dataclass(frozen=True, kw_only=True)
class PlaceAggregated(NeedPK):
    id: int
    name: str
    is_link: bool

    def _identify(self) -> tuple[str]:
        return (
            self.name,
        )

    def get_pk(self) -> str:
        return self.name

    def __hash__(self) -> int:
        return hash(self._identify())

    def __eq__(self, other) -> bool:
        if isinstance(other, PlaceAggregated):
            return self._identify() == other._identify()
        return NotImplemented


@dataclass(frozen=True, kw_only=True)
class TeacherAggregated(Teacher, NeedPK):
    id: int
    has_lessons: bool

    def get_pk(self) -> tuple[str, str, str]:
        return (
            self.name,
            self.surname,
            self.patronymic
        )


@dataclass(frozen=True, kw_only=True)
class TeacherSmallAggregated(TeacherSmall, NeedPK):
    id: int
    has_lessons: bool

    def get_pk(self) -> str:
        return self.initials
