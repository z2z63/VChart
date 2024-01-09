import asyncio
from queue import Queue
from typing import Optional, TYPE_CHECKING

from vchat.model import User, Chatroom, MassivePlatform

if TYPE_CHECKING:
    from vchat.model import Message


class Storage:
    def __init__(self):
        self.myname: Optional[str] = None
        self.nick_name: Optional[str] = None
        self.members: dict[str, User] = {}
        self.mps: dict[str, MassivePlatform] = {}
        self.chatrooms: dict[str, Chatroom] = {}
        self.msgs: asyncio.Queue[Message] = asyncio.Queue()
        self.las_input_username = None

    def dumps(self):
        return {
            "myname": self.myname,
            "nick_name": self.nick_name,
            "members": self.members,
            "mps": self.mps,
            "chatrooms": self.chatrooms,
            "las_input_username": self.las_input_username,
        }

    def loads(self, jar: dict):
        self.myname = jar["myname"]
        self.nick_name = jar["nick_name"]
        self.members = jar["members"]
        self.mps = jar["mps"]
        self.chatrooms = jar["chatrooms"]
        self.las_input_username = jar["las_input_username"]

    def clear(self):
        self.myname = None
        self.nick_name = None
        self.members.clear()
        self.mps.clear()
        self.chatrooms.clear()
        self.las_input_username = None
        self.msgs = Queue(-1)
