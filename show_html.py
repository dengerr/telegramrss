#!/bin/env python
import sys

from to_epub import TelegramToEpub


if __name__ == "__main__":
    if len(sys.argv) > 1:
        py_filename, name, post_id = sys.argv
        obj = TelegramToEpub([name])
        print(obj.html_from_shelve(name, [post_id]))
