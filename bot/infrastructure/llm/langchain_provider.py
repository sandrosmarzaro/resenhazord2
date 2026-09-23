import json
from dataclasses import dataclass
from typing import ClassVar

import structlog
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import Runnable
from langchain_groq import ChatGroq
from langchain_mistralai import ChatMistralAI
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from bot.infrastructure.llm.providers.base import LLMResponse

logger = structlog.get_logger()


@dataclass(frozen=True)
class _Model:
    chat: BaseChatModel
    supports_tools: bool


class LangChainProvider:
    PROVIDER_NAME: ClassVar[str] = 'langchain'
    MISTRAL_MODEL: ClassVar[str] = 'mistral-small-latest'
    GROQ_MODEL: ClassVar[str] = 'openai/gpt-oss-120b'
    GOOGLE_MODEL: ClassVar[str] = 'gemini-3.6-flash'
    GOOGLE_BASE_URL: ClassVar[str] = 'https://generativelanguage.googleapis.com/v1beta/openai'
    MAX_TOKENS: ClassVar[int] = 500

    _instance: ClassVar['LangChainProvider | None'] = None

    def __init__(self, models: list[_Model]) -> None:
        self._models = models

    @classmethod
    def from_credentials(
        cls, mistral_key: str, groq_key: str, google_key: str
    ) -> 'LangChainProvider':
        # langchain integrations drift on field names: Mistral takes model_name,
        # Groq/OpenAI take model. Gemini rides its OpenAI-compatible endpoint through
        # ChatOpenAI + a custom base_url. Keys are wrapped in SecretStr.
        models: list[_Model] = []
        if mistral_key:
            mistral = ChatMistralAI(
                model_name=cls.MISTRAL_MODEL,
                api_key=SecretStr(mistral_key),
                max_tokens=cls.MAX_TOKENS,
            )
            models.append(_Model(mistral, supports_tools=True))
        if groq_key:
            groq = ChatGroq(
                model=cls.GROQ_MODEL, api_key=SecretStr(groq_key), max_tokens=cls.MAX_TOKENS
            )
            models.append(_Model(groq, supports_tools=True))
        if google_key:
            google = ChatOpenAI(
                model=cls.GOOGLE_MODEL,
                api_key=SecretStr(google_key),
                base_url=cls.GOOGLE_BASE_URL,
                max_completion_tokens=cls.MAX_TOKENS,
            )
            models.append(_Model(google, supports_tools=True))
        return cls(models)

    @classmethod
    def configure(cls, mistral_key: str, groq_key: str, google_key: str) -> 'LangChainProvider':
        cls._instance = cls.from_credentials(mistral_key, groq_key, google_key)
        return cls._instance

    @classmethod
    def configured(cls) -> 'LangChainProvider | None':
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    async def complete(self, prompt: str, tools: list[dict]) -> LLMResponse:
        chain = self._build_chain(tools)
        message = await chain.ainvoke([HumanMessage(content=prompt)])
        return self._to_response(message)

    def _build_chain(self, tools: list[dict]) -> Runnable:
        runnables = [self._bind(model, tools) for model in self._models]
        primary, fallbacks = runnables[0], runnables[1:]
        return primary.with_fallbacks(fallbacks) if fallbacks else primary

    @staticmethod
    def _bind(model: _Model, tools: list[dict]) -> Runnable:
        if tools and model.supports_tools:
            return model.chat.bind_tools(tools)
        return model.chat

    def _to_response(self, message: AIMessage) -> LLMResponse:
        model_name = message.response_metadata.get('model_name', '')
        return LLMResponse(
            content=message.text,
            provider=self.PROVIDER_NAME,
            model=model_name,
            tool_call=self._first_tool_call(message),
        )

    @staticmethod
    def _first_tool_call(message: AIMessage) -> dict | None:
        if not message.tool_calls:
            return None
        call = message.tool_calls[0]
        return {'name': call['name'], 'arguments': json.dumps(call['args'])}
