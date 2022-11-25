from __future__ import annotations

from asyncio import sleep
from collections.abc import Awaitable, Callable
from datetime import datetime
import json
import logging
import sys

from aiohttp import ClientResponseError

from homeassistant.core import HomeAssistant

from ...configuration.models.config_data import ConfigData
from ...core.api.base_api import BaseAPI
from ...core.helpers.enums import ConnectivityStatus
from ..helpers.const import *
from ..helpers.exceptions import APIValidationException
from ..models.monitor_data import MonitorData

REQUIREMENTS = ["aiohttp"]

_LOGGER = logging.getLogger(__name__)


class IntegrationAPI(BaseAPI):
    """The Class for handling the data retrieval."""

    hass: HomeAssistant
    config_data: ConfigData | None
    _repairing: list[str]
    _support_video_browser_api: bool

    def __init__(self,
                 hass: HomeAssistant | None,
                 async_on_data_changed: Callable[[], Awaitable[None]] | None = None,
                 async_on_status_changed: Callable[[ConnectivityStatus], Awaitable[None]] | None = None
                 ):

        super().__init__(hass, async_on_data_changed, async_on_status_changed)

        try:
            self.config_data = None
            self._repairing = []
            self._support_video_browser_api = False

            self.data = {
                API_DATA_MONITORS: {}
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
    def recorded_days(self):
        return self.data.get(API_DATA_DAYS, 10)

    @property
    def api_url(self):
        config_data = self.config_data
        protocol = PROTOCOLS[config_data.ssl]

        path = "/" if config_data.path == "" else config_data.path

        url = (
            f"{protocol}://{config_data.host}:{config_data.port}{path}"
        )

        return url

    async def initialize(self, config_data: ConfigData):
        _LOGGER.info("Initializing Shinobi Video")

        try:
            await self.set_status(ConnectivityStatus.Connecting)

            self.config_data = config_data

            await self.initialize_session()

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to initialize Shinobi Video API ({self.api_url}), error: {ex}, line: {line_number}"
            )

            await self.set_status(ConnectivityStatus.Failed)

    async def validate(self, data: dict | None = None):
        config_data = ConfigData.from_dict(data)

        await self.initialize(config_data)

    def build_url(self, endpoint, monitor_id: str = None):
        if endpoint.startswith("/"):
            endpoint = endpoint[1:]

        data = {
            URL_PARAMETER_BASE_URL: self.api_url,
            URL_PARAMETER_GROUP_ID: self.group_id,
            URL_PARAMETER_API_KEY: self.api_key,
            URL_PARAMETER_MONITOR_ID: monitor_id
        }

        url = endpoint.format(**data)

        return url

    def _validate_request(self, endpoint):
        if endpoint == URL_LOGIN:
            is_allowed = self.status not in [
                ConnectivityStatus.NotConnected,
                ConnectivityStatus.Disconnected
            ]

        elif endpoint in [URL_VIDEO_WALL]:
            is_allowed = self.status in [
                ConnectivityStatus.TemporaryConnected,
                ConnectivityStatus.Connected
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

        return result

    async def _async_get(self, endpoint, monitor_id: str = None, resource_available_check: bool = False):
        result = None

        try:
            self._validate_request(endpoint)

            url = self.build_url(endpoint, monitor_id)

            _LOGGER.debug(f"GET {url}")

            async with self.session.get(url, ssl=False) as response:
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

        return result

    async def async_update(self):
        _LOGGER.debug(f"Updating data from Shinobi Video Server ({self.config_data.host})")

        if self.status == ConnectivityStatus.Failed:
            await self.initialize(self.config_data)

        if self.status == ConnectivityStatus.Connected:
            await self._load_monitors()

    async def login(self):
        await super().login()

        try:
            self._support_video_browser_api = False
            self.data[API_DATA_API_KEY] = None

            config_data = self.config_data

            data = {
                LOGIN_USERNAME: config_data.username,
                LOGIN_PASSWORD: config_data.password
            }

            login_data = await self._async_post(URL_LOGIN, data)

            if login_data is None:
                _LOGGER.warning(f"Failed to login, Response is empty")

                await self.set_status(ConnectivityStatus.Failed)

            else:
                user_data = login_data.get("$user", {})

                if user_data.get("ok", False):
                    self.data[API_DATA_GROUP_ID] = user_data.get(ATTR_MONITOR_GROUP_ID)

                    temp_api_key = user_data.get("auth_token")
                    uid = user_data.get("uid")
                    user_details = user_data.get("details")

                    self.data[API_DATA_USER_ID] = uid

                    self.data[API_DATA_API_KEY] = temp_api_key

                    await self.set_status(ConnectivityStatus.TemporaryConnected)

                    api_keys_data: dict = await self._async_get(URL_API_KEYS)

                    self.data[API_DATA_API_KEY] = None

                    if api_keys_data is not None:
                        if api_keys_data.get("ok", False):
                            keys = api_keys_data.get("keys", [])

                            for key in keys:
                                key_uid = key.get("uid", None)

                                if key_uid is not None and key_uid == uid:
                                    self.data[API_DATA_API_KEY] = key.get("code")

                                    self.data[API_DATA_DAYS] = int(float(user_details.get(API_DATA_DAYS, 10)))

                                    await self._set_socket_io_version()

                                    await self._set_support_video_browser_api()

                                    await self.set_status(ConnectivityStatus.Connected)

                                    break

                            if self.api_key is None:
                                _LOGGER.warning(
                                    f"No API key associated with user, Payload: {api_keys_data}"
                                )

                        else:
                            _LOGGER.warning(
                                f"Invalid response while trying to get API keys, Payload: {api_keys_data}")

                    else:
                        _LOGGER.warning(f"Invalid response while trying to get API keys, Payload is empty")

                    if self.status != ConnectivityStatus.Disconnected:
                        if self.status == ConnectivityStatus.Connected:
                            await self.fire_data_changed_event()

                        else:
                            await self.set_status(ConnectivityStatus.MissingAPIKey)

                else:
                    await self.set_status(ConnectivityStatus.InvalidCredentials)

        except Exception as ex:
            self.data[API_DATA_API_KEY] = None

            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            if self.status != ConnectivityStatus.Disconnected:
                await self.set_status(ConnectivityStatus.Failed)

                _LOGGER.error(f"Login attempt failed, Error: {ex}, Line: {line_number}")

    async def _set_socket_io_version(self):
        _LOGGER.debug("Set SocketIO version")
        version = 3

        response: bool = await self._async_get(URL_SOCKET_IO_V4, resource_available_check=True)

        if response:
            version = 4

        self.data[API_DATA_SOCKET_IO_VERSION] = version

    async def _set_support_video_browser_api(self):
        _LOGGER.debug("Set support flag for video browser API")

        support_video_browser_api: bool = await self._async_get(URL_VIDEO_WALL, resource_available_check=True)

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

    async def fire_data_changed_event(self):
        self.data[API_DATA_LAST_UPDATE] = datetime.now()

        await super().fire_data_changed_event()

    def _set_monitor_data(self, monitor: MonitorData):
        self.data[API_DATA_MONITORS][monitor.id] = monitor

    def _get_monitor_data(self, monitor_id: str) -> MonitorData:
        monitor = self.data[API_DATA_MONITORS][monitor_id]

        return monitor

    async def get_video_wall(self) -> list[dict] | None:
        result = []

        if self._support_video_browser_api:
            response: dict | None = await self._async_get(URL_VIDEO_WALL)

            if response is not None:
                result = response.get("data", [])

        else:
            for monitor_id in self.monitors:
                monitor_data = {
                    ATTR_MONITOR_ID: monitor_id,
                    ATTR_MONITOR_GROUP_ID: self.group_id
                }

                result.append(monitor_data)

        return result

    async def get_video_wall_monitor(self, monitor_id: str) -> list[dict] | None:
        result = []

        if self._support_video_browser_api:
            response: dict | None = await self._async_get(URL_VIDEO_WALL_MONITOR, monitor_id)

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
                    ATTR_DATE: video_date_iso
                }

                result.append(monitor_data)

        return result

    async def get_video_wall_monitor_date(self, monitor_id: str, date: str) -> list[dict] | None:
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
                        VIDEO_DETAILS_EXTENSION: video_data.get(VIDEO_DETAILS_EXTENSION)
                    }

                    result.append(monitor_data)

        return result

    async def async_repair_monitors(self):
        monitors = self.data.get("monitors", {})

        for monitor_id in monitors:
            monitor = monitors.get(monitor_id)

            if monitor_id not in self._repairing and monitor.should_repair:
                await self._async_repair_monitor(monitor_id)

    async def _async_repair_monitor(self, monitor_id: str):
        monitor = self._get_monitor_data(monitor_id)

        if monitor_id in self._repairing:
            _LOGGER.warning(f"Monitor {monitor_id} is in progress, cannot start additional repair job")

        elif not monitor.should_repair:
            _LOGGER.warning(f"Monitor {monitor_id} is working properly, no need to repair")

        else:
            try:
                _LOGGER.info(f"Repairing monitor {monitor_id}")

                self._repairing.append(monitor_id)

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
                self._repairing.remove(monitor_id)

    async def async_set_monitor_mode(self, monitor_id: str, mode: str):
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
