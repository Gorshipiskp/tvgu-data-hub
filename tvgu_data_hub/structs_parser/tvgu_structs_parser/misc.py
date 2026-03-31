import json
import re
from typing import Optional, Any

from bs4 import Tag

from .config import STRUCTS_TO_SKIP, NON_DIGITS_PATTERN, TEACHER_FULLNAME_PATTERN, TEACHER_NAME_PARTS


def truly_capitalize(word: Optional[str]) -> str:
    if not word:
        return ""
    return word[0].upper() + word[1:]


def split_n_clean(text: str, *splitters: str) -> list[str]:
    if splitters:
        splitted = re.split(r"(?:%s)(?![^()]*\))" % "|".join(map(re.escape, splitters)), text)
    else:
        splitted = [text]

    return list(filter(lambda x: x, (truly_capitalize(job.strip().strip("/")) for job in splitted)))


def parse_name(name_l: str) -> str:
    name_l = name_l.replace("\xa0", " ").replace("\u00A0", " ")
    return name_l.strip()


def parse_description(desc_l: str) -> str:
    desc_l = desc_l.replace("\xa0", " ").replace("\u00A0", " ")
    return desc_l.strip()


def parse_website(website_l: str) -> Optional[str]:
    website_l = website_l.replace("\xa0", " ").replace("\u00A0", " ").replace("Сайт:", " ")

    if not website_l:
        return None

    return website_l.strip().strip("/")


def parse_email(email_l: str) -> str:
    email_l = email_l.replace("\xa0", " ").replace("\u00A0", " ").replace("Электронная почта:", " ")
    return email_l.strip()


def parse_address(address_l: str) -> tuple[str, str]:
    address_l = address_l.replace("\xa0", " ").replace("\u00A0", " ").replace("Адрес:", "")
    postal_code, address_l = address_l.split(",", 1)

    return postal_code.strip(), address_l.strip()


# Бывают кнопки "Показать", если текста много, так что вытягиваем из модалки инфу
def handle_possible_modal(tag: Tag, *splitters: str) -> list[str]:
    modal_container: Optional[Tag] = tag.find(class_="showpart-container-modal")

    if modal_container is None:
        contents: list[str] = split_n_clean(tag.text, *splitters)
    else:
        contents: list[str] = [
            truly_capitalize(li.text.strip().strip(";")) for li in modal_container.find_all("li")
        ]

        if not contents:
            p: Tag = modal_container.find("p")

            if p is None:
                contents = split_n_clean(modal_container.text, *splitters, )
            else:
                contents = split_n_clean(p.text, *splitters)
    return contents


def parse_phones_n_additional_codes(phones_text: Optional[str]) -> tuple[Optional[list[str]], Optional[list[str]]]:
    if not phones_text:
        return None, None

    phones: list[str] = []
    additional_codes: list[str] = []

    phones_text = phones_text.lower()
    for phone_text in split_n_clean(phones_text, ",", ";"):
        phone_with_add_code: Optional[list[str]] = [
            re.sub(NON_DIGITS_PATTERN, "", phone_part) for phone_part in phone_text.split("доб")
        ] if phone_text else None
        phone: Optional[str] = phone_with_add_code[0] if phone_with_add_code else None

        if phone and len(phone_with_add_code) > 1:
            phone_additional_code: Optional[str] = phone_with_add_code[1]
        else:
            phone_additional_code: Optional[str] = None

        phones.append(phone)
        additional_codes.append(phone_additional_code)

    return phones, additional_codes


def parse_address_n_postal_code(address_text: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    address_splitted: list[str] = address_text.strip().split(",", 1)

    postal_code: Optional[str] = None

    if len(address_splitted) == 1:
        address_str: Optional[str] = address_splitted[0]
    else:
        postal_code, address_str = address_splitted

    return None if postal_code is None else postal_code.strip(), address_str.strip()


def parse_phone(phone_l: str) -> str:
    phone_l = phone_l.replace("Телефон:", "").split("доб")[0]
    phone_l = phone_l.translate(str.maketrans({
        "\xa0": "",
        " ": "",
        "+": "",
        "-": "",
        "(": "",
        ")": "",
    }))

    return phone_l.strip()


def parse_teacher_name(boss_name: str) -> dict[str, str]:
    parts: list[str] = re.findall(TEACHER_FULLNAME_PATTERN, boss_name)[0]
    return dict(zip(TEACHER_NAME_PARTS, [part.capitalize() for part in parts]))


def is_struct_skipping(struct_name: str) -> bool:
    for skip_struct in STRUCTS_TO_SKIP:
        if skip_struct.lower() in struct_name.lower():
            return True
    return False


class CustomEncoder(json.JSONEncoder):
    def default(self, obj) -> dict[str, Any]:
        return obj.__dict__
