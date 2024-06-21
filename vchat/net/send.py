import hashlib
import json
import math
import mimetypes
import time
from abc import ABC
from typing import BinaryIO
from urllib.parse import quote

import yarl
from aiohttp import FormData

from vchat import config
from vchat.errors import VOperationFailedError
from vchat.model import MediaTypes
from vchat.net.interface import NetHelperInterface


class NetHelperSendMixin(NetHelperInterface, ABC):
    async def upload_file(
        self, file_name: str, fd: BinaryIO, to_username: str
    ) -> tuple[str, int]:
        assert self.login_info.url is not None
        encoded_file_name = quote(file_name)
        file_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
        file_bytes = fd.read()
        fd.seek(0)
        file_size = len(file_bytes)
        file_md5 = hashlib.md5(file_bytes).hexdigest()
        client_media_id = int(time.time() * 1e4)  # TODO: 尝试改进client_media_id

        if "." not in file_name:
            media_type = MediaTypes.DOC
        else:
            match file_name.split(".")[-1].lower():
                case "jpg" | "jpeg" | "png":
                    media_type = MediaTypes.IMG
                case "mp4":
                    media_type = MediaTypes.VIDEO
                case _:
                    media_type = MediaTypes.DOC

        upload_media_request = {
            "UploadType": 2,
            "BaseRequest": self.login_info.base_request,
            "ClientMediaId": client_media_id,
            "TotalLen": file_size,
            "StartPos": 0,
            "DataLen": file_size,
            "MediaType": 4,
            "FromUserName": self.login_info.myname,
            "ToUserName": to_username,
            "FileMd5": file_md5,
        }
        assert self.login_info.pass_ticket is not None
        # https://requests.readthedocs.io/en/latest/api/#:~:text=with%20the%20Request.-,files,-%E2%80%93%20(optional)%20Dictionary%20of%20%27name
        # files: dict[str, tuple[None, str] | tuple[str, bytes, str]] = {
        #     "id": (None, "WU_FILE_0"),
        #     "name": (None, encoded_file_name),
        #     "type": (None, file_type),
        #     "lastModifiedDate": (
        #         None,
        #         time.strftime(
        #             "%a %b %d %Y %H:%M:%S GMT+0800 (CST)"
        #         ),  # TODO: 加入fstat读取mtime功能
        #     ),
        #     "size": (None, str(file_size)),
        #     "mediatype": (None, media_type.value),
        #     "uploadmediarequest": (None, json.dumps(upload_media_request)),
        #     "webwx_data_ticket": (
        #         None,
        #         self.session.cookie_jar.filter_cookies(yarl.URL(self.login_info.url))[
        #             "webwx_data_ticket"
        #         ].value,
        #     ),
        #     "pass_ticket": (None, self.login_info.pass_ticket),
        # }
        form_data = FormData()
        fields = [
            ("id", "WU_FILE_0"),
            ("name", encoded_file_name),
            ("type", file_type),
            (
                "lastModifiedDate",
                time.strftime("%a %b %d %Y %H:%M:%S GMT+0800 (CST)"),
            ),
            ("size", str(file_size)),
            ("mediatype", media_type.value),
            ("uploadmediarequest", json.dumps(upload_media_request)),
            (
                "webwx_data_ticket",
                self.session.cookie_jar.filter_cookies(yarl.URL(self.login_info.url))[
                    "webwx_data_ticket"
                ].value,
            ),
            ("pass_ticket", self.login_info.pass_ticket),
        ]
        if file_size <= 512 * 1024:
            # files["filename"] = (
            #     encoded_file_name,
            #     fd.read(),
            #     "application/octet-stream",
            # )

            form_data.add_fields(*fields)
            form_data.add_field("filename", fd.read(), filename=encoded_file_name)
            data = await self._upload_chunk_file(form_data)
            media_id = data["MediaId"]
        else:
            chunks = math.ceil(file_size / (512 * 1024))
            data = {}
            for chunk in range(chunks):
                form_data = FormData()
                form_data.add_fields(*fields)
                form_data.add_field("chunk", str(chunk))
                form_data.add_field("chunks", str(chunks))
                form_data.add_field(
                    "filename", fd.read(512 * 1024), filename=encoded_file_name
                )

                # files.update(
                #     {
                #         "chunk": (None, str(chunk)),
                #         "chunks": (None, str(chunks)),
                #         "filename": (
                #             encoded_file_name,
                #             fd.read(512 * 1024),
                #             "application/octet-stream",
                #         ),
                #     }
                # )
                data = await self._upload_chunk_file(form_data)
            media_id = data["MediaId"]
        return media_id, file_size

    async def _upload_chunk_file(self, form_data: FormData):
        assert self.login_info.file_url is not None
        url = self.login_info.file_url + "/webwxuploadmedia?f=json"

        async with self.session.post(
            url, data=form_data, timeout=config.TIMEOUT
        ) as resp:
            data = await resp.json(content_type=None)
            if data["BaseResponse"]["Ret"] != 0:
                raise VOperationFailedError("上传文件失败")
            return data

    async def send_document(
        self, file_name: str, media_id: str, file_size: int, to_username: str
    ) -> str:
        if "." in file_name:
            suffix = file_name.split(".")[-1]
        else:  # 处理没有扩展名的情况
            suffix = ""
        url = "%s/webwxsendappmsg?fun=async&f=json" % self.login_info.url
        msg_id = str(int(time.time() * 1e4))
        data = {
            "BaseRequest": self.login_info.base_request,
            "Msg": {
                "Type": 6,
                "Content": (
                    f"<appmsg appid='wxeb7ec651dd0aefa9' sdkver=''><title>{file_name}</title>"
                    + "<des></des><action></action><type>6</type><content></content><url></url><lowurl></lowurl>"
                    + f"<appattach><totallen>{file_size}</totallen><attachid>{media_id}</attachid>"
                    + f"<fileext>{suffix}</fileext></appattach><extinfo></extinfo></appmsg>"
                ),
                "FromUserName": self.login_info.myname,
                "ToUserName": to_username,
                "LocalID": msg_id,
                "ClientMsgId": msg_id
            },
            "Scene": 0,
        }
        async with self.session.post(url, json=data) as resp:
            dic = await resp.json(content_type=None)
            if dic["BaseResponse"]["Ret"] != 0:
                raise VOperationFailedError("发送文件失败")
        return msg_id

    async def send_image(self, media_id: str, to_username: str) -> str:
        assert self.login_info.url is not None
        url = self.login_info.url + "/webwxsendmsgimg?fun=async&f=json"
        msg_id = str(int(time.time() * 1e4))
        data = {
            "BaseRequest": self.login_info.base_request,
            "Msg": {
                "Type": 3,
                "MediaId": media_id,
                "FromUserName": self.login_info.myname,
                "ToUserName": to_username,
                "LocalID": msg_id,
                "ClientMsgId": msg_id,
            },
            "Scene": 0,
        }

        async with self.session.post(url, json=data) as resp:
            dic = await resp.json(content_type=None)
            if dic["BaseResponse"]["Ret"] != 0:
                raise VOperationFailedError("发送图片失败")
        return msg_id

    async def send_gif(self, media_id: str, to_username: str) -> None:
        assert self.login_info.url is not None
        url = self.login_info.url + "/webwxsendemoticon?fun=sys"
        msg_id = str(int(time.time() * 1e4))
        data = {
            "BaseRequest": self.login_info.base_request,
            "Msg": {
                "Type": 47,
                "EmojiFlag": 2,
                "MediaId": media_id,
                "FromUserName": self.login_info.myname,
                "ToUserName": to_username,
                "LocalID": msg_id,
                "ClientMsgId": msg_id,
            },
            "Scene": 0,
        }
        async with self.session.post(url, json=data) as resp:
            dic = await resp.json(content_type=None)
            if dic["BaseResponse"]["Ret"] != 0:
                raise VOperationFailedError("发送gif失败")
        return msg_id

    async def send_video(self, media_id: str, to_username: str) -> str:
        url = "%s/webwxsendvideomsg?fun=async&f=json&pass_ticket=%s" % (
            self.login_info.url,
            self.login_info.pass_ticket,
        )
        msg_id = str(int(time.time() * 1e4))
        data = {
            "BaseRequest": self.login_info.base_request,
            "Msg": {
                "Type": 43,
                "MediaId": media_id,
                "FromUserName": self.login_info.myname,
                "ToUserName": to_username,
                "LocalID": msg_id,
                "ClientMsgId": msg_id,
            },
            "Scene": 0,
        }

        async with self.session.post(url, json=data) as resp:
            dic = await resp.json(content_type=None)
            if dic["BaseResponse"]["Ret"] != 0:
                raise VOperationFailedError("发送视频失败")
        return msg_id

    async def send_raw_msg(self, msg_type: int, content: str, to_username: str) -> str:
        # 有些帐号不能给自己发送消息
        assert self.login_info.url is not None
        url = self.login_info.url + "/webwxsendmsg"
        msg_id = str(int(time.time() * 1e4))
        data = {
            "BaseRequest": self.login_info.base_request,
            "Msg": {
                "Type": msg_type,
                "Content": content,
                "FromUserName": self.login_info.myname,
                "ToUserName": to_username,
                "LocalID": msg_id,
                "ClientMsgId": msg_id,
            },
            "Scene": 0,
        }
        async with self.session.post(url, json=data) as resp:
            dic = await resp.json(content_type=None)
            if dic["BaseResponse"]["Ret"] != 0:
                raise VOperationFailedError("发送消息失败")
        return msg_id

    async def revoke(self, msg_id: str, to_username: str, local_id=None) -> None:
        assert self.login_info.url is not None
        url = self.login_info.url + "/webwxrevokemsg"
        data = {
            "BaseRequest": self.login_info.base_request,
            "ClientMsgId": local_id or str(time.time() * 1e3),
            "SvrMsgId": msg_id,
            "ToUserName": to_username,
        }
        async with self.session.post(url, json=data) as resp:
            dic = await resp.json(content_type=None)
        if dic["BaseResponse"]["Ret"] != 0:
            raise VOperationFailedError("撤回消息失败")
