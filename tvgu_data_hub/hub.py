import asyncio
from collections import defaultdict

from schedule_parser.tvgu_schedule_parser import get_all_tvgu_schedules
from schedule_parser.tvgu_schedule_parser.misc import AllGroupsSchedules
from structs_parser.tvgu_structs_parser import get_all_tvgu_structs
from structs_parser.tvgu_structs_parser.normalizer import TvGUStruct
from teachers_parser.tvgu_teachers_parser import get_all_tvgu_teachers
from teachers_parser.tvgu_teachers_parser.misc import Teacher
from .aggregator import prepare_lessons, LessonAggregated, prepare_places, prepare_subjects, prepare_teachers, \
    GroupAggregated, prepare_groups, StructAggregated, prepare_structs, DepartmentAggregated, prepare_departments
from .creator_fk import PK, create_entities_pks, inherit_instance_dataclass
from .normalizer import LessonWithGroups, lessons_normalize, LessonWithID, \
    SubjectAggregated, PlaceAggregated, normalize_teachers_for_lessons


async def get_all_tvgu_data() -> dict[str, list]:
    structs: list[TvGUStruct]
    teachers: list[Teacher]
    schedules: AllGroupsSchedules

    structs, teachers, schedules = await asyncio.gather(
        get_all_tvgu_structs(),
        get_all_tvgu_teachers(),
        get_all_tvgu_schedules()
    )

    structs_pks: dict[str, PK] = create_entities_pks(structs, "name")
    groups_pks: dict[tuple, PK] = create_entities_pks(
        [group for groups in schedules.values() for group in groups],
        custom_key_getter=lambda group: group._identify()
    )

    normalized_lessons: list[LessonWithGroups] = lessons_normalize(schedules)
    lessons_pks: dict[tuple, PK] = create_entities_pks(
        normalized_lessons, custom_key_getter=lambda lesson: lesson._identify()
    )
    lessons_pks = normalize_teachers_for_lessons(lessons_pks, teachers)

    lessons_with_ids: list[LessonWithID] = [
        inherit_instance_dataclass(LessonWithID, lesson_pk.entity, id=lesson_pk.id)
        for lesson_pk in lessons_pks.values()
    ]

    departments_identified: dict[tuple, DepartmentAggregated] = prepare_departments(structs_pks)
    structs_identified: dict[tuple, StructAggregated] = prepare_structs(structs_pks, groups_pks, departments_identified)
    teachers_identified = prepare_teachers(lessons_pks)
    places_identified: defaultdict[str, PlaceAggregated] = prepare_places(lessons_with_ids)
    subjects_identified: dict[str, dict[str, SubjectAggregated]] = prepare_subjects(lessons_with_ids)
    groups_identified: defaultdict[str, GroupAggregated] = prepare_groups(schedules, groups_pks, structs_identified)
    lessons_aggregated: defaultdict[str, LessonAggregated] = prepare_lessons(
        lessons_with_ids,
        places_identified,
        subjects_identified,
        teachers_identified,
        groups_identified
    )

    print(*groups_identified.values(), sep="\n")

    return {
        "departments": list(departments_identified.values()),
        "structs": list(structs_identified.values()),
        "teachers": list(teachers_identified.values()),
        "places": list(places_identified.values()),
        "subjects": [subject for subjects in subjects_identified.values() for subject in subjects.values()],
        "groups": list(groups_identified.values()),
        "lessons": list(lessons_aggregated.values())
    }
