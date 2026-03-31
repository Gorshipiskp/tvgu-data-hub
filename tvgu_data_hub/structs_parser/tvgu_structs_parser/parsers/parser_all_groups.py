from collections import defaultdict
from dataclasses import dataclass
from typing import Optional, Any

from ..config import ALL_GROUPS_API_URL
from ..misc import is_struct_skipping


@dataclass(frozen=True, kw_only=True)
class StructInfoGroups:
    name: str
    code: str
    groups: list[str]


def get_struct_code_from_group_name(group_name: str) -> str:
    return group_name.split("-")[0].strip()


def parse_all_groups(all_groups_response: dict[str, list[dict[str, str]]]):
    if "groups" not in all_groups_response:
        raise ValueError(f"Неверный формат ответа от {ALL_GROUPS_API_URL}")

    structs_groups: defaultdict[str, dict[str, Any]] = defaultdict(lambda: {"groups": [], "code": None})

    for group in all_groups_response["groups"]:
        struct_name: Optional[str] = group.get("facultyName")
        group_name: Optional[str] = group.get("groupName")

        if struct_name is None or group_name is None:
            raise ValueError(f"Неверный формат группы: {group}")

        if is_struct_skipping(struct_name):
            continue

        if structs_groups[struct_name]["code"] is None:
            structs_groups[struct_name]["code"] = get_struct_code_from_group_name(group_name)

        structs_groups[struct_name]["groups"].append(group_name)

    return [
        StructInfoGroups(
            name=struct_name,
            code=structs_groups[struct_name]["code"],
            groups=structs_groups[struct_name]["groups"],
        )
        for struct_name in structs_groups
    ]
