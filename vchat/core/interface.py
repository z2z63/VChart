from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from collections.abc import Iterable
from pathlib import Path
from typing import Optional, Callable, BinaryIO, overload, Awaitable

from vchat.model import Contact, User, MassivePlatform, Chatroom
from vchat.model import ContentTypes, ContactTypes
from vchat.model import RawMessage, Message
from vchat.net import NetHelper
from vchat.storage import Storage


class CoreInterface(ABC):
    def __init__(self):
        self._alive = False
        self._storage: Storage = Storage()
        self._net_helper: NetHelper = NetHelper()
        self._uuid: Optional[str] = None
        self._function_dict: dict[ContactTypes, list[Callable[..., Awaitable]]] = {
            ContactTypes.USER: [],
            ContactTypes.CHATROOM: [],
            ContactTypes.MP: [],
        }
        self._use_hot_reload = False
        self._hot_reload_path = Path("vchat.pkl")
        self._receiving_retry_count = 5

    @abstractmethod
    def _login(
        self,
        enable_cmd_qr=False,
        pic_path=None,
        qr_callback=None,
        login_callback=None,
    ):
        pass

    @abstractmethod
    def get_qr(
        self,
        uuid: Optional[str] = None,
        enable_cmd_qr=False,
        pic_path: Optional[str] = None,
        qr_callback=None,
    ):
        pass

    @abstractmethod
    def start_receiving(
        self, exit_callback: Optional[Callable] = None, get_receiving_fn_only=False
    ):
        pass

    @abstractmethod
    async def logout(self):
        pass

    @abstractmethod
    @overload
    async def update_chatroom(self, username: str, detailed_member=False) -> Chatroom:
        pass

    @abstractmethod
    @overload
    async def update_chatroom(
        self, username: list[str], detailed_member=False
    ) -> list[Chatroom]:
        pass

    @abstractmethod
    async def update_chatroom(
        self, username: str | list[str], detailed_member=False
    ) -> Chatroom | list[Chatroom]:
        pass

    @abstractmethod
    @overload
    async def update_friend(self, username: str) -> User:
        pass

    @overload
    @abstractmethod
    async def update_friend(self, username: list[str]) -> list[User]:
        pass

    @abstractmethod
    async def update_friend(self, username: str | list[str]) -> User | list[User]:
        pass

    @abstractmethod
    async def get_contact(self, update=False): ...

    @property
    @abstractmethod
    def friends(self) -> dict[str, Contact]: ...

    @property
    @abstractmethod
    def me(self) -> User: ...

    @property
    @abstractmethod
    def chatrooms(self): ...

    @property
    @abstractmethod
    def mps(self) -> dict[str, MassivePlatform]: ...

    @abstractmethod
    def set_alias(self, username: str, alias: str): ...

    @abstractmethod
    def set_pinned(self, username: str, is_pinned=True): ...

    @abstractmethod
    async def accept_friend(self, username: str, v4: str, auto_update=True): ...

    @abstractmethod
    async def get_head_img(
        self,
        username: Optional[str] = None,
        chatroom_username: Optional[str] = None,
        pic_path: Optional[Path] = None,
        fd: Optional[BinaryIO] = None,
    ):
        pass

    @abstractmethod
    def create_chatroom(self, members, topic=""): ...

    @abstractmethod
    def set_chatroom_name(self, chatroom_username, name): ...

    @abstractmethod
    def delete_member_from_chatroom(self, chatroom_username, members): ...

    @abstractmethod
    async def add_member_into_chatroom(
        self, chatroom_user_name, member_list, use_invitation=False
    ):
        pass

    @abstractmethod
    async def send_msg(self, msg: str, to_username: str) -> str:
        pass

    @abstractmethod
    async def send_file(
        self,
        to_username: str,
        file_path: Path | None = None,
        fd: BinaryIO | None = None,
        media_id: str | None = None,
        file_size: int | None = None,
        file_name: str | None = None,
    ):
        pass

    @abstractmethod
    def send_image(
        self,
        to_username: str,
        file_path: Optional[Path] = None,
        fd: Optional[BinaryIO] = None,
        media_id: Optional[str] = None,
        file_name: Optional[str] = None,
    ) -> str:
        pass

    @abstractmethod
    def send_video(
        self,
        to_username,
        file_path=None,
        fd=None,
        media_id=None,
        file_name: Optional[str] = None,
    ):
        pass

    @abstractmethod
    def revoke(self, msg_id, to_username, local_id=None):
        pass

    @abstractmethod
    def _dump_login_status(self, file_path: Optional[Path] = None):
        pass

    @abstractmethod
    async def _load_login_status(self, file_path, login_callback=None):
        pass

    @abstractmethod
    async def auto_login(
        self,
        hot_reload=True,
        status_storage_path: Path | str = Path("vchat.pkl"),
        enable_cmd_qr=False,
        pic_path=None,
        qr_callback=None,
        login_callback=None,
    ):
        pass

    @abstractmethod
    async def _configured_reply(self):
        pass

    @abstractmethod
    def msg_register(self, msg_type: ContentTypes, contact_type: ContactTypes):
        pass

    @abstractmethod
    def run(self, exit_callback=None):
        pass

    @abstractmethod
    def _update_local_chatrooms(self, chatrooms: list[Chatroom]):
        pass

    @abstractmethod
    def _update_local_friend(self, friends: list[User]):
        pass

    @abstractmethod
    async def _produce_msg(
        self, rmsgs: Iterable[RawMessage]
    ) -> AsyncGenerator[Message, None]:
        # 绕过mypy类型检查，这个函数体没有实际意义
        async for msg in self._produce_msg(rmsgs):
            yield msg
    @abstractmethod
    def search_contact(self, searcher: Callable[[Contact], bool], contact_types=ContactTypes.ALL) -> list[Contact]: ...
    @abstractmethod
    def search_friends(self, searcher: Callable[[Contact], bool]) -> list[Contact]: ...
    @abstractmethod
    def search_chatrooms(self, searcher: Callable[[Contact], bool]) -> list[Contact]: ...
    @abstractmethod
    def search_friends_by_nickname(self, name: str) -> list[Contact]: ...
    @abstractmethod
    def search_chatrooms_by_nickname(self, name: str) -> list[Contact]: ...
    
    @property
    @abstractmethod
    def alive(self) -> bool: ...