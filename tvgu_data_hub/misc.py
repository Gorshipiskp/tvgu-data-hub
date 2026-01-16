import json
from collections import defaultdict
from typing import Optional


def list_to_dict_by_key(list_: list, key_name: str, skip_none_keys: bool = False, could_be_collisions: bool = False,
                        *, handle_key_func: callable = lambda x: x) -> dict:
    dict_: defaultdict = defaultdict(lambda: [] if could_be_collisions else (lambda: None))

    for entity in list_:
        if isinstance(entity, dict):
            key: Optional[str] = entity.get(key_name)
        else:
            key: Optional[str] = getattr(entity, key_name)

        if key is None:
            if skip_none_keys:
                continue
            raise KeyError(f"Ключ {key_name} отсутствует в словаре: {entity}")

        if could_be_collisions:
            dict_[handle_key_func(key)].append(entity)
        else:
            dict_[handle_key_func(key)] = entity

    return dict(dict_)


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        return obj.__dict__
