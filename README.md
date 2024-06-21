# VChat - 基于itchat-uos完全重构的微信个人号接口

# 为什么使用VChat

- 2024年确认可使用的少数微信个人帐号接口项目
- 基于itchat-uos完全重构，type hint友好
- 使用异步协程和结构化并发代替原itchat-uos的基于多线程的并发，性能更高，更容易集成到你的项目中
- 不需要在2017年之前登录过微信网页端，不需要开通支付功能，新注册的微信号也能使用
- 支持帐号多开

# 快速开始

最小工作实例

```python
import asyncio

from vchat import Core
from vchat.model import ContentTypes, ContactTypes

core = Core()
# 注册消息回调函数，收到感兴趣的消息后，VChat会调用这个函数
# 设置过滤器，只处理文本类型的消息，只接受群聊的消息
@core.msg_register(msg_types=ContentTypes.TEXT, contact_type=ContactTypes.CHATROOM)
async def _(msg):
   print(msg.content.content)  # 打印消息的内容


async def main():
   await core.init()
   await core.auto_login(hot_reload=True)
   # 给文件传输助手发送hello, filehelper
   await core.send_msg("hello, filehelper", to_username="filehelper")
   # 启动VChat的消息接收循环
   await core.run()


if __name__ == "__main__":
   asyncio.run(main())
```

已确认可以工作的功能

1. 接受文本，图片，音频，视频，文件
2. 发送文本，图片，视频，文件
3. 收发好友消息和群聊消息

更多介绍详见doc目录
# 免责声明

使用本项目默认用户已经阅读并知悉[微信个人账号使用规范](https://weixin.qq.com/cgi-bin/readtemplate?&t=page/agreement/personal_account&lang=zh_CN)

推荐单独注册一个微信号，并严格限制其用途，严格遵守《计算机软件保护条例》（2013修订）第十七条规定，禁止商用
> 为了学习和研究软件内含的设计思想和原理，通过安装、显示、传输或者存储软件等方式使用软件的，可以不经软件著作权人许可

一切由于使用本项目造成的后果由使用者自行承担

如有侵权，请联系作者删除
