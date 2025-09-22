import aiosqlite, os
from typing import List

DB_PATH = os.getenv("DB_PATH", "posted.db")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "CREATE TABLE IF NOT EXISTS posted_links (link TEXT PRIMARY KEY)"
        )
        await db.commit()

async def was_posted(link: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT 1 FROM posted_links WHERE link = ?", (link,))
        return await cur.fetchone() is not None

async def mark_posted(links: List[str]):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany("INSERT OR IGNORE INTO posted_links(link) VALUES (?)", [(l,) for l in links])
        await db.commit()
