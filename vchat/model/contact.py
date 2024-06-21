import copy
import enum
from abc import ABC
from typing import Mapping


class ContactTypes(enum.Flag):
    USER = enum.auto()
    CHATROOM = enum.auto()
    CHATROOM_MEMBER = enum.auto()
    MP = enum.auto()
    ALL = USER | CHATROOM | MP | CHATROOM_MEMBER


class Contact(Mapping, ABC):
    """
    Contact 是抽象类，可以是 User, Chatroom, Mp
    """
    type = ContactTypes.ALL

    def __getitem__(self, __key):
        return self._other[__key]

    def __len__(self):
        return len(self._other)

    def __iter__(self):
        return iter(self._other)

    def __init__(self, **kwargs) -> None:
        self.username: str = kwargs["UserName"]
        self.nickname: str = kwargs.get("NickName", "")
        self._other: dict = kwargs

    def update_from_dict(self, d: dict) -> "Contact":
        dic = copy.deepcopy(d)
        dic.update(d)
        return self.__class__(**dic)

    def todict(self):
        pass

    @staticmethod
    def constructor(data: dict) -> "Contact":
        if data["UserName"].startswith("@@"):
            return Chatroom(**data)
        return User(**data)  # 因为verify_flag不跟随username，所以无法判断是否是公众号


class Chatroom(Contact):
    type = ContactTypes.CHATROOM

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.members: dict[str, ChatroomMember] = {}  # 群聊的成员列表
        for member in self.get("MemberList", []):
            self.members.update({member["UserName"]: ChatroomMember(self, **member)})

    def update_from_dict(self, d: dict) -> "Chatroom":
        dic = copy.deepcopy(d)
        dic.update(d)
        return self.__class__(**dic)

    def __repr__(self):
        return f"<Chatroom {self._other.get('NickName') or self.username}>"

    def todict(self):
        return {
            "username": self.username,
            "nickname": self.nickname,
            "members": {k: v.todict() for k, v in self.members.items()},
        }


class User(Contact):
    type = ContactTypes.USER

    def __deepcopy__(self, memo):
        return User(**self._other)

    def update_from_dict(self, d: dict) -> "User":
        dic = copy.deepcopy(d)
        dic.update(d)
        return self.__class__(**dic)

    def __repr__(self):
        return f"<User {self._other.get('NickName', self.username)}>"

    def todict(self):
        return {
            "username": self.username,
            "nickname": self.nickname,
        }


class MassivePlatform(Contact):
    type = ContactTypes.MP

    def update_from_dict(self, d: dict) -> "MassivePlatform":
        dic = copy.deepcopy(d)
        dic.update(d)
        return self.__class__(**dic)

    def __repr__(self):
        return f"<MassivePlatform {self._other.get('NickName', self.username)}>"

    def todict(self):
        return {
            "username": self.username,
            "nickname": self.nickname,
        }


class ChatroomMember(Contact):
    type = ContactTypes.CHATROOM_MEMBER

    def __init__(self, chatroom: Chatroom, **kwargs):
        super().__init__(**kwargs)
        self.display_name: str = kwargs.get("DisplayName") or kwargs["NickName"]
        self.from_chatroom: Chatroom = chatroom

    def __repr__(self):
        return f"<ChatroomMember {self.display_name} in {self.from_chatroom}>"


class MediaTypes(enum.Enum):
    DOC = "doc"
    IMG = "pic"
    VIDEO = "video"
