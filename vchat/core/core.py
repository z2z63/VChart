from vchat.core.contact import CoreContactMixin
from vchat.core.hotreload import CoreHotReloadMixin
from vchat.core.login import CoreLoginMixin
from vchat.core.messages import CoreMessageMixin
from vchat.core.register import CoreRegisterMixin
from vchat.core.utils import CoreUtilsMixin


class Core(
    CoreRegisterMixin,
    CoreHotReloadMixin,
    CoreContactMixin,
    CoreMessageMixin,
    CoreLoginMixin,
    CoreUtilsMixin,
):
    async def init(self):
        await self._net_helper.init()
