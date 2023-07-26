from __future__ import annotations

import logging
import sys

from homeassistant.components.binary_sensor import BinarySensorDeviceClass

from ..common.consts import (
    ATTR_DISABLED,
    ATTR_FPS,
    ATTR_MONITOR_DETAILS,
    ATTR_MONITOR_DETAILS_AUDIO_CODEC,
    ATTR_MONITOR_DETAILS_DETECTOR,
    ATTR_MONITOR_DETAILS_DETECTOR_AUDIO,
    ATTR_MONITOR_GROUP_ID,
    ATTR_MONITOR_ID,
    ATTR_MONITOR_MODE,
    ATTR_MONITOR_NAME,
    ATTR_MONITOR_SNAPSHOT,
    ATTR_MONITOR_STATUS,
    ATTR_MONITOR_STREAMS,
    ATTR_ORIGINAL_STREAM,
    ATTR_STREAM_FPS,
    ATTR_STREAM_PASSWORD,
    ATTR_STREAM_USERNAME,
    MOTION_DETECTION,
    SOUND_DETECTION,
    STREAM_PROTOCOL_SUFFIX,
    TRIGGER_PLUG_DB,
)
from ..common.enums import MonitorMode, MonitorState

_LOGGER = logging.getLogger(__name__)


class MonitorData:
    id: str
    group_id: str
    name: str
    details: dict
    has_audio: bool
    has_audio_detector: bool
    has_motion_detector: bool
    fps: int
    jpeg_api_enabled: bool
    original_stream: str
    mode: str
    status: str
    snapshot: str | None

    def __init__(self, monitor):
        try:
            self.id = monitor.get(ATTR_MONITOR_ID)
            self.group_id = monitor.get(ATTR_MONITOR_GROUP_ID)
            self.name = monitor.get(ATTR_MONITOR_NAME)
            self.status = monitor.get(ATTR_MONITOR_STATUS, MonitorState.STOPPED)
            self.snapshot = monitor.get(ATTR_MONITOR_SNAPSHOT)
            self.streams = monitor.get(ATTR_MONITOR_STREAMS)
            self.mode = monitor.get(ATTR_MONITOR_MODE)
            self.details = monitor
            self.jpeg_api_enabled = self.snapshot is not None and self.snapshot != ""

            monitor_details = monitor.get(ATTR_MONITOR_DETAILS, {})

            fps = monitor_details.get(ATTR_STREAM_FPS, "1")

            if "." in fps:
                fps = fps.split(".")[0]

            self.fps = 1 if fps == "" else int(fps)
            self.has_audio = (
                monitor_details.get(ATTR_MONITOR_DETAILS_AUDIO_CODEC, "no") != "no"
            )
            self.has_audio_detector = (
                monitor_details.get(ATTR_MONITOR_DETAILS_DETECTOR_AUDIO, "0") != "0"
            )
            self.has_motion_detector = (
                monitor_details.get(ATTR_MONITOR_DETAILS_DETECTOR, "0") != "0"
            )
            original_stream = monitor_details.get(ATTR_ORIGINAL_STREAM)
            stream_username = monitor_details.get(ATTR_STREAM_USERNAME)
            stream_password = monitor_details.get(ATTR_STREAM_PASSWORD)
            stream_credentials = (
                f"{STREAM_PROTOCOL_SUFFIX}{stream_username}:{stream_password}@"
            )

            if (
                original_stream is not None
                and stream_credentials not in original_stream
            ):
                original_stream = original_stream.replace(
                    STREAM_PROTOCOL_SUFFIX, stream_credentials
                )

            self.original_stream = original_stream

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to initialize MonitorData: {monitor}, Error: {ex}, Line: {line_number}"
            )

    @property
    def disabled(self):
        is_disabled = self.mode == MonitorMode.STOP

        return is_disabled

    def is_detector_active(self, sensor_type: BinarySensorDeviceClass):
        result = False

        if sensor_type.SOUND and self.has_audio_detector:
            result = True

        if sensor_type.MOTION and self.has_motion_detector:
            result = True

        return result

    def to_dict(self):
        obj = {
            ATTR_MONITOR_ID: self.id,
            ATTR_MONITOR_NAME: self.name,
            ATTR_MONITOR_STATUS: self.status,
            ATTR_MONITOR_SNAPSHOT: self.snapshot,
            ATTR_MONITOR_STREAMS: self.streams,
            ATTR_MONITOR_DETAILS: self.details,
            ATTR_ORIGINAL_STREAM: self.original_stream,
            MOTION_DETECTION: self.has_motion_detector,
            SOUND_DETECTION: self.has_audio_detector,
            TRIGGER_PLUG_DB: self.has_audio,
            ATTR_FPS: self.fps,
            ATTR_MONITOR_MODE: self.mode,
            ATTR_DISABLED: self.disabled,
        }

        return obj

    def __repr__(self):
        to_string = f"{self.to_dict()}"

        return to_string
