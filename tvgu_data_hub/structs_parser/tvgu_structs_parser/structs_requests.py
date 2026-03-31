import aiohttp

from .config import STRUCTS_PAGE_URL, STRUCTS_TVERSU_PAGE_URL, STRUCTS_API_URL, ALL_GROUPS_API_URL


async def get_structs_page() -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(STRUCTS_PAGE_URL) as response:
            return await response.text()


async def get_structs_small_info() -> dict[str, list[dict[str, str]]]:
    async with aiohttp.ClientSession() as session:
        async with session.get(STRUCTS_API_URL) as response:
            return await response.json()


async def get_structs_tversu_page() -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(STRUCTS_TVERSU_PAGE_URL) as response:
            return await response.text()


async def get_all_groups() -> dict[str, list[dict[str, str]]]:
    async with aiohttp.ClientSession() as session:
        async with session.get(ALL_GROUPS_API_URL) as response:
            return await response.json()
