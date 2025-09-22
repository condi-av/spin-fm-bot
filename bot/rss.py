import feedparser
from typing import List, Dict
from db import was_posted, mark_posted  # Изменено здесь

FEEDS = [
    "https://fishing-74.ru/rss.xml",
    "https://huntfish.ru/rss.xml",
    "https://rybalka.guru/feed/",
    "https://ribalka-v-rossii.ru/feed/"
]

async def fetch_new_posts() -> List[Dict]:
    """Возвращает ТОЛЬКО новые записи (без дубликатов)"""
    candidates = []
    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                candidates.append({
                    "title": entry.title,
                    "summary": entry.summary,
                    "link": entry.link,
                    "published": entry.get("published", "")
                })
        except Exception:
            continue
    # фильтруем
    new_links = [c["link"] for c in candidates if not await was_posted(c["link"])]
    new_posts = [c for c in candidates if c["link"] in new_links]
    if new_links:
        await mark_posted(new_links)
    return new_posts
