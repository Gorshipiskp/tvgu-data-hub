import argparse
import asyncio
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

from .hub import get_all_tvgu_data
from .misc import CustomEncoder


@dataclass(frozen=True, kw_only=True)
class Args:
    prettify: bool
    output: Optional[str]
    output_directory: Optional[str]
    output_auto: Optional[str]


def dump_teachers(data: dict[str, list], output_path: str, prettify: bool) -> None:
    json.dump(
        data,
        open(output_path, "w+", encoding="UTF-8"),
        ensure_ascii=False,
        indent=2 if prettify else None,
        cls=CustomEncoder
    )


async def main(args: Args) -> None:
    all_data: dict[str, list] = await get_all_tvgu_data()

    if args.output is not None or args.output_auto:
        if args.output_auto is not None:
            output_path: str = f"all_tvgu_data-{date.today()}.json"
        else:
            output_path: str = args.output

        if args.output_directory is not None:
            directory: Path = Path(args.output_directory)
            directory.mkdir(parents=True, exist_ok=True)
            output_path = directory / output_path

        dump_teachers(all_data, output_path, args.prettify)


def parse_args() -> Args:
    parser = argparse.ArgumentParser(description="Парсер всей информации ТвГУ")

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

    args: Args = parse_args()

    if args.output is not None and args.output_auto is not None:
        raise ValueError("Одновременно можно использовать параметр -o и -oa")

    asyncio.run(main(args))
