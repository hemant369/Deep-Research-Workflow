import asyncio
import logging
import time
from typing import Any
from urllib.parse import parse_qs, urlparse, urlunparse

import httpx
from langchain_core.callbacks import AsyncCallbackManagerForLLMRun, CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_ollama import ChatOllama

from core.config import settings


logger = logging.getLogger(__name__)

ROLE_MAP = {
    "system": "system",
    "human": "user",
    "ai": "assistant",
    "tool": "tool",
}
RETRY_STATUSES = {429, 500, 502, 503, 504}


class AzureOpenAIChatModel(BaseChatModel):
    """Lightweight LangChain chat wrapper for Azure OpenAI and Azure AI Foundry endpoints."""

    endpoint: str
    api_key: str
    deployment: str = "gpt-4.1-mini"
    api_version: str = "2025-01-01-preview"
    temperature: float = 0.0
    max_tokens: int = 8192
    timeout: float = 120.0
    max_retries: int = 2

    @property
    def _llm_type(self) -> str:
        return "azure-openai"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {"model_name": self.deployment, "deployment": self.deployment}

    def _build_request(self, messages: list[BaseMessage]) -> tuple[str, dict[str, str], dict[str, Any]]:
        formatted = [
            {"role": ROLE_MAP.get(msg.type, "user"), "content": str(msg.content)}
            for msg in messages
        ]

        raw = self.endpoint.strip().rstrip("/")
        parsed = urlparse(raw)
        path = parsed.path.rstrip("/")
        params: dict[str, str] = {}

        # Azure OpenAI /v1 endpoints (including Azure AI Foundry /api/projects/.../openai/v1/*)
        # reject the `api-version` query parameter and take `model` in the JSON body.
        if "/openai/v1" in path:
            clean_url = urlunparse(parsed._replace(path=path, query=""))
            if path.endswith("/responses"):
                return (
                    clean_url,
                    {},
                    {
                        "model": self.deployment,
                        "input": formatted,
                        "temperature": self.temperature,
                        "max_output_tokens": self.max_tokens,
                    },
                )
            url = clean_url if path.endswith("/chat/completions") else f"{clean_url}/chat/completions"
            return (
                url,
                {},
                {
                    "model": self.deployment,
                    "messages": formatted,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                },
            )

        payload: dict[str, Any] = {
            "messages": formatted,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        if "/chat/completions" in path:
            url = raw
            if "api-version" not in parse_qs(parsed.query):
                params["api-version"] = self.api_version
        elif path.endswith("/models"):
            url = f"{raw}/chat/completions"
            payload["model"] = self.deployment
        else:
            url = f"{raw}/openai/deployments/{self.deployment}/chat/completions"
            params["api-version"] = self.api_version

        return url, params, payload

    def _headers(self) -> dict[str, str]:
        return {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }

    def _to_chat_result(self, data: dict[str, Any]) -> ChatResult:
        # Handle Responses API shape (`output` / `output_text`)
        if "output" in data or "output_text" in data:
            content = data.get("output_text") or ""
            if not content:
                parts: list[str] = []
                for item in data.get("output") or []:
                    if item.get("type") != "message":
                        continue
                    for block in item.get("content") or []:
                        if block.get("text"):
                            parts.append(str(block["text"]))
                content = "\n".join(parts)
            usage = data.get("usage") or {}
            usage_metadata = (
                {
                    "input_tokens": int(usage.get("input_tokens", 0)),
                    "output_tokens": int(usage.get("output_tokens", 0)),
                    "total_tokens": int(usage.get("total_tokens", 0)),
                }
                if usage
                else None
            )
            model_name = str(data.get("model") or self.deployment)
            return ChatResult(
                generations=[
                    ChatGeneration(
                        message=AIMessage(
                            content=content,
                            usage_metadata=usage_metadata,
                            response_metadata={"model_name": model_name},
                        )
                    )
                ]
            )

        # Handle Chat Completions shape (`choices`)
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError(f"Azure OpenAI returned no choices: {data}")

        content = choices[0].get("message", {}).get("content") or ""
        usage = data.get("usage") or {}
        usage_metadata = (
            {
                "input_tokens": int(usage.get("prompt_tokens", 0)),
                "output_tokens": int(usage.get("completion_tokens", 0)),
                "total_tokens": int(usage.get("total_tokens", 0)),
            }
            if usage
            else None
        )
        model_name = str(data.get("model") or self.deployment)
        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(
                        content=content,
                        usage_metadata=usage_metadata,
                        response_metadata={"model_name": model_name},
                    )
                )
            ]
        )

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        url, params, payload = self._build_request(messages)
        if stop:
            payload["stop"] = stop

        with httpx.Client(timeout=self.timeout) as client:
            for attempt in range(self.max_retries + 1):
                response = client.post(url, params=params, headers=self._headers(), json=payload)
                if response.status_code not in RETRY_STATUSES or attempt == self.max_retries:
                    if response.is_error:
                        raise RuntimeError(f"Azure OpenAI error {response.status_code}: {response.text[:400]}")
                    return self._to_chat_result(response.json())
                time.sleep(0.5 * (attempt + 1))

        raise RuntimeError("Azure OpenAI request failed after retries.")

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        url, params, payload = self._build_request(messages)
        if stop:
            payload["stop"] = stop

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries + 1):
                response = await client.post(url, params=params, headers=self._headers(), json=payload)
                if response.status_code not in RETRY_STATUSES or attempt == self.max_retries:
                    if response.is_error:
                        raise RuntimeError(f"Azure OpenAI error {response.status_code}: {response.text[:400]}")
                    return self._to_chat_result(response.json())
                await asyncio.sleep(0.5 * (attempt + 1))

        raise RuntimeError("Azure OpenAI request failed after retries.")


def build_llm() -> BaseChatModel:
    has_azure = bool(settings.azure_openai_endpoint and settings.azure_openai_api_key)
    use_azure = settings.llm_provider == "azure" or (settings.llm_provider == "auto" and has_azure)

    if use_azure:
        if not has_azure:
            raise RuntimeError(
                "LLM_PROVIDER=azure requires AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY."
            )
        logger.info("LLM provider: Azure OpenAI (deployment=%s)", settings.azure_openai_deployment)
        return AzureOpenAIChatModel(
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            deployment=settings.azure_openai_deployment,
            api_version=settings.azure_openai_api_version,
            temperature=0.0,
            max_tokens=settings.azure_max_tokens,
            timeout=float(settings.llm_timeout_seconds),
        )

    logger.info("LLM provider: Ollama (model=%s)", settings.ollama_model)
    return ChatOllama(
        model=settings.ollama_model,
        temperature=0,
        num_ctx=settings.ollama_context_size,
        num_predict=settings.ollama_max_tokens,
    )


llm = build_llm()
