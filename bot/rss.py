import feedparser, aiohttp
from typing import List, Dict

FEEDS = [
    "https://fishering.ru/feed/",
    "https://ribakov.net/feed/",
    "https://www.rybolov-elit.ru/feed/"
]

async def fetch_news() -> List[Dict]:
    """Возвращает список свежих записей (title, summary, link, published)"""
    items = []
    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:  # 3 записи с каждого сайта
                items.append({
                    "title": entry.title,
                    "summary": entry.summary,
                    "link": entry.link,
                    "published": entry.get("published", "")
                })
        except Exception:
            continue  # пропускаем недоступные ленты
    return items
