from __future__ import annotations

from datetime import datetime
import logging
import mimetypes

from homeassistant.components.camera import DOMAIN as DOMAIN_CAMERA

from .consts import (
    MEDIA_SOURCE_ITEM_IDENTIFIER_CATEGORY,
    MEDIA_SOURCE_ITEM_IDENTIFIER_DAY,
    MEDIA_SOURCE_ITEM_IDENTIFIER_KEY,
    MEDIA_SOURCE_ITEM_IDENTIFIER_MODE,
    MEDIA_SOURCE_ITEM_IDENTIFIER_MONITOR_ID,
    MEDIA_SOURCE_ITEM_IDENTIFIER_VIDEO_EXTENSION,
    MEDIA_SOURCE_ITEM_IDENTIFIER_VIDEO_TIME,
    VIDEO_DETAILS_DATE_FORMAT,
    VIDEO_DETAILS_TIME_INVALID_CHAR,
)

_LOGGER = logging.getLogger(__name__)


class MediaSourceItemIdentifier:
    category: str | None
    monitor_id: str | None
    day: str | None
    identifier: str | None
    video_time: str | None
    video_extension: str | None
    current_mode: int

    def __init__(self, identifier: str | None):
        if identifier is None:
            identifier = DOMAIN_CAMERA

        identifier_parts = identifier.split("/")

        self.current_mode = len(identifier_parts)
        self.identifier = identifier
        self.category = None
        self.monitor_id = None
        self.day = None
        self.video_time = None
        self.video_extension = None

        if self.current_mode > 0:
            self.category = identifier_parts[0]

        if self.current_mode > 1:
            self.monitor_id = identifier_parts[1]

        if self.current_mode > 2:
            self.day = identifier_parts[2]

        if self.current_mode > 3:
            self.video_time = identifier_parts[3]

        if self.current_mode > 4:
            self.video_extension = identifier_parts[4]

    @property
    def video_date(self) -> str:
        result = self._format_datetime(self.day, VIDEO_DETAILS_DATE_FORMAT)

        return result

    @property
    def video_mime_type(self) -> str:
        result = self._get_mime_type(self.video_extension)

        return result

    def to_dict(self):
        obj = {
            MEDIA_SOURCE_ITEM_IDENTIFIER_MODE: self.current_mode,
            MEDIA_SOURCE_ITEM_IDENTIFIER_KEY: self.identifier,
            MEDIA_SOURCE_ITEM_IDENTIFIER_CATEGORY: self.category,
            MEDIA_SOURCE_ITEM_IDENTIFIER_MONITOR_ID: self.monitor_id,
            MEDIA_SOURCE_ITEM_IDENTIFIER_DAY: self.day,
            MEDIA_SOURCE_ITEM_IDENTIFIER_VIDEO_TIME: self.video_time,
            MEDIA_SOURCE_ITEM_IDENTIFIER_VIDEO_EXTENSION: self.video_extension,
        }

        return obj

    def __repr__(self):
        to_string = f"{self.to_dict()}"

        return to_string

    @staticmethod
    def _get_mime_type(extension: str) -> str | None:
        """Determine mime type of video."""
        mime_type = mimetypes.types_map.get(f".{extension}".lower())

        if not mime_type:
            _LOGGER.warning(f"Mime Type for {extension.upper()} was not found")

        return mime_type

    @staticmethod
    def _format_datetime(video_time: str, date_format: str) -> str:
        result = None

        try:
            if video_time is not None:
                if video_time.lower().endswith(VIDEO_DETAILS_TIME_INVALID_CHAR):
                    video_time = video_time[0 : len(video_time) - 1]

                timestamp = datetime.fromisoformat(video_time)

                result = datetime.strftime(timestamp, date_format)

        finally:
            return result
