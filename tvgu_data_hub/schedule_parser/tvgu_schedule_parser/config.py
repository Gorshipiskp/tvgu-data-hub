from typing import Final

API_ALL_GROUPS: Final[str] = "https://timetable.tversu.ru/api/v3/groups"
API_SCHEDULE: Final[str] = "https://timetable.tversu.ru/api/v3/timetable?group_name={0}&type={1}"

PAIRS_SCHEDULE_TYPE: Final[int] = 0
# Значения ниже пока что не используются
EXAMINES_SCHEDULE_TYPE: Final[int] = 1
RETAKES_SCHEDULE_TYPE: Final[int] = 2
GIA_SCHEDULE_TYPE: Final[int] = 3

REQUEST_TIMEOUT: Final[int] = 30
MAX_CONCURRENT_REQUESTS: Final[int] = 50

# Рекомендуется пропускать аспирантуру ввиду отсутствия поддержки
# (неопределённое поведение при использовании tvgu-data-hub)
SKIP_ASPIRANTES: Final[bool] = True
# Пропускать пары с некорректной информацией
SKIP_BAD_LESSONS: Final[bool] = False
SKIP_UNKNOWN_SUBJECT_TYPES: Final[bool] = False
