import re
from typing import Optional

from rapidfuzz import fuzz

from schedule_parser.tvgu_schedule_parser.misc import Lesson
from teachers_parser.tvgu_teachers_parser.misc import Teacher


def get_surname_from_initials(initials: str) -> str:
    return normalize(initials).split()[0]


def normalize(s: Optional[str]) -> str:
    if not s:
        return ""
    return re.sub(r'\s+', ' ', s.strip().lower())


def token_set(s: Optional[str]) -> set:
    if not s:
        return set()
    return set(re.findall(r'\w+', s.lower()))


def do_fuzzy_score(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return fuzz.token_set_ratio(a, b) / 100.0


def score_candidate(lesson: Lesson, candidate: Teacher) -> float:
    score: float = 0.0

    subject = lesson.subject_name or ""

    # Есть ли предмет в списке преподаваемых дисциплин
    if subject and candidate.teaching_disciplines:
        best: float = max(
            (do_fuzzy_score(subject, d) for d in candidate.teaching_disciplines),
            default=0.0
        )
        score += 50.0 * best

    # Есть ли предмет в списке преподаваемых предметов
    if subject and candidate.teaching_programs:
        best: float = max(
            (do_fuzzy_score(subject, p) for p in candidate.teaching_programs),
            default=0.0
        )
        score += 20.0 * best

    # Есть ли отчасти предмет в списке образований
    if subject and candidate.direction_education:
        score += 7.0 * do_fuzzy_score(subject, candidate.direction_education)

    if subject and candidate.level_education:
        score += 7.0 * do_fuzzy_score(subject, candidate.level_education)

    # Пусть стаж преподавателя тоже решает
    score += min(candidate.experience_age or 0, 40) * 0.1

    return score


def resolve_teacher_small_in_lesson(lesson: Lesson, candidates: list[Teacher],
                                    accept_single_if_unique=True) -> list[tuple[Teacher, float]]:
    if not candidates:
        return []

    if len(candidates) == 1 and accept_single_if_unique:
        return [(candidates[0], 100.0)]

    scored: list[tuple[Teacher, float]] = []
    for candidate in candidates:
        score: float = score_candidate(lesson, candidate)
        scored.append((candidate, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored
