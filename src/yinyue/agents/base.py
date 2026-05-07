import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable

from yinyue.llm.base import LLMClient


class AgentBase(ABC):
    """Base class for all agents. Provides tool registration and LLM interaction."""

    def __init__(self, llm: LLMClient, name: str = ""):
        self.llm = llm
        self.name = name or self.__class__.__name__
        self.logger = logging.getLogger(self.name)
        self._tools: dict[str, dict] = {}       # tool_name -> tool_def
        self._handlers: dict[str, Callable] = {}  # tool_name -> handler_fn

    def register_tool(self, name: str, description: str, parameters: dict, handler: Callable):
        """Register a tool the LLM can call."""
        self._tools[name] = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
        }
        self._handlers[name] = handler

    def get_tools(self) -> list[dict]:
        return list(self._tools.values())

    async def _call_tool(self, name: str, arguments: dict) -> Any:
        handler = self._handlers.get(name)
        if not handler:
            raise ValueError(f"Unknown tool: {name}")
        return await handler(**arguments) if hasattr(handler, "__call__") else handler(**arguments)

    async def _llm_chat(self, messages: list[dict], temperature: float = 0.7) -> str:
        return await self.llm.chat(messages, temperature=temperature)

    async def _llm_chat_with_tools(
        self, messages: list[dict], temperature: float = 0.7
    ) -> dict:
        return await self.llm.chat_with_tools(
            messages=messages,
            tools=self.get_tools(),
            temperature=temperature,
        )

    async def run_tool_loop(
        self, system_prompt: str, user_message: str, max_turns: int = 5
    ) -> list[dict]:
        """
        Execute a tool-use loop: send prompt, handle tool calls, repeat.
        Returns conversation history.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        history = list(messages)

        for _ in range(max_turns):
            response = await self._llm_chat_with_tools(messages)

            if response.get("role") == "tool":
                # LLM returned a tool call
                tool_name = response.get("tool_name", "")
                arguments = response.get("arguments", {})
                self.logger.info(f"Tool call: {tool_name}({arguments})")
                result = await self._call_tool(tool_name, arguments)
                result_msg = {
                    "role": "tool",
                    "content": json.dumps(result, ensure_ascii=False),
                    "tool_call_id": response.get("tool_call_id", ""),
                }
                messages.append({"role": "assistant", "content": None, "tool_calls": [response]})
                messages.append(result_msg)
                history.append(response)
                history.append(result_msg)
            else:
                # LLM returned text — done
                history.append(response)
                return history

        return history

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute this agent's task. Subclasses must implement."""
        ...
