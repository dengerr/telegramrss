"""
Этот код:
1. Создает простое FastAPI приложение
2. Определяет модель данных для элементов RSS
3. Содержит функцию для генерации XML RSS-ленты
4. Создает endpoint `/rss`, который возвращает RSS в формате XML

Для запуска:
1. Запустите сервер: `python main.py`
2. Откройте в браузере `http://localhost:8000/rss/{channel}`

Вы можете модифицировать функцию `generate_rss_feed` и данные в `items` под свои нужды.
"""
from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
import datetime
from typing import List

import markdown
from pydantic import BaseModel

from go import (
    cfg,
    format_chat_message_as_md,
    tz_hours,
    get_telegram_client,
)
from telegram_storage import TelegramChannelStorage

app = FastAPI()
app.mount("/vault", StaticFiles(directory="md/vault"), name="vault")
IMG_PREFIX = cfg.get('http', 'prefix')
rss_items_count = int(cfg.get('http', 'rss_items_count'))


class RSSFeed(BaseModel):
    title: str
    link: str
    description: str


class RSSItem(BaseModel):
    title: str
    link: str
    description: str
    pub_date: datetime.datetime


def generate_rss_feed(feed: RSSFeed, items: List[RSSItem]) -> str:
    rss_items = []
    for item in items:
        rss_items.append(f"""
        <item>
            <title>{item.title}</title>
            <link>{item.link}</link>
            <description>{item.description}</description>
            <pubDate>{item.pub_date.strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>
        </item>
        """)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>{feed.title}</title>
        <link>{feed.link}</link>
        <description>{feed.description}</description>
        {''.join(rss_items)}
    </channel>
</rss>"""


def create_telegram_md(chat):
    texts = []
    if path := chat.get('photo_webpage_path'):
        texts.append(f"\n\n![]({path})\n\n")
    if path := chat.get('photo_local_path'):
        texts.append(f"\n\n![]({IMG_PREFIX}{path})\n\n")
    texts.append(format_chat_message_as_md(chat['message']))
    return '\n\n'.join(texts)


@app.get("/rss/{name}/")
@app.get("/rss/{name}")
async def get_rss_feed(name):
    items = []
    storage = TelegramChannelStorage(name)
    # await update_channel_last(storage, last_count=rss_items_count)
    async with get_telegram_client() as client:
        await storage.dump_channel(client=client, last_count=rss_items_count, download_media=True)
    for chat in storage.chats_from_shelve_generator(last_count=rss_items_count):
        local_time = chat['date'] + datetime.timedelta(hours=tz_hours)
        link = f"https://t.me/{name}/{chat['id']}"
        md = create_telegram_md(chat)
        md.replace('#', 'SHARP')
        html = markdown.markdown(md)
        html = html.replace('SHARP', '#')
        items.append(RSSItem(
            title=local_time.strftime("%Y-%m-%d %H:%M"),
            link=link,
            description=html,
            pub_date=chat['date'],
        ))

    feed = RSSFeed(
        title=name,
        link=f'https://t.me/{name}/',
        description=f'{name} telegram feed',
    )

    rss_content = generate_rss_feed(feed, items)
    return Response(content=rss_content, media_type="application/xml")
