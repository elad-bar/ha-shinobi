from datetime import datetime
import json
import logging
import sys
from typing import List, Optional

import aiohttp
from aiohttp import ClientSession

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from ..helpers.const import *
from ..managers.configuration_manager import ConfigManager
from ..models.camera_data import CameraData

REQUIREMENTS = ["aiohttp"]

_LOGGER = logging.getLogger(__name__)


class ShinobiApi:
    """The Class for handling the data retrieval."""

    is_logged_in: bool
    group_id: Optional[str]
    user_id: Optional[str]
    api_key: Optional[str]
    session: Optional[ClientSession]
    camera_list: List[CameraData]
    hass: HomeAssistant
    config_manager: ConfigManager
    base_url: Optional[str]

    def __init__(self, hass: HomeAssistant, config_manager: ConfigManager):
        try:
            self._last_update = datetime.now()
            self.hass = hass
            self.config_manager = config_manager
            self.session_id = None
            self.is_logged_in = False
            self.group_id = None
            self.user_id = None
            self.api_key = None
            self.session = None
            self.is_logged_in = False
            self.base_url = None

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to load Shinobi Video API, error: {ex}, line: {line_number}"
            )

    @property
    def is_initialized(self):
        return self.session is not None and not self.session.closed

    @property
    def config_data(self):
        return self.config_manager.data

    async def initialize(self):
        _LOGGER.info("Initializing Shinobi Video")

        try:
            self.base_url = self.config_data.api_url
            self.is_logged_in = False
            self.camera_list = []

            if self.hass is None:
                if self.session is not None:
                    await self.session.close()

                self.session = aiohttp.client.ClientSession()
            else:
                self.session = async_create_clientsession(hass=self.hass)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to initialize Shinobi Video API ({self.base_url}), error: {ex}, line: {line_number}"
            )

    def build_url(self, endpoint, monitor_id: str = None):
        url = f"{self.base_url}{endpoint}"

        if GROUP_ID in url and self.group_id is not None:
            url = url.replace(GROUP_ID, self.group_id)

        if AUTH_TOKEN in url and self.api_key is not None:
            url = url.replace(AUTH_TOKEN, self.api_key)

        if MONITOR_ID in url and monitor_id is not None:
            url = url.replace(MONITOR_ID, monitor_id)

        return url

    async def async_post(self, endpoint, request_data: dict, camera_id: str = None, is_url_encoded: bool = False):
        result = None
        url = self.build_url(endpoint, camera_id)

        try:
            _LOGGER.debug(f"POST {url}, Url Encoded: {is_url_encoded}")

            if self.is_initialized:
                data = None if is_url_encoded else request_data
                json_data = request_data if is_url_encoded else None

                async with self.session.post(url, data=data, json=json_data, ssl=False) as response:
                    _LOGGER.debug(f"Status of {url}: {response.status}")

                    response.raise_for_status()

                    result = await response.json()

                    self._last_update = datetime.now()

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to post JSON to {endpoint}, Error: {ex}, Line: {line_number}"
            )

        return result

    async def async_get(self, endpoint, resource_available_check: bool = False):
        result = None
        url = self.build_url(endpoint)

        try:
            _LOGGER.debug(f"GET {url}")

            if self.is_initialized:
                async with self.session.get(url, ssl=False) as response:
                    _LOGGER.debug(f"Status of {url}: {response.status}")

                    response.raise_for_status()

                    if resource_available_check:
                        result = True

                    else:
                        result = await response.json()

                    self._last_update = datetime.now()

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to get data from {endpoint}, Error: {ex}, Line: {line_number}"
            )

        return result

    async def async_update(self):
        _LOGGER.info(f"Updating data from Shinobi Video Server ({self.config_data.name})")

        await self.load_camera()

    async def login(self):
        _LOGGER.info("Performing login")

        try:
            self.api_key = None

            config_data = self.config_manager.data

            data = {
                LOGIN_USERNAME: config_data.username,
                LOGIN_PASSWORD: config_data.password_clear_text
            }

            login_data = await self.async_post(URL_LOGIN, data)

            if login_data is not None:
                user_data = login_data.get("$user", {})

                if user_data.get("ok", False):
                    self.group_id = user_data.get(ATTR_CAMERA_GROUP_ID)
                    temp_api_key = user_data.get("auth_token")
                    uid = user_data.get("uid")

                    self.user_id = uid

                    _LOGGER.debug(f"Temporary auth token: {temp_api_key}")

                    self.api_key = temp_api_key

                    api_keys_data: dict = await self.async_get(URL_API_KEYS)

                    self.api_key = None

                    if api_keys_data is not None and api_keys_data.get("ok", False):
                        keys = api_keys_data.get("keys", [])

                        for key in keys:
                            key_uid = key.get("uid", None)

                            if key_uid is not None and key_uid == uid:
                                self.api_key = key.get("code")

                                _LOGGER.debug(f"Permanent access token: {self.api_key}")

                                break

            if self.api_key is None:
                error_message = "Failed to get permanent API Key"
                error_instructions = f"please go to Shinobi Video Dashboard and add API for `{config_data.username}`"

                _LOGGER.error(f"{error_message}, {error_instructions}")

        except Exception as ex:
            self.api_key = None

            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to login, Error: {ex}, Line: {line_number}")

        self.is_logged_in = self.api_key is not None

        return self.is_logged_in

    async def get_socket_io_version(self):
        _LOGGER.debug("Get SocketIO version")
        version = 3

        response: bool = await self.async_get(URL_SOCKET_IO_V4, True)

        if response:
            version = 4

        return version

    async def load_camera(self):
        _LOGGER.debug("Retrieving camera list")

        camera_list = []
        response: dict = await self.async_get(URL_MONITORS)

        if response is None:
            _LOGGER.warning("No monitors were found")

        else:
            if isinstance(response, list):
                monitors = response

            else:
                monitors: List = [response]

            for monitor in monitors:
                try:
                    if monitor is None:
                        _LOGGER.warning(f"Invalid camera details found")

                    else:
                        monitor_details_str = monitor.get("details")
                        details = json.loads(monitor_details_str)

                        monitor["details"] = details

                        camera = CameraData(monitor)
                        camera_list.append(camera)

                except Exception as ex:
                    exc_type, exc_obj, tb = sys.exc_info()
                    line_number = tb.tb_lineno

                    _LOGGER.error(
                        f"Failed to load camera data: {monitor}, Error: {ex}, Line: {line_number}"
                    )

        self.camera_list = camera_list

    async def async_set_motion_detection(self, camera_id: str, motion_detection_enabled: bool):
        _LOGGER.debug(f"Updating camera {camera_id} motion detection state to {motion_detection_enabled}")

        url = f"{URL_MONITORS}/{camera_id}"

        response: dict = await self.async_get(url)
        camera_data = response[0]
        camera_details_str = camera_data.get("details")
        details = json.loads(camera_details_str)

        details[ATTR_CAMERA_DETAILS_DETECTOR] = str(1 if motion_detection_enabled else 0)

        camera_data["details"] = details

        data = {
            "data": camera_data
        }

        await self.async_post(URL_UPDATE_MONITOR, data, camera_id, True)
