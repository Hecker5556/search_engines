# Search Engines
This module grants access to searching up information through multiple search engines through scraping. Uses asynchronous programming and aiohttp for fast results.
Currently supported search engines:
* Duckduckgo

## Installation
### UV:
```bash
uv add "git+https://github.com/hecker5556/search_engines"
```
### pip:
```bash
pip install "git+https://github.com/hecker5556/search_engines"
```

## Usage
### Python
```py
from search_engines import Search_Engines
import asyncio

async def main():
    sg = Search_Engines()
    result = await sg.search("sp500 news")
    print(result)
    image_results = await sg.image_search("cats")
    print(image_results)

    # Providing your own aiohttp.ClientSession for speed
    import aiohttp
    async with aiohttp.ClientSession() as session:
        sg = Search_Engines(session=session)
    
    # Providing proxy
    sg = Search_Engines(proxy="socks5://username:password@ip:port")

    # Getting access to a specific engine
    from search_engines import DuckDuckGo_Search

    async with DuckDuckGo_Search() as ddgs:
        result = await ddgs.search("sp500 news")
        print(result)
        image_results = await ddgs.image_search("cats")
        print(image_results)

asyncio.run(main())
```

### Commandline
```bash
usage: search-engines [-h] [--engine {duckduckgo}] [--search-type {normal,images}] query

positional arguments:
  query                 text to search up

options:
  -h, --help            show this help message and exit
  --engine {duckduckgo}, -e {duckduckgo}
                        which search engine to use
  --search-type {normal,images}, -s {normal,images}
                        search type (normal, images)
```