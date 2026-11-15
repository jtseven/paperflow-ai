import asyncio
import json
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest
from llama_index.core.llms import ChatMessage

from paperless_ai.client import AIClient

TOOL_CALL = {
    "id": "search-1",
    "type": "function",
    "function": {"name": "search_documents", "arguments": '{"query":"invoice"}'},
}
CONTENT_BLOCKS = [
    {"type": "thinking", "thinking": [{"type": "text", "text": "PRIVATE"}]},
    {"type": "text", "text": "Answer"},
    {"type": "image_url", "image_url": {"url": "https://example.com/image"}},
    {"type": "text", "text": " [1]"},
]


@pytest.fixture
def compatible_llm():
    responses = []

    def respond(request):
        body = json.loads(request.content)
        assert body["model"] == "test-model"
        if body.get("stream"):
            deltas = [
                {
                    "role": "assistant",
                    "content": [CONTENT_BLOCKS[0]],
                    "tool_calls": [{"index": 0, **TOOL_CALL}],
                },
                {"content": CONTENT_BLOCKS},
                {"content": "!"},
                {"content": None},
                {"content": []},
            ]
            chunks = [
                {
                    "id": "chat-1",
                    "object": "chat.completion.chunk",
                    "created": 1,
                    "model": "test-model",
                    "choices": [{"index": 0, "delta": delta}],
                }
                for delta in deltas
            ]
            chunks.append(
                {
                    "id": "chat-1",
                    "object": "chat.completion.chunk",
                    "created": 1,
                    "model": "test-model",
                    "choices": [],
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 5,
                        "total_tokens": 15,
                    },
                },
            )
            content = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks)
            response = httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                content=content + "data: [DONE]\n\n",
            )
        else:
            response = httpx.Response(
                200,
                json={
                    "id": "chat-1",
                    "object": "chat.completion",
                    "created": 1,
                    "model": "test-model",
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": "tool_calls",
                            "message": {
                                "role": "assistant",
                                "content": CONTENT_BLOCKS,
                                "tool_calls": [TOOL_CALL],
                            },
                        },
                    ],
                },
            )
        responses.append(response)
        return response

    config = SimpleNamespace(
        llm_backend="openai-like",
        llm_endpoint="https://provider.example/v1",
        llm_api_key="test-key",
        llm_model="test-model",
        llm_request_timeout=30,
        llm_allow_internal_endpoints=False,
        llm_extra_params={},
    )
    transport = httpx.MockTransport(respond)
    with (
        httpx.Client(transport=transport) as sync_client,
        patch("paperless_ai.client.AIConfig", return_value=config),
        patch(
            "paperless_ai.client.create_pinned_httpx_client",
            return_value=sync_client,
        ),
        patch(
            "paperless_ai.client.create_pinned_async_httpx_client",
            return_value=httpx.AsyncClient(transport=transport),
        ),
    ):
        yield AIClient().llm, responses


@pytest.mark.parametrize("asynchronous", [False, True])
def test_stream_content_blocks_preserves_text_tools_and_usage(
    compatible_llm,
    asynchronous,
):
    llm, responses = compatible_llm
    messages = [ChatMessage(role="user", content="Find an invoice")]

    async def collect():
        stream = await llm.astream_chat(messages)
        return [chunk async for chunk in stream]

    chunks = asyncio.run(collect()) if asynchronous else list(llm.stream_chat(messages))

    assert "".join(chunk.delta or "" for chunk in chunks) == "Answer [1]!"
    assert chunks[-1].message.content == "Answer [1]!"
    assert chunks[-1].additional_kwargs["total_tokens"] == 15
    tools = llm.get_tool_calls_from_response(chunks[-1])
    assert tools[0].tool_id == "search-1"
    assert tools[0].tool_name == "search_documents"
    assert tools[0].tool_kwargs == {"query": "invoice"}
    assert responses[0].is_closed


@pytest.mark.parametrize("asynchronous", [False, True])
def test_chat_content_blocks_excludes_reasoning_and_preserves_tools(
    compatible_llm,
    asynchronous,
):
    llm, responses = compatible_llm
    messages = [ChatMessage(role="user", content="Find an invoice")]
    result = asyncio.run(llm.achat(messages)) if asynchronous else llm.chat(messages)

    assert result.message.content == "Answer [1]"
    assert llm.get_tool_calls_from_response(result)[0].tool_kwargs == {
        "query": "invoice",
    }
    assert responses[0].is_closed
