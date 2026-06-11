"""Thin async wrapper over the Groq SDK with streaming + token accounting.

We keep prompt/response bodies out of logs (safety §8): only metadata (model, token
counts, retries) may be logged by callers."""

import asyncio
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass

from groq import AsyncGroq
from groq import APIStatusError, RateLimitError

from .config import get_settings

log = logging.getLogger("decision_court.groq")

_client: AsyncGroq | None = None


def client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=get_settings().groq_api_key)
    return _client


@dataclass
class StreamResult:
    in_tokens: int = 0
    out_tokens: int = 0


async def stream_chat(
    *,
    model: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float,
    result: StreamResult,
    max_retries: int = 3,
) -> AsyncIterator[str]:
    """Yield content deltas. Fills `result` with usage when the stream ends.
    Retries 429 / overload with exponential backoff before the first token only."""
    attempt = 0
    while True:
        try:
            stream = await client().chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )
            async for chunk in stream:
                # Groq reports usage on the final streamed chunk under x_groq.
                usage = getattr(chunk, "usage", None) or getattr(
                    getattr(chunk, "x_groq", None), "usage", None
                )
                if usage is not None:
                    result.in_tokens = getattr(usage, "prompt_tokens", 0) or 0
                    result.out_tokens = getattr(usage, "completion_tokens", 0) or 0
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
            return
        except (RateLimitError, APIStatusError) as e:
            status = getattr(e, "status_code", None)
            if status not in (429, 500, 502, 503) or attempt >= max_retries:
                log.warning("groq error model=%s status=%s giving up", model, status)
                raise
            backoff = 2**attempt
            log.info("groq retry model=%s status=%s in %ss", model, status, backoff)
            await asyncio.sleep(backoff)
            attempt += 1
