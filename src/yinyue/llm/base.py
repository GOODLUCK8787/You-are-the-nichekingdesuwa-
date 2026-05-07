from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Abstract LLM client. Implementations: DeepSeek, OpenAI, Ollama."""

    @abstractmethod
    async def chat(self, messages: list[dict], temperature: float = 0.7) -> str:
        """Send a chat completion request. Returns the response text."""
        ...

    @abstractmethod
    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        temperature: float = 0.7,
    ) -> dict:
        """Send a chat completion with function calling. Returns the tool call or text response."""
        ...
