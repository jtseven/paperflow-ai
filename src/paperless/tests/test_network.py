from unittest import mock

import httpx
import pytest

from paperless.network import PinnedHostHTTPTransport


def test_pinned_host_transport_blocks_internal_rebinding():
    transport = PinnedHostHTTPTransport(allow_internal=False)
    request = httpx.Request("GET", "http://example.com/test")

    with (
        mock.patch(
            "paperless.network.resolve_hostname_ips",
            return_value=["127.0.0.1"],
        ),
        pytest.raises(httpx.ConnectError, match="non-public address"),
    ):
        transport.handle_request(request)


def test_pinned_host_transport_rewrites_to_vetted_ip():
    transport = PinnedHostHTTPTransport(allow_internal=False)
    request = httpx.Request("GET", "https://example.com:8443/test")

    def assert_rewritten_request(
        self,
        rewritten_request,
    ):
        assert str(rewritten_request.url) == "https://93.184.216.34:8443/test"
        assert rewritten_request.headers["Host"] == "example.com:8443"
        assert rewritten_request.extensions["sni_hostname"] == "example.com"
        return httpx.Response(200, request=rewritten_request)

    with (
        mock.patch(
            "paperless.network.resolve_hostname_ips",
            return_value=["93.184.216.34"],
        ),
        mock.patch.object(
            httpx.HTTPTransport,
            "handle_request",
            autospec=True,
            side_effect=assert_rewritten_request,
        ),
    ):
        response = transport.handle_request(request)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_pinned_async_transport_preserves_async_stream():
    """The rewritten request must keep its original (async-capable) stream.

    Re-encoding ``request.stream`` through ``content=`` wraps it in a sync-only
    IteratorByteStream, and ``AsyncHTTPTransport.handle_async_request`` asserts
    the stream is an AsyncByteStream — breaking every async client built on the
    pinned transport (e.g. streamed LLM chat).
    """
    from httpx._types import AsyncByteStream

    from paperless.network import PinnedHostAsyncHTTPTransport

    transport = PinnedHostAsyncHTTPTransport(allow_internal=False)
    request = httpx.AsyncClient().build_request(
        "POST",
        "https://example.com/v1/chat/completions",
        json={"q": "hello"},
    )

    async def assert_rewritten_request(self, rewritten_request):
        assert isinstance(rewritten_request.stream, AsyncByteStream)
        body = b"".join([part async for part in rewritten_request.stream])
        assert body == b'{"q":"hello"}'
        return httpx.Response(200, request=rewritten_request)

    with (
        mock.patch(
            "paperless.network.resolve_hostname_ips",
            return_value=["93.184.216.34"],
        ),
        mock.patch.object(
            httpx.AsyncHTTPTransport,
            "handle_async_request",
            autospec=True,
            side_effect=assert_rewritten_request,
        ),
    ):
        response = await transport.handle_async_request(request)

    assert response.status_code == 200
