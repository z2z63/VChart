from vchat.core.contact import CoreContactMixin
from vchat.core.hotreload import CoreHotReloadMixin
from vchat.core.login import CoreLoginMixin
from vchat.core.messages import CoreMessageMixin
from vchat.core.register import CoreRegisterMixin


class Core(
    CoreRegisterMixin,
    CoreHotReloadMixin,
    CoreContactMixin,
    CoreMessageMixin,
    CoreLoginMixin,
):
    async def init(self):
        await self._net_helper.init()
