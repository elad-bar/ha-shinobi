from __future__ import annotations

from datetime import datetime
import json
import logging
import sys

import aiohttp
from aiohttp import ClientResponseError, ClientSession

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from ...component.helpers.const import *
from ...component.helpers.exceptions import APIValidationException
from ...component.models.monitor_data import MonitorData
from ...component.models.video_data import VideoData
from ...configuration.models.config_data import ConfigData
from ..helpers.enums import ConnectivityStatus

REQUIREMENTS = ["aiohttp"]

_LOGGER = logging.getLogger(__name__)


class ShinobiApi:
    """The Class for handling the data retrieval."""

    group_id: str | None
    user_id: str | None
    api_key: str | None
    session: ClientSession | None
    video_list: list[VideoData]
    hass: HomeAssistant
    config_data: ConfigData
    base_url: str | None
    monitors: dict[str, MonitorData]
    status: ConnectivityStatus

    def __init__(self, hass: HomeAssistant, config_data: ConfigData):
        try:
            self._last_update = datetime.now()
            self.hass = hass
            self.config_data = config_data
            self.session_id = None
            self.group_id = None
            self.user_id = None
            self.api_key = None
            self.session = None
            self.base_url = None
            self.monitors = {}
            self.status = ConnectivityStatus.NotConnected

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to load Shinobi Video API, error: {ex}, line: {line_number}"
            )

    @property
    def api_url(self):
        config_data = self.config_data
        protocol = PROTOCOLS[config_data.ssl]

        path = "/" if config_data.path == "" else config_data.path

        url = (
            f"{protocol}://{config_data.host}:{config_data.port}{path}"
        )

        return url

    async def terminate(self):
        self.status = ConnectivityStatus.Disconnected

    async def initialize(self, config_data: ConfigData | None = None):
        _LOGGER.info("Initializing Shinobi Video")

        try:
            if config_data is not None:
                self.config_data = config_data

            self.base_url = self.api_url
            self.video_list = []

            if self.hass is None:
                if self.session is not None:
                    await self.session.close()

                self.session = aiohttp.client.ClientSession()
            else:
                self.session = async_create_clientsession(hass=self.hass)

            await self._login()

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to initialize Shinobi Video API ({self.base_url}), error: {ex}, line: {line_number}"
            )

    def build_url(self, endpoint, monitor_id: str = None):
        if endpoint.startswith("/"):
            endpoint = endpoint[1:]

        endpoint = self.build_endpoint(endpoint, monitor_id)

        url = f"{self.base_url}{endpoint}"

        return url

    def build_endpoint(self, endpoint, monitor_id: str = None):
        if endpoint.startswith("/"):
            endpoint = endpoint[1:]

        if GROUP_ID in endpoint and self.group_id is not None:
            endpoint = endpoint.replace(GROUP_ID, self.group_id)

        if AUTH_TOKEN in endpoint and self.api_key is not None:
            endpoint = endpoint.replace(AUTH_TOKEN, self.api_key)

        if MONITOR_ID in endpoint and monitor_id is not None:
            endpoint = endpoint.replace(MONITOR_ID, monitor_id)

        return endpoint

    def _validate_request(self, endpoint):
        if not ConnectivityStatus.is_api_request_allowed(endpoint, self.status):
            raise APIValidationException(endpoint, self.status)

    async def async_post(self,
                         endpoint,
                         request_data: dict,
                         monitor_id: str | None = None,
                         is_url_encoded: bool = False):
        result = None

        try:
            self._validate_request(endpoint)

            url = self.build_url(endpoint, monitor_id)

            _LOGGER.debug(f"POST {url}, Url Encoded: {is_url_encoded}")

            data = None if is_url_encoded else request_data
            json_data = request_data if is_url_encoded else None

            async with self.session.post(url, data=data, json=json_data, ssl=False) as response:
                _LOGGER.debug(f"Status of {url}: {response.status}")

                response.raise_for_status()

                result = await response.json()

                self._last_update = datetime.now()

        except ClientResponseError as crex:
            _LOGGER.error(
                f"Failed to post JSON to {endpoint}, HTTP Status: {crex.message} ({crex.status})"
            )

            if crex.status in [404, 405]:
                self.status = ConnectivityStatus.NotFound

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to post JSON to {endpoint}, Error: {ex}, Line: {line_number}"
            )

            self.status = ConnectivityStatus.Failed

        return result

    async def async_get(self, endpoint, resource_available_check: bool = False):
        result = None

        try:
            self._validate_request(endpoint)

            url = self.build_url(endpoint)

            _LOGGER.debug(f"GET {url}")

            async with self.session.get(url, ssl=False) as response:
                _LOGGER.debug(f"Status of {url}: {response.status}")

                if resource_available_check:
                    result = response.ok

                else:
                    response.raise_for_status()

                    result = await response.json()

                self._last_update = datetime.now()

        except ClientResponseError as crex:
            _LOGGER.error(
                f"Failed to get data from {endpoint}, HTTP Status: {crex.message} ({crex.status})"
            )

            if crex.status in [404, 405]:
                self.status = ConnectivityStatus.NotFound

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to get data from {endpoint}, Error: {ex}, Line: {line_number}"
            )

            self.status = ConnectivityStatus.Failed

        return result

    async def async_update(self):
        _LOGGER.info(f"Updating data from Shinobi Video Server ({self.config_data.name})")

        if self.status == ConnectivityStatus.Failed:
            await self.initialize()

        if self.status == ConnectivityStatus.Connected:
            await self.load_monitors()
            await self.load_videos()

    async def _login(self):
        _LOGGER.info("Performing login")
        exception_data = None

        try:
            self.status = ConnectivityStatus.Connecting

            self.api_key = None

            config_data = self.config_data

            data = {
                LOGIN_USERNAME: config_data.username,
                LOGIN_PASSWORD: config_data.password
            }

            login_data = await self.async_post(URL_LOGIN, data)

            if login_data is not None:
                user_data = login_data.get("$user", {})

                if user_data.get("ok", False):
                    self.group_id = user_data.get(ATTR_MONITOR_GROUP_ID)
                    temp_api_key = user_data.get("auth_token")
                    uid = user_data.get("uid")

                    self.user_id = uid

                    self.api_key = temp_api_key
                    self.status = ConnectivityStatus.TemporaryConnected

                    api_keys_data: dict = await self.async_get(URL_API_KEYS)

                    self.api_key = None

                    if api_keys_data is not None and api_keys_data.get("ok", False):
                        keys = api_keys_data.get("keys", [])

                        for key in keys:
                            key_uid = key.get("uid", None)

                            if key_uid is not None and key_uid == uid:
                                self.api_key = key.get("code")
                                self.status = ConnectivityStatus.Connected

                                break

                    if self.api_key is None:
                        self.status = ConnectivityStatus.MissingAPIKey

                else:
                    self.status = ConnectivityStatus.InvalidCredentials

        except Exception as ex:
            self.api_key = None

            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            exception_data = f"Error: {ex}, Line: {line_number}"

            if self.status != ConnectivityStatus.NotFound:
                self.status = ConnectivityStatus.Failed

        log_level = ConnectivityStatus.get_log_level(self.status)

        message = self.status if exception_data is None else f"{self.status}, {exception_data}"

        _LOGGER.log(log_level, message)

    async def get_socket_io_version(self):
        _LOGGER.debug("Get SocketIO version")
        version = 3

        response: bool = await self.async_get(URL_SOCKET_IO_V4, True)

        if response:
            version = 4

        return version

    async def load_monitors(self):
        _LOGGER.debug("Retrieving monitors")

        response: dict = await self.async_get(URL_MONITORS)

        if response is None:
            _LOGGER.warning("No monitors were found")

        else:
            if isinstance(response, list):
                monitors = response

            else:
                monitors: list = [response]

            for monitor in monitors:
                try:
                    if monitor is None:
                        _LOGGER.warning(f"Invalid monitor details found")

                    else:
                        monitor_details_str = monitor.get(ATTR_MONITOR_DETAILS)
                        details = json.loads(monitor_details_str)

                        monitor[ATTR_MONITOR_DETAILS] = details

                        monitor_data = MonitorData(monitor)

                        self.monitors[monitor_data.id] = monitor_data

                except Exception as ex:
                    exc_type, exc_obj, tb = sys.exc_info()
                    line_number = tb.tb_lineno

                    _LOGGER.error(
                        f"Failed to load monitor data: {monitor}, Error: {ex}, Line: {line_number}"
                    )

    async def load_videos(self):
        _LOGGER.debug("Retrieving videos list")
        video_list = []

        response: dict = await self.async_get(URL_VIDEOS)

        if response is None:
            _LOGGER.warning("Invalid video response")

        else:
            video_details = response.get("videos", [])

            if len(video_details) == 0:
                _LOGGER.warning("No videos found")

            else:
                for video in video_details:
                    try:
                        if video is None:
                            _LOGGER.warning(f"Invalid video details found")

                        else:
                            video_data = VideoData(video, self.monitors)

                            if video_data is not None:
                                video_list.append(video_data)

                    except Exception as ex:
                        exc_type, exc_obj, tb = sys.exc_info()
                        line_number = tb.tb_lineno

                        _LOGGER.error(
                            f"Failed to load video data: {video}, Error: {ex}, Line: {line_number}"
                        )

        self.video_list = video_list

    async def async_set_monitor_mode(self, monitor_id: str, mode: str):
        _LOGGER.info(f"Updating monitor {monitor_id} mode to {mode}")

        endpoint = self.build_endpoint(f"{URL_UPDATE_MODE}/{mode}", monitor_id)

        response = await self.async_get(endpoint)

        response_message = response.get("msg")

        result = response.get("ok", False)

        if result:
            _LOGGER.info(f"{response_message} for {monitor_id}")
        else:
            _LOGGER.warning(f"{response_message} for {monitor_id}")

        return result

    async def async_set_motion_detection(self, monitor_id: str, enabled: bool):
        await self._async_set_detection_mode(monitor_id, ATTR_MONITOR_DETAILS_DETECTOR, enabled)

    async def async_set_sound_detection(self, monitor_id: str, enabled: bool):
        await self._async_set_detection_mode(monitor_id, ATTR_MONITOR_DETAILS_DETECTOR_AUDIO, enabled)

    async def _async_set_detection_mode(self, monitor_id: str, detector: str, enabled: bool):
        _LOGGER.info(f"Updating monitor {monitor_id} {detector} to {enabled}")

        url = f"{URL_MONITORS}/{monitor_id}"

        response: dict = await self.async_get(url)
        monitor_data = response[0]
        monitor_details_str = monitor_data.get(ATTR_MONITOR_DETAILS)
        details = json.loads(monitor_details_str)

        details[detector] = str(1 if enabled else 0)

        monitor_data[ATTR_MONITOR_DETAILS] = details

        data = {
            "data": monitor_data
        }

        response = await self.async_post(URL_UPDATE_MONITOR, data, monitor_id, True)

        response_message = response.get("msg")

        result = response.get("ok", False)

        if result:
            _LOGGER.info(f"{response_message} for {monitor_id}")
        else:
            _LOGGER.warning(f"{response_message} for {monitor_id}")
