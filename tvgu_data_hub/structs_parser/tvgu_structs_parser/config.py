import re
from typing import Final

STRUCTS_PAGE_URL: Final[str] = "https://tversu.ru/sveden/struct"
STRUCTS_API_URL: Final[str] = "https://abiturient.tversu.ru/api/catalog/faculties"
STRUCTS_TVERSU_PAGE_URL: Final[str] = "https://tversu.ru/pages/2182"
# Единственный известный мне эндпоинт, где есть коды структур (в названиях групп, например, "ПМиК", "М", "ИСТ" и т.д.)
ALL_GROUPS_API_URL: Final[str] = "https://timetable.tversu.ru/api/v3/groups"

TEACHER_FULLNAME_PATTERN: Final[re.Pattern] = re.compile(r"([a-zA-Zёа-яА-Я\-]+(?:\s+[a-zA-Zёа-яА-Я\-]*)?)"
                                                         r"\s+([a-zA-Zёа-яА-Я\-]+)\s+([a-zA-Zёа-яА-Я\-]+)")
TEACHER_NAME_PARTS: Final[tuple[str, ...]] = ("surname", "name", "patronymic")

NON_DIGITS_PATTERN: Final[re.Pattern] = re.compile(r"\D")

# Без приписок "Центральный федеральный округ, Тверская область"
USE_SHORTER_ADDRESSES: Final[bool] = True

STRUCTS_TO_SKIP: Final[tuple[str, ...]] = (
    # Иногда попадается в списках
    "Аспирантура",
    "Институт непрерывного образования",
    # Хз, что это, лучше пропустим: страница на сайте (https://doud.tversu.ru/) тоже пустая
    "Отделение общеуниверситетских кафедр",
    "Другие кафедры",
)
