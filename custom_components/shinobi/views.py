from collections.abc import Mapping
from http import HTTPStatus
from ipaddress import ip_address
import logging
from typing import Any

import aiohttp
from aiohttp import hdrs, web
from aiohttp.web_exceptions import HTTPBadGateway
from multidict import CIMultiDict
from yarl import URL

from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .common.consts import DOMAIN, PROXY_PREFIX
from .managers.coordinator import Coordinator

_LOGGER = logging.getLogger(__name__)


def async_setup(hass: HomeAssistant, coordinator: Coordinator) -> None:
    """Set up the views."""
    session = async_get_clientsession(hass)

    hass.http.register_view(ThumbnailsProxyView(coordinator, session))
    hass.http.register_view(TimelapseThumbnailsProxyView(coordinator, session))
    hass.http.register_view(RecordingProxyView(coordinator, session))


class ProxyView(HomeAssistantView):  # type: ignore[misc]
    """HomeAssistant view."""

    _coordinator: Coordinator
    requires_auth = True

    def __init__(self, coordinator: Coordinator, session: aiohttp.ClientSession):
        """Initialize the frigate clips proxy view."""
        self._session = session
        self._coordinator = coordinator

    def _create_path(self, **kwargs: Any) -> str | None:
        """Create path."""
        raise NotImplementedError  # pragma: no cover

    def _permit_request(
        self, _request: web.Request, _config_entry: ConfigEntry, **_kwargs: Any
    ) -> bool:
        """Determine whether to permit a request."""
        return True

    async def get(
        self,
        request: web.Request,
        **kwargs: Any,
    ) -> web.Response | web.StreamResponse | web.WebSocketResponse:
        """Route data to service."""
        try:
            return await self._handle_request(request, **kwargs)

        except aiohttp.ClientError as err:
            _LOGGER.debug("Reverse proxy error for %s: %s", request.rel_url, err)

        raise HTTPBadGateway() from None

    @staticmethod
    def _get_query_params(request: web.Request) -> Mapping[str, str]:
        """Get the query params to send upstream."""
        return {k: v for k, v in request.query.items() if k != "authSig"}

    @staticmethod
    def _init_header(request: web.Request) -> CIMultiDict | dict[str, str]:
        """Create initial header."""
        headers = {}

        # filter flags
        for name, value in request.headers.items():
            if name in (
                hdrs.CONTENT_LENGTH,
                hdrs.CONTENT_ENCODING,
                hdrs.SEC_WEBSOCKET_EXTENSIONS,
                hdrs.SEC_WEBSOCKET_PROTOCOL,
                hdrs.SEC_WEBSOCKET_VERSION,
                hdrs.SEC_WEBSOCKET_KEY,
                hdrs.HOST,
            ):
                continue
            headers[name] = value

        # Set X-Forwarded-For
        forward_for = request.headers.get(hdrs.X_FORWARDED_FOR)
        assert request.transport
        connected_ip = ip_address(request.transport.get_extra_info("peername")[0])
        if forward_for:
            forward_for = f"{forward_for}, {connected_ip!s}"
        else:
            forward_for = f"{connected_ip!s}"
        headers[hdrs.X_FORWARDED_FOR] = forward_for

        # Set X-Forwarded-Host
        forward_host = request.headers.get(hdrs.X_FORWARDED_HOST)
        if not forward_host:
            forward_host = request.host
        headers[hdrs.X_FORWARDED_HOST] = forward_host

        # Set X-Forwarded-Proto
        forward_proto = request.headers.get(hdrs.X_FORWARDED_PROTO)
        if not forward_proto:
            forward_proto = request.url.scheme
        headers[hdrs.X_FORWARDED_PROTO] = forward_proto

        return headers

    @staticmethod
    def _response_header(response: aiohttp.ClientResponse) -> dict[str, str]:
        """Create response header."""
        headers = {}

        for name, value in response.headers.items():
            if name in (
                hdrs.TRANSFER_ENCODING,
                # Removing Content-Length header for streaming responses
                #   prevents seeking from working for mp4 files
                # hdrs.CONTENT_LENGTH,
                hdrs.CONTENT_TYPE,
                hdrs.CONTENT_ENCODING,
                # Strips inbound CORS response headers since the aiohttp_cors
                # library will assert that they are not already present for CORS
                # requests.
                hdrs.ACCESS_CONTROL_ALLOW_ORIGIN,
                hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
            ):
                continue
            headers[name] = value

        return headers

    async def _handle_request(
        self,
        request: web.Request,
        **kwargs: Any,
    ) -> web.Response | web.StreamResponse:
        """Handle route for request."""
        config_manager = self._coordinator.config_manager

        config_entry = config_manager.entry
        if not config_entry:
            _LOGGER.error(f"Invalid request, Data: {request}")

            return web.Response(status=HTTPStatus.BAD_REQUEST)

        if not self._permit_request(request, config_entry, **kwargs):
            _LOGGER.error(f"Request blocked, Data: {request}")

            return web.Response(status=HTTPStatus.FORBIDDEN)

        full_path = self._create_path(**kwargs)
        if not full_path:
            _LOGGER.warning(f"{full_path} not found")

            return web.Response(status=HTTPStatus.NOT_FOUND)

        url = str(URL(config_manager.api_url) / full_path)

        data = await request.read()
        source_header = self._init_header(request)

        async with self._session.request(
            request.method,
            url,
            headers=source_header,
            params=self._get_query_params(request),
            allow_redirects=False,
            data=data,
        ) as result:
            headers = self._response_header(result)

            # Stream response
            response = web.StreamResponse(status=result.status, headers=headers)
            response.content_type = result.content_type

            try:
                await response.prepare(request)
                async for data in result.content.iter_any():
                    await response.write(data)

            except (aiohttp.ClientError, aiohttp.ClientPayloadError) as err:
                _LOGGER.debug("Stream error for %s: %s", request.rel_url, err)
            except ConnectionResetError:
                # Connection is reset/closed by peer.
                pass

            return response


class ThumbnailsProxyView(ProxyView):
    """A proxy for snapshots."""

    url = f"{PROXY_PREFIX}/{{api_key:.+}}/jpeg/{{group_id:.+}}/{{monitor_id:.+}}/s.jpg"

    name = f"api:{DOMAIN}:thumbnails"

    def _create_path(self, **kwargs: Any) -> str | None:
        """Create path."""
        api_key: str = kwargs["api_key"]
        group_id: str = kwargs["group_id"]
        monitor_id: str = kwargs["monitor_id"]

        return f"{api_key}/jpeg/{group_id}/{monitor_id}/s.jpg"


class TimelapseThumbnailsProxyView(ProxyView):
    """A proxy for snapshots."""

    url = f"{PROXY_PREFIX}/{{api_key:.+}}/timelapse/{{group_id:.+}}/{{monitor_id:.+}}/{{date:.+}}/{{file:.*}}"

    name = f"api:{DOMAIN}:timelapse"

    def _create_path(self, **kwargs: Any) -> str | None:
        """Create path."""
        api_key: str = kwargs["api_key"]
        group_id: str = kwargs["group_id"]
        monitor_id: str = kwargs["monitor_id"]
        date: str = kwargs["date"]
        file: str = kwargs["file"]

        return f"{api_key}/timelapse/{group_id}/{monitor_id}/{date}/{file}"


class RecordingProxyView(ProxyView):
    """A proxy for snapshots."""

    url = f"{PROXY_PREFIX}/{{api_key:.+}}/videos/{{group_id:.+}}/{{monitor_id:.+}}/{{file:.*}}"

    name = f"api:{DOMAIN}:videos"

    def _create_path(self, **kwargs: Any) -> str | None:
        """Create path."""
        api_key: str = kwargs["api_key"]
        group_id: str = kwargs["group_id"]
        monitor_id: str = kwargs["monitor_id"]
        file: str = kwargs["file"]

        return f"{api_key}/videos/{group_id}/{monitor_id}/{file}"
