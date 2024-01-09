from vchat.core.contact import CoreContactMixin
from vchat.core.hotreload import CoreHotReloadMixin
from vchat.core.login import CoreLoginMixin
from vchat.core.messages import CoreMessageMixin
from vchat.core.register import CoreRegisterMixin
from vchat.net import NetHelper


class Core(
    CoreRegisterMixin,
    CoreHotReloadMixin,
    CoreContactMixin,
    CoreMessageMixin,
    CoreLoginMixin,
):
    @staticmethod
    async def factory() -> "Core":
        helper = await NetHelper.factory()
        return Core(helper)
