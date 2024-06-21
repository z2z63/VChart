import sys
import time
from abc import ABC
from collections.abc import AsyncGenerator
from typing import BinaryIO

from vchat.errors import VOperationFailedError
from vchat.model import User
from vchat.net.interface import NetHelperInterface

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override


class NetHelperFriendMixin(NetHelperInterface, ABC):
    @override
    async def update_friends(self, usernames: list[str]) -> AsyncGenerator[User, None]:
        assert self.login_info.url is not None
        url = self.login_info.url + "webwxbatchgetcontact"
        params: dict[str, str | int] = {"type": "ex", "r": int(time.time())}

        data = {
            "BaseRequest": self.login_info.base_request,
            "Count": len(usernames),
            "List": [{"UserName": u, "EncryChatRoomId": ""} for u in usernames],
        }
        async with self.session.post(url, params=params, json=data) as resp:
            dic = await resp.json(content_type=None)
            for friend in dic["ContactList"]:
                yield User(**friend)

    @override
    async def set_alias(self, username, alias):
        assert self.login_info.url is not None
        url = self.login_info.url + "/webwxoplog"
        params = {"lang": "zh_CN", "pass_ticket": self.login_info.pass_ticket}
        data = {
            "UserName": username,
            "CmdId": 2,
            "RemarkName": alias,
            "BaseRequest": self.login_info.base_request,
        }
        async with self.session.post(
            url, params=params, data=data
        ) as resp:  # TODO: 验证接口格式是否正确
            dic = await resp.json(content_type=None)
            if dic["BaseResponse"]["Ret"] != 0:
                raise VOperationFailedError(f"为{username}设置alias操作失败")

    @override
    async def set_pinned(self, username, is_pinned=True):
        assert self.login_info.url is not None
        url = self.login_info.url + "/webwxoplog"
        params = {"pass_ticket": self.login_info.pass_ticket}
        data = {
            "UserName": username,
            "CmdId": 3,
            "OP": int(is_pinned),
            "BaseRequest": self.login_info.base_request,
        }

        async with self.session.post(url, params=params, json=data) as resp:
            dic = await resp.json(content_type=None)
            if dic["BaseResponse"]["Ret"] != 0:
                raise VOperationFailedError(f"为{username}设置pinned操作失败")

    @override
    async def accept_friend(self, username, v4=""):
        assert self.login_info.url is not None
        url = self.login_info.url + "/webwxverifyuser"
        params = {"r": int(time.time()), "pass_ticket": self.login_info.pass_ticket}
        data = {
            "BaseRequest": self.login_info.base_request,
            "Opcode": 3,  # 3
            "VerifyUserListSize": 1,
            "VerifyUserList": [{"Value": username, "VerifyUserTicket": v4}],
            "VerifyContent": "",
            "SceneListCount": 1,
            "SceneList": [33],
            "skey": self.login_info.skey,
        }

        async with self.session.post(url, params=params, json=data) as resp:
            dic = await resp.json(content_type=None)
            if dic["BaseResponse"]["Ret"] != 0:
                raise VOperationFailedError(f"接受{username}好友请求失败")

    @override
    async def get_user_head_img(self, username: str, fd: BinaryIO) -> None:
        assert self.login_info.url is not None
        url = self.login_info.url + "/webwxgeticon"

        params = {"userName": username, "skey": self.login_info.skey, "type": "big"}
        async with self.session.get(url, params=params) as resp:
            async for chunk in resp.content.iter_chunked(1024):
                fd.write(chunk)
