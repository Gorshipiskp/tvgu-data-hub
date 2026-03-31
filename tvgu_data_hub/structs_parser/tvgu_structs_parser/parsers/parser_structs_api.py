from dataclasses import dataclass
from typing import Optional

from ..config import STRUCTS_API_URL
from ..misc import is_struct_skipping


@dataclass(frozen=True, kw_only=True)
class StructInfoAPI:
    name: str
    shortname: str


def parser_structs_api(structs_api_response: dict[str, list[dict[str, str]]]):
    if "data" not in structs_api_response:
        raise ValueError(f"Некорректный ответ от сервера на запрос от {STRUCTS_API_URL}")

    structs: list[StructInfoAPI] = []

    for struct in structs_api_response["data"]:
        struct_name: Optional[str] = struct.get("facultyName")
        struct_shortname: Optional[str] = struct.get("facultyShort")

        if struct_name is None or struct_shortname is None:
            raise ValueError(f"Некорректный ответ от сервера на запрос от {STRUCTS_API_URL}")

        if is_struct_skipping(struct_name):
            continue

        structs.append(
            StructInfoAPI(
                name=struct_name,
                shortname=struct_shortname
            )
        )

    return structs
