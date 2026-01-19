from dataclasses import dataclass, fields
from typing import Any, Optional

from schedule_parser.tvgu_schedule_parser.misc import TeacherSmall
from teachers_parser.tvgu_teachers_parser.misc import Teacher


@dataclass(frozen=True, kw_only=True)
class PK:
    id: int
    entity: Any


@dataclass(frozen=True, kw_only=True)
class TeacherAggregated(Teacher):
    id: int
    has_lessons: bool


@dataclass(frozen=True, kw_only=True)
class TeacherSmallAggregated(TeacherSmall):
    id: int
    has_lessons: bool


# Функция для создания уникальных идентификаторов на основе итогово списка сущностей
# (должно гарантироваться, что этот список является конечным, то есть, иных сущностей того же рода нигде не встретится)
def create_entities_pks(entities: list[PK], key_name: Optional[str] = None, skip_none_keys: bool = False,
                        *, custom_key_getter: Optional[callable] = None) -> dict[PK, PK]:
    fks: dict[PK, PK] = {}

    if key_name is None and custom_key_getter is None:
        raise ValueError("`key_name` или `custom_key_getter` должны быть выставлены")
    if key_name is not None and custom_key_getter is not None:
        raise ValueError("`key_name` и `custom_key_getter` не могут быть выставлены одновременно")

    for entity_id, entity in enumerate(entities):
        if custom_key_getter is None:
            if isinstance(entity, dict):
                key: PK = entity.get(key_name)
            else:
                key: PK = getattr(entity, key_name)
        else:
            key: PK = custom_key_getter(entity)

        if key is None:
            if skip_none_keys:
                continue
            raise KeyError(f"Ключ {key_name} отсутствует в сущности: {entity}")

        if key in fks:
            raise ValueError(f"Конфликт имён: {key} и {fks[key].id} ({entity})")

        fks[key] = PK(
            id=entity_id,
            entity=entity
        )

    return fks


def inherit_instance_dataclass(class_: callable, entity: PK, *to_filter, **extra_data) -> PK:
    data = {
        f.name: getattr(entity, f.name)
        for f in fields(type(entity)) if f.name not in to_filter
    }
    return class_(**extra_data, **data)
