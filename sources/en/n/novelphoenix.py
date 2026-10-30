import logging
import re

from lncrawl.core import Chapter, LegacyCrawler, Volume
from lncrawl.core.models import SearchResult

logger = logging.getLogger(__name__)


class NovelFireCrawler(LegacyCrawler):
    search_url = "https://novelphoenix.com/search?keyword={}"
    base_url = ["https://novelphoenix.com/"]
    has_mtl = False
    has_manga = False
    can_search = True
    request_rate_limit = 3

    def read_novel_info(self) -> None:
        soup = self.get_soup(self.novel_url)

        self.novel_title = soup.find("h1").get_text(strip=True)
        self.novel_author = soup.select_one('span[itemprop="author"]').get_text(strip=True)

        img = soup.select_one(".cover img")
        self.novel_cover = self.absolute_url(img["src"])

        vol_id = 1
        base_url = self.novel_url + "/chapters"
        seen = set()
        page = 1

        while True:
            soup = self.get_soup(self.absolute_url(f"{base_url}?page={page}"))
            chapters = soup.select("ul.chapter-list li a")

            fresh = [a for a in chapters if a["href"] not in seen]
            if not fresh:
                break
            seen.update(a["href"] for a in fresh)

            for a in fresh:
                chap_id = len(self.chapters) + 1
                self.chapters.append(
                    Chapter(
                        id=chap_id,
                        volume=vol_id,
                        title=a.get("title") or a.get_text(strip=True),
                        url=self.absolute_url(a["href"]),
                    )
                )

            self.volumes.append(Volume(id=vol_id))
            vol_id += 1
            page += 1

    def download_chapter_body(self, chapter) -> str:
        soup = self.get_soup(chapter["url"])
        contents = soup.select_one("div#content")
        if not contents:
            return ""

        for tag in contents.find_all(['h1', 'h2', 'h3', 'p'], limit=10):
            text = tag.get_text(" ", strip=True)
            if re.match(r"(?i)^\s*(chapter|ch)\s*\d+", text):
                tag.decompose()

        return self.cleaner.extract_contents(contents)

    def search_novel(self, query):
        query = query.lower().replace(" ", "+")
        soup = self.get_soup(self.search_url.format(query))

        results = []
        for item in soup.select(".novel-item"):
            a = item.select_one("a")
            if not a:
                continue

            title = a.get("title") or a.get_text(strip=True)
            url = self.absolute_url(a.get("href"))

            chapters = item.select_one(".icon-book-open")
            rank = item.select_one(".icon-crown")

            results.append(
                SearchResult(
                    title=title,
                    url=url,
                    info=f"{chapters.text.strip() if chapters else '?'} | "
                         f"{rank.text.strip() if rank else '-'}",
                )
            )

        return results

        # A row runs number, title and timestamp together with no separators between the
        # spans, so the text has to be read with one inserted.
        text = SPACES.sub(" ", soup.get_text(" ", strip=True))
        chapter.title = POSTED_AGO.sub("", text).strip()
