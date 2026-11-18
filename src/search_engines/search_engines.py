from .duckduckgo import DuckDuckGo_Search
import aiohttp
import asyncio
from typing import Literal

class Search_Engines:
    def __init__(self, proxy: str = None, session: aiohttp.ClientSession = None):
        self.proxy = proxy
        self.session = session
    async def search(self, query: str, engine: Literal['duckduckgo'] = 'duckduckgo', **options):
        match engine:
            case "duckduckgo":
                async with DuckDuckGo_Search(self.proxy, self.session) as ddgs:
                    result = await ddgs.search(query, **options)
        return result
    async def image_search(self, query: str, engine: Literal['duckduckgo'] = 'duckduckgo', **options):
        match engine:
            case "duckduckgo":
                async with DuckDuckGo_Search(self.proxy, self.session) as ddgs:
                    result = await ddgs.image_search(query, **options)
        return result
async def async_main():
    import argparse
    import json
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="text to search up")
    parser.add_argument("--engine", "-e", help="which search engine to use", default="duckduckgo", choices=[
        "duckduckgo"
    ])
    parser.add_argument("--search-type", "-s", help="search type (normal, images)", default="normal", choices=[
        "normal", "images"
    ])
    args = parser.parse_args()
    sg = Search_Engines()
    if args.search_type == "normal":
        result = await sg.search(args.query, engine=args.engine)
    elif args.search_type == "images":
        result = await sg.image_search(args.query, engine=args.engine)
    print(json.dumps(result, indent=4))
def main():
    asyncio.run(async_main())