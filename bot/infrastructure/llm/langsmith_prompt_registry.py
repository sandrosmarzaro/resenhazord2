from typing import ClassVar

import structlog
from langsmith import Client
from langsmith.utils import LangSmithError

logger = structlog.get_logger()


class PromptRegistryError(Exception):
    pass


class LangSmithPromptRegistry:
    # Registry-only use of LangSmith: pull the versioned system prompt at runtime,
    # no tracing. The SDK caches pulls stale-while-revalidate (TTL 300s, refresh
    # 60s), so a hub edit propagates within minutes without a re-deploy. A pull
    # failure is a boundary error; the agent degrades to "IA indisponível" rather
    # than shipping a stale vendored copy.
    _instance: ClassVar['LangSmithPromptRegistry | None'] = None

    def __init__(self, client: Client, prompt_identifier: str) -> None:
        self._client = client
        self._prompt_identifier = prompt_identifier

    @classmethod
    def from_credentials(cls, api_key: str, name: str, tag: str) -> 'LangSmithPromptRegistry':
        return cls(Client(api_key=api_key), f'{name}:{tag}')

    @classmethod
    def configure(cls, api_key: str, name: str, tag: str) -> 'LangSmithPromptRegistry':
        cls._instance = cls.from_credentials(api_key, name, tag)
        return cls._instance

    @classmethod
    def configured(cls) -> 'LangSmithPromptRegistry | None':
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    def system_prompt_template(self) -> str:
        try:
            pulled = self._client.pull_prompt(self._prompt_identifier)
        except LangSmithError as error:
            raise PromptRegistryError(str(error)) from error
        return self._extract_template(pulled)

    _NOT_A_TEMPLATE: ClassVar[str] = 'pulled prompt is not a single f-string PromptTemplate'

    @staticmethod
    def _extract_template(pulled: object) -> str:
        template = getattr(pulled, 'template', None)
        if not isinstance(template, str):
            raise PromptRegistryError(LangSmithPromptRegistry._NOT_A_TEMPLATE)
        return template
