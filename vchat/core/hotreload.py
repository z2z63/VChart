import pickle
import sys
from abc import ABC
from pathlib import Path
from typing import Optional


from vchat.core.interface import CoreInterface
from vchat.errors import (
    VNetworkError,
    VFileIOError,
    VUserCallbackError,
    VOperationFailedError,
)
from vchat.model import Chatroom, User

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override
from vchat.config import logger


class CoreHotReloadMixin(CoreInterface, ABC):
    @override
    async def _dump_login_status(self, file_path: Optional[Path] = None) -> None:
        file_path = file_path or self._hot_reload_path
        status = {
            "loginInfo": self._net_helper.login_info,
            "cookies": self._net_helper.get_dumpable_cookies(),
            "storage": self._storage.dumps(),
        }
        try:
            with open(file_path, "wb") as f:
                pickle.dump(status, f, pickle.HIGHEST_PROTOCOL)
        except IOError:
            logger.warning("Dump login status failed.")
            return
        logger.debug("Dump login status for hot reload successfully.")

    @override
    async def _load_login_status(self, file_path, login_callback=None):
        try:
            with open(file_path, "rb") as f:
                jar = pickle.load(f)
        except IOError:
            logger.debug("No login status found, loading login status failed.")
            raise VFileIOError("No login status found, loading login status failed.")

        self._net_helper.load_login_info_from_pickle(jar["loginInfo"])
        self._net_helper.load_cookies(jar["cookies"])
        self._storage.loads(jar["storage"])
        try:
            rmsgs, contacts = await self._net_helper.get_msg()
        except VOperationFailedError:
            await self.logout()
            logger.debug("server refused, loading login status failed.")
            raise VNetworkError("server refused, loading login status failed.")

        chatroom_list = []
        other_list = []
        for contact in contacts:
            if isinstance(contact, Chatroom):
                chatroom_list.append(contact)
            elif isinstance(contact, User):
                other_list.append(contact)
        self._update_local_chatrooms(chatroom_list)
        self._update_local_friend(other_list)
        async for msg in self._produce_msg(rmsgs):
            await self._storage.msgs.put(msg)
        logger.debug("loading login status succeeded.")
        if login_callback is not None:
            try:
                await login_callback(self._storage.myname)
            except VUserCallbackError as e:
                logger.warning("login callback failed:\n" + str(e))

    async def _load_last_login_status(self, cookie_jar: dict[str, str]):
        try:
            self._net_helper.load_cookies(
                {
                    "webwxuvid": cookie_jar["webwxuvid"],
                    "webwx_auth_ticket": cookie_jar["webwx_auth_ticket"],
                    "login_frequency": "2",
                    "last_wxuin": cookie_jar["wxuin"],
                    "wxloadtime": cookie_jar["wxloadtime"] + "_expired",
                    "wxpluginkey": cookie_jar["wxloadtime"],
                    "wxuin": cookie_jar["wxuin"],
                    "mm_lang": "zh_CN",
                    "MM_WX_NOTIFY_STATE": "1",
                    "MM_WX_SOUND_STATE": "1",
                }
            )
        except:
            logger.info(
                "Load status for push login failed, we may have experienced a cookies change."
            )
            logger.info(
                "If you are using the newest version of vchat, you may report a bug."
            )
