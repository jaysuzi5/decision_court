import json
from collections.abc import AsyncIterator


def format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def to_sse(events: AsyncIterator[dict]) -> AsyncIterator[str]:
    async for ev in events:
        yield format_sse(ev["event"], ev.get("data", {}))
