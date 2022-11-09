from __future__ import annotations

from datetime import datetime
import logging
import mimetypes

from .const import *

_LOGGER = logging.getLogger(__name__)


def format_datetime(video_time: str, date_format: str) -> str:
    result = None

    try:
        if video_time is not None:
            if video_time.lower().endswith(VIDEO_DETAILS_TIME_INVALID_CHAR):
                video_time = video_time[0: len(video_time) - 1]

            timestamp = datetime.fromisoformat(video_time)

            result = datetime.strftime(timestamp, date_format)

    finally:
        return result


def get_mime_type(extension: str) -> str | None:
    """Determine mime type of video."""
    mime_type = mimetypes.types_map.get(f".{extension}".lower())

    if not mime_type:
        _LOGGER.warning(f"Mime Type for {extension.upper()} was not found")

    return mime_type
