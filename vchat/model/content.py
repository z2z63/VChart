import enum
import re
from abc import ABC
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

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
    DEFAULT = enum.auto()
    USELESS = enum.auto()
    ALL = UNKNOWN | TEXT | IMAGE | VIDEO | VOICE | ATTACH | SYSTEM


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
            content = TextContent.from_raw_message(rmsg)
        elif msg_type == 3 or msg_type == 47:
            content = ImageContent.from_raw_message(rmsg, net_helper)
        elif msg_type == 34:
            content = VoiceContent.from_raw_message(rmsg, net_helper)
        elif msg_type == 37:
            raise NotImplementedError
        elif msg_type == 42:  # 个人名片
            # raise NotImplementedError
            # TODO: 实现个人名片，处理HTML转义
            content = TextContent.from_raw_message(rmsg)
        elif msg_type == 43 or msg_type == 62:
            content = VideoContent.from_raw_message(rmsg, net_helper)
        elif msg_type == 49:
            content = Content._parse_sharing_message(rmsg, net_helper)
        elif msg_type == 10000:
            # TODO: 处理撤回消息
            # demo: &lt;sysmsg type="revokemsg"&gt;&lt;revokemsg&gt;&lt;session&gt;48659484053@chatroom&lt;/session&gt;&lt;oldmsgid&gt;1601457293&lt;/oldmsgid&gt;&lt;msgid&gt;2351104337353368038&lt;/msgid&gt;&lt;replacemsg&gt;&lt;![CDATA["ロリ何で最高です" 撤回了一条消息]]&gt;&lt;/replacemsg&gt;&lt;announcement_id&gt;&lt;![CDATA[]]&gt;&lt;/announcement_id&gt;&lt;/revokemsg&gt;&lt;/sysmsg&gt;
            content = SystemContent.from_raw_message(rmsg)
        elif msg_type == 10002:
            content = RevokeContent.from_raw_message(rmsg)
        elif msg_type in [40, 43, 50, 52, 53, 9999]:
            content = UselessContent.from_raw_message(rmsg, "useless message")
        else:
            logger.warning("未知的消息类型: %s\n%s", msg_type, rmsg["Content"])
            content = TextContent.from_raw_message(rmsg)
        content.is_at_me = is_at_me  # type: ignore
        return content

    @staticmethod
    def _parse_sharing_message(
        rmsg: "RawMessage", net_helper: "NetHelperInterface"
    ) -> "Content":
        app_msg_type = rmsg["AppMsgType"]
        if app_msg_type == 0:
            return DefaultContent.from_raw_message(rmsg, rmsg["Content"])
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


@dataclass
class TextContent(Content):
    type = ContentTypes.TEXT
    content: str
    is_at_me: bool | None = None

    @staticmethod
    def from_raw_message(rmsg: "RawMessage") -> "TextContent":
        return TextContent(rmsg["Content"])


@dataclass
class ImageContent(Content):
    type = ContentTypes.IMAGE
    download_fn: Callable[..., Awaitable]
    is_at_me: bool | None = None

    @staticmethod
    def from_raw_message(
        rmsg: "RawMessage", net_helper: "NetHelperInterface"
    ) -> "ImageContent":
        return ImageContent(net_helper.get_img_download_fn(rmsg["MsgId"]))


@dataclass
class VideoContent(Content):
    type = ContentTypes.VIDEO
    download_fn: Callable[..., Awaitable]
    is_at_me: bool | None = None

    @staticmethod
    def from_raw_message(
        rmsg: "RawMessage", net_helper: "NetHelperInterface"
    ) -> "VideoContent":
        return VideoContent(net_helper.get_video_download_fn(rmsg["MsgId"]))


@dataclass
class VoiceContent(Content):
    type = ContentTypes.VOICE
    download_fn: Callable[..., Awaitable]
    is_at_me: bool | None = None

    @staticmethod
    def from_raw_message(
        rmsg: "RawMessage", net_helper: "NetHelperInterface"
    ) -> "VoiceContent":
        return VoiceContent(net_helper.get_voice_download_fn(rmsg["MsgId"]))


@dataclass
class AttachContent(Content):
    type = ContentTypes.ATTACH
    download_fn: Callable[..., Awaitable]
    is_at_me: bool | None = None

    @staticmethod
    def from_raw_message(
        rmsg: "RawMessage", net_helper: "NetHelperInterface"
    ) -> "AttachContent":
        return AttachContent(net_helper.get_attach_download_fn(rmsg))


@dataclass
class SystemContent(Content):
    type = ContentTypes.SYSTEM
    content: str
    is_at_me: bool | None = None

    @staticmethod
    def from_raw_message(rmsg: "RawMessage") -> "SystemContent":
        return SystemContent(rmsg["Content"])


@dataclass
class RevokeContent(Content):
    type = ContentTypes.SYSTEM
    revoked_message_id: str
    is_at_me: bool | None = None

    @staticmethod
    def from_raw_message(rmsg: "RawMessage") -> "SystemContent":
        # TODO: 解析撤回的消息id
        return SystemContent(rmsg["Content"])


@dataclass
class UselessContent(Content):
    type = ContentTypes.UNKNOWN
    rmsg: "RawMessage"
    content: str
    is_at_me: bool | None = None

    @staticmethod
    def from_raw_message(_rmsg: "RawMessage", content: str) -> "UselessContent":
        return UselessContent(_rmsg, content)


@dataclass
class DefaultContent(Content):
    type = ContentTypes.DEFAULT
    rmsg: "RawMessage"
    content: str
    is_at_me: bool | None = None

    @staticmethod
    def from_raw_message(_rmsg: "RawMessage", content: str) -> "DefaultContent":
        return DefaultContent(_rmsg, content)
