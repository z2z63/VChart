import sys
import time
from abc import ABC
from collections.abc import AsyncGenerator, Collection
from typing import BinaryIO

from vchat.errors import VOperationFailedError
from vchat.model import User
from vchat.net.interface import NetHelperInterface, catch_exception

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override


class NetHelperChatroomMixin(NetHelperInterface, ABC):
    @override
    @catch_exception
    async def update_chatroom(self, usernames: list[str]) -> list[dict]:
        assert self.login_info.url is not None
        url = self.login_info.url + "/webwxbatchgetcontact"
        params: dict[str, str | int] = {"type": "ex", "r": int(time.time())}

        data = {
            "BaseRequest": self.login_info.base_request,
            "Count": len(usernames),
            "List": [{"UserName": u, "ChatRoomId": ""} for u in usernames],
        }

        async with self.session.post(url, params=params, json=data) as resp:
            dic = await resp.json(content_type=None)
        return dic["ContactList"]  # type: ignore

    @override
    async def get_chatroom_head_img(self, chatroom_name: str, fd: BinaryIO) -> None:
        assert self.login_info.url is not None
        url = self.login_info.url + "/webwxgetheadimg"

        params = {
            "userName": chatroom_name,
            "skey": self.login_info.skey,
            "type": "big",
        }
        async with self.session.get(url, params=params) as resp:
            async for chunk in resp.content.iter_chunked(1024):
                fd.write(chunk)

    @override
    @catch_exception
    async def get_chatroom_member_head_img(
        self, username: str, chatroom_id: str, fd: BinaryIO
    ) -> None:
        assert self.login_info.url is not None
        url = self.login_info.url + "/webwxgeticon"

        params = {
            "userName": username,
            "chatroomid": chatroom_id,
            "skey": self.login_info.skey,
            "type": "big",
        }
        async with self.session.get(url, params=params) as resp:
            async for chunk in resp.content.iter_chunked(1024):
                fd.write(chunk)

    @override
    @catch_exception
    async def create_chatroom(self, members, topic=""):
        assert self.login_info.url is not None
        url = self.login_info.url + "/webwxcreatechatroom"
        params = {"pass_ticket": self.login_info.pass_ticket, "r": int(time.time())}
        data = {
            "BaseRequest": self.login_info.base_request,
            "MemberCount": len(members.split(",")),
            "MemberList": [{"UserName": member} for member in members.split(",")],
            "Topic": topic,
        }

        async with self.session.post(url, params=params, json=data) as resp:
            dic = await resp.json(content_type=None)
            if dic["BaseResponse"]["Ret"] != 0:
                raise VOperationFailedError(f"创建群聊{topic}失败")

    @override
    @catch_exception
    async def set_chatroom_name(self, chatroom_username, name):
        assert self.login_info.url is not None
        url = self.login_info.url + "/webwxupdatechatroom"
        params = {"fun": "modtopic", "pass_ticket": self.login_info.pass_ticket}
        data = {
            "BaseRequest": self.login_info.base_request,
            "ChatRoomName": chatroom_username,
            "NewTopic": name,
        }
        # TODO: 验证是否使用urlencoded
        async with self.session.post(url, params=params, data=data) as resp:
            dic = await resp.json(content_type=None)
            if dic["BaseResponse"]["Ret"] != 0:
                raise VOperationFailedError(
                    f"设置群聊{chatroom_username}名称为{name}失败"
                )

    @override
    @catch_exception
    async def delete_member_from_chatroom(
        self, chatroom_username: str, members: list[User]
    ):
        assert self.login_info.url is not None
        url = self.login_info.url + "/webwxupdatechatroom"
        params = {"fun": "delmember", "pass_ticket": self.login_info.pass_ticket}
        data = {
            "BaseRequest": self.login_info.base_request,
            "ChatRoomName": chatroom_username,
            "DelMemberList": ",".join([member["UserName"] for member in members]),
        }
        # TODO: 验证是否使用urlencoded
        async with self.session.post(url, params=params, data=data) as resp:
            dic = await resp.json(content_type=None)
            if dic["BaseResponse"]["Ret"] != 0:
                raise VOperationFailedError(f"从{chatroom_username}删除{members}失败")

    @override
    @catch_exception
    async def add_member_into_chatroom(self, chatroom_name, members):
        assert self.login_info.url is not None
        url = self.login_info.url + "/webwxupdatechatroom"
        params = {"pass_ticket": self.login_info.pass_ticket, "fun": "addmember"}

        data = {
            "BaseRequest": self.login_info.base_request,
            "ChatRoomName": chatroom_name,
            "AddMemberList": members,
        }
        async with self.session.post(url, params=params, json=data) as resp:
            dic = await resp.json(content_type=None)
            if dic["BaseResponse"]["Ret"] != 0:
                raise VOperationFailedError(f"向{chatroom_name}添加{members}失败")

    @override
    @catch_exception
    async def invite_member_into_chatroom(self, chatroom_name, members):
        assert self.login_info.url is not None
        url = self.login_info.url + "/webwxupdatechatroom"
        params = {"pass_ticket": self.login_info.pass_ticket, "fun": "invitemember"}

        data = {
            "BaseRequest": self.login_info.base_request,
            "ChatRoomName": chatroom_name,
            "InviteMemberList": members,
        }
        async with self.session.post(url, params=params, json=data) as resp:
            dic = await resp.json(content_type=None)
            if dic["BaseResponse"]["Ret"] != 0:
                raise VOperationFailedError(f"邀请{members}加入{chatroom_name}失败")

    @override
    async def get_detailed_member_info(
        self, encry_chatroom_id: str, members: Collection[User]
    ) -> AsyncGenerator[User, None]:
        assert self.login_info.url is not None
        url = self.login_info.url + "/webwxbatchgetcontact"
        params: dict[str, str | int] = {"type": "ex", "r": int(time.time())}

        data = {
            "BaseRequest": self.login_info.base_request,
            "Count": len(members),
            "List": [
                {"UserName": member.username, "EncryChatRoomId": encry_chatroom_id}
                for member in members
            ],
        }
        async with self.session.post(url, params=params, json=data) as resp:
            dic = await resp.json(content_type=None)
            for member in dic["ContactList"]:
                yield User(**member)
