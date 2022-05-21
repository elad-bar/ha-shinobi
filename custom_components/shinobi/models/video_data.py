from __future__ import annotations

from datetime import datetime
import logging
import mimetypes
import sys

from homeassistant.exceptions import HomeAssistantError

from . import CameraNotFoundError
from ..helpers.const import *
from .camera_data import MonitorData

_LOGGER = logging.getLogger(__name__)


class VideoData:
    monitor_id: str
    camera_name: str
    action_url: str
    time: str
    mime_type: str

    def __init__(self, video: dict, camera_dict: dict[str, MonitorData]):
        try:
            camera_id = video.get(VIDEO_DETAILS_MONITOR_ID)

            if camera_id is None:
                raise HomeAssistantError()

            camera = camera_dict.get(camera_id)

            if camera is None:
                raise CameraNotFoundError(camera_id)

            extension = video.get(VIDEO_DETAILS_EXTENSION)
            video_time: str = video.get(VIDEO_DETAILS_TIME)

            self.monitor_id = camera_id
            self.camera_name = camera.name
            self.action_url = video.get(VIDEO_DETAILS_URL)
            self.mime_type = self.get_video_mime_type(extension)
            self.time = self._get_video_timestamp(video_time)

        except CameraNotFoundError as cnfex:
            _LOGGER.error(
                f"Failed to find camera: {cnfex.camera_id} for video: {video}"
            )

        except HomeAssistantError:
            _LOGGER.error(
                f"Failed to extract camera ID for video: {video}"
            )

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to initialize VideoData: {video}, Error: {ex}, Line: {line_number}"
            )

    @property
    def title(self):
        title = f"{self.camera_name} {self.time}"

        return title

    @property
    def identifier(self):
        identifier = f"{self.action_url}|{self.mime_type}"

        return identifier

    @staticmethod
    def get_video_mime_type(extension: str) -> str | None:
        """Determine mime type of video."""
        mime_type = mimetypes.types_map.get(f".{extension}".lower())

        if not mime_type:
            _LOGGER.warning(f"Mime Type for {extension.upper()} was not found")

        return mime_type

    @staticmethod
    def _get_video_timestamp(video_time: str):
        result = None

        try:
            if video_time is not None:
                if video_time.lower().endswith(VIDEO_DETAILS_TIME_INVALID_CHAR):
                    video_time = video_time[0: len(video_time) - 1]

                timestamp = datetime.fromisoformat(video_time)

                result = datetime.strftime(timestamp, VIDEO_DETAILS_TIME_FORMAT)

        finally:
            return result

    def __repr__(self):
        obj = {
            ATTR_CAMERA_MONITOR_ID: self.monitor_id,
            ATTR_CAMERA_NAME: self.camera_name,
            VIDEO_DETAILS_URL: self.action_url,
            VIDEO_DETAILS_MIME_TYPE: self.mime_type,
            VIDEO_DETAILS_TIME: self.time,
            VIDEO_DETAILS_TITLE: self.title,
            VIDEO_DETAILS_IDENTIFIER: self.identifier
        }

        to_string = f"{obj}"

        return to_string
