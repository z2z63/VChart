from dataclasses import dataclass

from vchat.model import User


@dataclass
class LoginInfo:
    url: str | None = None
    deviceid: str | None = None
    login_time: int | None = None
    base_request: dict | None = None
    skey: str | None = None
    wxsid: str | None = None
    wxuin: str | None = None
    pass_ticket: str | None = None
    user: User | None = None
    invite_start_count: int | None = None
    SyncKey: dict | None = None
    synckey: str | None = None
    file_url: str | None = None
    sync_url: str | None = None
    myname: str | None = None
