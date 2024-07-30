import asyncio
import sys
import traceback
from abc import ABC
from collections.abc import Callable, Awaitable
from pathlib import Path

from vchat.core.interface import CoreInterface
from vchat.errors import VChatError
from vchat.errors import VUserCallbackError
from vchat.model import Chatroom, MassivePlatform, User
from vchat.model import ContentTypes, ContactTypes
from vchat.model import Message

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override
from vchat.config import logger


class CoreRegisterMixin(CoreInterface, ABC):
    @override
    async def auto_login(
        self,
        hot_reload=True,
        status_storage_path: Path | str = Path("vchat.pkl"),
        enable_cmd_qr=False,
        pic_path=None,
        qr_callback=None,
        login_callback=None,
    ):
        if not await self._net_helper.test_connect():
            logger.info("You can't get access to internet or wechat domain, so exit.")
            sys.exit()
        self._use_hot_reload = hot_reload
        if isinstance(status_storage_path, str):
            self._hot_reload_path = Path(status_storage_path)
        else:
            self._hot_reload_path = status_storage_path
        if hot_reload:
            try:
                await self._load_login_status(
                    status_storage_path,
                    login_callback=login_callback,
                )
                return
            except VChatError as e:
                logger.warning("hot reload failed\n" + str(e))

        await self._login(
            enable_cmd_qr=enable_cmd_qr,
            pic_path=pic_path,
            qr_callback=qr_callback,
            login_callback=login_callback,
        )
        if hot_reload:
            await self._dump_login_status(self._hot_reload_path)

    @override
    async def _configured_reply(self):
        """determine the type of message and reply if its method is defined
        however, I use a strange way to determine whether a msg is from massive platform
        I haven't found a better solution here
        The main problem I'm worrying about is the mismatching of new friends added on phone
        If you have any good idea, pleeeease report an issue. I will be more than grateful.
        """

        msg = await self._storage.msgs.get()
        if isinstance(msg.from_, User):
            reply_fn_list = self._function_dict[ContactTypes.USER]
        elif isinstance(msg.from_, MassivePlatform):
            reply_fn_list = self._function_dict[ContactTypes.MP]
        elif isinstance(msg.from_, Chatroom):
            reply_fn_list = self._function_dict[ContactTypes.CHATROOM]
        else:
            reply_fn_list = []

        try:
            for reply_fn in reply_fn_list:
                r = await reply_fn(msg)  # 用户定义的函数

        except VUserCallbackError:
            logger.warning(traceback.format_exc())

    @override
    def msg_register(self, msg_types: ContentTypes, contact_type: ContactTypes):
        """a decorator constructor
        return a specific decorator based on information given"""

        def _msg_register(fn):
            if ContactTypes.USER in contact_type:
                self._function_dict[ContactTypes.USER].append(
                    _conditional_wrapper(msg_types, fn)
                )
            if ContactTypes.CHATROOM in contact_type:
                self._function_dict[ContactTypes.CHATROOM].append(
                    _conditional_wrapper(msg_types, fn)
                )
            if ContactTypes.MP in contact_type:
                self._function_dict[ContactTypes.MP].append(
                    _conditional_wrapper(msg_types, fn)
                )
            return fn

        return _msg_register

    async def _message_queue_consume_loop(self):
        logger.info("Start auto replying.")

        try:
            while True:
                await self._configured_reply()
        except KeyboardInterrupt:
            self._alive = False
            logger.debug("vchat received an ^C and exit.")
            logger.info("Bye~")
        print("error!")

    @override
    async def run(self, exit_callback=None):
        # `TaskGroup` is unavailable before 3.11
        # async with asyncio.TaskGroup() as tg:
        #     tg.create_task(self._message_queue_consume_loop())
        #     tg.create_task(self.start_receiving(exit_callback))
        # await self._net_helper.close()

        await asyncio.gather(
            (self._message_queue_consume_loop()),
            (self.start_receiving(exit_callback)),
        )
        await self._net_helper.close()


def _conditional_wrapper(filter_types, fn) -> Callable[..., Awaitable]:
    async def _execute(msg: Message):
        if msg.content.type in filter_types:
            await fn(msg)

    return _execute
