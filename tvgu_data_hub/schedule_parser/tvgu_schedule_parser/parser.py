import asyncio
import re
from collections import defaultdict
from typing import Coroutine, Any, Union, Optional

import aiohttp
from aiohttp import TCPConnector, ClientSession

from .config import API_ALL_GROUPS, MAX_CONCURRENT_REQUESTS, API_SCHEDULE, PAIRS_SCHEDULE_TYPE, SKIP_BAD_LESSONS, \
    SKIP_UNKNOWN_SUBJECT_TYPES
from .consts import WeekMark, SubjectType
from .misc import AllGroupsSchedules, Group, Lesson, fetch_json, parse_group_by_name, UnHandlingGroupException, \
    SkipAspirantesException, LessonTime, SkipLessonException, determine_subject_type, clean_subject_name, TeacherSmall


async def get_all_tvgu_schedules(show_warnings: bool = False) -> AllGroupsSchedules:
    """Асинхронная функция для получения расписания всех групп"""

    faculties_groups: dict[str, list[Group]] = await get_all_groups_by_faculty_key(show_warnings)

    groups_schedule_requests: list[Coroutine[Any, Any, dict[Group, tuple[Lesson, ...]]]] = [
        get_groups_schedules(groups) for groups in faculties_groups.values()
    ]
    groups_schedules: list[dict[Group, tuple[Lesson]]] = await asyncio.gather(*groups_schedule_requests)

    return dict(zip(faculties_groups.keys(), groups_schedules))


async def get_all_groups_by_faculty_key(show_warnings: bool = False) -> dict[str, list[Group]]:
    """Асинхронная функция для получения списка групп"""

    try:
        async with aiohttp.ClientSession() as session:
            jsonned: dict[str, list[Any]] = await fetch_json(session, API_ALL_GROUPS)
    except Exception as e:
        raise e

    if "groups" not in jsonned:
        raise Exception(f"Error: {jsonned}")

    all_groups: defaultdict[str, list] = defaultdict(list)

    for group_req in jsonned["groups"]:
        group_name: str = group_req["groupName"]

        try:
            group: Group = parse_group_by_name(group_name)
        except UnHandlingGroupException:
            if show_warnings:
                print("Неизвестный шаблон группы:", group_name)
            continue
        except SkipAspirantesException:
            continue

        all_groups[group.faculty_code].append(group)
    return all_groups


async def get_groups_schedules(groups: list[Group]) -> dict[Group, tuple[Lesson, ...]]:
    """Асинхронная функция для получения расписания групп"""

    connector: TCPConnector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_REQUESTS)

    async with ClientSession(connector=connector) as session:
        tasks: list[Coroutine[Any, Any, dict]] = [
            fetch_json(session, API_SCHEDULE.format(group.origin_name, PAIRS_SCHEDULE_TYPE))
            for group in groups
        ]
        schedule_pages: list[dict[str, Union[str, dict[str, Any]]]] = await asyncio.gather(*tasks)

    # Не беспокоимся: датакласс (Group) с параметром `frozen=True` генерирует `self.__hash__` сам, а значит может
    # использоваться в качестве ключа словаря
    # `asyncio.gather` сохраняет порядок, несмотря на конкурентность выполнения запросов
    return dict(zip(groups, list(map(handle_schedule_response, schedule_pages))))


def handle_schedule_response(json_page: dict[str, Union[str, dict[str, Any]]]) -> Optional[tuple[Lesson, ...]]:
    """Функция для обработки ответа API"""

    message: Optional[str] = json_page.get("message")

    if message is not None:
        # В ответе API есть опечатка: вместо "не найдено" написано "на найдено"
        if "расписание на найдено" in message.lower() or "расписание не найдено" in message.lower():
            return None

    lesson_time_data: Optional[list[dict[str, str]]] = json_page.get("lessonTimeData")

    if lesson_time_data is None:
        raise KeyError(f"Нет информации о времени пар у группы: {json_page}")

    lessons_containers: Optional[list[dict[str, Any]]] = json_page.get("lessonsContainers")

    if lessons_containers is None:
        raise KeyError(f"Error: {json_page}")

    times: dict[int, LessonTime] = handle_lesson_times(lesson_time_data)

    lessons: list[Lesson] = []
    for lesson_info in lessons_containers:
        try:
            lesson: Lesson = handle_lesson(lesson_info, times)
        except SkipLessonException:
            continue

        lessons.append(lesson)
    return tuple(lessons)


def handle_lesson(lesson_info: dict[str, Any], times: dict[int, LessonTime]) -> Lesson:
    """Главная функция для обработки пары"""

    lesson_number: Optional[int] = lesson_info.get("lessonNumber")
    week_day: Optional[int] = lesson_info.get("weekDay")
    week_mark: Optional[WeekMark] = lesson_info.get("weekMark")

    size_x: Optional[int] = lesson_info.get("sizeX")
    position_x: Optional[int] = lesson_info.get("positionX")

    texts: Optional[list[str]] = lesson_info.get("texts")

    if (
            lesson_number is None
            or week_day is None
            or week_mark is None
            or size_x is None
            or position_x is None
            or len(texts) < 4
    ):
        if SKIP_BAD_LESSONS:
            raise SkipLessonException
        raise KeyError(f"У пары нет нужной информации: {lesson_info}")

    subgroup: Optional[int] = position_x if size_x == 2 else None

    subject: Optional[str] = None if texts[1] is None else texts[1].strip()
    teachers_str: Optional[str] = None if texts[2] is None else texts[2].strip()
    place: Optional[str] = None if texts[3] is None else texts[3].strip()

    subject_type: SubjectType = determine_subject_type(subject)
    subject_name: Optional[str] = clean_subject_name(subject, subject_type)

    if SKIP_UNKNOWN_SUBJECT_TYPES and subject_type is None:
        raise SkipLessonException

    return Lesson(
        lesson_number=lesson_number,
        week_day=week_day,
        week_mark=week_mark,
        time_start=times[lesson_number].start,
        time_end=times[lesson_number].end,
        subject_name=subject_name,
        subject_type=subject_type,
        place=place,
        teachers=tuple(handle_teachers(teachers_str)),
        subgroup=subgroup,
    )


def handle_lesson_times(lesson_time_data: list[dict[str, str]]) -> dict[int, LessonTime]:
    """Функция для обработки данных о времени проведения пар"""

    times: dict[int, LessonTime] = {}

    for lesson_num, lesson_time in enumerate(lesson_time_data):
        start, end = lesson_time.get("start"), lesson_time.get("end")

        if start is None or end is None:
            raise Exception(f"Нет информации о границах времени пары: {lesson_time}")

        start_hour, start_minutes = start.split(":")
        end_hour, end_minutes = end.split(":")

        times[lesson_num] = LessonTime(
            start=int(start_hour) * 60 + int(start_minutes),
            end=int(end_hour) * 60 + int(end_minutes),
        )

    return times


def handle_teachers(teachers_str: str) -> set[TeacherSmall]:
    """Функция для обработки строки преподавателей"""

    teachers: set[TeacherSmall] = set()
    teachers_infos: list[tuple[str, str]] = re.findall(r'([^,(]+?)\s*\(([^()]*(?:\(.*?\)[^()]*)*)\)', teachers_str)

    for teacher_info in teachers_infos:
        teachers.add(
            TeacherSmall(
                initials=teacher_info[0].strip(),
                role=teacher_info[1].strip(),
            )
        )

    return teachers
