import sys
from collections.abc import Mapping
from dataclasses import dataclass

from vchat.model import Contact
from vchat.model import Content
from vchat.model import User

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override


class RawMessage(Mapping):
    """
    不可变的映射类，用于表示从服务器接受到的原始信息，包含了微信消息常见的字段
    """

    @override
    def __len__(self):
        return len(self._other)

    @override
    def __iter__(self):
        return iter(self._other)

    @override
    def __getitem__(self, __key):
        return self._other[__key]

    def __init__(self, **kwargs):
        self.from_username: str = kwargs["FromUserName"]
        self.to_username: str = kwargs["ToUserName"]
        self.content: str = kwargs["Content"]
        self.status_notify_username: str = kwargs["StatusNotifyUserName"]
        self.img_width: int = kwargs["ImgWidth"]
        self.play_length: int = kwargs["PlayLength"]
        self.recommend_info: dict = kwargs["RecommendInfo"]
        self.status_notify_code: int = kwargs["StatusNotifyCode"]
        self.new_msg_id: int = kwargs["NewMsgId"]
        self.status: int = kwargs["Status"]
        self.voice_length: int = kwargs["VoiceLength"]
        self.forward_flag: int = kwargs["ForwardFlag"]
        self.app_msg_type: int = kwargs["AppMsgType"]
        self.ticket: int = kwargs["Ticket"]
        self.app_info: dict = kwargs["AppInfo"]
        self.url: str = kwargs["Url"]
        self.img_status: int = kwargs["ImgStatus"]
        self.msg_type: int = kwargs["MsgType"]
        self.img_height: int = kwargs["ImgHeight"]
        self.media_id: str = kwargs["MediaId"]
        self.msg_id: str = kwargs["MsgId"]
        self.file_name: str = kwargs["FileName"]
        self.has_product_id = kwargs["HasProductId"]
        self.file_size: str = kwargs["FileSize"]
        self.create_time: int = kwargs["CreateTime"]
        self.sub_msg_type: int = kwargs["SubMsgType"]

        self._other: dict = kwargs

    def set_content(self, content: str) -> None:
        self._other["Content"] = content
        self.content = content


@dataclass
class Message:
    from_: Contact
    to: Contact
    content: Content
    message_id: str
    chatroom_sender: User | None = None

    def __repr__(self):
        return f"<Message: {self.from_} -> {self.to}: {self.content}>"

    def todict(self):
        return {
            "from_": self.from_.todict(),
            "to": self.to.todict(),
            "content": self.content.todict(),
            "message_id": self.message_id,
            "chatroom_sender": (
                None if self.chatroom_sender is None else self.chatroom_sender.todict()
            ),
        }
