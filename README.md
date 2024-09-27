# VChat - 基于itchat-uos完全重构的微信个人号接口

# 为什么使用VChat

- 2024年确认可使用的少数微信个人帐号接口项目
- 基于itchat-uos完全重构，type hint友好
- 使用异步协程和结构化并发代替原itchat-uos的基于多线程的并发，性能更高，更容易集成到你的项目中
- 不需要在2017年之前登录过微信网页端，不需要开通支付功能，新注册的微信号也能使用
- 支持帐号多开

# 演示
<div style="display: flex;justify-content: space-around;width: 900px">
<img alt="demo1" style="width:400px" src="https://raw.githubusercontent.com/z2z63/image/main/202407302302972.png"/>
<img alt="demo1"  style="width:400px" src="https://raw.githubusercontent.com/z2z63/image/main/202407302305229.png"/>
</div>

# 快速开始
1. 安装`vchat`(目前需要python版本3.10及以上)
    ```shell
    pip install vchat
    ```
2. 新建文件`main.py`，内容如下
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
3. 运行
    ```shell
    python main.py
    ```
4. 终端中完成扫码
5. enjoy

# 文档
- [联系人(Contact)](./docs/model.md#联系人contact)
- [消息(Message)](./docs/model.md#消息message)
- [内容(Content)](./docs/model.md#内容content)
- [收发消息](./docs/send.md#收发消息)

已确认可以工作的功能

1. 接受文本，图片，音频，视频，文件
2. 发送文本，图片，视频，文件
3. 收发好友消息和群聊消息

## 兼容性
因为使用了新的union语法，需要python3.10及以上版本，未来会去除这个限制
## QA
- VChat支持同步调用吗？  
不支持，因为异步协程是更简单的并发模型，符合结构化并发，而且python的同步和异步差别很大，无法一份代码同时供同步异步调用  

- 如何将VChat集成到我的项目中？  
异步：使用`TaskGroup`等待`core.run`和你的异步主函数即可  
同步：创建一个线程，使用`asyncio.run`运行`vchat`即可  
# 重要
VChat是在MIT许可证下发行的自由软件，这意味着您可以在承认原作者（LittleCoder）的copyright的前提下以任何意图运行VChat、分发VChat的副本、修改VChat、重分发修改后的副本

使用VChat前，您应当知悉，VChat依赖于微信服务，这是一个商业的、专有的互联网服务，您无法在不使用微信服务的情况下使用VChat  
因此，尽管原作者通过MIT协议授予您使用VChat的自由，但您如何使用微信服务仍然受[微信个人账号使用规范](https://weixin.qq.com/cgi-bin/readtemplate?&t=page/agreement/personal_account&lang=zh_CN)，以及您所在地区或国家的法律法规所限制  

作者遵循原itchat-uos的协议，不在MIT协议之上附加任何条款，也不限制您使用VChat的自由。作者开发并维护VChat的原因仅仅是学习itchat-uos内部的原理、在linux平台使用微信。您在使用VChat过程中产生的任何滥用行为所造成的后果由您承担
> 为了学习和研究软件内含的设计思想和原理，通过安装、显示、传输或者存储软件等方式使用软件的，可以不经软件著作权人许可
