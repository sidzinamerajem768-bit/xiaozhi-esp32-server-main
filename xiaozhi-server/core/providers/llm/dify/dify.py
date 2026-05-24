import json
from config.logger import setup_logging
import requests
from core.providers.llm.base import LLMProviderBase
from core.providers.llm.system_prompt import get_system_prompt_for_function
from core.utils.util import check_model_key

TAG = __name__
logger = setup_logging()


class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.api_key = config["api_key"]
        self.mode = config.get("mode", "chat-messages")
        self.base_url = config.get("base_url", "https://api.dify.ai/v1").rstrip("/")
        self.session_conversation_map = {}  # 存储session_id和conversation_id的映射
        model_key_msg = check_model_key("DifyLLM", self.api_key)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)

    def response(self, session_id, dialogue, **kwargs):
        # Normalize mode: "streaming" is an alias for "chat-messages"
        api_mode = self.mode
        if api_mode == "streaming":
            api_mode = "chat-messages"

        logger.bind(tag=TAG).info(f"[LLM-DIFY] base_url={self.base_url} mode={api_mode} session={session_id[:8]}...")

        last_msg = next(m for m in reversed(dialogue) if m["role"] == "user")
        conversation_id = self.session_conversation_map.get(session_id)

        if api_mode == "chat-messages":
            request_json = {
                "query": last_msg["content"],
                "response_mode": "streaming",
                "user": session_id,
                "inputs": {},
                "conversation_id": conversation_id,
            }
        elif api_mode == "workflows/run":
            request_json = {
                "inputs": {"text": last_msg["content"]},
                "response_mode": "streaming",
                "user": session_id,
            }
            logger.bind(tag=TAG).info(f"{request_json}")
        elif api_mode == "completion-messages":
            request_json = {
                "inputs": {"query": last_msg["content"]},
                "response_mode": "streaming",
                "user": session_id,
            }
        else:
            raise ValueError(
                f"Unsupported Dify mode: {api_mode}, "
                "expected one of: chat-messages, workflows/run, completion-messages"
            )

        with requests.post(
            f"{self.base_url}/{api_mode}",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=request_json,
            stream=True,
        ) as r:
            logger.bind(tag=TAG).info(f"[LLM-DIFY] HTTP {r.status_code} content-type={r.headers.get('content-type', '')}")
            if api_mode == "chat-messages":
                for line in r.iter_lines():
                    if line.startswith(b"data: "):
                        payload = line[6:].decode("utf-8", errors="replace")
                        try:
                            event = json.loads(payload)
                        except json.JSONDecodeError:
                            logger.bind(tag=TAG).warning(f"[LLM-DIFY] malformed SSE: {payload[:200]}")
                            continue
                        logger.bind(tag=TAG).debug(f"[LLM-DIFY] event={event.get('event')} answer_len={len(event.get('answer', '') or '')}")
                        # 如果没有找到conversation_id，则获取此次conversation_id
                        if not conversation_id:
                            conversation_id = event.get("conversation_id")
                            self.session_conversation_map[session_id] = (
                                conversation_id  # 更新映射
                            )
                        # 过滤 message_replace 事件，此事件会全量推一次
                        if event.get("event") != "message_replace" and event.get(
                            "answer"
                        ):
                            yield event["answer"]
            elif api_mode == "workflows/run":
                wf_line_count = 0
                for line in r.iter_lines():
                    wf_line_count += 1
                    if wf_line_count <= 5:
                        logger.bind(tag=TAG).debug(f"[LLM-DIFY-WF] raw[{wf_line_count}]: {line[:300]}")
                    if line.startswith(b"data: "):
                        payload = line[6:].decode("utf-8", errors="replace")
                        try:
                            event = json.loads(payload)
                        except json.JSONDecodeError:
                            logger.bind(tag=TAG).warning(f"[LLM-DIFY] malformed SSE: {payload[:200]}")
                            continue
                        evt = event.get("event")
                        data = event.get("data", {})
                        logger.bind(tag=TAG).debug(f"[LLM-DIFY-WF] event={evt} data_keys={list(data.keys()) if data else 'none'}")
                        if evt == "workflow_finished":
                            status = data.get("status", "")
                            outputs = data.get("outputs", {})
                            answer = outputs.get("answer", "") or outputs.get("text", "") or outputs.get("output", "")
                            logger.bind(tag=TAG).info(f"[LLM-DIFY-WF] finished status={status} outputs_keys={list(outputs.keys()) if outputs else 'none'} answer_len={len(answer)}")
                            if status == "succeeded":
                                if answer:
                                    yield answer
                                else:
                                    yield "【服务响应异常：工作流完成但无输出】"
                            else:
                                yield "【服务响应异常】"
                logger.bind(tag=TAG).debug(f"[LLM-DIFY-WF] total_lines={wf_line_count}")
            elif api_mode == "completion-messages":
                for line in r.iter_lines():
                    if line.startswith(b"data: "):
                        event = json.loads(line[6:])
                        # 过滤 message_replace 事件，此事件会全量推一次
                        if event.get("event") != "message_replace" and event.get(
                            "answer"
                        ):
                            yield event["answer"]

    def response_with_functions(self, session_id, dialogue, functions=None):
        if len(dialogue) == 2 and functions is not None and len(functions) > 0:
            # 第一次调用llm， 取最后一条用户消息，附加tool提示词
            last_msg = dialogue[-1]["content"]
            function_str = json.dumps(functions, ensure_ascii=False)
            modify_msg = get_system_prompt_for_function(function_str) + last_msg
            dialogue[-1]["content"] = modify_msg

        # 如果最后一个是 role="tool"，附加到user上
        if len(dialogue) > 1 and dialogue[-1]["role"] == "tool":
            assistant_msg = "\ntool call result: " + dialogue[-1]["content"] + "\n\n"
            while len(dialogue) > 1:
                if dialogue[-1]["role"] == "user":
                    dialogue[-1]["content"] = assistant_msg + dialogue[-1]["content"]
                    break
                dialogue.pop()

        for token in self.response(session_id, dialogue):
            yield token, None
