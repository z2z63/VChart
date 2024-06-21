import random
import re
import time
from abc import ABC
from collections.abc import Callable, Iterable
from typing import Optional, Literal

from aiohttp import ClientError

from vchat import config
from vchat.config import logger
from vchat.errors import VNetworkError, VOperationFailedError
from vchat.model import Contact, RawMessage
from vchat.net.interface import NetHelperInterface, catch_exception


class NetHelperUpdateMixin(NetHelperInterface, ABC):
    async def update_batch_contact(
        self, seq: int, callback: Callable
    ) -> tuple[Literal[0, 1], Iterable[Contact]]:
        assert self.login_info.url is not None
        url = self.login_info.url + "/webwxgetcontact"
        params = {"r": int(time.time()), "seq": seq, "skey": self.login_info.skey}

        try:
            resp = await self.session.get(url, params=params)
        except ClientError:
            logger.info(
                "Failed to fetch contact, that may because of the amount of your chatrooms"
            )
            callback()
            return 0, []
        else:
            data = await resp.json(content_type=None)
            resp.close()
            member_list = data.get("MemberList", [])

            return data.get("Seq", 0), (
                Contact.constructor(contact) for contact in member_list
            )

    async def sync_check(self) -> Optional[str]:
        assert self.login_info.sync_url is not None
        assert self.login_info.login_time is not None
        url = self.login_info.sync_url + "/synccheck"
        params = {
            "r": int(time.time() * 1000),
            "skey": self.login_info.skey,
            "sid": self.login_info.wxsid,
            "uin": self.login_info.wxuin,
            "deviceid": self.login_info.deviceid,
            "synckey": self.login_info.synckey,
            "_": self.login_info.login_time,
        }
        self.login_info.login_time += 1
        async with self.session.get(url, params=params, timeout=config.TIMEOUT) as resp:
            text = await resp.text()
            regx = r'window.synccheck={retcode:"(\d+)",selector:"(\d+)"}'
            pm = re.search(regx, text)
            if pm is None:
                raise VNetworkError("Unexpected sync check result: %s" % text)
            return pm.group(2)

    @catch_exception
    async def get_msg(self) -> tuple[Iterable[RawMessage], Iterable[Contact]]:
        assert self.login_info.url is not None
        self.login_info.deviceid = "e" + str(random.random())[2:17]
        url = self.login_info.url + "/webwxsync"
        params = {
            "sid": self.login_info.wxsid,
            "skey": self.login_info.skey,
            "pass_ticket": self.login_info.pass_ticket,
        }
        data = {
            "BaseRequest": self.login_info.base_request,
            "SyncKey": self.login_info.SyncKey,
            "rr": ~int(time.time()),
        }
        async with self.session.post(
            url, params=params, json=data, timeout=config.TIMEOUT
        ) as resp:
            dic = await resp.json(content_type=None)
            if dic["BaseResponse"]["Ret"] != 0:
                raise VOperationFailedError("获取新消息失败，请重新登录")
            self.login_info.SyncKey = dic["SyncKey"]
            self.login_info.synckey = "|".join(
                [
                    "%s_%s" % (item["Key"], item["Val"])
                    for item in dic["SyncCheckKey"]["List"]
                ]
            )
            return (
                (RawMessage(**msg) for msg in dic.get("AddMsgList", [])),
                (
                    Contact.constructor(contact)
                    for contact in dic.get("ModContactList", [])
                ),
            )
