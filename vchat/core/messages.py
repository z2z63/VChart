import json
import re
import sys
from abc import ABC
from collections.abc import Iterable, AsyncGenerator
from pathlib import Path
from typing import BinaryIO

from vchat import utils
from vchat.core.interface import CoreInterface
from vchat.errors import VMalformedParameterError
from vchat.model import Content
from vchat.model import RawMessage, Message
from vchat.model import User, Contact

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override
from vchat.config import logger


class CoreMessageMixin(CoreInterface, ABC):
    async def _parse_raw_message_contact(
        self, rmsg: RawMessage
    ) -> tuple[Contact, Contact, User | None, bool | None]:
        sender = None
        is_at_me = None
        params: dict[str, Contact | None] = {
            "from": None,
            "to": None,
        }
        if rmsg.from_username == self._storage.myname and rmsg.to_username.startswith(
            "@@"
        ):
            # 自己发给群聊的消息
            (sender, is_at_me) = await self._produce_group_chat(rmsg)
            chatroom = self._storage.chatrooms[rmsg.to_username]  # 群聊
            params["from"] = chatroom.members[self._storage.myname]
            params["to"] = self._storage.chatrooms[rmsg.to_username]
        elif rmsg.from_username == self._storage.myname and rmsg.to_username.startswith(
            "@"
        ):
            # 自己发给好友的消息
            params["from"] = self._storage.members[self._storage.myname]
            # 先查找本地缓存，如果没有说明是新好友，更新本地缓存
            params["to"] = self._storage.members.get(
                rmsg.to_username, User(UserName=rmsg.to_username)
            )
        elif rmsg.from_username == self._storage.myname and rmsg.to_username in (
            "filehelper",
            "fmessage",
            "weixin",
        ):
            #     自己发给特殊账号的消息
            params["to"] = self._storage.members.get(
                rmsg.to_username, User(UserName=rmsg.to_username)
            )
            assert self._storage.myname is not None
            params["from"] = self._storage.members[self._storage.myname]
        elif rmsg.to_username == self._storage.myname and rmsg.from_username.startswith(
            "@@"
        ):
            # 群聊发给自己的消息（收到群聊消息）
            (sender, is_at_me) = await self._produce_group_chat(rmsg)
            chatroom = self._storage.chatrooms[rmsg.from_username]  # 群聊
            params["from"] = chatroom
            params["to"] = chatroom.members[
                rmsg.to_username
            ]  # 自己在群聊中的信息（多了DisplayName)

        elif rmsg.to_username == self._storage.myname and rmsg.from_username.startswith(
            "@"
        ):
            # 好友发给自己的消息
            params["from"] = self._storage.members.get(
                rmsg.from_username, User(UserName=rmsg.from_username)
            )
            params["to"] = self._storage.members[self._storage.myname]
        elif rmsg.to_username == self._storage.myname:
            # 特殊账号发给自己的消息
            params["from"] = self._storage.members.get(
                rmsg.from_username, User(UserName=rmsg.from_username)
            )
            params["to"] = self._storage.members[self._storage.myname]
        else:
            logger.warning("unknown message type: %s" % rmsg)
            logger.warning(json.dumps(rmsg._other))

        rmsg.set_content(
            utils.msg_formatter(rmsg.content)
        )  # 微信没有使用unicode表示emoji，需要修改emoji显示
        assert params["from"] is not None
        assert params["to"] is not None
        return params["from"], params["to"], sender, is_at_me

    @override
    async def _produce_msg(
        self, rmsgs: Iterable[RawMessage]
    ) -> AsyncGenerator[Message, None]:
        for m in rmsgs:
            (
                from_contact,
                to_contact,
                chatroom_sender,
                is_at_me,
            ) = await self._parse_raw_message_contact(m)
            content = Content.build_from_content_trimmed_raw_message(
                m, self._net_helper, is_at_me
            )
            msg = Message(
                from_contact, to_contact, content, m["MsgId"], chatroom_sender
            )
            yield msg

    async def _produce_group_chat(self, rmsg: RawMessage) -> tuple[User, bool]:
        """
        群聊消息在解析Content前需要特殊处理
        1. 保证群聊信息已经加载（可能更新）
        2. 保证发送消息的群员信息已经加载（可能更新）
        3. 群员（自己除外）发送的Content中的‘首部’表示发送消息的群员，去掉‘首部’后才上正常的消息内容
        4. 判断是否@自己
        """
        # 收到消息的两种情况
        # 1. 或者群聊给自己发送消息，content带有‘首部’
        # demo: '@feed53c4feec0c07ea9bcd85737559720c537f6fc3a8ea765d2e2ddc79be5d3f:<br/>李四'
        # 2. 自己打开群聊并点击输入框，会收到一条空的消息
        # 3. 自己给群聊发送消息，没有‘首部’
        content = rmsg.content
        ma = re.match("(@[0-9a-z]*?):<br/>(.*)$", content)
        if ma is not None:
            actualUserName, content = ma.groups()
            chatroom_username = rmsg.from_username
            rmsg.set_content(content)  # trim发生在此处
        elif rmsg["FromUserName"] == self._storage.myname:
            actualUserName = self._storage.myname
            chatroom_username = rmsg["ToUserName"]
        else:
            raise NotImplementedError
            # TODO: 发送文本为空字符串时会接受到消息指示错误
        # 如果是新群聊，需要加载群聊信息
        if chatroom_username not in self._storage.chatrooms:
            await self.update_chatroom(chatroom_username)
        chatroom = self._storage.chatrooms[chatroom_username]
        # 查找发送消息的群员
        member = chatroom.members.get(actualUserName, None)
        if member is None:  # 如果发送消息的群员在本地找不到，就更新群员列表
            chatroom = await self.update_chatroom(chatroom_username, True)
        if member is None:  # 更新后还是找不到发送消息的群员
            logger.debug("chatroom member fetch failed with %s" % actualUserName)
            is_at_me = False
        else:
            # 自己在群中显示的昵称，优先是自己设置的群昵称，其次是微信昵称
            my_display_name = (
                chatroom.get("Self", {}).get("DisplayName", None)
                or self._storage.nick_name
            )
            assert my_display_name is not None
            atFlag = "@" + my_display_name
            if atFlag + "\u2005" in rmsg["Content"] or atFlag + " " in rmsg["Content"]:
                is_at_me = True
            elif rmsg["Content"].endswith(atFlag):
                is_at_me = True
            else:
                is_at_me = False

        assert member is not None
        return member, is_at_me

    @override
    async def send_msg(self, msg: str, to_username: str) -> str:
        logger.debug("Request to send a text message to %s: %s" % (to_username, msg))
        return await self._net_helper.send_raw_msg(1, msg, to_username)

    @override
    async def send_file(
        self,
        to_username: str,
        file_path: Path | None = None,
        fd: BinaryIO | None = None,
        media_id: str | None = None,
        file_size: int | None = None,
        file_name: str | None = None,
    ):
        """
        1. 发送本地文件，提供file_path，默认使用file_path的文件名，可以通过file_name覆盖文件名
        2. 发送内存缓冲中的数据，提供fd和file_name
        先上传文件，得到media_id，再发送一条消息引用这个media_id
        """
        logger.debug("Request to send a file to %s: %s" % (to_username, file_path))
        if [file_path, fd, media_id].count(None) != 2:
            error_msg = f"cannot specify which file to send: file_path:{file_path} fd:{fd} media_id:{media_id}"
            logger.warning(error_msg)
            raise VMalformedParameterError(error_msg)
        if [media_id, file_size].count(None) == 1:
            error_msg = "must specify both media_id and file_size or neither"
            logger.warning(error_msg)
            raise VMalformedParameterError(error_msg)
        # file_name = file_name or file_path.name
        if file_name is not None:
            file_name = file_name
        else:
            assert file_path is not None
            file_name = file_path.name
        if media_id is None:
            if file_path is not None:
                with file_path.open("rb") as fd:
                    media_id, file_size = await self._net_helper.upload_file(
                        file_name, fd, to_username
                    )
            else:
                assert fd is not None
                media_id, file_size = await self._net_helper.upload_file(
                    file_name, fd, to_username
                )
        assert file_size is not None
        msg_id = await self._net_helper.send_document(
            file_name, media_id, file_size, to_username
        )
        return msg_id, media_id, file_size

    @override
    async def send_image(
        self,
        to_username: str,
        file_path: Path | None = None,
        fd: BinaryIO | None = None,
        media_id: str | None = None,
        file_name: str | None = None,
    ) -> str:
        logger.debug(
            "Request to send a image(mediaId: %s) to %s: %s"
            % (media_id, to_username, file_path)
        )
        if [file_path, fd, media_id].count(None) != 2:
            error_msg = f"cannot specify which file to send: file_path:{file_path} fd:{fd} media_id:{media_id}"
            logger.warning(error_msg)
            raise VMalformedParameterError(error_msg)
        if file_path is not None:
            file_name = file_name or file_path.name or "default.png"
        else:
            file_name = file_name or "default.png"
        if media_id is None:
            if file_path is not None:
                with file_path.open("rb") as fd:
                    media_id, file_size = await self._net_helper.upload_file(
                        file_name, fd, to_username
                    )
            else:
                media_id, file_size = await self._net_helper.upload_file(
                    file_name, fd, to_username
                )
        return await self._net_helper.send_image(media_id, to_username)

    @override
    async def send_video(
        self,
        to_username,
        file_path=None,
        fd=None,
        media_id=None,
        file_name: str | None = None,
    ):
        """
        1. 发送本地文件，提供file_path
        2. 发送内存缓冲中的数据，提供fd
        3. 发送已经上传过的文件，提供media_id
        file_name可选，优先使用提供的file_name，其次使用file_path的文件名，最后使用默认的default.mp4
        """
        logger.debug(
            "Request to send a video(mediaId: %s) to %s: %s"
            % (media_id, to_username, file_path)
        )
        if [file_path, fd, media_id].count(None) != 2:
            logger.warning(
                f"cannot specify which file to send: file_path:{file_path} fd:{fd} media_id:{media_id}"
            )
        file_name = file_name or file_path.name or "default.mp4"
        if media_id is None:
            if file_path is not None:
                with file_path.open("rb") as fd:
                    media_id, file_size = await self._net_helper.upload_file(
                        file_name, fd, to_username
                    )
            else:
                media_id, file_size = await self._net_helper.upload_file(
                    file_name, fd, to_username
                )

        return await self._net_helper.send_video(media_id, to_username)

    @override
    async def revoke(self, msg_id, to_username, local_id=None):
        return await self._net_helper.revoke(msg_id, to_username, local_id)
