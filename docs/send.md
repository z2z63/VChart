# 收发消息
## username
`username`是一个联系人（Contact）的临时标识，分为四种情况
1. 个人的`username`格式类似`@ahjad31242ad...`
2. 群聊的`username`的格式类似`@@ahjad31242ad...`
3. 公众号的`username`格式与个人相同，但`VerifyFlag & 8 != 0`
4. 特殊帐号，例如`filehelper`（文件传输助手），`weixin`（微信团队）等

## 消息的发送者，接受者
- 好友给自己发送消息  
  收到的消息中，`msg.from_.username`为好友的`username`，`msg.to.username`为自己的`username`
- 收到群聊中某个群员发送的消息  
  收到的消息中，`msg.from_.username`为群聊的`username`，`msg.to.username`为自己的`username`，`msg.chatroom_sender.username`为发送消息的群员的`username`
- 自己给好友发送消息
  会收到回显消息，一般需要过滤此消息
- 自己在群聊中发送消息
  会收到回显消息，一般需要过滤此消息

## 发送消息
目前支持以下消息的发送
- `send_msg`：发送文本消息
- `send_file`：发送文件，可以提供文件路径，也可以传入一个file like的对象
- `send_image`：发送图片，可以提供文件路径，也可以传入一个file like的对象
- `send_video`：发送视频，可以提供文件路径，也可以传入一个file like的对象
- `revoke`: 撤回消息，需要提供发送的消息的`message_id`

## 接受消息
获取的消息`msg`的`content`携带了消息的内容，支持以下消息，具体见[Content](./model.md#内容content)
- TextContent(文本)
- ImageContent(图片)
- VideoContent(视频)
- VoiceContent(音频)
- AttachContent(文件)
- RevokeContent(撤回消息)

场景1: 已知`msg.content`的类型  
因为注册回调函数时已经指明了消息的类型，此时使用`assert(isinstance(msg.content, TextContent))`，就能利用`TextContent`类型声明提供的补全

场景2: 需要判断`msg.content`的类型  
使用if else判断类型即可，例如
```python
if isinstance(msg.content, TextContent):
    # 处理文本消息
elif isinstance(msg.content, ImageContent):
    # 处理图片消息
#  ...
```