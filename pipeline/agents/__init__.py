import asyncio
import json
import re

from claude_agent_sdk import query, ClaudeAgentOptions

_RETRY_ATTEMPTS = 3
_RETRY_DELAY = 10  # seconds


async def run_agent_call(system: str, prompt: str, model: str, tools: list[str] | None = None) -> str:
    """Call an agent and return collected text response. Retries on transient errors."""
    options = ClaudeAgentOptions(
        model=model,
        system_prompt=system,
        allowed_tools=tools or [],
    )
    last_exc = None
    for attempt in range(_RETRY_ATTEMPTS):
        if attempt > 0:
            wait = _RETRY_DELAY * attempt
            print(f"  [retry {attempt}/{_RETRY_ATTEMPTS - 1}] Waiting {wait}s before retrying...")
            await asyncio.sleep(wait)
        try:
            collected = []
            async for message in query(prompt=prompt, options=options):
                # Direct text attribute (some SDK versions)
                if hasattr(message, "text") and isinstance(message.text, str):
                    collected.append(message.text)
                # Content blocks (AssistantMessage with list of blocks)
                elif hasattr(message, "content") and isinstance(message.content, list):
                    for block in message.content:
                        if hasattr(block, "text") and isinstance(block.text, str):
                            collected.append(block.text)
            return "".join(collected)
        except Exception as e:
            last_exc = e
            print(f"  [error] Agent call failed: {e}")
    raise last_exc


def _extract_json(text: str) -> dict:
    """Extract JSON from agent response, handling markdown fences."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting between first { and last }
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and last > first:
        try:
            return json.loads(text[first : last + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract JSON from response:\n{text[:500]}")
