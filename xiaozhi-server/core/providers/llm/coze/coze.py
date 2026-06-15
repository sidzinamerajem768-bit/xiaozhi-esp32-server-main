from config.logger import setup_logging
import json
from core.providers.llm.base import LLMProviderBase

# official coze sdk for Python [cozepy](https://github.com/coze-dev/coze-py)
from cozepy import COZE_CN_BASE_URL
from cozepy import (
    Coze,
    TokenAuth,
    Message,
    ChatEventType,
)  # noqa
from core.providers.llm.system_prompt import get_system_prompt_for_function
from core.utils.util import check_model_key

TAG = __name__
logger = setup_logging()


class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.personal_access_token = config.get("personal_access_token")
        self.bot_id = str(config.get("bot_id"))
        self.user_id = str(config.get("user_id"))
        self.session_conversation_map = {}  # 存储session_id和conversation_id的映射
        # 标记为提示词注入模式，框架侧不会在工具调用后再调用 LLM 生成回复
        self._is_prompt_injection_provider = True

        # 复用 Coze 客户端实例（HTTP keep-alive 连接池），每轮不再新建
        coze_api_token = self.personal_access_token
        coze_api_base = COZE_CN_BASE_URL
        self.coze_client = Coze(
            auth=TokenAuth(token=coze_api_token), base_url=coze_api_base
        )

        model_key_msg = check_model_key("CozeLLM", self.personal_access_token)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)

    def response(self, session_id, dialogue, **kwargs):
        last_msg = next(m for m in reversed(dialogue) if m["role"] == "user")

        conversation_id = self.session_conversation_map.get(session_id)

        # 如果没有找到conversation_id，则创建新的对话
        if not conversation_id:
            conversation = self.coze_client.conversations.create(messages=[])
            conversation_id = conversation.id
            self.session_conversation_map[session_id] = conversation_id  # 更新映射

        for event in self.coze_client.chat.stream(
            bot_id=self.bot_id,
            user_id=self.user_id,
            additional_messages=[
                Message.build_user_question_text(last_msg["content"]),
            ],
            conversation_id=conversation_id,
        ):
            if event.event == ChatEventType.CONVERSATION_MESSAGE_DELTA:
                yield event.message.content

    def response_with_functions(self, session_id, dialogue, functions=None):
        # 动态注入工具列表：每次调用都把当前可用工具注入到最后一条用户消息
        if functions is not None and len(functions) > 0:
            last_msg = dialogue[-1]["content"]
            # 避免重复注入（检查是否已有 TOOL USE 标记）
            if "TOOL USE" not in last_msg:
                function_str = json.dumps(functions, ensure_ascii=False)
                modify_msg = get_system_prompt_for_function(function_str) + last_msg
                dialogue[-1]["content"] = modify_msg

        for token in self.response(session_id, dialogue):
            yield token, None
