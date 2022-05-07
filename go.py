#!/bin/python
import datetime
import os
from pprint import pprint
import shelve
import shutil
import sys
import time
from configparser import ConfigParser

from telethon import TelegramClient, sync
import pandas as pd

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
    "economikal",
    "ctodaily",
    "pmdaily",
    "crimsondigest",
    "dengmetr",
    "ohmypy",
    "ovcharovcorporation",
    "pensiya35",
    "topapopa",
]

news_channels = [
    "varlamov_news",
    # "academeg_true_original",
    # "polzaSKIDKI",
    # "vandroukiru",
]

all_channels = one_post_channels + news_channels

# You will be asked to enter your mobile number- Enter mobile number with country code
# Enter OTP (For OTP check Telegram inbox)


def print_participants(group_username):
    participants = client.get_participants(group_username)

    # This code can be used to extracted upto 10k user's details
    # Let's get first name, last name and username

    firstname = []
    lastname = []
    username = []
    if len(participants):
        for x in participants:
            print(x)
            firstname.append(x.first_name)
            lastname.append(x.last_name)
            username.append(x.username)

    # list to data frame conversion

    data = {"first_name": firstname, "last_name": lastname, "user_name": username}

    userdetails = pd.DataFrame(data)
    print(userdetails)


def print_chats(chats):
    print(group_username)
    for chat in chats:
        print(chat.date, chat.id)
        print(chat.message)
        print()


def get_data_frame(chats):
    # Get message id, message, sender id, reply to message id, and timestamp
    message_id = []
    message = []
    sender = []
    reply_to = []
    time = []
    for chat in chats:
        message_id.append(chat.id)
        message.append(chat.message)
        sender.append(chat.from_id)
        reply_to.append(chat.reply_to_msg_id)
        time.append(chat.date)

    data = {
        "message_id": message_id,
        "message": message,
        "sender_ID": sender,
        "reply_to_msg_id": reply_to,
        "time": time,
    }
    df = pd.DataFrame(data)
    return df


group_username = "buryi_private"
# Group name can be found in group link
# (Example group link : https://t.me/c0ban_global, group name = 'c0ban_global')


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
    chats = client.get_messages(name, count)
    for chat in chats:
        if not chat.message:
            continue

        local_time = chat.date + datetime.timedelta(hours=tz_hours)
        # print(local_time.strftime("%Y-%m-%d %H-%M.md"))
        with open(f"md/{name}/"  + local_time.strftime("%Y-%m-%d %H-%M.md"), "w") as output:
            output.write("%s\n\n" % local_time.strftime("%Y-%m-%d %H:%M"))
            output.write(chat.message)
            output.write("\n\n")


def dump_channel(name):
    with shelve.open(f"db/{name}.shelve") as db:
        kwargs = {}
        if min_id := db.get("max_id"):
            kwargs["min_id"] = min_id
        chats = client.get_messages(name, 5000, **kwargs)
        # print(name, len(chats), chats.total)
        max_id = None

        if len(chats):
            for x in chats:
                if max_id is None:
                    max_id = x.id

                data = x.to_dict()
                if x.photo:
                    if path := x.download_media():
                        data['photo_local_path'] = save_path(name, path)
                if media := data.get('media'):
                    if webpage := media.get('webpage'):
                        if webpage.get('type') == 'photo' and 'url' in webpage:
                            data['photo_webpage_path'] = webpage['url']
                db[str(x.id)] = data

            if max_id is not None:
                db["max_id"] = max_id

        # print(db["max_id"])

        return [x.id for x in chats]


def md_from_shelve(name, ids=None, group_by_day=False):
    mkdir('md', name)
    with shelve.open(f"db/{name}.shelve") as db:
        if not ids:
            ids = list(range(int(db["max_id"])))
        chats = [db[str(_id)] for _id in ids if str(_id) in db]

        for chat in chats:
            # pprint(chat)
            if not chat.get('message'):
                continue

            local_time = chat['date'] + datetime.timedelta(hours=tz_hours)
            # print(local_time.strftime("%Y-%m-%d %H-%M.md"))
            with open(f"md/{name}/" + local_time.strftime("%Y-%m-%d %H-%M.md"), "w") as output:
                output.write("%s\n\n" % local_time.strftime("%Y-%m-%d %H:%M"))

                output.write(f"https://t.me/{name}/{chat['id']}\n")
                output.write(f"[](tg://resolve?domain={name}&post={chat['id']})\n\n")

                if path := chat.get('photo_webpage_path') or chat.get('photo_local_path'):
                    output.write(f"![]({path})\n\n")

                output.write(chat['message'])
                output.write("\n\n")


def print_from_shelve(name, ids, short=False):
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


def md_all():
    md_days("varlamov_news", 2)
    md_posts("economikal", 20)
    md_posts("dengmetr", 20)
    md_posts("pmdaily", 20)
    md_posts("ctodaily", 20)
    md_posts("crimsondigest", 20)


def dump_all():
    for name in all_channels:
        ids = dump_channel(name)
        if ids:
            print(f"## {name}")
            print_from_shelve(name, ids, short=True)


def print_one(name, _id):
    with shelve.open(f"db/{name}.shelve") as db:
        pprint(db.get(str(_id)))


def save_path(name, path):
    new_path = f"vault/{name}/{path}"
    mkdir("md", "vault", name)
    os.rename(path, 'md/' + new_path)
    return new_path


def download(name, _id):
    if name in "polzaSKIDKI vandroukiru varlamov_news".split():
        # no download for this channels
        return

    chat = client.get_messages(name, 1, ids=int(_id))

    if chat.photo:
        return save_path(name, chat.download_media())


if __name__ == "__main__":
    with TelegramClient("my", api_id, api_hash).start() as client:
        if "update" in sys.argv:
            dump_all()

        if "md" in sys.argv:
            for name in all_channels:
                md_from_shelve(name)

        if "print" in sys.argv:
            print_one(*sys.argv[-2:])

        if "download" in sys.argv:
            download(*sys.argv[-2:])
