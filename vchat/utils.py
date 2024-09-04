import html
import os
import re
import subprocess
import sys
from collections.abc import Iterable
from typing import Any

from vchat import config
from vchat.model import Contact
from vchat.config import logger

emojiRegex = re.compile(r'<span class="emoji emoji(.{1,10})"></span>')


def clear_screen():
    os.system("cls" if config.OS == "win32" else "clear")


def emoji_formatter(text: str) -> str:
    """_emoji_deebugger is for bugs about emoji match caused by WeChat backstage
    like :face with tears of joy: will be replaced with :cat face with tears of joy:
    """

    def _emoji_debugger(_text):
        s = _text.replace(
            '<span class="emoji emoji1f450"></span',
            '<span class="emoji emoji1f450"></span>',
        )  # fix missing bug

        def __fix_miss_match(m):
            return '<span class="emoji emoji%s"></span>' % (
                {
                    "1f63c": "1f601",
                    "1f639": "1f602",
                    "1f63a": "1f603",
                    "1f4ab": "1f616",
                    "1f64d": "1f614",
                    "1f63b": "1f60d",
                    "1f63d": "1f618",
                    "1f64e": "1f621",
                    "1f63f": "1f622",
                }.get(m.group(1), m.group(1))
            )

        return emojiRegex.sub(__fix_miss_match, s)

    def _emoji_formatter(m):
        s = m.group(1)
        if len(s) == 6:
            return (
                ("\\U%s\\U%s" % (s[:2].rjust(8, "0"), s[2:].rjust(8, "0")))
                .encode("utf8")
                .decode("unicode-escape", "replace")
            )
        elif len(s) == 10:
            return (
                ("\\U%s\\U%s" % (s[:5].rjust(8, "0"), s[5:].rjust(8, "0")))
                .encode("utf8")
                .decode("unicode-escape", "replace")
            )
        else:
            return (
                ("\\U%s" % m.group(1).rjust(8, "0"))
                .encode("utf8")
                .decode("unicode-escape", "replace")
            )

    text = _emoji_debugger(text)
    text = emojiRegex.sub(_emoji_formatter, text)
    return text


def msg_formatter(text):
    text = emoji_formatter(text)
    text = text.replace("<br/>", "\n")
    text = html.unescape(text)
    return text


def print_qr(file_path):
    if config.OS == "linux":
        subprocess.call(["xdg-open", file_path])
    elif config.OS == "win32":
        subprocess.call(["start", file_path])
    elif config.OS == "darwin":
        subprocess.call(["open", file_path])
    else:
        raise NotImplementedError


def search_dict_list(contact_list: list["Contact"], key, value):
    """Search a list of dict
    * return dict with specific value & key"""
    for i in contact_list:
        if i.get(key) == value:
            return i


def print_line(msg, one_line=False):
    if one_line:
        sys.stdout.write(" " * 40 + "\r")
        sys.stdout.flush()
    else:
        sys.stdout.write("\n")
    sys.stdout.write(
        msg.encode(sys.stdin.encoding or "utf8", "replace").decode(
            sys.stdin.encoding or "utf8", "replace"
        )
    )
    sys.stdout.flush()


def get_image_postfix(data):
    data = data[:20]
    if b"GIF" in data:
        return "gif"
    elif b"PNG" in data:
        return "png"
    elif b"JFIF" in data:
        return "jpg"
    return ""


def update_info_dict(old_info_dict, new_info_dict):
    """only normal values will be updated here
    because newInfoDict is normal dict, so it's not necessary to consider templates
    """
    for key, value in new_info_dict.items():
        if any((isinstance(value, t) for t in (tuple, list, dict))):
            pass  # these values will be updated somewhere else
        elif old_info_dict.get(key) is None or value not in (None, "", "0", 0):
            old_info_dict[key] = value


def batch(data: Iterable[Any], n: int = 1):
    ret_val = []
    for i, item in enumerate(data):
        if (i + 1) % n == 0:
            yield ret_val
            ret_val = []
        else:
            ret_val.append(item)
    if len(ret_val) != 0:
        yield ret_val
    return
