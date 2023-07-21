"""Expose Radio Browser as a media source."""
from __future__ import annotations

from abc import ABC
from collections.abc import Awaitable, Callable
from datetime import datetime
import logging

from custom_components.shinobi.common.media_source_item_identifier import (
    MediaSourceItemIdentifier,
)
from homeassistant.components.media_player.const import MediaClass, MediaType
from homeassistant.components.media_source.models import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DATE
from homeassistant.core import HomeAssistant, callback

from .common.consts import (
    ATTR_MONITOR_ID,
    DATE_FORMAT_WEEKDAY,
    DOMAIN,
    MEDIA_BROWSER_NAME,
    MEDIA_SOURCE_SPECIAL_DAYS,
    TIME_LAPSE_FILE_NAME,
    TIME_LAPSE_TIME,
    URL_TIME_LAPSE,
    URL_VIDEOS,
    VIDEO_DETAILS_DATE_FORMAT,
    VIDEO_DETAILS_EXTENSION,
    VIDEO_DETAILS_TIME_FORMAT,
    VIDEO_DETAILS_TIME_INVALID_CHAR,
    VIDEO_DETAILS_TIME_ISO_FORMAT,
)
from .managers.coordinator import Coordinator
from .managers.rest_api import RestAPI

_LOGGER = logging.getLogger(__name__)


async def async_get_media_source(hass: HomeAssistant) -> IntegrationMediaSource:
    """Set up Shinobi Video Browser media source."""
    entries = hass.config_entries.async_entries(DOMAIN)

    for entry in entries:
        coordinator = hass.data[DOMAIN][entry.entry_id]
        return IntegrationMediaSource(hass, entry, coordinator)


class IntegrationMediaSource(MediaSource, ABC):
    """Provide Radio stations as media sources."""

    name = MEDIA_BROWSER_NAME
    hass: HomeAssistant = None
    _ha = None
    _ui_modes: dict[
        int, Callable[[MediaSourceItemIdentifier], Awaitable[list[BrowseMediaSource]]]
    ]

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, coordinator: Coordinator
    ) -> None:
        """Initialize CameraMediaSource."""
        _LOGGER.debug("Loading Shinobi Media Source")

        super().__init__(DOMAIN)
        self.hass = hass
        self.entry = entry

        self._coordinator = coordinator

        self._ui_modes = {
            1: self._async_build_monitors,
            2: self._async_build_calendar,
            3: self._async_build_videos,
            4: self._async_build_videos,
            5: self._async_build_videos,
        }

    @property
    def api(self) -> RestAPI:
        return self._coordinator.api

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Resolve selected Video to a streaming URL."""
        identifier = MediaSourceItemIdentifier(item.identifier)

        video_base_url = self.api.build_url(URL_VIDEOS, identifier.monitor_id)
        video_url = f"{video_base_url}/{identifier.day}T{identifier.video_time}.{identifier.video_extension}"

        mime_type = identifier.video_mime_type

        _LOGGER.debug(
            f"Resolving Identifier: {identifier.identifier},"
            f"URL: {video_url}, "
            f"Mime type: {mime_type}"
        )

        return PlayMedia(video_url, mime_type)

    async def async_browse_media(
        self,
        item: MediaSourceItem,
    ) -> BrowseMediaSource:
        """Return media."""
        identifier = MediaSourceItemIdentifier(item.identifier)

        title = self._get_title(identifier)
        action = self._ui_modes.get(identifier.current_mode)

        _LOGGER.debug(
            f"Browse media, " f"Identifier: {identifier.identifier}, " f"Title: {title}"
        )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=None,
            media_class=MediaClass.CHANNEL,
            media_content_type=MediaType.CHANNEL,
            title=title,
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.ALBUM,
            children=[
                *await action(identifier),
            ],
        )

    def _get_title(self, identifier: MediaSourceItemIdentifier) -> str:
        title_parts = [self.entry.title]

        if identifier.monitor_id is not None:
            monitor = self._coordinator.get_monitor(identifier.monitor_id)

            title_parts.append(monitor.name)

        if identifier.day is not None:
            date_title = datetime.fromisoformat(identifier.day).strftime("%x")
            title_parts.append(date_title)

        title = " / ".join(title_parts)

        return title

    @callback
    async def _async_build_monitors(
        self, identifier: MediaSourceItemIdentifier
    ) -> list[BrowseMediaSource]:
        """Build list of media sources from Shinobi Video Server."""
        items: list[BrowseMediaSource] = []

        _LOGGER.debug("Building monitors list")

        monitors = await self.api.get_video_wall()

        for monitor in monitors:
            monitor_id = monitor.get(ATTR_MONITOR_ID)
            monitor_data = self._coordinator.get_monitor(monitor_id)
            monitor_name = monitor_id
            snapshot = None

            if monitor_data is not None:
                snapshot = monitor_data.snapshot

                if snapshot.startswith("/"):
                    snapshot = snapshot[1:]

                snapshot = self.api.build_url(f"{{base_url}}{snapshot}")

            item = BrowseMediaSource(
                domain=DOMAIN,
                identifier=f"{identifier.identifier}/{monitor_id}",
                media_class=MediaClass.DIRECTORY,
                media_content_type=MediaType.ALBUM,
                title=monitor_name,
                can_play=False,
                can_expand=True,
                thumbnail=snapshot,
            )

            items.append(item)

        return items

    @callback
    async def _async_build_calendar(
        self, identifier: MediaSourceItemIdentifier
    ) -> list[BrowseMediaSource]:
        """Build list of media sources from Shinobi Video Server."""
        items: list[BrowseMediaSource] = []

        _LOGGER.debug(f"Building camera calendar, " f"Monitor: {identifier.monitor_id}")

        today = datetime.today()
        monitors = await self.api.get_video_wall_monitor(identifier.monitor_id)

        for monitor in monitors:
            date_iso = monitor.get(ATTR_DATE)
            filename = monitor.get(TIME_LAPSE_FILE_NAME)

            date = self._get_date(date_iso)
            day_delta = today - date
            days = day_delta.days

            if days in MEDIA_SOURCE_SPECIAL_DAYS:
                day_name = MEDIA_SOURCE_SPECIAL_DAYS.get(
                    days,
                )
            else:
                day_name_key = (
                    VIDEO_DETAILS_DATE_FORMAT if days > 7 else DATE_FORMAT_WEEKDAY
                )
                day_name = date.strftime(day_name_key)

            thumbnail_base_url = self.api.build_url(
                URL_TIME_LAPSE, identifier.monitor_id
            )
            thumbnail_url = (
                None
                if filename is None
                else f"{thumbnail_base_url}/{date_iso}/{filename}"
            )

            item = BrowseMediaSource(
                domain=DOMAIN,
                identifier=f"{identifier.identifier}/{date_iso}",
                media_class=MediaClass.DIRECTORY,
                media_content_type=MediaType.ALBUM,
                title=day_name,
                can_play=False,
                can_expand=True,
                thumbnail=thumbnail_url,
            )

            items.append(item)

        return items

    @callback
    async def _async_build_videos(
        self, identifier: MediaSourceItemIdentifier
    ) -> list[BrowseMediaSource]:
        """Build list of media sources from Shinobi Video Server."""
        items: list[BrowseMediaSource] = []

        monitors = await self.api.get_video_wall_monitor_date(
            identifier.monitor_id, identifier.day
        )

        for monitor in monitors:
            date = monitor.get(ATTR_DATE)
            filename = monitor.get(TIME_LAPSE_FILE_NAME)
            video_time_full = monitor.get(TIME_LAPSE_TIME)
            video_extension = monitor.get(VIDEO_DETAILS_EXTENSION)

            video_time = self._get_date(video_time_full)
            video_start_time = video_time.strftime(VIDEO_DETAILS_TIME_FORMAT)
            video_time_iso = video_time.strftime(VIDEO_DETAILS_TIME_ISO_FORMAT)

            thumbnail_base_url = self.api.build_url(
                URL_TIME_LAPSE, identifier.monitor_id
            )
            thumbnail_url = (
                None if filename is None else f"{thumbnail_base_url}/{date}/{filename}"
            )

            item = BrowseMediaSource(
                domain=DOMAIN,
                identifier=f"{identifier.identifier}/{video_time_iso}/{video_extension}",
                media_class=MediaClass.VIDEO,
                media_content_type=MediaType.VIDEO,
                title=video_start_time,
                can_play=True,
                can_expand=False,
                thumbnail=thumbnail_url,
            )

            items.append(item)

        return items

    @staticmethod
    def _get_date(date: str) -> datetime | None:
        result = None

        try:
            if date is not None:
                if date.lower().endswith(VIDEO_DETAILS_TIME_INVALID_CHAR):
                    date = date[0 : len(date) - 1]

                result = datetime.fromisoformat(date)

        finally:
            return result
