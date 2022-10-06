from __future__ import annotations

from asyncio import sleep
from datetime import datetime
import json
import logging
import sys
from typing import Awaitable, Callable

import aiohttp
from aiohttp import ClientResponseError, ClientSession

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from ...configuration.models.config_data import ConfigData
from ...core.api.base_api import BaseAPI
from ...core.helpers.enums import ConnectivityStatus
from ..helpers.const import *
from ..helpers.exceptions import APIValidationException
from ..models.monitor_data import MonitorData
from ..models.video_data import VideoData

REQUIREMENTS = ["aiohttp"]

_LOGGER = logging.getLogger(__name__)


class IntegrationAPI(BaseAPI):
    """The Class for handling the data retrieval."""

    session: ClientSession | None
    hass: HomeAssistant
    config_data: ConfigData | None
    base_url: str | None
    repairing: list[str]

    def __init__(self,
                 hass: HomeAssistant,
                 async_on_data_changed: Callable[[], Awaitable[None]] | None = None,
                 async_on_status_changed: Callable[[ConnectivityStatus], Awaitable[None]] | None = None
                 ):

        super().__init__(hass, async_on_data_changed, async_on_status_changed)

        try:
            self.config_data = None
            self.session = None
            self.base_url = None
            self.repairing = []

            self.data = {
                API_DATA_MONITORS: {},
                API_DATA_VIDEO_LIST: []
            }

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to load Shinobi Video API, error: {ex}, line: {line_number}"
            )

    @property
    def group_id(self):
        return self.data.get(API_DATA_GROUP_ID)

    @property
    def user_id(self):
        return self.data.get(API_DATA_USER_ID)

    @property
    def api_key(self):
        return self.data.get(API_DATA_API_KEY)

    @property
    def monitors(self):
        return self.data.get(API_DATA_MONITORS, {})

    @property
    def video_list(self):
        return self.data.get(API_DATA_VIDEO_LIST, [])

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
        await self.set_status(ConnectivityStatus.Disconnected)

    async def initialize(self, config_data: ConfigData):
        _LOGGER.info("Initializing Shinobi Video")

        try:
            self.config_data = config_data

            self.base_url = self.api_url

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

    async def validate(self, data: dict | None = None):
        config_data = ConfigData.from_dict(data)

        await self.initialize(config_data)

    def build_url(self, endpoint, monitor_id: str = None):
        if endpoint.startswith("/"):
            endpoint = endpoint[1:]

        endpoint = self._build_endpoint(endpoint, monitor_id)

        url = f"{self.base_url}{endpoint}"

        return url

    def _build_endpoint(self, endpoint, monitor_id: str = None):
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
        if endpoint == URL_LOGIN:
            is_allowed = self.status not in [
                ConnectivityStatus.NotConnected,
                ConnectivityStatus.Disconnected
            ]

        elif endpoint in [URL_API_KEYS, URL_SOCKET_IO_V4]:
            is_allowed = self.status == ConnectivityStatus.TemporaryConnected

        else:
            is_allowed = self.status == ConnectivityStatus.Connected

        if not is_allowed:
            raise APIValidationException(endpoint, self.status)

    async def _async_post(self,
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

                self.data[API_DATA_LAST_UPDATE] = datetime.now()

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

    async def _async_get(self, endpoint, resource_available_check: bool = False):
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

                self.data[API_DATA_LAST_UPDATE] = datetime.now()

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
        _LOGGER.debug(f"Updating data from Shinobi Video Server ({self.config_data.host})")

        if self.status == ConnectivityStatus.Failed:
            await self.initialize(self.config_data)

        if self.status == ConnectivityStatus.Connected:
            await self._load_monitors()
            await self._load_videos()

    async def _login(self):
        _LOGGER.info("Performing login")
        exception_data = None

        await self.set_status(ConnectivityStatus.Connecting)

        try:
            self.data[API_DATA_API_KEY] = None

            config_data = self.config_data

            data = {
                LOGIN_USERNAME: config_data.username,
                LOGIN_PASSWORD: config_data.password
            }

            login_data = await self._async_post(URL_LOGIN, data)

            if login_data is not None:
                user_data = login_data.get("$user", {})

                if user_data.get("ok", False):
                    self.data[API_DATA_GROUP_ID] = user_data.get(ATTR_MONITOR_GROUP_ID)
                    temp_api_key = user_data.get("auth_token")
                    uid = user_data.get("uid")

                    self.data[API_DATA_USER_ID] = uid

                    self.data[API_DATA_API_KEY] = temp_api_key

                    await self.set_status(ConnectivityStatus.TemporaryConnected)

                    api_keys_data: dict = await self._async_get(URL_API_KEYS)

                    self.data[API_DATA_API_KEY] = None

                    if api_keys_data is not None and api_keys_data.get("ok", False):
                        keys = api_keys_data.get("keys", [])

                        for key in keys:
                            key_uid = key.get("uid", None)

                            if key_uid is not None and key_uid == uid:
                                self.data[API_DATA_API_KEY] = key.get("code")

                                await self._set_socket_io_version()

                                await self.set_status(ConnectivityStatus.Connected)

                                break

                    if self.api_key is None:
                        await self.set_status(ConnectivityStatus.MissingAPIKey)

                else:
                    await self.set_status(ConnectivityStatus.InvalidCredentials)

        except Exception as ex:
            self.data[API_DATA_API_KEY] = None

            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            exception_data = f"Error: {ex}, Line: {line_number}"

            if self.status != ConnectivityStatus.NotFound:
                await self.set_status(ConnectivityStatus.Failed)

        log_level = ConnectivityStatus.get_log_level(self.status)

        message = self.status if exception_data is None else f"{self.status}, {exception_data}"

        _LOGGER.log(log_level, message)

        await self.fire_data_changed_event()

    async def _set_socket_io_version(self):
        _LOGGER.debug("Set SocketIO version")
        version = 3

        response: bool = await self._async_get(URL_SOCKET_IO_V4, True)

        if response:
            version = 4

        self.data[API_DATA_SOCKET_IO_VERSION] = version

    async def _load_monitors(self):
        _LOGGER.debug("Retrieving monitors")

        response: dict = await self._async_get(URL_MONITORS)

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

                        self._set_monitor_data(monitor_data)

                except Exception as ex:
                    exc_type, exc_obj, tb = sys.exc_info()
                    line_number = tb.tb_lineno

                    _LOGGER.error(
                        f"Failed to load monitor data: {monitor}, Error: {ex}, Line: {line_number}"
                    )

            await self.fire_data_changed_event()

    def _set_monitor_data(self, monitor: MonitorData):
        self.data[API_DATA_MONITORS][monitor.id] = monitor

    def _get_monitor_data(self, monitor_id: str) -> MonitorData:
        monitor = self.data[API_DATA_MONITORS][monitor_id]

        return monitor

    async def _load_videos(self):
        _LOGGER.debug("Retrieving videos list")
        video_list = []

        response: dict = await self._async_get(URL_VIDEOS)

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

                self.data[API_DATA_VIDEO_LIST] = video_list

                await self.fire_data_changed_event()

    async def async_repair_monitors(self):
        monitors = self.data.get("monitors", {})

        for monitor_id in monitors:
            monitor = monitors.get(monitor_id)

            if monitor_id not in self.repairing and monitor.should_repair:
                await self._async_repair_monitor(monitor_id)

    async def _async_repair_monitor(self, monitor_id: str):
        monitor = self._get_monitor_data(monitor_id)

        if monitor_id in self.repairing:
            _LOGGER.warning(f"Monitor {monitor_id} is in progress, cannot start additional repair job")

        elif not monitor.should_repair:
            _LOGGER.warning(f"Monitor {monitor_id} is working properly, no need to repair")

        else:
            try:
                _LOGGER.info(f"Repairing monitor {monitor_id}")

                self.repairing.append(monitor_id)

                await self.async_set_monitor_mode(monitor_id, MONITOR_MODE_STOP)

                await sleep(REPAIR_REPAIR_RECORD_INTERVAL)

                await self.async_set_monitor_mode(monitor_id, MONITOR_MODE_RECORD)

                for index in range(REPAIR_UPDATE_STATUS_ATTEMPTS):
                    await sleep(REPAIR_UPDATE_STATUS_INTERVAL)

                    await self._async_update_monitor_details(monitor_id)

                    monitor = self._get_monitor_data(monitor_id)

                    if self.status != ConnectivityStatus.Connected:
                        status_message = ConnectivityStatus.get_log_level(self.status)
                        _LOGGER.warning(f"Stopped sampling status for {monitor_id}, Reason: {status_message}")
                        break

                    if not monitor.should_repair:
                        _LOGGER.info(f"Monitor {monitor_id} is repaired, Attempt #{index + 1}")
                        break

                if monitor.should_repair and self.status == ConnectivityStatus.Connected:
                    _LOGGER.warning(f"Unable to repair monitor {monitor_id}, Attempts: {REPAIR_UPDATE_STATUS_ATTEMPTS}")

                await self.fire_data_changed_event()

            except Exception as ex:
                exc_type, exc_obj, tb = sys.exc_info()
                line_number = tb.tb_lineno

                _LOGGER.error(
                    f"Failed to repair monitor: {monitor_id}, Error: {ex}, Line: {line_number}"
                )

            finally:
                self.repairing.remove(monitor_id)

    async def async_set_monitor_mode(self, monitor_id: str, mode: str):
        _LOGGER.info(f"Updating monitor {monitor_id} mode to {mode}")

        endpoint = self._build_endpoint(f"{URL_UPDATE_MODE}/{mode}", monitor_id)

        response = await self._async_get(endpoint)

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

        response: dict = await self._async_get(url)
        monitor_data = response[0]
        monitor_details_str = monitor_data.get(ATTR_MONITOR_DETAILS)
        details = json.loads(monitor_details_str)

        details[detector] = str(1 if enabled else 0)

        monitor_data[ATTR_MONITOR_DETAILS] = details

        data = {
            "data": monitor_data
        }

        response = await self._async_post(URL_UPDATE_MONITOR, data, monitor_id, True)

        response_message = response.get("msg")

        result = response.get("ok", False)

        if result:
            _LOGGER.info(f"{response_message} for {monitor_id}")
        else:
            _LOGGER.warning(f"{response_message} for {monitor_id}")

        await self.fire_data_changed_event()

    async def _async_update_monitor_details(self, monitor_id: str):
        _LOGGER.debug(f"Updating monitor details for {monitor_id}")

        if self.status == ConnectivityStatus.Connected:
            url = f"{URL_MONITORS}/{monitor_id}"

            response: dict = await self._async_get(url)
            monitor_data = response[0]

            monitor_details_str = monitor_data.get(ATTR_MONITOR_DETAILS)
            details = json.loads(monitor_details_str)

            monitor_data[ATTR_MONITOR_DETAILS] = details

            monitor_data = MonitorData(monitor_data)

            if monitor_data is not None:
                self._set_monitor_data(monitor_data)

            await self.fire_data_changed_event()
