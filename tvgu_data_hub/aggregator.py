from collections import defaultdict
from dataclasses import dataclass
from typing import Union, Optional

from schedule_parser.tvgu_schedule_parser.misc import LessonBase, TeacherSmall, GroupBase, Group, AllGroupsSchedules
from structs_parser.tvgu_structs_parser.normalizer import TvGUStructBase, TvGUStruct
from structs_parser.tvgu_structs_parser.parsers.parser_structs import DepartmentBase, Department
from teachers_parser.tvgu_teachers_parser.misc import Teacher
from tvgu_data_hub.creator_fk import PK, TeacherAggregated, TeacherSmallAggregated, \
    inherit_instance_dataclass
from tvgu_data_hub.normalizer import LessonWithID, PlaceAggregated, SubjectAggregated


@dataclass(frozen=True, kw_only=True)
class GroupAggregated(GroupBase):
    id: int
    struct_id: int
    has_schedule: bool


@dataclass(frozen=True, kw_only=True)
class StructAggregated(TvGUStructBase):
    id: int
    boss_id: Optional[int]
    groups_ids: tuple[int]
    departments_ids: tuple[int]


@dataclass(frozen=True, kw_only=True)
class DepartmentAggregated(DepartmentBase):
    id: int
    boss_id: Optional[int]
    boss_jobs: Optional[list[str]]
    struct_id: int


@dataclass(frozen=True, kw_only=True)
class LessonAggregated(LessonBase):
    id: int
    groups_ids: tuple[int]
    teachers_ids: tuple[int]
    subject_id: int
    place_id: int

    def _identify(self) -> tuple[int, int, int, int, int]:
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


def prepare_departments(
        structs_pks: dict[tuple, PK],
        teachers_identified: dict[tuple, Union[TeacherAggregated, TeacherSmallAggregated]],
) -> dict[tuple, StructAggregated]:
    departments: dict[tuple, StructAggregated] = {}
    department_id_counter: int = 0

    max_teacher_id: int = max(teacher.id for teacher in teachers_identified.values())

    for struct_pk in structs_pks.values():
        for department in struct_pk.entity.departments:
            if department.boss_surname is None:
                cur_teacher = None
            else:
                cur_teacher, max_teacher_id, is_new = find_teacher_or_create_small(
                    teachers_identified.values(), department, max_teacher_id
                )

                if is_new:
                    teachers_identified[cur_teacher._identify()] = cur_teacher

            new_department: DepartmentAggregated = inherit_instance_dataclass(
                DepartmentAggregated,
                department,
                "struct_name", "boss_name", "boss_surname", "boss_patronymic",
                id=department_id_counter,
                struct_id=struct_pk.id,
                boss_id=cur_teacher.id if cur_teacher is not None else None
            )
            department_id_counter += 1

            departments[new_department._identify()] = new_department

    return departments


def prepare_structs(structs_pks: dict[tuple, PK], groups_pks: dict[tuple, PK],
                    teachers_identified: dict[tuple, Union[TeacherAggregated, TeacherSmallAggregated]],
                    departments_identified: dict[tuple, StructAggregated]) -> dict[tuple, StructAggregated]:
    structs_aggregated: list[StructAggregated] = []

    max_teacher_id: int = max(teacher.id for teacher in teachers_identified.values())

    def find_group_by_name(group_name: str) -> Optional[PK]:
        for group_pk in groups_pks.values():
            if group_pk.entity.origin_name == group_name:
                return group_pk
        return None

    for struct_id, struct_pk in enumerate(structs_pks.values()):
        struct: TvGUStruct = struct_pk.entity
        groups_ids: list[int] = []

        for group in struct.groups:
            group_pk: Optional[PK] = find_group_by_name(group)

            if group_pk is not None:
                groups_ids.append(group_pk.id)

        departments_ids: tuple[int] = tuple(
            departments_identified[department._identify()].id for department in struct.departments
        )

        if struct.boss_surname is None:
            cur_teacher = None
        else:
            cur_teacher, max_teacher_id, is_new = find_teacher_or_create_small(
                teachers_identified.values(), struct, max_teacher_id
            )

            if is_new:
                teachers_identified[cur_teacher._identify()] = cur_teacher

        structs_aggregated.append(
            inherit_instance_dataclass(
                StructAggregated,
                struct,
                "groups", "departments", "boss_name", "boss_surname", "boss_patronymic",
                id=struct_id,
                groups_ids=tuple(groups_ids),
                departments_ids=departments_ids,
                boss_id=None if cur_teacher is None else cur_teacher.id
            )
        )
    structs_identified: dict[tuple, StructAggregated] = {}

    for struct in structs_aggregated:
        structs_identified[struct._identify()] = struct

    return structs_identified


def prepare_groups(schedules: AllGroupsSchedules, groups_pks: dict[tuple, PK],
                   structs_identified: dict[tuple, StructAggregated]) -> dict[tuple, GroupAggregated]:
    groups_aggregated: list[GroupAggregated] = []

    def find_struct_by_name(struct_name: str) -> Optional[StructAggregated]:
        for struct in structs_identified.values():
            if struct.code == struct_name:
                return struct
        return None

    for group_pk in groups_pks.values():
        group: Group = group_pk.entity
        struct: Optional[StructAggregated] = find_struct_by_name(group.faculty_code)

        if struct is None:
            raise Exception(
                f"Структура \"{group.faculty_code}\", заданная у группы {group.origin_name}, не найдена"
            )

        groups_aggregated.append(
            inherit_instance_dataclass(
                GroupAggregated,
                group,
                "faculty_code",
                id=group_pk.id,
                struct_id=struct.id,
                has_schedule=schedules.get(struct.code, {}).get(group) is not None
            )
        )
    groups_identified: dict[tuple, GroupAggregated] = {}

    for group in groups_aggregated:
        groups_identified[group._identify()] = group

    return groups_identified


def prepare_teachers(
        lessons_pks: dict[tuple, PK],
        teachers: list[Teacher]
) -> dict[tuple, Union[TeacherAggregated, TeacherSmallAggregated]]:
    teacher_set: dict[Teacher | TeacherSmall, bool] = {}

    for teacher in teachers:
        teacher_set[teacher] = False

    for lesson_pk in lessons_pks.values():
        for teacher in lesson_pk.entity.teachers:
            teacher_set[teacher] = True

    teachers_pks: list[tuple[bool, PK]] = [
        (is_has_lessons, PK(id=teacher_id, entity=teacher))
        for teacher_id, (teacher, is_has_lessons) in enumerate(teacher_set.items())
    ]

    teachers_aggregated: list[Union[TeacherAggregated, TeacherSmallAggregated]] = []

    for has_lessons, teacher_pk in teachers_pks:
        teacher_new_instance: Union[TeacherAggregated, TeacherSmallAggregated] = inherit_instance_dataclass(
            TeacherAggregated if isinstance(teacher_pk.entity, Teacher) else TeacherSmallAggregated,
            teacher_pk.entity,
            id=teacher_pk.id,
            has_lessons=has_lessons
        )

        teachers_aggregated.append(teacher_new_instance)

    teachers_identified: dict[tuple, Union[TeacherAggregated, TeacherSmallAggregated]] = {
        teacher_aggregated._identify(): teacher_aggregated for teacher_aggregated in teachers_aggregated
    }

    return teachers_identified


def prepare_subjects(lessons_with_ids: list[LessonWithID]) -> dict[str, dict[str, SubjectAggregated]]:
    all_subjects: set[tuple[str, str]] = set((group.subject_name, group.subject_type) for group in lessons_with_ids)
    subjects_aggregated: list[SubjectAggregated] = []

    for subject_id, subject in enumerate(all_subjects):
        subjects_aggregated.append(
            SubjectAggregated(
                id=subject_id,
                name=subject[0],
                type=subject[1]
            )
        )
    subjects_identified: defaultdict[str, dict[str, SubjectAggregated]] = defaultdict(dict)

    for subject in subjects_aggregated:
        subjects_identified[subject.type][subject.name] = subject

    return dict(subjects_identified)


def prepare_places(lessons_with_ids: list[LessonWithID]) -> dict[str, PlaceAggregated]:
    all_places: set[str] = set(group.place for group in lessons_with_ids)
    places_aggregated: list[PlaceAggregated] = []

    for place_id, place in enumerate(all_places):
        places_aggregated.append(
            PlaceAggregated(
                id=place_id,
                name=place,
                is_link="http" in place
            )
        )
    places_identified: dict[str, PlaceAggregated] = {}

    for place in places_aggregated:
        places_identified[place.name] = place

    return places_identified


def prepare_lessons(
        lessons: list[LessonWithID],
        places_identified: dict[tuple, PlaceAggregated],
        subjects_identified: dict[str, dict[str, SubjectAggregated]],
        teachers_identified: dict[tuple, Union[TeacherAggregated, TeacherSmallAggregated]],
        groups_identified: dict[tuple, GroupAggregated],
) -> dict[tuple, LessonAggregated]:
    lessons_aggregated: list[LessonAggregated] = []

    for lesson in lessons:
        teachers_ids: list[int] = [
            teachers_identified[teacher._identify()].id
            for teacher in lesson.teachers
        ]

        lessons_aggregated.append(
            inherit_instance_dataclass(
                LessonAggregated,
                lesson,
                "groups", "teachers", "subject_name", "subject_type", "place",
                groups_ids=tuple(groups_identified[group._identify()].id for group in lesson.groups),
                teachers_ids=tuple(teachers_ids),
                subject_id=subjects_identified[lesson.subject_type][lesson.subject_name].id,
                place_id=places_identified[lesson.place].id
            )
        )
    lessons_identified: dict[tuple, LessonAggregated] = {}

    for lesson in lessons_aggregated:
        lessons_identified[lesson._identify()] = lesson

    return lessons_identified


def find_teacher_or_create_small(
        teachers: list[Union[TeacherAggregated, TeacherSmallAggregated]],
        struct: Union[TvGUStruct, Department],
        cur_max_teacher_id: int
) -> tuple[Union[TeacherSmallAggregated, TeacherAggregated], int, bool]:
    initials_to_check: str = f"{struct.boss_surname} {struct.boss_name[0]}.{struct.boss_patronymic[0]}."

    for teacher in teachers:
        if isinstance(teacher, TeacherAggregated):
            cond: bool = all([
                teacher.name.lower() == struct.boss_name.lower(),
                teacher.surname.lower() == struct.boss_surname.lower(),
                teacher.patronymic.lower() == struct.boss_patronymic.lower()
            ])
        elif isinstance(teacher, TeacherSmallAggregated):
            cond: bool = teacher.initials.lower() == initials_to_check.lower()
        else:
            raise NotImplementedError(f"Необрабатываемый тип преподавателя: {type(teacher)}")

        if cond:
            return (
                teacher,
                cur_max_teacher_id,
                False
            )

    return (
        TeacherSmallAggregated(
            initials=initials_to_check,
            role=f"Руководитель '{struct.name}'",
            id=cur_max_teacher_id + 1,
            has_lessons=False
        ),
        cur_max_teacher_id + 1,
        True
    )
