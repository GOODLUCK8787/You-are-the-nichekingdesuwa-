import os
import json
import logging
from openai import AsyncOpenAI
from yinyue.llm.base import LLMClient

logger = logging.getLogger(__name__)

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-v4-pro"


class DeepSeekClient(LLMClient):
    """DeepSeek API client with function calling support."""

    def __init__(self, api_key: str = "", model: str = DEFAULT_MODEL):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.model = model
        self._client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=DEEPSEEK_BASE_URL,
        )

    async def chat(self, messages: list[dict], temperature: float = 0.7) -> str:
        response = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""

    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        temperature: float = 0.7,
    ) -> dict:
        response = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            temperature=temperature,
        )

        choice = response.choices[0]
        msg = choice.message

        if msg.tool_calls:
            tc = msg.tool_calls[0]
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}
            return {
                "role": "tool",
                "tool_name": tc.function.name,
                "arguments": args,
                "tool_call_id": tc.id,
            }
        else:
            return {
                "role": "assistant",
                "content": msg.content or "",
            }
