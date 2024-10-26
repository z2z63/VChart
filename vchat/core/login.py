import asyncio
import io
import os
import sys
import traceback
from abc import ABC
from collections.abc import Iterable
from typing import Optional

from aiohttp.client_exceptions import ClientResponseError
from pyqrcode import QRCode

from vchat import config, utils
from vchat.core.interface import CoreInterface
from vchat.errors import VUserCallbackError, VOperationFailedError, VLoginError
from vchat.model import Chatroom, User, Contact
from vchat.model import RawMessage

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override

from vchat.config import logger


class CoreLoginMixin(CoreInterface, ABC):
    @override
    async def _login(
        self,
        enable_cmd_qr=False,
        pic_path=None,
        qr_callback=None,
        event_scan_payload=None,
        scan_status=None,
        event_stream=None,
        login_callback=None,
    ):
        if self._alive:
            logger.warning("vchat has already logged in.")
            return

        resp_text = await self._get_uuid_and_wait_for_scan(
            enable_cmd_qr=enable_cmd_qr, pic_path=pic_path, qr_callback=qr_callback
        )
        await self._net_helper.load_login_info_from_wechat(resp_text)

        logger.info("Loading the contact, this may take a little while.")
        await self._web_init()
        await self._net_helper.show_mobile_login()
        await self.get_contact(True)
        if hasattr(login_callback, "__call__"):
            await login_callback(self._storage.myname)
        else:
            utils.clear_screen()
            if os.path.exists(pic_path or config.DEFAULT_QR):
                os.remove(pic_path or config.DEFAULT_QR)
        logger.info("Login successfully as %s" % self._storage.nick_name)

    async def push_login(self) -> Optional[str]:
        return await self._net_helper.push_login()

    @override
    async def get_qr(
        self, uuid=None, enable_cmd_qr=False, pic_path=None, qr_callback=None
    ):
        uuid = uuid or self.uuid
        pic_path = pic_path or config.DEFAULT_QR
        qrStorage = io.BytesIO()
        qrCode = QRCode("https://login.weixin.qq.com/l/" + uuid)
        qrCode.svg(qrStorage, scale=10)
        if hasattr(qr_callback, "__call__"):
            await qr_callback(uuid=uuid, status="0", qrcode=qrStorage.getvalue())
        else:
            with open(pic_path, "wb") as f:
                f.write(qrStorage.getvalue())
            if enable_cmd_qr:
                logger.critical("Please scan the QR code to log in.")
                logger.critical(qrCode.terminal())
            else:
                utils.print_qr(pic_path)
        return qrStorage

    async def _get_uuid_and_wait_for_scan(
        self, enable_cmd_qr=False, pic_path=None, qr_callback=None
    ) -> str:
        """
        wait for user scan QR code, if timeout, get new uuid and retry until login
        enable login after return
        for options:
            - uuid: if uuid is not set, latest uuid you fetched will be used
        for return values:
            - a string will be returned
            - for meaning of return values
                - 200: log in successfully
                - 201: waiting for press confirm
                - 408: uuid timed out
                - 0  : unknown error
        for processing:
            - syncUrl and fileUrl is set
            - BaseRequest is set
        blocks until reaches any of above status
        """
        self.uuid = (
            await self._net_helper.push_login() or await self._net_helper.get_qr_uuid()
        )
        await self.get_qr(self.uuid, enable_cmd_qr, pic_path, qr_callback)
        for _ in range(5):  # 重试五次
            while True:
                code, text = await self._net_helper.check_qr_scan_status(self.uuid)
                if code == "201":
                    logger.info("Please press confirm on your phone.")
                    await asyncio.sleep(2)
                elif code == "200":
                    return text
                elif code == "408":  # 超时
                    logger.warning("QR code scan timeout, retrying...")
                    break
                else:
                    raise RuntimeError("unknown status: %s" % code)
        raise VLoginError("QR code scan exceed the limit. Please try again.")

    async def _web_init(self):
        """
        get info necessary for initializing
        for processing:
            - own account info is set
            - inviteStartCount is set
            - syncKey is set
            - part of contact is fetched
        it is defined in components/login.py
        """
        contact_list = await self._net_helper.web_init()
        # deal with login info
        # utils.emoji_formatter(dic["User"], "NickName")
        me = self._net_helper.login_info.user
        assert me is not None
        self._storage.members[me.username] = me

        self._storage.myname = me.username
        self._storage.nick_name = me["NickName"]
        # deal with contact list returned when init

        chatroomList, otherList = [], []
        for m in contact_list:
            if isinstance(m, Chatroom):
                chatroomList.append(m)
            elif isinstance(m, User):
                otherList.append(m)
        if chatroomList:
            self._update_local_chatrooms(chatroomList)
        if otherList:
            self._update_local_friend(otherList)

    @override
    async def start_receiving(self, exit_callback=None, get_receiving_fn_only=False):
        self._alive = True

        if get_receiving_fn_only:
            return lambda callback: self._maintain_loop(callback)
        else:
            await self._maintain_loop(exit_callback)

    async def _maintain_loop(self, exit_callback):
        retryCount = 0
        while self._alive:
            try:
                code = await self._net_helper.sync_check()
            except ClientResponseError as e:
                logger.info(e)
                continue
            if code is None:
                self._alive = False
            elif code == "0":
                await asyncio.sleep(5)
                logger.info("heartbeat")
            else:
                try:
                    msgs, contacts = await self._net_helper.get_msg()
                except VOperationFailedError:
                    retryCount += 1
                    logger.error(traceback.format_exc())
                    if self._receiving_retry_count < retryCount:
                        self._alive = False
                    else:
                        await asyncio.sleep(1)
                else:
                    await self._consume_message_loop_body(msgs, contacts)
            retryCount = 0
        await self.logout()
        if exit_callback is not None:
            try:
                exit_callback()
            except VUserCallbackError as e:
                logger.warning(e)
        logger.info("LOG OUT!")

    async def _consume_message_loop_body(
        self, rmsgs: Iterable[RawMessage], contacts: Iterable[Contact]
    ):
        async for msg in self._produce_msg(rmsgs):
            await self._storage.msgs.put(msg)

        chatroomList: list[Chatroom] = []
        otherList: list[User] = []
        for contact in contacts:
            if "@@" in contact["UserName"]:
                chatroomList.append(Chatroom(**contact))
            else:
                otherList.append(User(**contact))
        # TODO: fix NoneType Error
        chatroomMsg = self._update_local_chatrooms(chatroomList)
        # chatroomMsg["User"] = self._net_helper.login_info.user
        # self._storage.msgs.put(chatroomMsg)
        # self._update_local_friend(otherList)

    @override
    async def logout(self):
        if self._alive:
            await self._net_helper.logout()
            self._alive = False
        self._net_helper.clear_cookies()
        self._storage.clear()
        
    @override
    @property
    def alive(self) -> bool:
        return self._alive
