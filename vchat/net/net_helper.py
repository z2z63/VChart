import json

import aiohttp

from vchat.net.chatroom import NetHelperChatroomMixin
from vchat.net.download import NetHelperDownloadMixin
from vchat.net.friend import NetHelperFriendMixin
from vchat.net.login import NetHelperLoginMixin
from vchat.net.send import NetHelperSendMixin
from vchat.net.update import NetHelperUpdateMixin


class NetHelper(
    NetHelperLoginMixin,
    NetHelperChatroomMixin,
    NetHelperDownloadMixin,
    NetHelperSendMixin,
    NetHelperFriendMixin,
    NetHelperUpdateMixin,
):
    @staticmethod
    async def factory():
        session = aiohttp.ClientSession(
            json_serialize=lambda s: json.dumps(s, ensure_ascii=False)
        )
        return NetHelper(session)
