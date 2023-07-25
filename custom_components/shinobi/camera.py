"""
Support for camera.
"""
from __future__ import annotations

from abc import ABC
import asyncio
import collections
import logging

import aiohttp

from homeassistant.components.camera import (
    DEFAULT_CONTENT_TYPE,
    Camera,
    CameraEntityFeature,
)
from homeassistant.components.stream import Stream
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ICON, ATTR_STATE, Platform
from homeassistant.core import HomeAssistant

from .common.base_entity import IntegrationBaseEntity, async_setup_base_entry
from .common.consts import (
    ACTION_ENTITY_TURN_OFF,
    ACTION_ENTITY_TURN_ON,
    ATTR_ATTRIBUTES,
    SINGLE_FRAME_PS,
)
from .common.entity_descriptions import IntegrationCameraEntityDescription
from .common.enums import MonitorState
from .common.monitor_data import MonitorData
from .managers.coordinator import Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    await async_setup_base_entry(
        hass,
        entry,
        Platform.CAMERA,
        IntegrationCameraEntity,
        async_add_entities,
    )


class IntegrationCameraEntity(IntegrationBaseEntity, Camera, ABC):
    """Representation of a sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        entity_description: IntegrationCameraEntityDescription,
        coordinator: Coordinator,
        monitor: MonitorData,
    ):
        super().__init__(hass, entity_description, coordinator, monitor)

        self.stream: Stream | None = None
        self.stream_options: dict[str, str | bool | float] = {}
        self.content_type: str = DEFAULT_CONTENT_TYPE
        self.access_tokens: collections.deque = collections.deque([], 2)
        self._warned_old_signature = False
        self.async_update_token()
        self._create_stream_lock: asyncio.Lock | None = None
        self._rtsp_to_webrtc = False

        self._stream_source = None

        self._attr_supported_features = CameraEntityFeature(0)
        self._attr_frame_interval = SINGLE_FRAME_PS / monitor.fps

        self._last_image = None
        self._last_url = None
        self._snapshot_url = None

        username = coordinator.config_manager.username
        password = coordinator.config_manager.password

        if username and password:
            self._auth = aiohttp.BasicAuth(username, password=password)

        self._set_stream_source(monitor)

    def _set_stream_source(self, monitor: MonitorData):
        coordinator = self._local_coordinator
        config_manager = coordinator.config_manager
        api = coordinator.api

        use_original_stream = config_manager.use_original_stream
        snapshot = monitor.snapshot

        if snapshot.startswith("/"):
            snapshot = snapshot[1:]

        snapshot = api.build_url(f"{{base_url}}{snapshot}")

        stream_source = None

        if not use_original_stream:
            for stream in monitor.streams:
                if stream is not None:
                    if stream.startswith("/"):
                        stream = stream[1:]

                    stream_source = api.build_url(f"{{base_url}}{stream}")
                    break

        if use_original_stream or stream_source is None:
            stream_source = monitor.original_stream

        self._stream_source = stream_source
        self._attr_is_streaming = stream_source is not None
        self._snapshot_url = snapshot

        if self._stream_source:
            self._attr_supported_features = CameraEntityFeature.STREAM

    async def stream_source(self) -> str | None:
        """Return the source of the stream."""
        return self._stream_source

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return a still image response from the camera."""
        api = self._local_coordinator.api

        image = await api.get_snapshot(self._snapshot_url)

        return image

    async def async_enable_motion_detection(self) -> None:
        """Enable motion detection in the camera."""
        if self.motion_detection_enabled:
            _LOGGER.error(f"{self.name} - motion detection already enabled'")

        else:
            await self.async_execute_device_action(ACTION_ENTITY_TURN_ON)

    async def async_disable_motion_detection(self) -> None:
        """Disable motion detection in camera."""
        if self.motion_detection_enabled:
            await self.async_execute_device_action(ACTION_ENTITY_TURN_OFF)

        else:
            _LOGGER.error(f"{self.name} - motion detection already disabled'")

    def update_component(self, data):
        """Fetch new state parameters for the sensor."""
        if data is not None:
            monitor = self._local_coordinator.get_monitor(self.monitor_id)

            state = data.get(ATTR_STATE).lower()
            attributes = data.get(ATTR_ATTRIBUTES)
            icon = data.get(ATTR_ICON)

            is_on = MonitorState.is_online(state)
            is_recording = MonitorState.is_recording(state)

            self._attr_motion_detection_enabled = monitor.has_motion_detector
            self._attr_is_recording = is_recording
            self._attr_is_streaming = is_on and not is_recording
            self._attr_is_on = is_on

            self._attr_extra_state_attributes = attributes

            if icon is not None:
                self._attr_icon = icon

        else:
            self._attr_motion_detection_enabled = False
            self._attr_is_recording = False
            self._attr_is_on = False
