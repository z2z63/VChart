import re
import sys
import time
from abc import ABC
from collections.abc import Iterable
from typing import Optional

import yarl
from aiohttp.abc import AbstractCookieJar

from vchat import config
from vchat.errors import VLoginError
from vchat.model import Contact
from vchat.model import User
from vchat.net.interface import NetHelperInterface, catch_exception
from vchat.storage.login_info import LoginInfo

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override


def _cookie_lookup(cookie_jar: AbstractCookieJar, key: str) -> str | None:
    # cookie_jar在iter时自动完成过期，此时报错
    #     for (domain, path), cookie in self._cookies.items():
    #         ^^^^^^^^^^^^^^
    # ValueError: too many values to unpack (expected 2)
    try:
        for cookie in cookie_jar:
            if key == cookie.key:
                return cookie.value
    except ValueError as e:
        pass
    return None


class NetHelperLoginMixin(NetHelperInterface, ABC):
    @override
    @catch_exception
    async def get_qr_uuid(self) -> str:
        url = config.BASE_URL + "/jslogin"
        params = {
            "appid": "wx782c26e4c19acffb",
            "fun": "new",
            "redirect_uri": "https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxnewloginpage?mod=desktop",
            "lang": "zh_CN",
        }

        async with self.session.get(url, params=params) as resp:
            text = await resp.text()
            regx = r'window.QRLogin.code = (\d+); window.QRLogin.uuid = "(\S+?)";'
            ma = re.search(regx, text)
            if ma is None:
                raise VLoginError("QR code not found: " + text)
            elif ma.group(1) != "200":
                raise VLoginError("QR code invalid: " + text)
            else:
                return ma.group(2)

    @override
    @catch_exception
    async def check_qr_scan_status(self, uuid):
        url = config.BASE_URL + "/cgi-bin/mmwebwx-bin/login"
        localTime = int(time.time())
        params = {
            "loginicon": "true",
            "uuid": uuid,
            "tip": 1,
            "r": int(-localTime / 1579),
            "_": localTime,
        }

        async with self.session.get(url, params=params) as resp:
            text = await resp.text()
            regx = r"window.code=(\d+)"
            ma = re.search(regx, text)
            if ma is None:
                raise VLoginError("code not found" + text)
            return ma.group(1), text

    @override
    def load_login_info_from_pickle(self, login_info: LoginInfo):
        self.login_info = login_info

    @override
    @catch_exception
    async def load_login_info_from_wechat(self, login_content):
        """when finish login (scanning qrcode)
        * syncUrl and fileUploadingUrl will be fetched
        * deviceid and msgid will be generated
        * skey, wxsid, wxuin, pass_ticket will be fetched
        """
        regx = r'window.redirect_uri="(\S+)";'
        ma = re.search(regx, login_content)
        if ma is None:
            raise VLoginError("login error")
        self.login_info.url = ma.group(1)
        headers = {
            "User-Agent": config.USER_AGENT,
            "client-version": config.UOS_PATCH_CLIENT_VERSION,
            "extspam": config.UOS_PATCH_EXTSPAM,
            "referer": "https://wx.qq.com/?&lang=zh_CN&target=t",
        }
        async with self.session.get(
            self.login_info.url, headers=headers, allow_redirects=False
        ) as resp:
            text = await resp.text()
        # TODO: 优化
        self.login_info.url = self.login_info.url[: self.login_info.url.rfind("/")]
        for index_url, detailed_url in (
            ("wx2.qq.com", ("file.wx2.qq.com", "webpush.wx2.qq.com")),
            ("wx8.qq.com", ("file.wx8.qq.com", "webpush.wx8.qq.com")),
            ("qq.com", ("file.wx.qq.com", "webpush.wx.qq.com")),
            ("web2.wechat.com", ("file.web2.wechat.com", "webpush.web2.wechat.com")),
            ("wechat.com", ("file.web.wechat.com", "webpush.web.wechat.com")),
        ):
            file_url = f"https://{detailed_url[0]}/cgi-bin/mmwebwx-bin"
            sync_url = f"https://{detailed_url[1]}/cgi-bin/mmwebwx-bin"
            if index_url in self.login_info.url:
                self.login_info.file_url = file_url
                self.login_info.sync_url = sync_url
                break
        else:
            self.login_info.file_url = self.login_info.sync_url = self.login_info.url
        self.login_info.deviceid = config.DEVICEID
        self.login_info.login_time = int(time.time() * 1e3)
        self.login_info.base_request = {}
        skey = re.findall("<skey>(.*?)</skey>", text, re.S)[0]
        pass_ticket = re.findall("<pass_ticket>(.*?)</pass_ticket>", text, re.S)[0]
        self.login_info.skey = self.login_info.base_request["Skey"] = skey

        cookies = self.session.cookie_jar.filter_cookies(yarl.URL(self.login_info.url))
        self.login_info.wxsid = self.login_info.base_request["Sid"] = cookies[
            "wxsid"
        ].value
        self.login_info.wxuin = self.login_info.base_request["Uin"] = cookies[
            "wxuin"
        ].value
        self.login_info.pass_ticket = pass_ticket

    @override
    @catch_exception
    async def web_init(self) -> Iterable[Contact]:
        """
        get info necessary for initializing
        for processing:
            - own account info is set
            - inviteStartCount is set
            - syncKey is set
            - part of contact is fetched
        it is defined in components/login.py
        """
        assert self.login_info.url is not None
        assert self.login_info.pass_ticket is not None
        url = self.login_info.url + "/webwxinit"
        params: dict[str, str | int] = {
            "r": int(-time.time() / 1579),
            "pass_ticket": self.login_info.pass_ticket,
        }
        data = {"BaseRequest": self.login_info.base_request}

        async with self.session.post(url, params=params, json=data) as resp:
            dic = await resp.json(content_type=None)
        self.login_info.invite_start_count = int(dic["InviteStartCount"])
        self.login_info.user = User(**dic["User"])
        self.login_info.myname = self.login_info.user.username  # TODO
        self.login_info.SyncKey = dic["SyncKey"]
        self.login_info.synckey = "|".join(
            ["%s_%s" % (item["Key"], item["Val"]) for item in dic["SyncKey"]["List"]]
        )
        return (Contact.constructor(item) for item in dic["ContactList"])

    @override
    @catch_exception
    async def show_mobile_login(self):
        """show web WeChat login sign
        the sign is on the top of mobile phone WeChat
        sign will be added after sometime even without calling this function
        it is defined in components/login.py
        """
        assert self.login_info.url is not None
        url = self.login_info.url + "/webwxstatusnotify"
        params = {"lang": "zh_CN", "pass_ticket": self.login_info.pass_ticket}
        data = {
            "BaseRequest": self.login_info.base_request,
            "Code": 3,
            "FromUserName": self.login_info.myname,
            "ToUserName": self.login_info.myname,
            "ClientMsgId": int(time.time()),
        }

        async with self.session.post(url, params=params, json=data):
            pass

    @override
    def clear_cookies(self):
        self.session.cookie_jar.clear()

    @override
    def load_cookies(self, cookie):
        self.session.cookie_jar._cookies = (
            cookie  # 因为aiohttp限制，为了将所有数据都保存在一个文件中
        )
        _cookie_lookup(self.session.cookie_jar, "wxuin")

    @override
    def get_dumpable_cookies(self):
        return (
            self.session.cookie_jar._cookies
        )  # 因为aiohttp限制，为了将所有数据都保存在一个文件中

    @override
    @catch_exception
    async def push_login(self) -> Optional[str]:
        # assert self.login_info.url is not None
        # cookie = self.session.cookie_jar.filter_cookies(
        #     yarl.URL(self.login_info.url)
        # )
        # if "wxuin" not in cookie:
        #     return None
        wxuin = _cookie_lookup(self.session.cookie_jar, "wxuin")
        if wxuin is None:
            return None
        url = config.BASE_URL + "/cgi-bin/mmwebwx-bin/webwxpushloginurl"
        params = {"uin": wxuin}
        async with self.session.get(url, params=params) as resp:
            data = await resp.json(content_type=None)
        if "uuid" in data and data.get("ret") in (0, "0"):
            return data["uuid"]
        return None

    @override
    @catch_exception
    async def logout(self):
        assert self.login_info.url is not None
        url = self.login_info.url + "/webwxlogout"
        params = {"redirect": 1, "type": 1, "skey": self.login_info.skey}
        async with self.session.get(url, params=params):
            pass
