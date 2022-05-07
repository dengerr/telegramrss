from telethon import TelegramClient

from go import api_id, api_hash


def get_contact_id(client, name):
    for dialog in client.iter_dialogs():
        if dialog.name == name:
            return dialog.id

with TelegramClient("my", api_id, api_hash).start() as client:
    if contact_id := get_contact_id(client, "Михаил Dteam"):
        client.send_message(contact_id, "Привет! Как дела?", silent=True)
