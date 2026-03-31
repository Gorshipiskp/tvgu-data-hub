import re
from dataclasses import dataclass
from typing import Optional, Final, Any, Literal

from bs4 import Tag, BeautifulSoup

from ..config import USE_SHORTER_ADDRESSES
from ..misc import is_struct_skipping, parse_phones_n_additional_codes, parse_address_n_postal_code, split_n_clean, \
    parse_teacher_name

INSTITUTE_TYPE: Final = "institute"
FACULTY_TYPE: Final = "faculty"

StructType = Literal[INSTITUTE_TYPE, FACULTY_TYPE]


@dataclass(frozen=True, kw_only=True)
class StructInfo:
    name: str
    type: StructType
    boss_name: Optional[str]
    boss_surname: Optional[str]
    boss_patronymic: Optional[str]
    address: str
    postal_code: Optional[str]
    website: Optional[str]
    email: str
    phones: Optional[list[str]]
    phones_additional_codes: Optional[list[str]]


@dataclass(frozen=True, kw_only=True)
class DepartmentBase:
    name: str
    address: Optional[str]
    postal_code: Optional[str]
    website: Optional[str]
    email: str
    division_clause_url: Optional[str]
    phones: Optional[list[str]]
    phones_additional_codes: Optional[list[str]]

    def _identify(self) -> tuple[str, str, str, str]:
        return (
            self.name,
            self.email,
            self.address,
            self.postal_code
        )

    def __hash__(self) -> int:
        return hash(self._identify())

    def __eq__(self, other) -> bool:
        if isinstance(other, DepartmentBase):
            return self._identify() == other._identify()
        return NotImplemented


@dataclass(frozen=True, kw_only=True)
class Department(DepartmentBase):
    struct_name: str
    boss_jobs: Optional[list[str]]
    boss_name: Optional[str]
    boss_surname: Optional[str]
    boss_patronymic: Optional[str]


def parse_structs(structs_table_body: Tag) -> list[StructInfo]:
    all_structs: list[Tag] = structs_table_body.find_all(itemprop="structOrgUprav")

    structs: list[StructInfo] = []
    for struct in all_structs:
        struct_name_tag: Tag = struct.find(itemprop="name")
        struct_name: str = struct_name_tag.text.strip()

        if is_struct_skipping(struct_name):
            continue

        struct_type: StructType = FACULTY_TYPE if "факультет" in struct_name.lower() else INSTITUTE_TYPE

        boss_name_tag: Tag = struct.find(itemprop="fio")
        boss_name: str = boss_name_tag.text.strip()

        if boss_name.lower() == "нет" or "отсутствует" in boss_name.lower():
            boss_name_parts: dict[str, Optional[str]] = {"name": None, "surname": None, "patronymic": None}
        else:
            boss_name_parts: dict[str, str] = parse_teacher_name(boss_name)

        address_str_n_postal_code_tag: Tag = struct.find(itemprop="addressStr")
        postal_code, address = parse_address_n_postal_code(address_str_n_postal_code_tag.text)

        if USE_SHORTER_ADDRESSES and address is not None:
            address = re.sub("Центральный федеральный округ, Тверская область,", "", address,
                             flags=re.IGNORECASE).strip()
            address = re.sub("Тверская область,", "", address, flags=re.IGNORECASE).strip()

        website_tag: Tag = struct.find(itemprop="site")
        website_str: str = website_tag.text.strip()
        website: Optional[str] = None if "нет" in website_str or "отсутствует" in website_str else website_str

        email_tag: Tag = struct.find(itemprop="email")
        email: str = email_tag.text.strip()

        division_clause_doc_link: Tag = struct.find(itemprop="divisionClauseDocLink")

        phone_tag: Tag = division_clause_doc_link.find_next("td")
        phone_text: str = phone_tag.text
        phones, phones_additional_codes = parse_phones_n_additional_codes(phone_text)

        structs.append(
            StructInfo(
                name=struct_name,
                type=struct_type,
                boss_name=boss_name_parts["name"],
                boss_surname=boss_name_parts["surname"],
                boss_patronymic=boss_name_parts["patronymic"],
                address=address,
                postal_code=postal_code,
                website=website,
                email=email,
                phones=phones,
                phones_additional_codes=phones_additional_codes
            )
        )

    return structs


def parse_departments(departments_table_body: Tag) -> list[Department]:
    all_departments: list[Tag] = departments_table_body.find_all("tr")
    departments: list[Department] = []
    cur_struct: str = "unknown"

    for department in all_departments:
        if department.get("itemprop") is None:
            cur_struct = department.text.strip()
            continue

        if is_struct_skipping(cur_struct):
            continue

        department_name_tag: Tag = department.find(itemprop="name")
        department_name: str = department_name_tag.text.strip()

        department_boss_tag: Tag = department.find(itemprop="fio")
        department_boss: str = department_boss_tag.text.strip()

        if department_boss.lower() == "нет" or "отсутствует" in department_boss.lower():
            boss_name_parts: dict[str, Optional[str]] = {"name": None, "surname": None, "patronymic": None}
        else:
            boss_name_parts: dict[str, str] = parse_teacher_name(department_boss)

        boss_jobs_tag: Tag = department.find(itemprop="post")
        boss_jobs_str: str = boss_jobs_tag.text.strip()

        if boss_jobs_str.lower() == "нет" or "отсутствует" in boss_jobs_str.lower():
            boss_jobs: Optional[list[str]] = None
        else:
            boss_jobs: Optional[list[str]] = [job.replace("И. о.", "И.о.") for job in
                                              split_n_clean(boss_jobs_str, ",", ";")]

        address_tag: Tag = department.find(itemprop="addressStr")
        postal_code, address = parse_address_n_postal_code(address_tag.text)

        if USE_SHORTER_ADDRESSES:
            address = re.sub("Центральный федеральный округ, Тверская область,", "", address,
                             flags=re.IGNORECASE).strip()
            address = re.sub("Тверская область,", "", address, flags=re.IGNORECASE).strip()

        website_tag: Tag = department.find(itemprop="site")
        website_str: Optional[str] = website_tag.text.strip().lower()
        website: Optional[str] = None if "нет" in website_str or "отсутствует" in website_str else website_str

        email_tag: Tag = department.find(itemprop="email")
        email: Optional[str] = email_tag.text.strip()
        email = None if "нет" in email.lower() or "отсутствует" in email.lower() else email

        division_clause_tag: Tag = department.find(itemprop="divisionClauseDocLink")

        # Положение
        if division_clause_tag.text.strip().lower() == "нет":
            division_clause_url = None
        else:
            division_clause_a_tag: Optional[Tag] = division_clause_tag.find("a")

            if division_clause_a_tag is None:
                division_clause_url = None
            else:
                division_clause_url = f"https://tversu.ru{division_clause_a_tag.get('href')}"

        phone_tag: Tag = division_clause_tag.find_next("td")
        phones, additional_codes = parse_phones_n_additional_codes(phone_tag.text)

        departments.append(
            Department(
                name=department_name,
                struct_name=cur_struct,
                boss_name=boss_name_parts["name"],
                boss_surname=boss_name_parts["surname"],
                boss_patronymic=boss_name_parts["patronymic"],
                boss_jobs=boss_jobs,
                address=address,
                postal_code=postal_code,
                website=website,
                email=email,
                division_clause_url=division_clause_url,
                phones=phones,
                phones_additional_codes=additional_codes
            )
        )

    return departments


def parse_structs_page(structs_page: str, show_warnings: bool = False) -> dict[str, Any]:
    soup: BeautifulSoup = BeautifulSoup(structs_page, "html.parser")

    tbodies: list[Tag] = soup.find_all("tbody")
    theaders: list[Tag] = soup.find_all("thead")
    h4s: list[Tag] = soup.find_all("h4")

    if len(tbodies) != len(theaders):
        raise ValueError(f"Неопределённое количество таблиц: {len(tbodies)} != {len(theaders)}")

    zipped: list[tuple[Tag, Tag, Tag]] = list(zip(h4s, theaders, tbodies))

    def get_next_table() -> tuple[str, Tag, Tag]:
        cur_h4, cur_head, cur_body = zipped.pop(0)
        return cur_h4.text.strip().lower(), cur_head, cur_body

    cur_h4: str
    cur_head: Tag
    cur_body: Tag

    cur_h4, cur_head, cur_body = get_next_table()

    if "Органы управления".lower() not in cur_h4:
        if show_warnings:
            print("Неожиданный заголовок таблицы органов управления:", cur_h4)

    cur_h4, cur_head, cur_body = get_next_table()

    if "Факультеты".lower() not in cur_h4:
        raise ValueError("Таблица факультетов и институтов не найдена:", cur_h4)

    structs: list[StructInfo] = parse_structs(cur_body)

    cur_h4, cur_head, cur_body = get_next_table()

    if "Кафедр".lower() not in cur_h4:
        raise ValueError("Таблица кафедр не найдена:", cur_h4)

    departments: list[Department] = parse_departments(cur_body)

    return {
        "structs": structs,
        "departments": departments
    }
