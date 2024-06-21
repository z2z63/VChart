import enum
import re
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from lxml import etree

from vchat.config import logger

if TYPE_CHECKING:
    from vchat.model import RawMessage
    from vchat.net.interface import NetHelperInterface


class ContentTypes(enum.Flag):
    UNKNOWN = enum.auto()
    TEXT = enum.auto()
    IMAGE = enum.auto()
    VIDEO = enum.auto()
    VOICE = enum.auto()
    ATTACH = enum.auto()
    SYSTEM = enum.auto()
    REVOKE = enum.auto()
    DEFAULT = enum.auto()
    USELESS = enum.auto()
    LINK = enum.auto()
    ALL = UNKNOWN | TEXT | IMAGE | VIDEO | VOICE | ATTACH | SYSTEM | REVOKE | DEFAULT | USELESS | LINK


@dataclass
class Content(ABC):
    type = ContentTypes.UNKNOWN

    @staticmethod
    def build_from_content_trimmed_raw_message(
            rmsg: "RawMessage", net_helper: "NetHelperInterface", is_at_me: bool | None
    ) -> "Content":
        msg_type = rmsg["MsgType"]
        content: "Content"
        if msg_type == 1:
            content = TextContent.from_raw_message(rmsg, is_at_me)
        elif msg_type == 3 or msg_type == 47:
            content = ImageContent.from_raw_message(rmsg, net_helper)
        elif msg_type == 34:
            content = VoiceContent.from_raw_message(rmsg, net_helper)
        elif msg_type == 37:
            content = DefaultContent.from_raw_message(rmsg, "新的好友")
        elif msg_type == 42:  # 个人名片
            # raise NotImplementedError
            # TODO: 实现个人名片，处理HTML转义
            content = DefaultContent.from_raw_message(rmsg, "xxx")
        elif msg_type == 43 or msg_type == 62:
            content = VideoContent.from_raw_message(rmsg, net_helper)
        elif msg_type == 49:
            content = Content._parse_sharing_message(rmsg, net_helper)
        elif msg_type == 10000:
            content = SystemContent.from_raw_message(rmsg)
        elif msg_type == 10002:
            content = RevokeContent.from_raw_message(rmsg)
        elif msg_type in [40, 43, 50, 52, 53, 9999]:
            content = UselessContent.from_raw_message(rmsg, "useless message")
        else:
            logger.warning("未知的消息类型: %s\n%s", msg_type, rmsg["Content"])
            content = DefaultContent.from_raw_message(rmsg, "xxx")
        return content

    @staticmethod
    def _parse_sharing_message(
            rmsg: "RawMessage", net_helper: "NetHelperInterface"
    ) -> "Content":
        app_msg_type = rmsg["AppMsgType"]
        if app_msg_type == 0:
            return DefaultContent.from_raw_message(rmsg, rmsg["Content"])
        elif app_msg_type == 5:
            return LinkContent.from_raw_message(rmsg)
        elif app_msg_type == 6:
            return AttachContent.from_raw_message(rmsg, net_helper)
        elif app_msg_type == 8:
            return ImageContent.from_raw_message(rmsg, net_helper)
        elif app_msg_type == 17:
            return DefaultContent.from_raw_message(rmsg, rmsg["FileName"])
        elif app_msg_type == 2000:
            regx = r"\[CDATA\[(.+?)\][\s\S]+?\[CDATA\[(.+?)\]"
            ma = re.search(regx, rmsg["Content"])
            if ma is not None:
                data = ma.group(2).split("\u3002")[0]
            else:
                data = "You may found detailed info in Content key."
            return DefaultContent.from_raw_message(rmsg, data)
        else:
            logger.warning("未知的分享消息类型: %s\n%s", app_msg_type, rmsg["Content"])
            return DefaultContent.from_raw_message(rmsg, rmsg["Content"])

    @abstractmethod
    def todict(self):
        pass


@dataclass
class TextContent(Content):
    type = ContentTypes.TEXT
    content: str
    is_at_me: bool | None

    @staticmethod
    def from_raw_message(rmsg: "RawMessage", is_at_me: bool | None) -> "TextContent":
        return TextContent(rmsg["Content"], is_at_me)

    def todict(self):
        return {"type": "text", "content": self.content, "is_at_me": self.is_at_me}


@dataclass
class ImageContent(Content):
    type = ContentTypes.IMAGE
    msg_id: str
    download_fn: Callable[..., Awaitable]

    @staticmethod
    def from_raw_message(
            rmsg: "RawMessage", net_helper: "NetHelperInterface"
    ) -> "ImageContent":
        return ImageContent(
            rmsg["MsgId"], net_helper.get_img_download_fn(rmsg["MsgId"])
        )

    def todict(self):
        return {"type": "image", "msg_id": self.msg_id}


@dataclass
class VideoContent(Content):
    type = ContentTypes.VIDEO
    msg_id: str
    download_fn: Callable[..., Awaitable]

    @staticmethod
    def from_raw_message(
            rmsg: "RawMessage", net_helper: "NetHelperInterface"
    ) -> "VideoContent":
        return VideoContent(
            rmsg["MsgId"], net_helper.get_video_download_fn(rmsg["MsgId"])
        )

    def todict(self):
        return {"type": "video", "msg_id": self.msg_id}


@dataclass
class VoiceContent(Content):
    type = ContentTypes.VOICE
    msg_id: str
    download_fn: Callable[..., Awaitable]

    @staticmethod
    def from_raw_message(
            rmsg: "RawMessage", net_helper: "NetHelperInterface"
    ) -> "VoiceContent":
        return VoiceContent(
            rmsg["MsgId"], net_helper.get_voice_download_fn(rmsg["MsgId"])
        )

    def todict(self):
        return {"type": "voice", "msg_id": self.msg_id}


@dataclass
class AttachContent(Content):
    type = ContentTypes.ATTACH
    sender: str
    media_id: str
    filename: str
    filesize: int
    download_fn: Callable[..., Awaitable]

    @staticmethod
    def from_raw_message(
            rmsg: "RawMessage", net_helper: "NetHelperInterface"
    ) -> "AttachContent | DefaultContent":
        ma = re.search('<totallen>(.*?)</totallen>', rmsg.content)
        if ma is None:
            return DefaultContent(rmsg, "解析附件信息失败")
        file_size = int(ma.group(1))
        return AttachContent(
            rmsg.from_username,
            rmsg.media_id,
            rmsg.file_name,
            file_size,
            net_helper.get_attach_download_fn(rmsg),
        )

    def todict(self):
        return {
            "type": "attach",
            "file_size": self.filesize,

            # 以下字段是下载文件所需的所有参数，key名不能变
            "sender": self.sender,
            "mediaid": self.media_id,
            "filename": self.filename,
        }


@dataclass
class SystemContent(Content):
    type = ContentTypes.SYSTEM
    content: str

    @staticmethod
    def from_raw_message(rmsg: "RawMessage") -> "SystemContent":
        return SystemContent(rmsg["Content"])

    def todict(self):
        return {"type": "system", "content": self.content}


@dataclass
class RevokeContent(Content):
    type = ContentTypes.REVOKE
    revoked_message_id: str

    @staticmethod
    def from_raw_message(rmsg: "RawMessage") -> "Content":
        ma = re.search(
            r"""<sysmsg\s*type="(.*?)"><revokemsg><session>.*?<msgid>(.*?)</msgid>.*""",
            rmsg.content,
        )
        if ma is None:
            return DefaultContent(rmsg, "解析系统信息失败")
        msg_type, msg_id = ma.groups()
        if msg_type != "revokemsg":
            return SystemContent(rmsg["Content"])
        return RevokeContent(msg_id)

    def todict(self):
        return {"type": "revoke", "revoked_message_id": self.revoked_message_id}


@dataclass
class UselessContent(Content):
    type = ContentTypes.UNKNOWN
    rmsg: "RawMessage"
    content: str

    @staticmethod
    def from_raw_message(_rmsg: "RawMessage", content: str) -> "UselessContent":
        return UselessContent(_rmsg, content)

    def todict(self):
        return {"type": "useless", "content": self.content}


@dataclass
class DefaultContent(Content):
    type = ContentTypes.DEFAULT
    rmsg: "RawMessage"
    content: str

    @staticmethod
    def from_raw_message(_rmsg: "RawMessage", content: str) -> "DefaultContent":
        return DefaultContent(_rmsg, content)

    def todict(self):
        return {"type": "default", "content": self.content}


@dataclass
class LinkContent(Content):
    type = ContentTypes.LINK
    title: str
    source_display_name: str
    url: str

    @staticmethod
    def from_raw_message(rmsg: "RawMessage") -> "LinkContent":
        tree = etree.XML(rmsg['Content'])
        title = tree.xpath("/msg/appmsg/title/text()")[0]
        source_display_name = tree.xpath("/msg/appmsg/sourcedisplayname/text()")[0]
        url = tree.xpath("/msg/appmsg/url/text()")[0]
        return LinkContent(title, source_display_name, url)

    def todict(self):
        return {
            "title": self.title,
            "source_display_name": self.source_display_name,
            "url": self.url,
        }
