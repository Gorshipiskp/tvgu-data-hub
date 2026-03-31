from dataclasses import dataclass
from typing import Optional

from bs4 import BeautifulSoup, Tag

from ..misc import parse_name, parse_description, parse_address, parse_email, parse_website, parse_phone, \
    is_struct_skipping


@dataclass(frozen=True, kw_only=True)
class StructInfoTversu:
    name: str
    description: str
    address: str
    postal_code: str
    email: str
    website: str
    video_url: Optional[str]
    phone: str


def parse_structs_tversu_page(structs_tversu_page: str) -> list[StructInfoTversu]:
    soup: BeautifulSoup = BeautifulSoup(structs_tversu_page, "html.parser")

    structs_info_div: Tag = soup.find(class_="tvsu-ck-content")
    cur_struct_title: Tag = structs_info_div.find_next("h4")

    structs: list[StructInfoTversu] = []

    for cur_fac in [cur_struct_title, *cur_struct_title.find_next_siblings("h4")]:
        struct_name: str = parse_name(cur_fac.text)

        if is_struct_skipping(struct_name):
            continue

        description_tag: Tag = cur_fac.find_next("p")
        description: str = parse_description(description_tag.text)

        figure_tag: Optional[Tag] = cur_fac.find_next("figure")

        if figure_tag is None:
            video_url: None = None
        else:
            video_url: Optional[str] = figure_tag.findChild("oembed").get("url")  # noqa

        ul_tag: Tag = description_tag.find_next("ul")

        address_tag: Tag = ul_tag.find_next("li")
        postal_code, address = parse_address(address_tag.text)

        website_tag: Tag = address_tag.find_next("li")
        website: str = parse_website(website_tag.text)

        email_tag: Tag = website_tag.find_next("li")
        email: str = parse_email(email_tag.text)

        phone_tag: Tag = email_tag.find_next("li")
        phone: str = parse_phone(phone_tag.text)

        structs.append(
            StructInfoTversu(
                name=struct_name,
                description=description,
                address=address,
                postal_code=postal_code,
                email=email,
                website=website,
                video_url=video_url,
                phone=phone
            )
        )

    return structs
