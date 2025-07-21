#!/bin/python
import datetime
import markdown
from pprint import pprint
import shelve
import sys
from configparser import ConfigParser
from pathlib import Path

from ebooklib import epub

from telegram_storage import TelegramChannelStorage
from go import format_chat_message_as_md, tz_hours, parse_file

OUTPUT_DIR = './output'


class TelegramToEpub:
    def __init__(self, names) -> None:
        self.names = names
        self.imgs = []
        self.book = epub.EpubBook()

    def save(self):
        names = self.names
        channels = []
        with shelve.open(f"db/max_id.shelve") as max_id_db:
            for name in names:
                storage = TelegramChannelStorage(name)
                if name not in max_id_db:
                    # новый канал, считается прочитаным до текущего момента
                    max_id_db[name] = storage.max_id
                    print(f'Новый канал {name}')
                    continue
                ids = range(max_id_db[name] + 1, storage.max_id + 1)
                if not len(ids):
                    continue
                output = self.html_from_shelve(name, ids)
                if output:
                    # print(output)
                    channels.append((name, output))

                max_id_db[name] = storage.max_id
        if channels:
            print('Создан epub для каналов', ', '.join(name for name, _ in channels))
            self.add_imgs_to_epub()
            self.create_epub(channels, 'Telegram digest', datetime.datetime.now().isoformat())

    def html_from_shelve(self, name, ids=None):
        result = [f'{name}\n===\n\n']
        storage = TelegramChannelStorage(name)
        for chat in storage.chats_from_shelve_generator(ids):
            local_time = chat['date'] + datetime.timedelta(hours=tz_hours)

            link = f"https://t.me/{name}/{chat['id']}"

            if chat.get('fwd_from'):
                result.append(f'**ПЕРЕСЛАНО из {chat["fwd_from"]["from_name"]}**\n\n')
            if reply_to := chat.get('reply_to'):
                # TODO откуда?
                if reply_to.get('quote_text'):
                    result.append(f'> {reply_to['quote_text']}\n\n')
                else:
                    result.append(f'**ЦИТАТА** id {reply_to["reply_to_msg_id"]}\n\n')
            if media := chat.get('media'):
                if media.get('video'):
                    result.append('**ВИДЕО**\n\n')
                if document := media.get('document'):
                    doc_names = [attr['file_name']
                                 for attr in document.get('attributes', [])
                                 if attr['_'] == 'DocumentAttributeFilename']
                    result.append(f'**ПРИЛОЖЕНИЯ** {", ".join(doc_names)}\n\n')

            if path := chat.get('photo_local_path'):
                self.imgs.append(f'md/{path}')
                result.append(f"![](md/{path})\n\n")
            elif path := chat.get('photo_webpage_path'):
                result.append(f"![]({path})\n\n")

            message = chat['message']
            if entities := chat.get('entities'):
                for entity in reversed(entities):
                    inner = message[entity['offset']:entity['offset']+entity['length']]
                    match entity['_']:
                        case 'MessageEntityTextUrl':
                            changed = f"[{inner}]({entity['url']})"
                        case 'MessageEntityBold':
                            changed = f"**{inner}**"
                        case 'MessageEntityItalic':
                            changed = f"_{inner}_"
                        case 'MessageEntityBlockquote':
                            changed = '\n'.join(f"> {line}" for line in inner.split('\n'))
                        case _:
                            changed = inner
                    message = ''.join((
                        message[:entity['offset']],
                        changed,
                        message[entity['offset']+entity['length']:]
                    ))

            result.append(format_chat_message_as_md(message))
            result.append("\n\n")
            result.append(f"[tg](tg://resolve?domain={name}&post={chat['id']})  ")
            result.append(f'[{name}/{chat["id"]}]({link}) {local_time.strftime("%Y-%m-%d %H:%M")}')
            result.append("\n\n---\n\n")

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

    def add_imgs_to_epub(self):
        for j, img in enumerate(self.imgs):
            with open(Path(img), 'rb') as img_file:
                content = img_file.read()
            eimg = epub.EpubImage(uid=f'image_{j}', file_name=img, content=content)
            self.book.add_item(eimg)

    def create_epub(self, channels, author, name):
        book = self.book
        book.set_title(name)
        book.add_author(author)
        book.set_language("ru")
        chapters = []
        toc = []

        for i, (channel_name, html_content) in enumerate(channels):
            chapter = epub.EpubHtml(title=channel_name, file_name=f"chap{i}.xhtml", lang="ru")
            chapter.content = html_content

            book.add_item(chapter)
            chapters.append(chapter)
            toc.append(chapter)
        book.spine = chapters
        book.toc = toc
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        epub.write_epub(f"{OUTPUT_DIR}/{author} - {name}.epub", book)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        py_filename, *names = sys.argv
        have_txt = [1 for file in names if '.txt' in file]
        if have_txt:
            for filename in names:
                variables, names = parse_file(filename)
                processor = TelegramToEpub(names)
                processor.save()
        else:
            processor = TelegramToEpub(names)
            processor.save()
