import copy
import sys
from abc import ABC

from pathlib import Path
from typing import Optional, BinaryIO, overload

from aiohttp import ClientError

from vchat.core.interface import CoreInterface
from vchat.errors import VMalformedParameterError
from vchat.model import Chatroom, User, MassivePlatform, Contact

if sys.version_info >= (3, 12):
    from typing import override
    from itertools import batched
else:
    from typing_extensions import override
    from vchat.utils import batch as batched

from vchat.config import logger


class CoreContactMixin(CoreInterface, ABC):
    @overload
    async def update_chatroom(self, username: str, detailed_member=False) -> Chatroom:
        pass

    @overload
    async def update_chatroom(
        self, username: list[str], detailed_member=False
    ) -> list[Chatroom]:
        pass

    @override
    async def update_chatroom(
        self, username: str | list[str], detailed_member: bool = False
    ) -> Chatroom | list[Chatroom]:
        if not isinstance(username, list):
            username_list = [username]
        else:
            username_list = username
        chatroom_list = [
            Chatroom(**raw)
            for raw in await self._net_helper.update_chatroom(username_list)
        ]

        if detailed_member:
            for chatroom in chatroom_list:
                for batch in batched(chatroom.members.values(), 50):
                    async for user in self._net_helper.get_detailed_member_info(
                        chatroom["EncryChatRoomId"], batch
                    ):
                        chatroom.members.update({user.username: user})

        self._update_local_chatrooms(chatroom_list)
        if len(chatroom_list) == 1:
            return chatroom_list[0]
        else:
            return chatroom_list

    @overload
    async def update_friend(self, username: str) -> User:
        pass

    @overload
    async def update_friend(self, username: list[str]) -> list[User]:
        pass

    @override
    async def update_friend(self, username: str | list[str]) -> User | list[User]:
        if isinstance(username, list):
            username_list = []
            async for friend in self._net_helper.update_friends(username):
                username_list.append(friend)
            return username_list
        else:
            return await anext(self._net_helper.update_friends([username]))

    @override
    def _update_local_chatrooms(self, chatrooms: list[Chatroom]):
        """
        get a list of chatrooms for updating local chatrooms
        return a list of given chatrooms with updated info
        """
        for chatroom in chatrooms:
            self._storage.chatrooms[chatroom.username] = chatroom

    @override
    def _update_local_friend(self, friends: list[User]) -> None:
        """
        get a list of friends or mps for updating local contact
        """
        for friend in friends:
            self._storage.members[friend.username] = friend

    @override
    async def get_contact(self, update=False):
        if not update:
            return copy.deepcopy(self._storage.members)

        async def callback():
            for chatroom in self.chatrooms.values():
                await self.update_chatroom(chatroom.username, detailed_member=True)

        seq = 0
        memberList: list[Contact] = []
        while True:
            seq, contact_batch = await self._net_helper.update_batch_contact(
                seq, callback
            )
            memberList.extend(contact_batch)
            if seq == 0:
                break
        chatroomList: list[Chatroom] = []
        otherList: list[User] = []
        for m in memberList:
            if isinstance(m, Chatroom):
                chatroomList.append(m)
            elif isinstance(m, User):
                otherList.append(m)
        self._update_local_friend(otherList)
        self._update_local_chatrooms(chatroomList)
        return chatroomList

    @override
    @property
    def friends(self):
        return self._storage.members

    @override
    @property
    def me(self) -> User:
        return self._net_helper.login_info.user

    @override
    @property
    def chatrooms(self) -> dict[str, Chatroom]:
        return self._storage.chatrooms

    @override
    @property
    def mps(self) -> dict[str, MassivePlatform]:
        return self._storage.mps

    @override
    def set_alias(self, username, alias):
        oldFriendInfo = self._storage.members[username]
        if oldFriendInfo is None:
            logger.warning("本地没有该好友的信息，设置alias失败")
            return
        try:
            self._net_helper.set_alias(username, alias)
        except (ClientError, KeyError) as e:
            logger.warning(e)
        else:
            # oldFriendInfo["RemarkName"] = alias
            self._storage.members[username] = User(
                **dict(oldFriendInfo, RemarkName=alias)
            )

    @override
    def set_pinned(self, username, is_pinned=True):
        return self._net_helper.set_pinned(username, is_pinned)

    @override
    async def accept_friend(self, username, v4="", auto_update=True):
        await self._net_helper.accept_friend(username, v4)
        if auto_update:
            await self.update_friend(username)

    @override
    async def get_head_img(
        self,
        username: Optional[str] = None,
        chatroom_username: Optional[str] = None,
        pic_path: Optional[Path] = None,
        fd: Optional[BinaryIO] = None,
    ):
        """get head image
        * if you want to get chatroom header: only set chatroomUserName
        * if you want to get friend header: only set userName
        * if you want to get chatroom member header: set both
        """
        if [pic_path, fd].count(None) != 1:
            raise VMalformedParameterError(
                "must specify one and only one of pic_path and fd"
            )
        if pic_path is not None:
            fd = pic_path.open("wb")
        assert fd is not None
        if username is None and chatroom_username is None:  # 非法情况
            raise VMalformedParameterError("must specify who's head image to get")
        elif username is not None and chatroom_username is None:  # 获取好友头像
            infoDict = self._storage.members[username]
            if infoDict is None:
                raise VMalformedParameterError("no such friend")
            await self._net_helper.get_user_head_img(username, fd)
        elif username is None and chatroom_username is not None:  # 获取群头像
            await self._net_helper.get_chatroom_head_img(chatroom_username, fd)
        else:  # 获取群成员头像
            assert chatroom_username is not None

            chatroom = self._storage.chatrooms[chatroom_username]
            chatroom_id: str = chatroom["UserName"]
            if "EncryChatRoomId" in chatroom:
                chatroom_id = chatroom["EncryChatRoomId"]
            assert username is not None
            await self._net_helper.get_chatroom_member_head_img(
                username, chatroom_id, fd
            )

        if pic_path is not None:
            fd.close()

    @override
    def create_chatroom(self, members, topic=""):
        return self._net_helper.create_chatroom(members, topic)

    @override
    def set_chatroom_name(self, chatroom_username, name):
        return self._net_helper.set_chatroom_name(chatroom_username, name)

    @override
    async def delete_member_from_chatroom(self, chatroom_username, members):
        return await self._net_helper.delete_member_from_chatroom(
            chatroom_username, members
        )

    @override
    async def add_member_into_chatroom(
        self, chatroom_name, members, use_invitation=False
    ):
        """add or invite member into chatroom
        * there are two ways to get members into chatroom: invite or directly add
        * but for chatrooms with more than 40 users, you can only use invite
        * but don't worry we will auto-force userInvitation for you when necessary
        """
        can_use_add = True
        if not use_invitation:
            chatroom = self._storage.chatrooms.get(chatroom_name, None)
            if not chatroom:
                chatroom = await self.update_chatroom(chatroom_name)
            invite_start_count = self._net_helper.login_info.invite_start_count
            assert chatroom is not None
            assert invite_start_count is not None
            if len(chatroom["MemberList"]) > invite_start_count:
                can_use_add = False

        if can_use_add and not use_invitation:  # 希望使用add方法，并且可以使用
            return self._net_helper.add_member_into_chatroom(chatroom_name, members)
        else:
            # 1. 希望使用invite方法
            # 2. 希望使用add方法，但是人数过多，只能使用invite方法
            return self._net_helper.invite_member_into_chatroom(chatroom_name, members)
