import asyncio

from .normalizer import normalize_structs, TvGUStruct
from .parsers.parser_all_groups import StructInfoGroups, parse_all_groups
from .parsers.parser_structs import Department, StructInfo, parse_structs_page
from .parsers.parser_structs_api import StructInfoAPI, parser_structs_api
from .parsers.parser_structs_tversu_page import StructInfoTversu, parse_structs_tversu_page
from .structs_requests import get_structs_tversu_page, get_structs_page, get_structs_small_info, get_all_groups


async def get_all_tvgu_structs(show_warnings: bool = False) -> list[TvGUStruct]:
    tversu_page, structs_page, structs_small_page, all_groups_page = await asyncio.gather(
        get_structs_tversu_page(),
        get_structs_page(),
        get_structs_small_info(),
        get_all_groups(),
    )

    structs_n_departments: dict[str, list] = parse_structs_page(structs_page, show_warnings)
    structs: list[StructInfo] = structs_n_departments["structs"]
    departments: list[Department] = structs_n_departments["departments"]
    structs_tversu: list[StructInfoTversu] = parse_structs_tversu_page(tversu_page)
    structs_from_api: list[StructInfoAPI] = parser_structs_api(structs_small_page)
    structs_from_groups: list[StructInfoGroups] = parse_all_groups(all_groups_page)

    structs_names: set[str] = set(struct.name for struct in structs)
    departments_structs_names: set[str] = set(department.struct_name for department in departments)
    structs_tversu_names: set[str] = set(struct.name for struct in structs_tversu)
    structs_from_api_names: set[str] = set(struct.name for struct in structs_from_api)
    structs_from_groups_names: set[str] = set(struct.name for struct in structs_from_groups)

    if not (structs_names == structs_tversu_names == structs_from_api_names == structs_from_groups_names):
        all_sets: dict[str, set[str]] = {
            "structs": structs_names,
            "departments_structs_names": departments_structs_names,
            "structs_tversu": structs_tversu_names,
            "structs_from_api": structs_from_api_names,
            "structs_from_groups": structs_from_groups_names,
        }

        all_names: set[str] = set.union(*all_sets.values())

        missing: dict[str, set[str]] = {
            name: all_names - values
            for name, values in all_sets.items()
        }

        for name, missing_names in missing.items():
            if missing_names:
                print(f"У `{name}` нет следующих структур: {missing_names}")

        raise ValueError("Несовпадение множества названий структур в расписаниях")

    return normalize_structs(
        departments,
        structs,
        structs_tversu,
        structs_from_api,
        structs_from_groups
    )
