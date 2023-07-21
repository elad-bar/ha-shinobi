from __future__ import annotations

from asyncio import sleep
from datetime import datetime, timedelta
import json
import logging
import sys
from typing import Any

from aiohttp import ClientResponseError, ClientSession

from homeassistant.const import ATTR_DATE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send

from ..common.connectivity_status import ConnectivityStatus
from ..common.consts import (
    API_DATA_API_KEY,
    API_DATA_DAYS,
    API_DATA_GROUP_ID,
    API_DATA_SOCKET_IO_VERSION,
    API_DATA_USER_ID,
    ATTR_MONITOR_DETAILS,
    ATTR_MONITOR_DETAILS_DETECTOR,
    ATTR_MONITOR_DETAILS_DETECTOR_AUDIO,
    ATTR_MONITOR_GROUP_ID,
    ATTR_MONITOR_ID,
    LOGIN_PASSWORD,
    LOGIN_USERNAME,
    MONITOR_SIGNALS,
    SIGNAL_API_STATUS,
    SIGNAL_SERVER_DISCOVERED,
    URL_API_KEYS,
    URL_LOGIN,
    URL_MONITORS,
    URL_PARAMETER_API_KEY,
    URL_PARAMETER_BASE_URL,
    URL_PARAMETER_GROUP_ID,
    URL_PARAMETER_MONITOR_ID,
    URL_SOCKET_IO_V4,
    URL_UPDATE_MODE,
    URL_UPDATE_MONITOR,
    URL_VIDEO_WALL,
    URL_VIDEO_WALL_MONITOR,
    URL_VIDEOS,
    VIDEO_DETAILS_EXTENSION,
    VIDEO_DETAILS_TIME,
)
from ..common.exceptions import APIValidationException
from ..common.monitor_data import MonitorData
from .config_manager import ConfigManager

_LOGGER = logging.getLogger(__name__)


class RestAPI:
    data: dict

    _hass: HomeAssistant | None
    _base_url: str | None
    _status: ConnectivityStatus | None
    _session: ClientSession | None
    _config_manager: ConfigManager

    _dispatched_devices: list

    def __init__(
        self,
        hass: HomeAssistant | None,
        config_manager: ConfigManager,
    ):
        try:
            self._hass = hass

            self._support_video_browser_api = False

            self.data = {}

            self._config_manager = config_manager

            self._local_async_dispatcher_send = None

            self._status = None

            self._session = None
            self._dispatched_devices = []

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to load MyDolphin Plus API, error: {ex}, line: {line_number}"
            )

    @property
    def is_connected(self):
        result = self._session is not None

        return result

    @property
    def status(self) -> str | None:
        status = self._status

        return status

    @property
    def _is_home_assistant(self):
        return self._hass is not None

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
    def recorded_days(self):
        return self.data.get(API_DATA_DAYS, 10)

    @property
    def support_video_browser_api(self):
        return self._support_video_browser_api

    async def _do_nothing(self, _status: ConnectivityStatus):
        pass

    async def initialize(self):
        _LOGGER.info("Initializing Shinobi Server API")

        self._set_status(ConnectivityStatus.Connecting)

        await self._initialize_session()

        await self.login()

    async def validate(self):
        await self.initialize()

        await self.login()

    def build_url(self, endpoint, monitor_id: str = None):
        if endpoint.startswith("/"):
            endpoint = endpoint[1:]

        data = {
            URL_PARAMETER_BASE_URL: self._config_manager.api_url,
            URL_PARAMETER_GROUP_ID: self.group_id,
            URL_PARAMETER_API_KEY: self.api_key,
            URL_PARAMETER_MONITOR_ID: monitor_id,
        }

        url = endpoint.format(**data)

        return url

    def _validate_request(self, endpoint):
        if endpoint == URL_LOGIN:
            is_allowed = self.status not in [
                ConnectivityStatus.NotConnected,
                ConnectivityStatus.Disconnected,
            ]

        elif endpoint in [URL_VIDEO_WALL]:
            is_allowed = self.status in [
                ConnectivityStatus.TemporaryConnected,
                ConnectivityStatus.Connected,
            ]

        elif endpoint in [URL_API_KEYS, URL_SOCKET_IO_V4]:
            is_allowed = self.status == ConnectivityStatus.TemporaryConnected

        else:
            is_allowed = self.status == ConnectivityStatus.Connected

        if not is_allowed:
            raise APIValidationException(endpoint, self._status)

    async def _async_post(
        self,
        endpoint,
        request_data: dict,
        monitor_id: str | None = None,
        is_url_encoded: bool = False,
    ):
        result = None

        try:
            self._validate_request(endpoint)

            url = self.build_url(endpoint, monitor_id)

            _LOGGER.debug(f"POST {url}, Url Encoded: {is_url_encoded}")

            data = None if is_url_encoded else request_data
            json_data = request_data if is_url_encoded else None

            async with self._session.post(
                url, data=data, json=json_data, ssl=False
            ) as response:
                _LOGGER.debug(f"Status of {url}: {response.status}")

                response.raise_for_status()

                result = await response.json()

        except ClientResponseError as crex:
            _LOGGER.error(
                f"Failed to post JSON to {endpoint}, HTTP Status: {crex.message} ({crex.status})"
            )

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to post JSON to {endpoint}, Error: {ex}, Line: {line_number}"
            )

        await sleep(0.001)

        return result

    async def get_snapshot(self, url) -> bytes:
        async with self._session.get(url, ssl=False) as response:
            result = await response.read()

            return result

    async def _async_get(
        self, endpoint, monitor_id: str = None, resource_available_check: bool = False
    ):
        result = None

        try:
            self._validate_request(endpoint)

            url = self.build_url(endpoint, monitor_id)

            _LOGGER.debug(f"GET {url}")

            async with self._session.get(url, ssl=False) as response:
                _LOGGER.debug(f"Status of {url}: {response.status}")

                if resource_available_check:
                    result = response.ok

                else:
                    response.raise_for_status()

                    result = await response.json()

        except ClientResponseError as crex:
            _LOGGER.error(
                f"Failed to get data from {endpoint}, HTTP Status: {crex.message} ({crex.status})"
            )

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to get data from {endpoint}, Error: {ex}, Line: {line_number}"
            )

        await sleep(0.001)

        return result

    async def update(self):
        _LOGGER.debug(
            f"Updating data from Shinobi Video Server ({self._config_manager.host})"
        )

        if self.status == ConnectivityStatus.Failed:
            await self.initialize()

        if self.status == ConnectivityStatus.Connected:
            self._async_dispatcher_send(self._hass, SIGNAL_SERVER_DISCOVERED)

            await self._load_monitors()

    async def login(self):
        try:
            self._support_video_browser_api = False
            self.data[API_DATA_API_KEY] = None

            data = {
                LOGIN_USERNAME: self._config_manager.username,
                LOGIN_PASSWORD: self._config_manager.password,
            }

            login_data = await self._async_post(URL_LOGIN, data)

            if login_data is None:
                _LOGGER.warning("Failed to login, Response is empty")

                self._set_status(ConnectivityStatus.Failed)

            else:
                user_data = login_data.get("$user", {})

                if user_data.get("ok", False):
                    self.data[API_DATA_GROUP_ID] = user_data.get(ATTR_MONITOR_GROUP_ID)

                    temp_api_key = user_data.get("auth_token")
                    uid = user_data.get("uid")
                    user_details = user_data.get("details")

                    self.data[API_DATA_USER_ID] = uid

                    self.data[API_DATA_API_KEY] = temp_api_key

                    self._set_status(ConnectivityStatus.TemporaryConnected)

                    api_keys_data: dict = await self._async_get(URL_API_KEYS)

                    self.data[API_DATA_API_KEY] = None

                    if api_keys_data is not None:
                        if api_keys_data.get("ok", False):
                            keys = api_keys_data.get("keys", [])

                            for key in keys:
                                key_uid = key.get("uid", None)

                                if key_uid is not None and key_uid == uid:
                                    self.data[API_DATA_API_KEY] = key.get("code")

                                    days = user_details.get(API_DATA_DAYS)

                                    self.data[API_DATA_DAYS] = (
                                        10
                                        if days is None or days == ""
                                        else int(float(days))
                                    )

                                    await self._set_socket_io_version()

                                    await self._set_support_video_browser_api()

                                    break

                            if self.api_key is None:
                                _LOGGER.warning(
                                    f"No API key associated with user, Payload: {api_keys_data}"
                                )

                            else:
                                self._set_status(ConnectivityStatus.Connected)

                        else:
                            _LOGGER.warning(
                                f"Invalid response while trying to get API keys, Payload: {api_keys_data}"
                            )

                    else:
                        _LOGGER.warning(
                            "Invalid response while trying to get API keys, Payload is empty"
                        )

                    if self.status != ConnectivityStatus.Disconnected:
                        if self.status != ConnectivityStatus.Connected:
                            self._set_status(ConnectivityStatus.MissingAPIKey)

                else:
                    self._set_status(ConnectivityStatus.InvalidCredentials)

        except Exception as ex:
            self.data[API_DATA_API_KEY] = None

            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            if self.status != ConnectivityStatus.Disconnected:
                self._set_status(ConnectivityStatus.Failed)

                _LOGGER.error(f"Login attempt failed, Error: {ex}, Line: {line_number}")

    async def _set_socket_io_version(self):
        _LOGGER.debug("Set SocketIO version")
        version = 3

        response: bool = await self._async_get(
            URL_SOCKET_IO_V4, resource_available_check=True
        )

        if response:
            version = 4

        self.data[API_DATA_SOCKET_IO_VERSION] = version

    async def _set_support_video_browser_api(self):
        _LOGGER.debug("Set support flag for video browser API")

        support_video_browser_api: bool = await self._async_get(
            URL_VIDEO_WALL, resource_available_check=True
        )

        self._support_video_browser_api = support_video_browser_api

        _LOGGER.debug("Video browser API, supported: {support_video_browser_api}")

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
                        _LOGGER.warning("Invalid monitor details found")

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

    async def _initialize_session(self):
        try:
            if self._is_home_assistant:
                self._session = async_create_clientsession(hass=self._hass)

            else:
                self._session = ClientSession()

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.warning(
                f"Failed to initialize session, Error: {str(ex)}, Line: {line_number}"
            )

            self._set_status(ConnectivityStatus.Failed)

    def _set_monitor_data(self, monitor: MonitorData):
        new_device = monitor.id not in self._dispatched_devices
        monitor_signal = MONITOR_SIGNALS.get(new_device)

        if new_device:
            self._dispatched_devices.append(monitor.id)

        self._async_dispatcher_send(
            self._hass,
            monitor_signal,
            monitor,
        )

    async def get_video_wall(self) -> list[dict] | None:
        result = None

        if self._support_video_browser_api:
            response: dict | None = await self._async_get(URL_VIDEO_WALL)

            if response is not None:
                result = response.get("data", [])

        return result

    async def get_video_wall_monitor(self, monitor_id: str) -> list[dict] | None:
        result = []

        if self._support_video_browser_api:
            response: dict | None = await self._async_get(
                URL_VIDEO_WALL_MONITOR, monitor_id
            )

            if response is not None:
                result = response.get("data", [])

        else:
            today = datetime.today()

            for day_offset in range(0, self.recorded_days):
                lookup_date = today - timedelta(days=day_offset)

                video_date_time_iso = lookup_date.isoformat()
                video_date_time_iso_parts = video_date_time_iso.split("T")
                video_date_iso = video_date_time_iso_parts[0]

                monitor_data = {
                    ATTR_MONITOR_ID: monitor_id,
                    ATTR_MONITOR_GROUP_ID: self.group_id,
                    ATTR_DATE: video_date_iso,
                }

                result.append(monitor_data)

        return result

    async def get_video_wall_monitor_date(
        self, monitor_id: str, date: str
    ) -> list[dict] | None:
        result = []

        if self._support_video_browser_api:
            url = self.build_url(URL_VIDEO_WALL_MONITOR, monitor_id)
            endpoint = f"{url}/{date}"

            response: dict | None = await self._async_get(endpoint)

            if response is not None:
                result = response.get("data", [])

        else:
            url = self.build_url(URL_VIDEOS, monitor_id)
            endpoint = f"{url}?start={date}T00:00:00&end={date}T23:59:59&noLimit=1"
            response: dict | None = await self._async_get(endpoint)

            if response is not None:
                videos = response.get("data", [])

                for video_data in videos:
                    monitor_data = {
                        ATTR_MONITOR_ID: monitor_id,
                        ATTR_MONITOR_GROUP_ID: self.group_id,
                        VIDEO_DETAILS_TIME: video_data.get(VIDEO_DETAILS_TIME),
                        VIDEO_DETAILS_EXTENSION: video_data.get(
                            VIDEO_DETAILS_EXTENSION
                        ),
                    }

                    result.append(monitor_data)

        return result

    async def set_monitor_mode(self, monitor_id: str, mode: str):
        _LOGGER.info(f"Updating monitor {monitor_id} mode to {mode}")

        endpoint = f"{URL_UPDATE_MODE}/{mode}"

        response = await self._async_get(endpoint, monitor_id)

        response_message = {} if response is None else response.get("msg")

        result = response.get("ok", False)

        if result:
            _LOGGER.info(f"{response_message} for {monitor_id}")
        else:
            _LOGGER.warning(f"{response_message} for {monitor_id}")

        return result

    async def set_motion_detection(self, monitor_id: str, enabled: bool):
        await self._async_set_detection_mode(
            monitor_id, ATTR_MONITOR_DETAILS_DETECTOR, enabled
        )

    async def set_sound_detection(self, monitor_id: str, enabled: bool):
        await self._async_set_detection_mode(
            monitor_id, ATTR_MONITOR_DETAILS_DETECTOR_AUDIO, enabled
        )

    async def _async_set_detection_mode(
        self, monitor_id: str, detector: str, enabled: bool
    ):
        _LOGGER.info(f"Updating monitor {monitor_id} {detector} to {enabled}")

        url = f"{URL_MONITORS}/{monitor_id}"

        response: dict = await self._async_get(url)
        monitor_data = response[0]
        monitor_details_str = monitor_data.get(ATTR_MONITOR_DETAILS)
        details = json.loads(monitor_details_str)

        details[detector] = str(1 if enabled else 0)

        monitor_data[ATTR_MONITOR_DETAILS] = details

        data = {"data": monitor_data}

        response = await self._async_post(URL_UPDATE_MONITOR, data, monitor_id, True)

        response_message = response.get("msg")

        result = response.get("ok", False)

        if result:
            _LOGGER.info(f"{response_message} for {monitor_id}")
        else:
            _LOGGER.warning(f"{response_message} for {monitor_id}")

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

    def _set_status(self, status: ConnectivityStatus):
        if status != self._status:
            log_level = ConnectivityStatus.get_log_level(status)

            _LOGGER.log(
                log_level,
                f"Status changed from '{self._status}' to '{status}'",
            )

            self._status = status

            self._async_dispatcher_send(self._hass, SIGNAL_API_STATUS, status)

    def set_local_async_dispatcher_send(self, callback):
        self._local_async_dispatcher_send = callback

    def _async_dispatcher_send(
        self, hass: HomeAssistant, signal: str, *args: Any
    ) -> None:
        if hass is None:
            self._local_async_dispatcher_send(
                signal, self._config_manager.entry_id, *args
            )

        else:
            async_dispatcher_send(hass, signal, self._config_manager.entry_id, *args)
