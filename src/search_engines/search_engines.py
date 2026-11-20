from .duckduckgo import DuckDuckGo_Search
from .brave import Brave_Search
import aiohttp
import asyncio
from typing import Literal
from curl_cffi import AsyncSession

available_engines_type = Literal['duckduckgo', 'brave']
available_engines = [
    "duckduckgo", "brave"
]

class Search_Engines:
    def __init__(self, proxy: str = None, aiohttp_session: aiohttp.ClientSession = None, curl_cffi_session: AsyncSession = None):
        self.proxy = proxy
        self.aiohttp_session = aiohttp_session
        self.curl_cffi_session = curl_cffi_session
    async def search(self, query: str, engine: available_engines_type = 'duckduckgo', **options):
        match engine:
            case "duckduckgo":
                async with DuckDuckGo_Search(self.proxy, self.aiohttp_session) as ddgs:
                    result = await ddgs.search(query, **options)
            case "brave":
                async with Brave_Search(self.proxy, self.curl_cffi_session) as bs:
                    result = await bs.search(query)
        return result
    async def image_search(self, query: str, engine: available_engines_type = 'duckduckgo', **options):
        match engine:
            case "duckduckgo":
                async with DuckDuckGo_Search(self.proxy, self.aiohttp_session) as ddgs:
                    result = await ddgs.image_search(query, **options)
            case "brave":
                async with Brave_Search(self.proxy, self.curl_cffi_session) as bs:
                    result = await bs.image_search(query)
        return result
async def async_main():
    import argparse
    import json
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="text to search up")
    parser.add_argument("--engine", "-e", help="which search engine to use", default="duckduckgo", choices=available_engines)
    parser.add_argument("--search-type", "-s", help="search type (normal, images)", default="normal", choices=[
        "normal", "images"
    ])
    args = parser.parse_args()
    sg = Search_Engines()
    if args.search_type == "normal":
        result = await sg.search(args.query, engine=args.engine)
    elif args.search_type == "images":
        result = await sg.image_search(args.query, engine=args.engine)
    print(json.dumps(result, indent=4, ensure_ascii=False))
def main():
    asyncio.run(async_main())