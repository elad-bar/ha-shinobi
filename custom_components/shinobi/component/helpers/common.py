from __future__ import annotations

from datetime import datetime
import logging
import mimetypes
import sys

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HomeAssistant

from ...component.managers.home_assistant import ShinobiHomeAssistantManager
from ...core.helpers.const import DATA
from .const import VIDEO_DETAILS_TIME_INVALID_CHAR

_LOGGER = logging.getLogger(__name__)


async def async_set_ha(hass: HomeAssistant, entry: ConfigEntry):
    try:
        if DATA not in hass.data:
            hass.data[DATA] = {}

        instance = ShinobiHomeAssistantManager(hass)

        await instance.async_init(entry)

        hass.data[DATA][entry.entry_id] = instance

        async def _async_unload(_: Event) -> None:
            await instance.async_unload()

        entry.async_on_unload(
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_unload)
        )
    except Exception as ex:
        exc_type, exc_obj, tb = sys.exc_info()
        line_number = tb.tb_lineno

        _LOGGER.error(f"Failed to async_set_ha, error: {ex}, line: {line_number}")


def get_ha(hass: HomeAssistant, entry_id) -> ShinobiHomeAssistantManager:
    ha_data = hass.data.get(DATA, {})
    ha = ha_data.get(entry_id)

    return ha


def clear_ha(hass: HomeAssistant, entry_id):
    if DATA not in hass.data:
        hass.data[DATA] = {}

    del hass.data[DATA][entry_id]


def format_datetime(video_time: str, date_format: str) -> str:
    result = None

    try:
        if video_time is not None:
            if video_time.lower().endswith(VIDEO_DETAILS_TIME_INVALID_CHAR):
                video_time = video_time[0 : len(video_time) - 1]

            timestamp = datetime.fromisoformat(video_time)

            result = datetime.strftime(timestamp, date_format)

    finally:
        return result


def get_date(date: str) -> datetime | None:
    result = None

    try:
        if date is not None:
            if date.lower().endswith(VIDEO_DETAILS_TIME_INVALID_CHAR):
                date = date[0 : len(date) - 1]

            result = datetime.fromisoformat(date)

    finally:
        return result


def get_mime_type(extension: str) -> str | None:
    """Determine mime type of video."""
    mime_type = mimetypes.types_map.get(f".{extension}".lower())

    if not mime_type:
        _LOGGER.warning(f"Mime Type for {extension.upper()} was not found")

    return mime_type
