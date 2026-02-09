#!/bin/python
import asyncio
from contextlib import asynccontextmanager
import datetime
import markdown
import os
from pprint import pprint
import shelve
import shutil
import sys
import time
from configparser import ConfigParser

from telethon import TelegramClient

from telegram_storage import TelegramChannelStorage

base_path = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(base_path, "config.ini")
if not os.path.exists(config_path):
    shutil.copyfile('config.example.ini', config_path)
cfg = ConfigParser()
cfg.read(config_path)

api_id = cfg.get("telegram", "api_id")
api_hash = cfg.get("telegram", "api_hash")
tz_hours = int(cfg.get("telegram", "tz_hours"))

one_post_channels = [
    "crimsondigest",
]
news_channels = [
]
all_channels = one_post_channels + news_channels



# chats = client.get_messages(group_username, 10, min_id=28756, reverse=True)  # good
# chats = client.iter_messages(group_username, 100, offset_date=datetime.datetime(2022,3,17), max_id=28714, reverse=True)
# 10, offset_id=28751 - вниз по истории, 28741-28750


def md_day(name, date, max_id=None):
    chats = client.get_messages(name, 100, offset_date=date, reverse=True)
    if not len(chats):
        return

    with open(f"md/{name}/" + date.strftime("%Y-%m-%d.md"), "w") as output:
        output.write("# %s\n\n" % date.strftime("%Y-%m-%d"))
        for chat in chats:
            if not chat.message:
                continue

            local_time = chat.date + datetime.timedelta(hours=tz_hours)
            output.write("**%s** " % local_time.strftime("%H:%M"))
            output.write(chat.message)
            output.write("\n\n")
    return chats[0].id


def md_days(name, days):
    date = datetime.datetime.now().date()  # .replace(hour=tz_hours, minute=0)
    first_id = None
    for x in range(days):
        print(name, date)
        first_id = md_day(name, date, first_id) or first_id
        date = date - datetime.timedelta(days=1)
        time.sleep(1)


def mkdir(*names):
    dirname = os.path.join(os.getcwd(), *names)
    if not os.path.exists(dirname):
        os.mkdir(dirname)


def md_posts(name, count):
    mkdir('md', name)
    chats = client.iter_messages(name, count)
    for chat in chats:
        if not chat.message:
            continue

        local_time = chat.date + datetime.timedelta(hours=tz_hours)
        # print(local_time.strftime("%Y-%m-%d %H-%M.md"))
        with open(f"md/{name}/"  + local_time.strftime("%Y-%m-%d %H-%M.md"), "w") as output:
            output.write("%s\n\n" % local_time.strftime("%Y-%m-%d %H:%M"))
            output.write(chat.message)
            output.write("\n\n")




def md_from_shelve(name, ids=None, group_by_day=False, one_html_file=False):
    mkdir('md', name)
    result = []
    header = None
    storage = TelegramChannelStorage(name)
    for chat in storage.chats_from_shelve_generator(ids):
        local_time = chat['date'] + datetime.timedelta(hours=tz_hours)
        # print(local_time.strftime("%Y-%m-%d %H-%M.md"))
        if not one_html_file:
            result = []
        prev_header, header = header, local_time.strftime("%Y-%m")
        if one_html_file and prev_header != header:
            result.append("%s\n===\n\n" % header)
        result.append("%s\n---\n\n" % local_time.strftime("%Y-%m-%d %H:%M"))

        link = f"https://t.me/{name}/{chat['id']}"
        result.append(f'[{link}]({link})\n')
        result.append(f"[](tg://resolve?domain={name}&post={chat['id']})\n\n")

        if path := chat.get('photo_webpage_path') or chat.get('photo_local_path'):
            result.append(f"![]({path})\n\n")

        result.append(format_chat_message_as_md(chat['message']))
        result.append("\n\n")
        if not one_html_file:
            with open(f"md/{name}/" + local_time.strftime("%Y-%m-%d %H-%M.md"), "w") as output:
                output.write("".join(result))
    if one_html_file:
        # blacklist = ('twitter', 'finance.yahooo', 'www.telegraph.co.uk',
        # 'uk.finance.yahoo', 'www.svoboda.org', 'www.facebook.com',
        # 'www.bbc.com', 'www.washingtonpost.com', 'pbs.twimg.com')

        md = "".join(result)
        md = md.replace('#', 'SHARP')
        output = markdown.markdown(md)
        output = output.replace('SHARP', '#')

        filtered_result = []
        for line in output.split('\n'):
            # внешние ссылки тормозят сборку epub
            # blacklisted = [1 for domain in blacklist if f'src="https://{domain}' in line]
            blacklisted = 'src="https://' in line
            if not blacklisted:
                filtered_result.append(line)
        output = '\n'.join(filtered_result)

        return output


def format_chat_message_as_md(message):
    # Двойные переводы строк надо оставить как есть,
    # а одинарные дополнить двумя пробелами
    message = message.replace('\n\n', 'ABZAC')
    message = message.replace('\n', '  \n')
    message = message.replace('ABZAC', '\n\n')
    return message


def format_chat_message_as_html(message):
    # Двойные переводы строк надо заменить на абзацы,
    # но сначала одинарные превратить в br
    message = message.replace('\n\n', 'ABZAC')
    message = message.replace('\n', '<br>\n')
    message = message.replace('ABZAC', '</p>\n\n<p>')
    return message


def print_from_shelve(name, ids, short=False, maxi=None):
    mkdir('md', name)
    with shelve.open(f"db/{name}.shelve") as db:
        chats = [db[str(_id)] for _id in ids if str(_id) in db]

    for chat in chats:
        local_time = chat['date'] + datetime.timedelta(hours=tz_hours)

        if short:
            if 'message' not in chat:
                continue
            print("**%s** " % local_time.strftime("%H:%M"),)
            print(chat['message'])
            print()
        else:
            print("%s\n" % local_time.strftime("%Y-%m-%d %H:%M"))

            print(f"https://t.me/{name}/{chat['id']}")
            print(f"[](tg://resolve?domain={name}&post={chat['id']})\n")

            if path := chat.get('photo_webpage_path') or chat.get('photo_local_path'):
                print(f"![]({path})\n")

            print(chat['message'])
            print("\n")
            if entities := chat.get('entities'):
                for entity in entities:
                    print(entity['_'], chat['message'][entity['offset']:entity['offset']+entity['length']])
                    if url := entity.get('url'):
                        print(url)


async def dump_all():
    for name in all_channels:
        storage = TelegramChannelStorage(name)
        ids = await storage.dump_channel(client)
        if ids:
            print(f"## {name}")
            print_from_shelve(name, ids, short=True)


def print_one(name, _id):
    with shelve.open(f"db/{name}.shelve") as db:
        pprint(db.get(str(_id)))


def print_last(name, count=3):
    print(name)
    with shelve.open(f"db/{name}.shelve") as db:
        max_id = db.get("max_id")
    assert isinstance(max_id, int)
    ids = list(range(max_id - count, max_id + 1))
    print_from_shelve(name, ids, short=False)


def save_path(name, path):
    new_path = f"vault/{name}/{path}"
    mkdir("md", "vault", name)
    os.rename(path, 'md/' + new_path)
    return new_path


def download(name, _id):
    chat = client.iter_messages(name, 1, ids=int(_id))

    if chat.photo:
        return save_path(name, chat.download_media())


def parse_file(filename):
    variables = {}
    names = []
    with open(filename, 'r', encoding='utf8') as fp:
        for line in fp.readlines():
            cmd, name, *options = line.split()
            if cmd == '=:':
                variables[name] = ' '.join(options)
            if cmd == '=>':
                names.append(name)
    return variables, names


async def process_file(filename, client: TelegramClient):
    variables, names = parse_file(filename)

    cmd = variables.pop('action')
    if not cmd:
        return
    options = variables

    if options.get('update') == 'true':
        for name in names:
            storage = TelegramChannelStorage(name)
            ids = await storage.dump_channel(client)

    for name in names:
        storage = TelegramChannelStorage(name)
        if cmd == 'update':
            ids = await storage.dump_channel(client)
            # if ids:
            #     print(f"## {name}")
            #     print_from_shelve(name, ids, short=True)
        elif cmd == 'md':
            md_from_shelve(name)
        elif cmd == 'html_book':
            # Сделать из телеграм канала книгу html.
            # Через sigil ее можно преобразовать в epub.
            output = md_from_shelve(name, one_html_file=True)
            with open(f'md/{name}.html', 'w') as fp:
                fp.write(output)
        elif cmd == 'print':
            # print one post
            print_one(name, options['id'])
        elif cmd == "download":
            download(name, options['id'])
        elif cmd == "download_all":
            print(f'download all from {name}')
            await storage.download_all(client)
        elif cmd == "print_last":
            try:
                count = int(options.get('count', 1))
            except (TypeError, ValueError):
                count = 1
            print_last(name, count)


@asynccontextmanager
async def get_telegram_client() -> TelegramClient:
    async with TelegramClient("my", api_id, api_hash) as client:
        yield client


async def run(files):
    have_txt = [1 for file in files if '.txt' in file]
    if have_txt:
        async with get_telegram_client() as client:
            client: TelegramClient
            for filename in files:
                await process_file(filename, client)
    else:
        args = tuple(files)
        match args:
            case 'book', name:
                output = md_from_shelve(name, one_html_file=True)
                with open(f'md/{name}.html', 'w') as fp:
                    fp.write(output)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        py_filename, *files = sys.argv
        asyncio.run(run(files))
