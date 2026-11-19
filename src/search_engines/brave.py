from curl_cffi import AsyncSession, Response
import asyncio
import re
import chompjs
import json
import logging
from markdownify import markdownify as md

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

class Brave_Search:
    def __init__(self, proxy: str = None, session: AsyncSession = None):
        self.proxy = proxy
        self.session = session
        self.close_session = session is None
        self.headers = {
            'accept': '*/*',
            'accept-language': 'pl,en;q=0.9,en-GB;q=0.8,en-US;q=0.7',
            'dnt': '1',
            'priority': 'u=1, i',
            'referer': 'https://search.brave.com/',
            'sec-ch-ua': '"Not-A.Brand";v="99", "Microsoft Edge";v="157", "Chromium";v="157"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36 Edg/157.0.0.0',
        }
    async def __aenter__(self):
        if self.session is None:
            self.session = AsyncSession(proxy=self.proxy)
        return self
    async def __aexit__(self, exc_type, exc, tb):
        if self.close_session:
            await self.session.close()
    async def autocomplete(self, query: str, country_code: str = "us"):
        params = {
            'q': query,
            'rich': 'false',
            'source': 'web',
            'country': country_code.lower()
        }
        autocomplete_url = "https://search.brave.com/api/suggest"
        r: Response = await self.session.get(autocomplete_url, headers=self.headers, params=params, stream=True)
        response = await asyncio.to_thread(json.loads, (await r.atext()))
        return response[1]
    @staticmethod
    def meta_to_url(meta: dict[str, str]):
        url = f"{meta.get('scheme')}://{meta.get('hostname')}/"
        path = meta.get("path")
        state = 0
        index = 0
        buf = ""
        while (index < len(path)):
            if path[index] == "›":
                state = 1
            elif state == 1 and path[index] != " ":
                buf += path[index]
            elif len(buf) > 1 and path[index] == " ":
                state = 0
                url += buf + "/"
                buf = ""
            index+=1
        if len(buf) > 0:
            url += buf
        return url
    async def image_search(self, query: str):
        params = {
            'q': query,
            'source': 'web'
        }
        image_search_url = "https://search.brave.com/images/__data.json"
        r: Response = await self.session.get(image_search_url, headers=self.headers, params=params, stream=True)
        data = (await asyncio.to_thread(json.loads, (await r.acontent())))["nodes"][1]["data"]
        data.append(None)
        body_index = data[0].get("body")
        response_index = data[body_index].get("response")
        results_index = data[response_index].get("results")
        results_indexes = data[results_index]
        result = {
            "entries": []
        }
        for index in results_indexes:
            result_entry = data[index]
            thumbnail = data[result_entry.get("thumbnail", -1)]
            if thumbnail == None:
                thumbnail = {}
            entry = {
                "title": data[result_entry.get("title", -1)],
                "url": data[result_entry.get("url", -1)],
                "snippet": data[result_entry.get("description", -1)],
                "discovery_date": data[result_entry.get("page_fetched", -1)],
                "date_published": data[result_entry.get("page_age", -1)],
                "image_url": data[thumbnail.get("original", -1)],
                "width": data[thumbnail.get("width", -1)],
                "height": data[thumbnail.get("height", -1)],
            }
            result["entries"].append(entry)
        return result

    async def search(self, query: str):
        params = {
            'q': query,
            'source': 'web'
        }
        search_url = "https://search.brave.com/search"
        data_pattern = r",\(function\([^\)]*?\)\{return (\{type:\"data\".*?\)\))\],"
        r: Response = await self.session.get(search_url, headers=self.headers, params=params)
        response = r.text
        data = await asyncio.to_thread(re.search, data_pattern, response)
        data = data.group(1)
        parsed_data = await asyncio.to_thread(chompjs.parse_js_object, data)
        result = {
            "entries": []
        }
        brave_results = parsed_data.get("data", {}).get("body", {}).get("response", {}).get("web", {}).get("results", [])
        for i in brave_results:
            if len(i.get("description", "")) == 1:
                continue
            entry = {
                "title": i.get("title"),
                "snippet": md(i.get("description")),
                "date_published": i.get("page_age", ""),
                "url": self.meta_to_url(i.get("meta_url", {})),
                "site_name": i.get("profile", {}).get("name")
            }
            if entry['date_published'] == "void 0":
                entry["date_published"] = None
            result["entries"].append(
                entry
            )

        return result
async def main():
    import json
    async with Brave_Search() as bs:
        result = await bs.image_search("nvidia news")
    with open("result.json", "w", encoding="utf-8") as f1:
        json.dump(result, f1, ensure_ascii=False)
if __name__ == "__main__":
    asyncio.run(main())