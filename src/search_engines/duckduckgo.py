import aiohttp
import asyncio
from aiohttp_socks import ProxyConnector
import logging
import re
from datetime import datetime, timezone
import json
from markdownify import markdownify as md
from typing import Literal

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

class DuckDuckGo_Search:
    def __init__(self, proxy: str = None, session: aiohttp.ClientSession = None):
        self.proxy = proxy
        self.session = session
        self.close_session = session is None
        self.headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.7',
            'priority': 'u=1, i',
            'referer': 'https://duckduckgo.com/',
            'sec-ch-ua': '"Not-A.Brand";v="99", "Brave";v="157", "Chromium";v="157"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'sec-gpc': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36',
        }
        self.vqd = {}
        self.home_page_response = {}
    async def __aenter__(self):
        if self.session is None:
            self.session = aiohttp.ClientSession(
                connector=ProxyConnector.from_url(self.proxy) if self.proxy else aiohttp.TCPConnector()
            )
        return self
    async def __aexit__(self, exc_type, exc, tb):
        if self.close_session:
            await self.session.close()
    async def autocomplete(self, query: str, key_locale: str = "wt-wt"):
        """
        Args:
            query (str): Current query to autocomplete
            key_locale (str): Which country and language to use, for example 'us-en' is United States, english, 'wt-wt' (default) is world-wide
        Returns: 
            list[str]: A list containing potential autocompletes
        """
        autocomplete_url = "https://duckduckgo.com/ac/"
        params = {
            'q': query,
            "kl": key_locale,
            "vertical": "homepage"
        }
        async with self.session.get(autocomplete_url, headers=self.headers, params=params) as r:
            logger.debug(f"Sent {r.method} request to {r.url}, status: {r.status}")
            try:
                response = json.loads(await r.text())
            except Exception as e:
                logger.debug(f"Failed to json parse autocompletion response: {e}, text: {await r.text()}")
                return []
        try:
            phrases = [phrase.get('phrase') for phrase in response]
        except Exception as e:
            logger.debug(f"Failed to autocomplete: {e}, response: {response}")
            return []
        return phrases
    async def _search_homepage(self, query: str):
        if self.home_page_response.get(query) is not None:
            return self.home_page_response
        search_url = "https://duckduckgo.com/"
        vqd_pattern = r"vqd=\"([^\"]*?)\""
        now = datetime.now(timezone.utc)
        params = {
            'ia': 'web',
            'origin': 'funnel_home_website',
            't': 'h_',
            'we_feature_name': 'search-from-homepage',
            'we_started_at': now.strftime(f"%H:%M:%S_{now.microsecond // 1000:03d}"),
            'q': query,
        }
        async with self.session.get(search_url, headers=self.headers, params=params) as r:
            logger.debug(f"Sent {r.method} request to {r.url}, status: {r.status}")
            response = await r.text()
        self.home_page_response[query] = response
        self.vqd[query] = (await asyncio.to_thread(re.search, vqd_pattern, response)).group(1)
        return response
    class image_filter:
        def __init__(self, hide_ai_images: Literal[1, 0] = False, safe_search: Literal[1, -1] = 1, 
                     time: Literal['Week', 'Day', 'Month', 'Year'] = None,
                     size: Literal['Large', 'Small', 'Medium', 'Wallpaper'] = None,
                     color: Literal['color', 'Monochrome', 'Red', 'Orange',
                                    'Yellow', 'Green', 'Blue', 'Purple', 'Pink',
                                    'Brown', 'Black', 'Gray', 'Teal', 'White'] = None,
                    image_type: Literal['photo', 'clipart', 'gif', 'transparent',
                                        'line'] = None,
                    layout: Literal['Square', 'Tall', 'Wide'] = None,
                    license: Literal['any', 'Public', 'Share', 'ShareCommercially',
                                     'Modify', 'ModifyCommercially'] = None):
            self.payload = {
                "hide_ai_images": hide_ai_images,
                "time": time,
                "size": size,
                "color": color,
                "type": image_type,
                "color": color,
                "layout": layout,
                "license": license,
            }
            self.safe_search = safe_search
        def __str__(self):
            string = ""
            for key, value in self.payload.items():
                if value is not None:
                    string += f"{key}:{value},"
            return string.rstrip(",")
        def change_value(self, key: str, value):
            if self.payload.get(key) is None and key != "safe_search" and key != "image_type":
                raise KeyError(f"Key not in filter payload, available keys:\n{', '.join(list(self.payload.keys()))}")
            if key == "image_type":
                self.payload['type'] = value
            elif key == "safe_search":
                self.safe_search = value
            else:
                self.payload[key] = value
    async def image_search(self, query: str, locale: str = "us-en", country_code: str = "US", filter: image_filter = None,
                           offset: int = None):
        """
        Args:
            query (str): text to search up
            locale (str): region and language used when searching
            country_code (str): country searched from
            filter (image_filter): filter for specific images using the DuckDuckGo_Search.image_filter class
            offset (int): skip offset amount of images
        Returns:
            dict: contains entries in a list and offset index to use in next request
        """
        if self.vqd.get(query) is None:
            await self._search_homepage(query)
        params = {
            'o': 'json',
            'q': query,
            'l': locale,
            'vqd': self.vqd.get(query),
            'ct': country_code,
        }
        if filter is not None:
            params['f'] = str(filter)
            params['p'] = filter.safe_search
        if offset is not None:
            params['s'] = offset
        image_search_url = "https://duckduckgo.com/i.js"
        async with self.session.get(image_search_url, headers=self.headers, params=params) as r:
            logger.debug(f"Sent {r.method} request to {r.url}, status: {r.status}")
            response = await r.content.read()
        images_result = await asyncio.to_thread(json.loads, response)
        result = {
            "entries": [],
        }
        for img in images_result.get('results', []):
            result['entries'].append(
                {
                    "discovery_date": img.get("discovery_date"),
                    "encoding_format": img.get("encoding_format"),
                    "width": img.get("width"),
                    "height": img.get("height"),
                    "image_url": img.get("image"),
                    "source": img.get("source"),
                    "thumbnail": img.get("thumbnail"),
                    "title": img.get("title"),
                    "source_url": img.get("url")
                }
            )
        if images_result.get("vqd"):
            self.vqd[query]= list(images_result.get("vqd", {}).values())[0]
        result['next_offset'] = len(result['entries']) + 2
        return result
    class page_layout_not_found(Exception):
        def __init__(self, *args):
            super().__init__(*args)
    async def search(self, query: str, next_link: str = None):
        """
        Args:
            query (str): text to search up
            next_link (str): Optional, next_link received from previous search
        Returns:
            dict: dictionary containing entries and a next_link"""
        d_js_pattern = r"https://links\.duckduckgo\.com/d\.js\?(?:[^\"]*?)\""
        page_layout_pattern = r"DDG\.pageLayout\.load\('d',(\[\{(?:.*?)\}\])\)"
        news_pattern = r"DDG\.duckbar\.load\('news', (\{(?:.*?)\})\)"
        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.7',
            'priority': 'u=1',
            'referer': 'https://duckduckgo.com/',
            'sec-ch-ua': '"Not-A.Brand";v="99", "Brave";v="157", "Chromium";v="157"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'script',
            'sec-fetch-mode': 'no-cors',
            'sec-fetch-site': 'same-site',
            'sec-gpc': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36',
        }
        if next_link is None:
            response = await self._search_homepage(query)
            d_js_link = (await asyncio.to_thread(re.search, d_js_pattern, response)).group()
        else:
            d_js_link = next_link
        async with self.session.get(d_js_link, headers=headers) as r:
            logger.debug(f"Sent {r.method} request to {r.url}, status: {r.status}")
            response = await r.text()
        tasks = [
            asyncio.create_task(
                asyncio.to_thread(re.search, page_layout_pattern, response)
            ),
            asyncio.create_task(
                asyncio.to_thread(re.search, news_pattern, response)
            )
        ]
        results = await asyncio.gather(*tasks)
        if not results[0]:
            raise self.page_layout_not_found(f"Couldn't find page layout in d.js")
        page_layout = json.loads(results[0].group(1))
        
        entries = []
        next_link = None
        for entry in page_layout:
            if entry.get("n"):
                next_link = "https://links.duckduckgo.com" + entry.get("n")
                continue
            entries.append(
                {
                    "snippet": md(entry.get("a", "")),
                    "url": entry.get("c"),
                    "site_type": entry.get("da"),
                    "date_published": entry.get("e"),
                    "source": entry.get("s"),
                    "title": entry.get("t"),
                    "site_name": entry.get("sn"),
                }
            )
        if results[1]:
            news = json.loads(results[1].group(1))
            for post in news.get("results", []):
                entries.append(
                    {
                        "snippet": md(post.get("excerpt", "")),
                        "url": post.get("url"),
                        "site_type": "news",
                        "date_published": datetime.fromtimestamp(post.get("date", 0)).isoformat(),
                        "relative_time": post.get("relative_time"),
                        "source": post.get("syndicate"),
                        "title": post.get("title"),
                        "site_name": post.get("source"),
                    }
                )
        return {
            "entries": entries,
            "next_page": next_link
        }

