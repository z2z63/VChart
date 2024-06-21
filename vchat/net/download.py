import io
from abc import ABC
from collections.abc import Callable, Awaitable
from typing import TYPE_CHECKING

from vchat.net.interface import NetHelperInterface, catch_exception

if TYPE_CHECKING:
    from vchat.model import RawMessage
import sys

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override
import yarl


class NetHelperDownloadMixin(NetHelperInterface, ABC):
    @override
    def _get_download_fn(
        self, url: str, params: dict, headers: dict | None = None
    ) -> Callable[..., Awaitable]:
        assert self.login_info.url is not None
        url = self.login_info.url + url

        @catch_exception
        async def download_fn(download_path=None):
            # TODO: 可能会禁用默认header
            async with self.session.get(url, params=params, headers=headers) as resp:
                if download_path is None:
                    with io.BytesIO() as output:
                        async for chunk in resp.content.iter_chunked(1024):
                            output.write(chunk)
                        return output.getvalue()
                else:
                    with open(download_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(1024):
                            f.write(chunk)
                        return

        return download_fn

    @override
    def get_img_download_fn(self, msg_id: str) -> Callable[..., Awaitable]:
        params = {"msgid": msg_id, "skey": self.login_info.skey}
        return self._get_download_fn("/webwxgetmsgimg", params)

    @override
    def get_voice_download_fn(self, msg_id: str):
        params = {"msgid": msg_id, "skey": self.login_info.skey}
        return self._get_download_fn("/webwxgetvoice", params)

    @override
    def get_video_download_fn(self, msg_id: str):
        params = {"msgid": msg_id, "skey": self.login_info.skey}
        headers = {"Range": "bytes=0-"}
        return self._get_download_fn("/webwxgetvideo", params, headers=headers)

    @override
    def get_attach_download_fn(self, rmsg: "RawMessage|dict[str, str]"):
        assert self.login_info.url is not None
        params: dict[str, str | None] = {
            "sender": rmsg["FromUserName"],
            "mediaid": rmsg["MediaId"],
            "filename": rmsg["FileName"],
            "fromuser": self.login_info.wxuin,
            "pass_ticket": "undefined",
            "webwx_data_ticket": self.session.cookie_jar.filter_cookies(
                yarl.URL(self.login_info.url)
            )["webwx_data_ticket"].value,
        }
        return self._get_download_fn("/webwxgetmedia", params)
