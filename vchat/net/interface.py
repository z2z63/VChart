import json
from abc import ABC, abstractmethod
from collections.abc import (
    AsyncGenerator,
    Iterable,
    Collection,
    Callable,
    Coroutine,
    Awaitable,
)
from typing import Optional, Literal, ParamSpec, TypeVar, Any, BinaryIO

import aiohttp
from aiohttp import ClientError

from vchat import config
from vchat.config import logger
from vchat.errors import VNetworkError, VOperationFailedError
from vchat.model import User, Contact, RawMessage
from vchat.storage.login_info import LoginInfo

T = TypeVar("T")
P = ParamSpec("P")


def catch_exception(
    fn: Callable[P, Coroutine[Any, Any, T]]
) -> Callable[P, Coroutine[Any, Any, T]]:
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return await fn(*args, **kwargs)
        except ClientError as e:
            msg = f"{fn.__name__}出现网络错误: {str(e)}"
            logger.warning(msg)
            raise VNetworkError(msg)
        except (KeyError, AttributeError, ValueError) as e:
            msg = f"服务器返回的数据错误: {str(e)}"
            logger.warning(msg)
            raise VOperationFailedError(msg)

    return wrapper


class NetHelperInterface(ABC):
    def __init__(self):
        self.session = None
        self.login_info: LoginInfo = LoginInfo()

    async def init(self):
        self.session = aiohttp.ClientSession(
            json_serialize=lambda s: json.dumps(s, ensure_ascii=False)
        )
        self.session.headers.update({"User-Agent": config.USER_AGENT})

    async def close(self):
        await self.session.close()

    @staticmethod
    @catch_exception
    async def test_connect(retry_times=5) -> bool:
        async with aiohttp.ClientSession() as session:
            for i in range(retry_times):
                try:
                    async with session.get(config.BASE_URL):
                        return True
                except ClientError:
                    pass
        return False

    @abstractmethod
    def load_login_info_from_pickle(self, login_info: LoginInfo):
        pass

    @abstractmethod
    async def get_qr_uuid(self) -> str:
        pass

    @abstractmethod
    async def check_qr_scan_status(self, uuid):
        pass

    @abstractmethod
    async def load_login_info_from_wechat(self, login_content):
        pass

    @abstractmethod
    async def web_init(self) -> Iterable[Contact]:
        pass

    @abstractmethod
    async def show_mobile_login(self):
        pass

    @abstractmethod
    async def update_batch_contact(
        self, batch: int, callback: Callable
    ) -> tuple[Literal[0, 1], Iterable[Contact]]:
        pass

    @abstractmethod
    @catch_exception
    async def update_chatroom(self, usernames: list[str]) -> list[dict]:
        pass

    @abstractmethod
    async def get_detailed_member_info(
        self, encry_chatroom_id: str, members: Collection[User]
    ) -> AsyncGenerator[User, None]:
        async for member in self.get_detailed_member_info(encry_chatroom_id, members):
            yield member

    @abstractmethod
    async def update_friends(self, usernames: list[str]) -> AsyncGenerator[User, None]:
        async for friend in self.update_friends(usernames):
            yield friend

    @abstractmethod
    async def set_alias(self, username, alias):
        pass

    @abstractmethod
    async def set_pinned(self, username, is_pinned=True):
        pass

    @abstractmethod
    async def accept_friend(self, username, v4=""):
        pass

    @abstractmethod
    async def get_user_head_img(self, username: str, fd: BinaryIO) -> None:
        pass

    @abstractmethod
    async def get_chatroom_head_img(self, chatroom_name: str, fd: BinaryIO) -> None:
        pass

    @abstractmethod
    async def get_chatroom_member_head_img(
        self, username: str, chatroom_id: str, fd: BinaryIO
    ) -> None:
        pass

    @abstractmethod
    async def create_chatroom(self, members, topic=""):
        pass

    @abstractmethod
    async def set_chatroom_name(self, chatroom_username, name):
        pass

    @abstractmethod
    async def delete_member_from_chatroom(
        self, chatroom_username: str, members: list[User]
    ):
        pass

    @abstractmethod
    async def add_member_into_chatroom(self, chatroom_name, members):
        pass

    @abstractmethod
    async def invite_member_into_chatroom(self, chatroom_name, members):
        pass

    @abstractmethod
    async def push_login(self) -> Optional[str]:
        pass

    @abstractmethod
    async def sync_check(self) -> Optional[str]:
        pass

    @abstractmethod
    async def get_msg(self) -> tuple[Iterable[RawMessage], Iterable[Contact]]:
        pass

    @abstractmethod
    async def logout(self):
        pass

    @abstractmethod
    def clear_cookies(self):
        pass

    @abstractmethod
    def load_cookies(self, cookies_dict):
        pass

    @abstractmethod
    def get_dumpable_cookies(self):
        pass

    @abstractmethod
    def _get_download_fn(
        self, url: str, params: dict, headers: dict | None = None
    ) -> Callable[..., Awaitable]:
        pass

    @abstractmethod
    def get_img_download_fn(self, msg_id) -> Callable[..., Awaitable]:
        pass

    @abstractmethod
    def get_voice_download_fn(self, msg_id):
        pass

    @abstractmethod
    def get_video_download_fn(self, msg_id):
        pass

    @abstractmethod
    def get_attach_download_fn(self, rmsg: "RawMessage|dict[str, str]"):
        pass

    @abstractmethod
    async def send_document(
        self, file_name: str, media_id: str, file_size: int, to_username: str
    ) -> None:
        pass

    @abstractmethod
    async def send_image(self, media_id: str, to_username: str) -> None:
        pass

    @abstractmethod
    async def send_gif(self, media_id: str, to_username: str) -> None:
        pass

    @abstractmethod
    async def send_video(self, media_id: str, to_username: str) -> None:
        pass

    @abstractmethod
    async def send_raw_msg(self, msg_type: int, content: str, to_username: str) -> None:
        pass

    @abstractmethod
    async def revoke(self, msg_id: str, to_username: str, local_id=None) -> None:
        pass
