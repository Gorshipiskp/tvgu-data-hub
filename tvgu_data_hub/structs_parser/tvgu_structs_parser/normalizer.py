from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from .parsers.parser_all_groups import StructInfoGroups
from .parsers.parser_structs import Department, StructInfo, StructType
from .parsers.parser_structs_api import StructInfoAPI
from .parsers.parser_structs_tversu_page import StructInfoTversu


@dataclass(frozen=True, kw_only=True)
class TvGUStructBase:
    name: str
    shortname: str
    description: str
    code: str
    type: StructType
    address: Optional[str]
    postal_code: Optional[str]
    website: Optional[str]
    email: str
    phones: Optional[list[str]]
    phones_additional_codes: Optional[list[str]]
    video_url: Optional[str]

    def _identify(self) -> tuple[str, str, StructType, str, str, str]:
        return (
            self.name,
            self.shortname,
            self.type,
            self.code,
            self.address,
            self.postal_code

        )

    def __hash__(self) -> int:
        return hash(self._identify())

    def __eq__(self, other) -> bool:
        if isinstance(other, TvGUStructBase):
            return self._identify() == other._identify()
        return NotImplemented


@dataclass(frozen=True, kw_only=True)
class TvGUStruct(TvGUStructBase):
    departments: list[Department]
    groups: list[str]
    boss_name: Optional[str]
    boss_surname: Optional[str]
    boss_patronymic: Optional[str]


def normalize_structs(
        departments: list[Department],
        structs: list[StructInfo],
        structs_tversu: list[StructInfoTversu],
        structs_from_api: list[StructInfoAPI],
        structs_from_groups: list[StructInfoGroups]
) -> list[TvGUStruct]:
    structs_pre_handle: dict[str, dict] = defaultdict(lambda: {
        "departments": [],
        "struct": None,
        "struct_not_full": None,
        "struct_from_api": None,
        "struct_from_groups": None
    })

    for department in departments:
        structs_pre_handle[department.struct_name]["departments"].append(department)

    for struct in structs:
        structs_pre_handle[struct.name]["struct"] = struct

    for struct in structs_tversu:
        structs_pre_handle[struct.name]["struct_not_full"] = struct

    for struct in structs_from_api:
        structs_pre_handle[struct.name]["struct_from_api"] = struct

    for struct in structs_from_groups:
        structs_pre_handle[struct.name]["struct_from_groups"] = struct

    final_structs: list[TvGUStruct] = []

    for struct_name, struct_info in structs_pre_handle.items():
        if not all(struct_info.values()):
            raise ValueError(f"Структура ТвГУ {struct_name} имеет не всю информацию: {struct_info}")

        struct: StructInfo = struct_info["struct"]
        struct_tversu: StructInfoTversu = struct_info["struct_not_full"]
        struct_from_api: StructInfoAPI = struct_info["struct_from_api"]
        struct_from_groups: StructInfoGroups = struct_info["struct_from_groups"]

        if struct.address is None:
            address: Optional[str] = struct_tversu.address
        else:
            address: str = struct.address

        final_structs.append(
            TvGUStruct(
                name=struct_name,
                shortname=struct_from_api.shortname,
                description=struct_tversu.description,
                code=struct_from_groups.code,
                type=struct.type,
                boss_name=struct.boss_name,
                boss_surname=struct.boss_surname,
                boss_patronymic=struct.boss_patronymic,
                address=address,
                postal_code=struct_tversu.postal_code or struct.postal_code,
                website=struct.website or struct_tversu.website,
                email=struct.email or struct_tversu.email,
                phones=struct.phones,
                phones_additional_codes=struct.phones_additional_codes,
                video_url=struct_tversu.video_url,
                departments=struct_info.get("departments", []),
                groups=struct_from_groups.groups
            )
        )

    return final_structs
