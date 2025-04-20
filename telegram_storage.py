import os
import shelve

from telethon import TelegramClient


def mkdir(*names):
    dirname = os.path.join(os.getcwd(), *names)
    if not os.path.exists(dirname):
        os.mkdir(dirname)


def save_path(name, path):
    new_path = f"vault/{name}/{path}"
    mkdir("md", "vault", name)
    os.rename(path, 'md/' + new_path)
    return new_path


class TelegramChannelStorage():
    def __init__(self, name):
        self.name = name
        self.shelve_file_name = f"db/{name}.shelve"

    def chats_from_shelve_generator(self, ids=None, last_count=None):
        with shelve.open(self.shelve_file_name) as db:
            if not ids:
                ids = list(range(1, int(db["max_id"]) + 1))
                if last_count is not None:
                    ids = ids[-last_count:]
            chats = [db[str(_id)] for _id in ids if str(_id) in db]

            for chat in chats:
                if chat.get('message'):
                    yield chat

    async def dump_channel(self, client: TelegramClient, last_count:int = 0, download_media=False):
        with shelve.open(self.shelve_file_name) as db:
            kwargs = {}
            limit = 5000
            if min_id := db.get("max_id"):
                # докачка на основе данных из базы
                kwargs["min_id"] = min_id
            elif last_count:
                # при начальной загрузке можно только последние сообщения, начальные не грузятся
                limit = last_count
            else:
                # начальная загрузка, ВСЕ сообщения (макс 5000)
                # нет смысла грузить медиа для такого количества,
                # надо потом вызвать self.download_all
                download_media = False

            chats = client.iter_messages(self.name, limit, **kwargs)
            max_id = None
            ids = []

            async for x in chats:
                ids.append(x.id)
                if max_id is None:
                    max_id = x.id

                data = x.to_dict()
                if download_media and x.photo:
                    if path := await x.download_media():
                        data['photo_local_path'] = save_path(self.name, path)
                if media := data.get('media'):
                    if webpage := media.get('webpage'):
                        if webpage.get('type') == 'photo' and 'url' in webpage:
                            data['photo_webpage_path'] = webpage['url']
                db[str(x.id)] = data

            if max_id is not None:
                db["max_id"] = max_id

            return ids

    async def download_all(self, client):
        """
        Загрузить для всех сохраненных сообщений недостающие медиа
        """
        with shelve.open(self.shelve_file_name) as db:
            max_id = db["max_id"]
            for i in range(1, int(max_id) + 1):
                if str(i) not in db:
                    continue
                chat = db[str(i)]
                if 'photo_local_path' in chat:
                    continue
                if (chat.get('media') or {}).get('photo'):
                    chats = client.iter_messages(self.name, limit=1, max_id=i+1)
                    async for x in chats:
                        x: Message
                        if path := await x.download_media():
                            chat['photo_local_path'] = save_path(self.name, path)
                            db[str(i)] = chat
