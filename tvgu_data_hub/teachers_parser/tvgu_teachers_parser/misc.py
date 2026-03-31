import json
import re
from dataclasses import dataclass
from typing import Optional, Callable, TypeVar, Any

from bs4 import Tag

from .config import NON_DIGITS_PATTERN, DIGITS_PATTERN, TEACHER_FULLNAME_PATTERN, TEACHER_NAME_PARTS


@dataclass(frozen=True, kw_only=True)
class Teacher:
    name: str
    surname: str
    patronymic: str
    initials: str
    lms_profile_link: Optional[str]
    current_job: str
    teaching_disciplines: list[str]
    level_education: str
    direction_education: str
    jobs: list[str]
    degrees: list[str]
    academ_stats: list[str]
    rewards: list[str]
    qualify_ups: list[str]
    experience_age: int
    phone: Optional[str]
    phone_additional_code: Optional[str]
    email: str
    teaching_programs: list[str]

    def _identify(self) -> tuple[str, str, str, str | None, str | None, int, str, str, str]:
        return (
            self.name,
            self.surname,
            self.patronymic,
            self.phone,
            self.phone_additional_code,
            self.experience_age,
            self.level_education,
            self.direction_education,
            self.email
        )

    def __hash__(self) -> int:
        return hash(self._identify())

    def __eq__(self, other) -> bool:
        if isinstance(other, Teacher):
            return self._identify() == other._identify()
        return NotImplemented


def truly_capitalize(text: str) -> str:
    if not text:
        return ""
    return text[0].upper() + text[1:]


T = TypeVar("T")


def flat(list_of_lists: list[list[T]]) -> list[T]:
    return [item for sublist in list_of_lists for item in sublist]


def remove_whitespaces(text: str) -> str:
    text: str = text.replace("\xa0", " ").strip()

    while "  " in text:
        text = text.replace("  ", " ")

    return text


def split_n_strip_n_capitalize(text: str, *splitters: str,
                               additional_func: Callable[..., str] = lambda x: x) -> list[str]:
    # Защищаем разделений от разграничителей внутри скобок
    if splitters:
        splitted = re.split(r"(?:%s)(?![^()]*\))" % "|".join(map(re.escape, splitters)), text)
    else:
        splitted = [text]

    return list(filter(
        lambda x: bool(x),
        (truly_capitalize(remove_whitespaces(additional_func(element).strip())) for element in splitted)
    ))


#  Бывают кнопки "Показать", если текста много, так что вытягиваем из модалки инфу
def handle_possible_modal(tag: Tag, *splitters: str,
                          additional_func: Callable[..., str] = lambda x: x) -> list[str]:
    modal_container: Optional[Tag] = tag.find(class_="showpart-container-modal")

    if modal_container is None:
        contents: list[str] = split_n_strip_n_capitalize(tag.text, *splitters, additional_func=additional_func)
    else:
        contents: list[str] = [
            truly_capitalize(li.text.strip().strip(";")) for li in modal_container.find_all("li")
        ]

        if not contents:
            p: Tag = modal_container.find("p")

            if p is None:
                contents = split_n_strip_n_capitalize(modal_container.text, *splitters,
                                                      additional_func=additional_func)
            else:
                contents = split_n_strip_n_capitalize(p.text, *splitters, additional_func=additional_func)
    return contents


#  Код плотный, но иначе будет слишком много бессмысленных переменных
def parse_teacher_record(teacher_record: Tag) -> Teacher:
    fullname_tag: Tag = teacher_record.find(itemprop="fio")
    fullname: str = fullname_tag.text.strip()
    lms_profile_link: Optional[str] = (fullname_tag.find("a") or {}).get("href")

    if lms_profile_link is not None:
        lms_profile_link = lms_profile_link.strip().strip("_").strip("\\").strip("/")

    parts: list[str] = re.findall(TEACHER_FULLNAME_PATTERN, fullname)[0]

    name_parts: dict[str, str] = dict(zip(
        TEACHER_NAME_PARTS, [re.sub(r'-(\w)', lambda m: '-' + m.group(1).upper(), part.capitalize()) for part in parts]
    ))

    #  В формате "Фамилия И.О."
    initials: str = f"{name_parts['surname']} {name_parts['name'][0]}.{name_parts['patronymic'][0]}.".strip()

    current_job_tag: Tag = teacher_record.find(itemprop="post")
    current_job: str = handle_possible_modal(current_job_tag, ",", ";")[0]

    teaching_disciplines_tag: Tag = teacher_record.find(itemprop="teachingDiscipline")
    teaching_disciplines: list[str] = handle_possible_modal(teaching_disciplines_tag, ",", ";")

    teaching_level_tag: Tag = teacher_record.find(itemprop="teachingLevel")
    educations_n_jobs: list[str] = split_n_strip_n_capitalize(
        teaching_level_tag.encode_contents().decode("UTF-8").replace("</br>", ""), "<br>"
    )
    educations_n_jobs = flat([
        split_n_strip_n_capitalize(education, ",", ";", ". ", additional_func=lambda x: x.replace("\"", "").strip("."))
        for education in educations_n_jobs
    ])

    level_education: str = educations_n_jobs.pop(0)
    direction_education: str = educations_n_jobs.pop(0)
    jobs: list[str] = educations_n_jobs

    degree_tag: Tag = teacher_record.find(itemprop="degree")
    degrees: list[str] = handle_possible_modal(degree_tag, ",", ";")

    academ_stat_tag: Tag = teacher_record.find(itemprop="academStat")
    academ_stats: list[str] = handle_possible_modal(academ_stat_tag, ",")

    rewards_tag: Tag = academ_stat_tag.find_next("td")
    rewards: list[str] = handle_possible_modal(rewards_tag, ",", ";")
    rewards = [reward for reward in rewards if reward and reward.lower() != "нет"]

    qualify_up_tag: Tag = teacher_record.find(itemprop="qualification")
    qualify_ups: list[str] = handle_possible_modal(qualify_up_tag, ",", ";")

    exp_age_tag: Tag = teacher_record.find(itemprop="specExperience")
    exp_age_str: str = handle_possible_modal(exp_age_tag)[0]

    try:
        exp_age: int = int(re.findall(DIGITS_PATTERN, exp_age_str)[0])
    except IndexError:
        exp_age = 0

    phone_tag: Tag = exp_age_tag.find_next("td")
    phones: list[str] = handle_possible_modal(phone_tag, ",", ";")
    phone: str = phones[0] if phones else None
    phone_with_add_code: Optional[list[str]] = [
        re.sub(NON_DIGITS_PATTERN, "", phone_part) for phone_part in re.split(r"(?:доб)|(?:доп)", phone)
    ] if phone else None
    phone: Optional[str] = phone_with_add_code[0] if phone_with_add_code else None
    phone_additional_code: Optional[str] = phone_with_add_code[1] if phone and len(phone_with_add_code) > 1 else None

    email_tag: Tag = phone_tag.find_next("td")
    emails: list[str] = handle_possible_modal(email_tag, ",", ";")
    email: str = emails[0] if emails else None

    teaching_programs_tag: Tag = teacher_record.find(itemprop="teachingOp")
    teaching_programs: list[str] = handle_possible_modal(teaching_programs_tag, ";")

    return Teacher(
        name=name_parts["name"],
        surname=name_parts["surname"],
        patronymic=name_parts["patronymic"],
        initials=initials,
        lms_profile_link=lms_profile_link,
        current_job=current_job,
        teaching_disciplines=teaching_disciplines,
        level_education=level_education,
        direction_education=direction_education,
        jobs=jobs,
        degrees=degrees,
        academ_stats=academ_stats,
        rewards=rewards,
        qualify_ups=qualify_ups,
        experience_age=exp_age,
        phone=phone,
        phone_additional_code=phone_additional_code,
        email=email,
        teaching_programs=teaching_programs
    )


class CustomEncoder(json.JSONEncoder):
    def default(self, obj) -> dict[str, Any]:
        return obj.__dict__
