import copy
import enum
from abc import ABC
from typing import Mapping


class Contact(Mapping, ABC):
    """
    Contact 是抽象类，可以是 User, Chatroom, Mp
    """

    def __getitem__(self, __key):
        return self._other[__key]

    def __len__(self):
        return len(self._other)

    def __iter__(self):
        return iter(self._other)

    def __init__(self, **kwargs) -> None:
        self.username: str = kwargs["UserName"]

        self._other: dict = kwargs

    def update_from_dict(self, d: dict) -> "Contact":
        dic = copy.deepcopy(d)
        dic.update(d)
        return self.__class__(**dic)

    @staticmethod
    def constructor(data: dict) -> "Contact":
        if data["UserName"].startswith("@@"):
            return Chatroom(**data)
        return User(**data)  # 因为verify_flag不跟随username，所以无法判断是否是公众号


class Chatroom(Contact):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.members: dict[str, User] = {}  # 群聊的成员列表
        if "MemberList" in self:
            for member in self["MemberList"]:
                self.members.update({member["UserName"]: User(**member)})

    def update_from_dict(self, d: dict) -> "Chatroom":
        dic = copy.deepcopy(d)
        dic.update(d)
        return self.__class__(**dic)

    def __repr__(self):
        return f"<Chatroom {self._other.get('NickName') or self.username}>"


class User(Contact):
    def __deepcopy__(self, memo):
        return User(**self._other)

    def update_from_dict(self, d: dict) -> "User":
        dic = copy.deepcopy(d)
        dic.update(d)
        return self.__class__(**dic)

    def __repr__(self):
        return f"<User {self._other.get('NickName', self.username)}>"


class MassivePlatform(Contact):
    def update_from_dict(self, d: dict) -> "MassivePlatform":
        dic = copy.deepcopy(d)
        dic.update(d)
        return self.__class__(**dic)

    def __repr__(self):
        return f"<MassivePlatform {self._other.get('NickName', self.username)}>"


class MediaTypes(enum.Enum):
    DOC = "doc"
    IMG = "pic"
    VIDEO = "video"


class ContactTypes(enum.Flag):
    USER = enum.auto()
    CHATROOM = enum.auto()
    MP = enum.auto()
    ALL = USER | CHATROOM | MP
