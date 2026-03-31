from collections import defaultdict
from dataclasses import fields, replace
from typing import Optional, Union

from .config import USE_HEURISTICS_FOR_TEACHERS, SKIP_UNRECOGNIZED_TEACHERS
from .creator_fk import PK
from .misc import list_to_dict_by_key
from .schedule_parser.tvgu_schedule_parser.misc import AllGroupsSchedules, TeacherSmall
from .teacher_heuristics import resolve_teacher_small_in_lesson
from .teachers_parser.tvgu_teachers_parser.misc import Teacher
from .types import LessonWithGroups


def lessons_normalize(schedules: AllGroupsSchedules) -> list[LessonWithGroups]:
    lessons_flat: list[LessonWithGroups] = [
        # Сорян за такой comprehension)
        LessonWithGroups(
            **dict((field.name, getattr(lesson, field.name)) for field in fields(lesson) if field.name != "week_day"),
            groups=(group,),
            # 0 - Понедельник (сдвигаем, потому что у API ТвГУ понедельник - это 1)
            week_day=lesson.week_day - 1
        )
        for groups_schedule in schedules.values()
        for group, lessons in groups_schedule.items() if lessons
        for lesson in lessons
    ]

    # Объединяем пары, которые на самом деле являются одной парой
    # Метод `.identify()` намеренно не учитывает состав преподавателей и групп
    normalized_lessons: list[LessonWithGroups] = []
    grouped: defaultdict[tuple, list[LessonWithGroups]] = defaultdict(list)

    for lesson in lessons_flat:
        grouped[lesson._identify()].append(lesson)

    for lessons_group in grouped.values():
        base_lesson: LessonWithGroups = lessons_group[0]
        grouped_teachers: defaultdict[str, list[TeacherSmall]] = defaultdict(list)

        for lesson in lessons_group:
            for teacher in lesson.teachers:
                grouped_teachers[teacher.initials].append(teacher)

        # Да, убираем повторения, коими считаем только совпадение инициал
        # Иногда у одного и того же преподавателя разные роли, а вероятность проведения пары преподавателями с
        # одинаковыми инициалами крайне мала
        normalized_teachers: tuple[TeacherSmall, ...] = tuple(teachers[0] for teachers in grouped_teachers.values())

        normalized_lessons.append(
            replace(
                base_lesson,
                teachers=normalized_teachers,
                groups=tuple({group for lesson in lessons_group for group in lesson.groups}),
            )
        )

    return normalized_lessons


def normalize_teachers_for_lessons(lesson_pks: dict[tuple, PK], teachers: list[Teacher]) -> dict[tuple, PK]:
    teachers_by_initials: dict[str, list[Teacher]] = list_to_dict_by_key(teachers, "initials", False, True,
                                                                         handle_key_func=lambda x: x.lower())
    for lesson_key, lesson_pk in lesson_pks.items():
        lesson: LessonWithGroups = lesson_pk.entity
        cur_teachers: list[Union[TeacherSmall, Teacher]] = []

        for teacher_small in lesson.teachers:
            suitable_teachers: Optional[list[Teacher]] = teachers_by_initials.get(teacher_small.initials.lower())

            if suitable_teachers is None or len(suitable_teachers) == 0:
                if SKIP_UNRECOGNIZED_TEACHERS:
                    continue

                cur_teachers.append(teacher_small)
            elif len(suitable_teachers) == 1:
                cur_teachers.append(suitable_teachers[0])
            else:
                if not USE_HEURISTICS_FOR_TEACHERS:
                    cur_teachers.append(teacher_small)
                    continue

                # Эвристическая оценка на основе информации пары
                possible_teachers: list[tuple[Teacher, float]] = resolve_teacher_small_in_lesson(
                    lesson, suitable_teachers
                )

                best_teacher_match: Teacher = max(possible_teachers, key=lambda x: x[1])[0]
                cur_teachers.append(best_teacher_match)

        lesson: LessonWithGroups = replace(lesson, teachers=tuple(cur_teachers))
        lesson_pks[lesson_key] = replace(lesson_pk, entity=lesson)

    return lesson_pks
