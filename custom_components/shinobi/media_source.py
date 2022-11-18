"""Expose Radio Browser as a media source."""
from __future__ import annotations

from abc import ABC
from collections.abc import Awaitable, Callable
from datetime import date, datetime
import logging

from homeassistant.components.media_player.const import MediaClass, MediaType
from homeassistant.components.media_source.models import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .component.api.api import IntegrationAPI
from .component.helpers import get_ha
from .component.helpers.const import *
from .component.models.media_source_item_identifier import MediaSourceItemIdentifier

_LOGGER = logging.getLogger(__name__)


async def async_get_media_source(hass: HomeAssistant) -> ShinobiMediaSource:
    """Set up Shinobi Video Browser media source."""
    entries = hass.config_entries.async_entries(DOMAIN)

    for entry in entries:
        return ShinobiMediaSource(hass, entry)


class ShinobiMediaSource(MediaSource, ABC):
    """Provide Radio stations as media sources."""
    name = MEDIA_BROWSER_NAME
    hass: HomeAssistant = None
    _ha = None
    _thumbnails_support: bool
    _ui_modes: dict[int, Callable[[MediaSourceItemIdentifier], Awaitable[list[BrowseMediaSource]]]]

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize CameraMediaSource."""
        _LOGGER.debug(f"Loading Shinobi Media Source")

        super().__init__(DOMAIN)
        self.hass = hass
        self.entry = entry

        self._ha = get_ha(self.hass, entry.entry_id)

        self._ui_modes = {
            1: self._async_build_monitors,
            2: self._async_build_calendar,
            3: self._async_build_videos,
            4: self._async_build_videos,
            5: self._async_build_videos,
        }

        self._thumbnails_support = False

    @property
    def api(self) -> IntegrationAPI:
        return self._ha.api

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

        self._thumbnails_support = await self.api.has_thumbnails_support()

        title = self._get_title(identifier)
        action = self._ui_modes.get(identifier.current_mode)

        _LOGGER.debug(
            f"Browse media, "
            f"Identifier: {identifier.identifier}, "
            f"Title: {title}, "
            f"Has thumbnails support: {self._thumbnails_support}"
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
        title_parts = [
            self.entry.title
        ]

        if identifier.monitor_id is not None:
            monitor = self.api.monitors.get(identifier.monitor_id)

            title_parts.append(monitor.name)

        if identifier.day is not None:
            date_title = datetime.fromisoformat(identifier.day).strftime("%x")
            title_parts.append(date_title)

        title = " / ".join(title_parts)

        return title

    @callback
    async def _async_build_monitors(self, identifier: MediaSourceItemIdentifier) -> list[BrowseMediaSource]:
        """Build list of media sources from Shinobi Video Server."""
        items: list[BrowseMediaSource] = []

        _LOGGER.debug(
            "Building monitors list"
        )

        for monitor_id in self.api.monitors:
            monitor = self.api.monitors.get(monitor_id)

            snapshot = monitor.snapshot

            if snapshot.startswith("/"):
                snapshot = snapshot[1:]

            snapshot = self.api.build_url(f"{{base_url}}{snapshot}")

            item = BrowseMediaSource(
                domain=DOMAIN,
                identifier=f"{identifier.category}/{monitor.id}",
                media_class=MediaClass.DIRECTORY,
                media_content_type=MediaType.ALBUM,
                title=monitor.name,
                can_play=False,
                can_expand=True,
                thumbnail=snapshot,
            )

            items.append(item)

        return items

    @callback
    async def _async_build_calendar(self, identifier: MediaSourceItemIdentifier) -> list[BrowseMediaSource]:
        """Build list of media sources from Shinobi Video Server."""
        items: list[BrowseMediaSource] = []

        today = date.today()
        _LOGGER.debug(
            f"Building camera calendar, "
            f"Monitor: {identifier.monitor_id}"
        )

        for day in range(0, 7):
            lookup_date = today - timedelta(days=day)
            monitor = self.api.monitors.get(identifier.monitor_id)

            day_name = MEDIA_SOURCE_SPECIAL_DAYS.get(day, lookup_date.strftime("%A"))

            snapshot = monitor.snapshot

            if snapshot.startswith("/"):
                snapshot = snapshot[1:]

            snapshot = self.api.build_url(f"{{base_url}}{snapshot}")

            item = BrowseMediaSource(
                domain=DOMAIN,
                identifier=f"{identifier.category}/{identifier.monitor_id}/{lookup_date}",
                media_class=MediaClass.DIRECTORY,
                media_content_type=MediaType.ALBUM,
                title=day_name,
                can_play=False,
                can_expand=True,
                thumbnail=snapshot,
            )

            items.append(item)

        return items

    @callback
    async def _async_build_videos(self, identifier: MediaSourceItemIdentifier) -> list[BrowseMediaSource]:
        """Build list of media sources from Shinobi Video Server."""
        items: list[BrowseMediaSource] = []

        videos = await self.api.get_videos(identifier.monitor_id, identifier.day)

        _LOGGER.debug(
            f"Building video directory, "
            f"Monitor: {identifier.monitor_id}, "
            f"Day: {identifier.day}, "
            f"Videos: {len(videos)}"
        )

        for video in videos:
            video_time_iso = video.time_iso

            thumbnail_base_url = self.api.build_url(URL_THUMBNAILS_IMAGE, identifier.monitor_id)
            thumbnail_url = f"{thumbnail_base_url}/{identifier.day}T{video_time_iso}/{video.extension}"

            thumbnail = thumbnail_url if self._thumbnails_support else None

            category = identifier.category
            monitor_id = identifier.monitor_id
            day = identifier.day

            item = BrowseMediaSource(
                domain=DOMAIN,
                identifier=f"{category}/{monitor_id}/{day}/{video_time_iso}/{video.extension}",
                media_class=MediaClass.VIDEO,
                media_content_type=MediaType.VIDEO,
                title=video.time,
                can_play=True,
                can_expand=False,
                thumbnail=thumbnail,
            )

            items.append(item)

        return items
