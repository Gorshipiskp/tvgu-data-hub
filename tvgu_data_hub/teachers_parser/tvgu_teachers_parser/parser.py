import aiohttp
import bs4
from aiohttp import ClientResponse

from .config import TEACHERS_TvGU_PAGE_URL
from .misc import Teacher, parse_teacher_record


async def get_teachers_page() -> str:
    async with aiohttp.ClientSession() as session:
        page: ClientResponse = await session.get(TEACHERS_TvGU_PAGE_URL)

        return await page.text()


def parse_teachers(text: str) -> list[Teacher]:
    soup: bs4.BeautifulSoup = bs4.BeautifulSoup(text, "html.parser")

    teachers: list[Teacher] = [
        parse_teacher_record(teacher_record) for teacher_record in soup.find_all(itemprop="teachingStaff")
    ]

    return teachers


async def get_all_tvgu_teachers() -> list[Teacher]:
    return parse_teachers(await get_teachers_page())
