import argparse
import asyncio
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

from .misc import Teacher, CustomEncoder
from .parser import get_all_tvgu_teachers


@dataclass(frozen=True, kw_only=True)
class Args:
    prettify: bool
    output: Optional[str]
    output_directory: Optional[str]
    output_auto: Optional[str]


def dump_teachers(teachers: list[Teacher], output_path: str, prettify: bool) -> None:
    json.dump(
        teachers,
        open(output_path, "w+", encoding="UTF-8"),
        ensure_ascii=False,
        indent=2 if prettify else None,
        cls=CustomEncoder
    )


async def main(args: Args) -> None:
    teachers: list[Teacher] = await get_all_tvgu_teachers()

    if args.output is not None or args.output_auto:
        if args.output_auto is not None:
            output_path: str = f"teachers-{date.today()}.json"
        else:
            output_path: str = args.output

        if args.output_directory is not None:
            directory: Path = Path(args.output_directory)
            directory.mkdir(parents=True, exist_ok=True)
            output_path: Path = directory / output_path

        dump_teachers(teachers, output_path, args.prettify)


def parse_args() -> Args:
    parser = argparse.ArgumentParser(description="Парсер преподавателей ТвГУ")

    parser.add_argument("-o", "--output", help="Путь к выходному файлу для экспорта расписаний")
    parser.add_argument("-od", "--output-directory", help="Путь к директории для экспорта расписаний")
    parser.add_argument("-oa", "--output-auto", action="store_true",
                        help="Автоматическое формирование имени выходного файла в виде даты")
    parser.add_argument("-p", "--prettify", action="store_true", help="Форматированный вывод JSON")

    args: argparse.Namespace = parser.parse_args()

    return Args(
        prettify=args.prettify,
        output=args.output,
        output_directory=args.output_directory,
        output_auto=args.output_auto
    )


if __name__ == "__main__":
    # Python >=3.10

    cur_args: Args = parse_args()

    if cur_args.output is not None and cur_args.output_auto is not None:
        raise ValueError("Одновременно можно использовать параметр -o и -oa")

    asyncio.run(main(cur_args))
