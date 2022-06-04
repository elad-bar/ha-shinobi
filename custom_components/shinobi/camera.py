"""
Support for Shinobi Video.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/camera.shinobi/
"""
from __future__ import annotations

from abc import ABC
import asyncio
from datetime import datetime
import logging

import aiohttp
import async_timeout

from homeassistant.components.camera import DEFAULT_CONTENT_TYPE, SUPPORT_STREAM, Camera
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import TemplateError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .component.api.shinobi_api import ShinobiApi
from .component.helpers.const import *
from .component.models.shinobi_entity import ShinobiEntity
from .core.models.base_entity import async_setup_base_entry
from .core.models.entity_data import EntityData

DEPENDENCIES = [DOMAIN]

_LOGGER = logging.getLogger(__name__)

CURRENT_DOMAIN = DOMAIN_CAMERA


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up the Shinobi Video Camera."""
    await async_setup_base_entry(
        hass, config_entry, async_add_devices, CURRENT_DOMAIN, get_camera
    )


async def async_unload_entry(hass, config_entry):
    _LOGGER.info(f"Unload entry for {CURRENT_DOMAIN} domain: {config_entry}")

    return True


def get_camera(hass: HomeAssistant, entity: EntityData):
    device_info = entity.details

    camera = ShinobiCamera(hass, device_info)
    camera.initialize(hass, entity, CURRENT_DOMAIN)

    return camera


class ShinobiCamera(Camera, ShinobiEntity, ABC):
    """ Shinobi Video Camera """

    def __init__(self, hass, device_info):
        super().__init__()
        self.hass = hass
        self._still_image_url = None
        self._stream_source = None
        self._frame_interval = 0
        self._supported_features = 0
        self.content_type = DEFAULT_CONTENT_TYPE
        self._auth = None
        self._last_url = None
        self._last_image = None
        self._limit_refetch = False
        self.verify_ssl = False

    @property
    def api(self) -> ShinobiApi:
        return self.ha.api

    def initialize(
        self,
        hass: HomeAssistant,
        entity: EntityData,
        current_domain: str,
    ):
        super().initialize(hass, entity, current_domain)

        config_data = self.ha.config_data

        username = config_data.username
        password = config_data.password
        use_original_stream = config_data.use_original_stream

        monitor = self.api.monitors.get(self.entity.id)

        snapshot = self.api.build_url(monitor.snapshot)
        still_image_url_template = cv.template(snapshot)

        stream_support = DOMAIN_STREAM in self.hass.data

        stream_source = None

        if not use_original_stream:
            for stream in monitor.streams:
                if stream is not None:
                    stream_source = self.api.build_url(stream)
                    break

        if use_original_stream or stream_source is None:
            stream_source = monitor.original_stream

        stream_support_flag = SUPPORT_STREAM if stream_source and stream_support else 0

        self._still_image_url = still_image_url_template
        self._still_image_url.hass = hass

        self._stream_source = stream_source
        self._frame_interval = 1 / monitor.fps
        self._supported_features = stream_support_flag

        if username and password:
            self._auth = aiohttp.BasicAuth(username, password=password)

    def _immediate_update(self, previous_state: str):
        if previous_state != self.entity.state:
            _LOGGER.debug(
                f"{self.name} updated from {previous_state} to {self.entity.state}"
            )

        super()._immediate_update(previous_state)

    async def async_added_to_hass_local(self):
        """Subscribe events."""
        _LOGGER.info(f"Added new {self.name}")

    @property
    def is_recording(self) -> bool:
        return self.entity.state == MONITOR_MODE_RECORD

    @property
    def motion_detection_enabled(self):
        return self.entity.details.get(CONF_MOTION_DETECTION, False)

    @property
    def supported_features(self):
        """Return supported features for this camera."""
        return self._supported_features

    @property
    def frame_interval(self):
        """Return the interval between frames of the mjpeg stream."""
        return self._frame_interval

    def camera_image(self, width: int | None = None, height: int | None = None) -> bytes | None:
        """Return bytes of camera image."""
        return asyncio.run_coroutine_threadsafe(
            self.async_camera_image(), self.hass.loop
        ).result()

    async def async_camera_image(self, width: int | None = None, height: int | None = None) -> bytes | None:
        """Return a still image response from the camera."""
        try:
            url = self._still_image_url.async_render()
        except TemplateError as err:
            _LOGGER.error(f"Error parsing template {self._still_image_url}, Error: {err}")
            return self._last_image

        if url == self._last_url and self._limit_refetch:
            return self._last_image

        try:
            ws = async_get_clientsession(self.hass, verify_ssl=self.verify_ssl)
            async with async_timeout.timeout(10):
                url = f"{url}?ts={datetime.now().timestamp()}"
                response = await ws.get(url, auth=self._auth)

            self._last_image = await response.read()

        except asyncio.TimeoutError:
            _LOGGER.error(f"Timeout getting camera image from {self.name}")
            return self._last_image

        except aiohttp.ClientError as err:
            _LOGGER.error(f"Error getting new camera image from {self.name}, Error: {err}")
            return self._last_image

        self._last_url = url
        return self._last_image

    async def stream_source(self):
        """Return the source of the stream."""
        return self._stream_source

    async def async_enable_motion_detection(self) -> None:
        """Enable motion detection in the camera."""
        if self.motion_detection_enabled:
            _LOGGER.error(f"{self.name} - motion detection already enabled'")

        else:
            await self.ha.async_set_motion_detection(self.entity.id, True)

    async def async_disable_motion_detection(self) -> None:
        """Disable motion detection in camera."""
        if self.motion_detection_enabled:
            await self.ha.async_set_motion_detection(self.entity.id, False)

        else:
            _LOGGER.error(f"{self.name} - motion detection already disabled'")
