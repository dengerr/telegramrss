import sys
from pprint import pprint

from telegram_storage import TelegramChannelStorage


if __name__ == "__main__":
    if len(sys.argv) > 1:
        py_filename, name, post_id = sys.argv
        storage = TelegramChannelStorage(name)
        for chat in storage.chats_from_shelve_generator([post_id]):
            pprint(chat)
