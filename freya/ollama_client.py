"""Client for interacting with the local Ollama HTTP API."""

from __future__ import annotations

import json
from typing import Iterable, Iterator, Optional

import requests
from requests import HTTPError, RequestException, Response, Session

from .config import OllamaConfig
from .logger import get_logger

logger = get_logger("ollama")


class OllamaError(RequestException):
    """Base exception for Ollama client failures."""


class OllamaModelNotFoundError(OllamaError):
    """Raised when the requested Ollama model is not available locally."""

    def __init__(self, model: str, response: Response | None = None) -> None:
        message = (
            f"Ollama model '{model}' is not installed. "
            "Run `ollama pull {model}` to download it."
        )
        super().__init__(message, response=response)
        self.model = model


class OllamaStreamNotSupported(OllamaError):
    """Raised when the Ollama server does not support streamed responses."""


class OllamaClient:
    """Thin wrapper around the Ollama chat API."""

    def __init__(self, config: OllamaConfig, session: Optional[Session] = None) -> None:
        self._config = config
        self._session = session or requests.Session()
        self._base_url = config.host.rstrip("/")

    def _post(self, endpoint: str, payload: dict, *, stream: bool = False) -> Response:
        url = f"{self._base_url}{endpoint}"
        logger.debug("POST %s payload=%s", url, payload)
        response = self._session.post(
            url,
            json=payload,
            timeout=60,
            stream=stream,
        )
        if response.status_code == 404 and self._model_missing(response):
            raise OllamaModelNotFoundError(self._config.model, response=response)
        response.raise_for_status()
        return response

    def _model_missing(self, response: Response) -> bool:
        """Return True when the response indicates a missing model."""
        message = ""
        try:
            data = response.json()
        except ValueError:
            message = response.text or ""
        else:
            if isinstance(data, dict):
                for key in ("error", "message", "detail"):
                    value = data.get(key)
                    if value:
                        message = str(value)
                        break
            elif data:
                message = str(data)

        message = (message or "").lower()
        return "model" in message and "not" in message and "found" in message

    def chat(self, messages: Iterable[dict]) -> str:
        """Send chat messages and return the assistant response."""
        payload = {
            "model": self._config.model,
            "messages": list(messages),
            "stream": False,
        }
        if self._config.options:
            payload["options"] = self._config.options

        chat_endpoints = ["/api/chat", "/chat"]
        response: Optional[Response] = None
        last_exc: Optional[HTTPError] = None
        for endpoint in chat_endpoints:
            try:
                response = self._post(endpoint, payload)
            except OllamaModelNotFoundError:
                raise
            except HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else None
                if status == 404:
                    logger.warning("Ollama %s endpoint unavailable", endpoint)
                    last_exc = exc
                    continue
                raise
            else:
                if endpoint != chat_endpoints[0]:
                    logger.info("Connected to alternate Ollama endpoint %s", endpoint)
                break

        if response is None:
            logger.warning("Falling back to Ollama legacy generate endpoint")
            if last_exc is not None:
                logger.debug("Last Ollama chat error: %s", last_exc)
            return self._chat_via_generate(payload["messages"])

        data = response.json()
        logger.debug("Ollama response payload=%s", data)

        # Ollama may stream responses; when aggregated it exposes `message`.
        if "message" in data and data["message"]:
            return data["message"].get("content", "").strip()

        # Fallback for legacy response format.
        if "response" in data:
            return str(data["response"]).strip()

        raise ValueError("Unexpected response from Ollama API")

    def _chat_via_generate(self, messages: list[dict]) -> str:
        """Fallback for older Ollama builds lacking the chat endpoint."""
        prompt_segments = []
        for message in messages:
            role = str(message.get("role", "")).strip().lower()
            content = str(message.get("content", "")).strip()
            if not content:
                continue
            if role == "system":
                prefix = "System"
            elif role == "assistant":
                prefix = "Freya"
            else:
                prefix = "User"
            prompt_segments.append(f"{prefix}: {content}")

        prompt_segments.append("Freya:")
        prompt = "\n\n".join(prompt_segments)
        payload = {
            "model": self._config.model,
            "prompt": prompt,
            "stream": False,
        }
        if self._config.options:
            payload["options"] = self._config.options

        generate_endpoints = ["/api/generate", "/generate"]
        response: Optional[Response] = None
        last_exc: Optional[HTTPError] = None
        for endpoint in generate_endpoints:
            try:
                response = self._post(endpoint, payload)
            except OllamaModelNotFoundError:
                raise
            except HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else None
                if status == 404:
                    logger.warning("Ollama %s endpoint unavailable", endpoint)
                    last_exc = exc
                    continue
                raise
            else:
                if endpoint != generate_endpoints[0]:
                    logger.info("Connected to alternate Ollama endpoint %s", endpoint)
                break
        else:
            if last_exc is not None:
                raise last_exc
            raise ValueError("Unable to contact Ollama generate endpoint")

        if response is None:
            raise ValueError("Ollama generate endpoint returned no response")

        data = response.json()
        logger.debug("Ollama legacy response payload=%s", data)

        if "response" in data:
            return str(data["response"]).strip()
        if "message" in data and data["message"]:
            return data["message"].get("content", "").strip()

        raise ValueError("Unexpected response from Ollama legacy API")

    def chat_stream(self, messages: Iterable[dict]) -> Iterator[str]:
        """Yield streamed chat chunks from Ollama.

        Raises:
            OllamaStreamNotSupported: When the Ollama server does not expose a
                streaming-compatible endpoint.
        """

        payload = {
            "model": self._config.model,
            "messages": list(messages),
            "stream": True,
        }
        if self._config.options:
            payload["options"] = self._config.options

        chat_endpoints = ["/api/chat", "/chat"]
        for endpoint in chat_endpoints:
            try:
                response = self._post(endpoint, payload, stream=True)
            except OllamaModelNotFoundError:
                raise
            except HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else None
                if status == 404:
                    logger.warning("Ollama %s stream endpoint unavailable", endpoint)
                    continue
                raise
            else:
                try:
                    yield from self._iter_chat_stream(response)
                finally:
                    response.close()
                return

        logger.warning("Falling back to Ollama legacy streaming generate endpoint")
        yield from self._generate_stream(payload["messages"])

    def _iter_chat_stream(self, response: Response) -> Iterator[str]:
        """Parse streamed chat responses."""

        for raw_line in response.iter_lines(decode_unicode=True):
            if not raw_line:
                continue
            try:
                data = json.loads(raw_line)
            except json.JSONDecodeError:
                logger.debug("Skipping non-JSON Ollama stream chunk: %s", raw_line)
                continue

            message = data.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if content:
                    yield str(content)

            if data.get("done"):
                break

    def _generate_stream(self, messages: list[dict]) -> Iterator[str]:
        """Stream results using the legacy generate endpoint."""

        prompt_segments = []
        for message in messages:
            role = str(message.get("role", "")).strip().lower()
            content = str(message.get("content", "")).strip()
            if not content:
                continue
            if role == "system":
                prefix = "System"
            elif role == "assistant":
                prefix = "Freya"
            else:
                prefix = "User"
            prompt_segments.append(f"{prefix}: {content}")

        prompt_segments.append("Freya:")
        prompt = "\n\n".join(prompt_segments)
        payload = {
            "model": self._config.model,
            "prompt": prompt,
            "stream": True,
        }
        if self._config.options:
            payload["options"] = self._config.options

        generate_endpoints = ["/api/generate", "/generate"]
        for endpoint in generate_endpoints:
            try:
                response = self._post(endpoint, payload, stream=True)
            except OllamaModelNotFoundError:
                raise
            except HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else None
                if status == 404:
                    logger.warning("Ollama %s stream endpoint unavailable", endpoint)
                    continue
                raise
            else:
                try:
                    yield from self._iter_generate_stream(response)
                finally:
                    response.close()
                return

        raise OllamaStreamNotSupported("Ollama server does not support streaming responses")

    def _iter_generate_stream(self, response: Response) -> Iterator[str]:
        """Parse legacy streaming responses."""

        buffer = []
        data = None
        for raw_line in response.iter_lines(decode_unicode=True):
            if not raw_line:
                continue
            try:
                data = json.loads(raw_line)
            except json.JSONDecodeError:
                logger.debug("Skipping non-JSON Ollama legacy stream chunk: %s", raw_line)
                continue

            if "response" in data and data["response"]:
                text = str(data["response"])
                buffer.append(text)
                yield text

            if data.get("done"):
                break

        if not buffer:
            message = data.get("message") if data is not None else None
            if isinstance(message, dict):
                content = message.get("content")
                if content:
                    yield str(content)



__all__ = [
    "OllamaClient",
    "OllamaError",
    "OllamaModelNotFoundError",
    "OllamaStreamNotSupported",
]
