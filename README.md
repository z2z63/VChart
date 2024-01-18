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

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

core = loop.run_until_complete(Core.factory())


# 注册消息回调函数，收到感兴趣的消息后，VChat会调用这个函数
# 设置过滤器，只处理文本类型的消息，只接受群聊的消息
@core.msg_register(msg_types=ContentTypes.TEXT, contact_type=ContactTypes.CHATROOM)
async def _(msg):
   print(msg.content.content)  # 打印消息的内容


async def main():
   await core.auto_login(hot_reload=True)
   # 给文件传输助手发送hello, filehelper
   await core.send_msg("hello, filehelper", to_username="filehelper")
   # 启动VChat的消息接收循环
   await core.run()


if __name__ == "__main__":
   asyncio.run(main(), loop_factory=lambda: loop)
```

已确认可以工作的功能

1. 接受文本，图片，音频，视频，文件
2. 发送文本，图片，视频，文件
3. 收发好友消息和群聊消息

更多介绍详见doc目录

# 项目背景

微信，作为中国大陆每个人不得不使用的即时通讯软件，在2024年仍然没有原生支持Linux，在可预见的几年内仍然没有希望在Linux平台正常使用微信  
**本项目的开发动机是方便Linux用户正常使用微信，并无意丰富微信的生态，只是在无法拒绝使用微信的情况下的无奈之举**  
本项目受[微信转发telegram](https://github.com/zhangyile/telegram-wechat)项目启发，试图使用flutter实现一个跨平台的微信客户端，尝试实现以下特性

1. 更小的磁盘占用  
   微信转发telegram使用六个月后，接受的文件总占用不超过400MB，这证明减小磁盘占用到1G以内是完全可行的
2. 更好的Linux高分屏适配  
   Linux的高分屏真的是一言难尽...
3. 更长的聊天记录保存和文件保存时长  
   客户端开源的telegram可以保存文件若干年，甚至有利用telegram服务器实现个人网盘的方案，对比微信用户常常遇到’文件已清理‘
4. 更优秀的内存占用和运行时开销，更小的软件体积  
   Linux上使用微信的方案基本上有两种，一是基于wine，二是基于uos微信，前者需要运行wine提供兼容层作为Windows微信运行时，后者是electron应用
   ，flutter作为现代跨平台app开发技术，在内存占用和软件体积上都能优于这两种解决方案

项目fork自[itchat-uos](https://github.com/why2lyj/ItChat-UOS)，微信关闭网页端入口后，许多微信自动化相关的项目都无法工作，近三年来由于国产统信
操作系统（UOS）的上使用微信的需要，微信开放了网页端接口但是限制只允许UOS请求头，使得少部分项目死而复生，本项目基于itchat-uos完全重构，是开发跨平台微信客户端的第一步尝试