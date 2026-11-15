"""Normalize provider content blocks before the OpenAI/LlamaIndex parsers.

Mistral's OpenAI-compatible API can return a list of content blocks even in
streaming deltas. LlamaIndex's OpenAI adapter concatenates those deltas as
strings. Keep only answer text, excluding reasoning and other non-text blocks.
"""

from openai import AsyncOpenAI
from openai import OpenAI
from openai.types.chat import ChatCompletion
from openai.types.chat import ChatCompletionChunk


def _normalize_content_blocks(data: dict, *, streaming: bool) -> None:
    for choice in data.get("choices", []):
        message = choice.get("delta" if streaming else "message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, list):
            message["content"] = "".join(
                block["text"]
                for block in content
                if isinstance(block, dict)
                and block.get("type") == "text"
                and isinstance(block.get("text"), str)
            )


class _ContentBlocksMixin:
    def _process_response_data(self, *, data, cast_to, response):
        # Normalize before SDK model validation, for both streaming and regular
        # chat responses. Leave errors and all other API response types intact.
        if isinstance(data, dict) and cast_to in (ChatCompletion, ChatCompletionChunk):
            _normalize_content_blocks(data, streaming=cast_to is ChatCompletionChunk)
        return super()._process_response_data(
            data=data,
            cast_to=cast_to,
            response=response,
        )


class CompatibleOpenAI(_ContentBlocksMixin, OpenAI):
    pass


class CompatibleAsyncOpenAI(_ContentBlocksMixin, AsyncOpenAI):
    pass
