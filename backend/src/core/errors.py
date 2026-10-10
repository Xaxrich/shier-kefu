"""业务层可抛出、路由层转换为 HTTP 的异常。"""


class ForbiddenError(Exception):
    def __init__(self, message: str = "禁止访问"):
        self.message = message
        super().__init__(message)


class BadRequestError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class LlmNotConfiguredError(Exception):
    """未在 config.toml 配置 llm_api_key。"""

    def __init__(self, message: str = "未配置 LLM（llm_api_key），无法生成智能回答"):
        self.message = message
        super().__init__(message)
