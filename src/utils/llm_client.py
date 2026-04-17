"""
Async LLM Client Module

Supports OpenAI and Anthropic APIs with configurable models,
retry logic with exponential backoff, and JSON response format.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union

import aiohttp

logger = logging.getLogger(__name__)


class LLMClientError(Exception):
    """Base exception for LLM client errors."""
    pass


class RateLimitError(LLMClientError):
    """Raised when rate limit is exceeded."""
    pass


class AuthenticationError(LLMClientError):
    """Raised when authentication fails."""
    pass


class APIError(LLMClientError):
    """Raised when API returns an error."""
    pass


class RetryExhaustedError(LLMClientError):
    """Raised when all retry attempts are exhausted."""
    pass


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    def __init__(
        self,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 120,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
        retry_max_delay: float = 60.0,
    ):
        """
        Initialize the base LLM client.

        Args:
            model: Model identifier (e.g., "gpt-4", "claude-3-opus-20240229")
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_base_delay: Base delay for exponential backoff (seconds)
            retry_max_delay: Maximum delay between retries (seconds)
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self.retry_max_delay = retry_max_delay

    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: str = "text",
    ) -> Union[str, dict]:
        """
        Generate a completion from the LLM.

        Args:
            system_prompt: System prompt to guide the model
            user_prompt: User prompt/query
            response_format: "text" for plain text or "json" for JSON response

        Returns:
            String response or dict if response_format is "json"

        Raises:
            LLMClientError: On errors during completion
        """
        pass

    async def _retry_with_backoff(
        self,
        coro,
        *args,
        **kwargs,
    ) -> Any:
        """
        Execute a coroutine with exponential backoff retry logic.

        Args:
            coro: Coroutine to execute
            *args: Positional arguments for coro
            **kwargs: Keyword arguments for coro

        Returns:
            Result from the coroutine

        Raises:
            RetryExhaustedError: When all retries are exhausted
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return await coro(*args, **kwargs)
            except RateLimitError as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = min(
                        self.retry_base_delay * (2 ** attempt),
                        self.retry_max_delay,
                    )
                    logger.warning(
                        f"Rate limit hit, retrying in {delay:.1f}s "
                        f"(attempt {attempt + 1}/{self.max_retries + 1})"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("Rate limit retry exhausted")
                    raise RetryExhaustedError(
                        f"Rate limit retry exhausted after {self.max_retries + 1} attempts"
                    ) from e
            except (AuthenticationError, APIError) as e:
                last_exception = e
                logger.error(f"API error (non-retryable): {e}")
                raise
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = min(
                        self.retry_base_delay * (2 ** attempt),
                        self.retry_max_delay,
                    )
                    logger.warning(
                        f"Request failed, retrying in {delay:.1f}s "
                        f"(attempt {attempt + 1}/{self.max_retries + 1}): {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Request retry exhausted: {e}")
                    raise RetryExhaustedError(
                        f"Request retry exhausted after {self.max_retries + 1} attempts"
                    ) from e

        raise RetryExhaustedError(
            f"All retries exhausted"
        ) from last_exception


class OpenAIClient(BaseLLMClient):
    """OpenAI API client implementation."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 120,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
        retry_max_delay: float = 60.0,
        base_url: str = "https://api.openai.com/v1",
    ):
        """
        Initialize the OpenAI client.

        Args:
            api_key: OpenAI API key
            model: Model identifier (e.g., "gpt-4", "gpt-3.5-turbo")
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_base_delay: Base delay for exponential backoff (seconds)
            retry_max_delay: Maximum delay between retries (seconds)
            base_url: API base URL
        """
        super().__init__(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
            retry_base_delay=retry_base_delay,
            retry_max_delay=retry_max_delay,
        )
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: str = "text",
    ) -> Union[str, dict]:
        """
        Generate a completion using OpenAI API.

        Args:
            system_prompt: System prompt to guide the model
            user_prompt: User prompt/query
            response_format: "text" for plain text or "json" for JSON response

        Returns:
            String response or dict if response_format is "json"
        """
        return await self._retry_with_backoff(
            self._make_request,
            system_prompt,
            user_prompt,
            response_format,
        )

    async def _make_request(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: str,
    ) -> Union[str, dict]:
        """Make the actual API request to OpenAI."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        request_body: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        if response_format == "json":
            request_body["response_format"] = {"type": "json_object"}

        url = f"{self.base_url}/chat/completions"

        timeout = aiohttp.ClientTimeout(total=self.timeout)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=request_body) as response:
                await self._handle_response_status(response)

                data = await response.json()

                content = data["choices"][0]["message"]["content"]

                if response_format == "json":
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON response: {e}")
                        raise APIError(f"Invalid JSON response from OpenAI: {e}") from e

                return content

    async def _handle_response_status(self, response: aiohttp.ClientResponse) -> None:
        """Handle HTTP response status and raise appropriate exceptions."""
        if response.status == 200:
            return
        elif response.status == 401:
            raise AuthenticationError("Invalid OpenAI API key")
        elif response.status == 429:
            raise RateLimitError("OpenAI rate limit exceeded")
        elif response.status == 500:
            raise APIError("OpenAI server error")
        else:
            text = await response.text()
            raise APIError(f"OpenAI API error (status {response.status}): {text}")


class AnthropicClient(BaseLLMClient):
    """Anthropic API client implementation."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-opus-20240229",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 120,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
        retry_max_delay: float = 60.0,
        base_url: str = "https://api.anthropic.com/v1",
    ):
        """
        Initialize the Anthropic client.

        Args:
            api_key: Anthropic API key
            model: Model identifier (e.g., "claude-3-opus-20240229")
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_base_delay: Base delay for exponential backoff (seconds)
            retry_max_delay: Maximum delay between retries (seconds)
            base_url: API base URL
        """
        super().__init__(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
            retry_base_delay=retry_base_delay,
            retry_max_delay=retry_max_delay,
        )
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: str = "text",
    ) -> Union[str, dict]:
        """
        Generate a completion using Anthropic API.

        Args:
            system_prompt: System prompt to guide the model
            user_prompt: User prompt/query
            response_format: "text" for plain text or "json" for JSON response

        Returns:
            String response or dict if response_format is "json"
        """
        return await self._retry_with_backoff(
            self._make_request,
            system_prompt,
            user_prompt,
            response_format,
        )

    async def _make_request(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: str,
    ) -> Union[str, dict]:
        """Make the actual API request to Anthropic."""
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        messages = [
            {"role": "user", "content": user_prompt},
        ]

        request_body: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        if system_prompt:
            request_body["system"] = system_prompt

        if response_format == "json":
            request_body["response_format"] = {"type": "json_object"}

        url = f"{self.base_url}/messages"

        timeout = aiohttp.ClientTimeout(total=self.timeout)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=request_body) as response:
                await self._handle_response_status(response)

                data = await response.json()

                content = data["content"][0]["text"]

                if response_format == "json":
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON response: {e}")
                        raise APIError(f"Invalid JSON response from Anthropic: {e}") from e

                return content

    async def _handle_response_status(self, response: aiohttp.ClientResponse) -> None:
        """Handle HTTP response status and raise appropriate exceptions."""
        if response.status == 200:
            return
        elif response.status == 401:
            raise AuthenticationError("Invalid Anthropic API key")
        elif response.status == 429:
            raise RateLimitError("Anthropic rate limit exceeded")
        elif response.status == 500:
            raise APIError("Anthropic server error")
        else:
            text = await response.text()
            raise APIError(f"Anthropic API error (status {response.status}): {text}")


def create_llm_client(config: Dict[str, Any]) -> BaseLLMClient:
    """
    Factory function to create an LLM client from configuration.

    Args:
        config: Configuration dictionary with keys:
            - provider: "openai" or "anthropic"
            - api_key: API key for the provider
            - model: Model identifier (optional, has defaults)
            - temperature: Sampling temperature (optional, default 0.7)
            - max_tokens: Maximum tokens (optional, default 4096)
            - timeout: Request timeout in seconds (optional, default 120)
            - max_retries: Maximum retry attempts (optional, default 3)
            - retry_base_delay: Base delay for backoff (optional, default 1.0)
            - retry_max_delay: Max delay for backoff (optional, default 60.0)
            - base_url: API base URL (optional)

    Returns:
        Configured LLM client instance

    Raises:
        ValueError: If provider is not supported or config is invalid
    """
    provider = config.get("provider", "").lower()
    api_key = config.get("api_key")

    if not api_key:
        raise ValueError("api_key is required in config")

    if not provider:
        raise ValueError("provider is required in config")

    common_kwargs = {
        "model": config.get("model"),
        "temperature": config.get("temperature", 0.7),
        "max_tokens": config.get("max_tokens", 4096),
        "timeout": config.get("timeout", 120),
        "max_retries": config.get("max_retries", 3),
        "retry_base_delay": config.get("retry_base_delay", 1.0),
        "retry_max_delay": config.get("retry_max_delay", 60.0),
    }

    # Remove None values to use defaults
    common_kwargs = {k: v for k, v in common_kwargs.items() if v is not None}

    if provider == "openai":
        return OpenAIClient(
            api_key=api_key,
            base_url=config.get("base_url", "https://api.openai.com/v1"),
            **common_kwargs,
        )
    elif provider == "anthropic":
        return AnthropicClient(
            api_key=api_key,
            base_url=config.get("base_url", "https://api.anthropic.com/v1"),
            **common_kwargs,
        )
    else:
        raise ValueError(
            f"Unsupported provider: {provider}. "
            f"Supported providers: openai, anthropic"
        )


__all__ = [
    "BaseLLMClient",
    "OpenAIClient",
    "AnthropicClient",
    "create_llm_client",
    "LLMClientError",
    "RateLimitError",
    "AuthenticationError",
    "APIError",
    "RetryExhaustedError",
]