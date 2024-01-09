# Ask for Forgiveness, Not Permission (AFNP)


class VChatError(RuntimeError):
    pass


class VMalformedParameterError(VChatError):
    """
    参数格式错误
    """

    pass


class VNetworkError(VChatError):
    """
    网络错误
    """

    pass


class VOperationFailedError(VChatError):
    """
    所有收发消息等需要网络请求的操作，都有可能收到服务器的错误指示，所以任何操作都有可能失败
    """

    pass


class VLoginError(VChatError):
    """
    无法登录，请不要捕获这个异常，无法登录就无法正常运行，应该立刻终止
    """

    pass


class VFileIOError(VChatError):
    """
    文件读写错误
    """

    pass


class VUserCallbackError(VChatError):
    """
    用户提供的回调函数应该抛出这个异常，VChat会处理它，其他异常会向上冒泡
    """

    pass


class VUselessError(VChatError):
    pass
