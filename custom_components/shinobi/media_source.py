"""Expose Radio Browser as a media source."""
from __future__ import annotations

from abc import ABC
from collections.abc import Awaitable, Callable
from datetime import datetime
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
from .component.helpers.common import get_date
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

        title = self._get_title(identifier)
        action = self._ui_modes.get(identifier.current_mode)

        _LOGGER.debug(
            f"Browse media, "
            f"Identifier: {identifier.identifier}, "
            f"Title: {title}"
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
                identifier=f"{identifier.identifier}/{monitor.id}",
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

        _LOGGER.debug(
            f"Building camera calendar, "
            f"Monitor: {identifier.monitor_id}"
        )

        video_dates = await self.api.get_videos_dates(identifier.monitor_id)

        for video_date in video_dates:
            day_name = video_dates.get(video_date)

            time_lapse_items = await self.api.async_get_time_lapse_images(identifier.monitor_id, video_date)
            thumbnail_url = None
            time_lapse_items_count = len(time_lapse_items)

            if time_lapse_items_count > 0:
                time_lapse_items_selected = int(time_lapse_items_count / 2)
                time_lapse_item = time_lapse_items[time_lapse_items_selected]

                filename = time_lapse_item.get("filename")

                self.api.monitors.get(URL_TIME_LAPSE, identifier.monitor_id)

                thumbnail_base_url = self.api.build_url(URL_TIME_LAPSE, identifier.monitor_id)
                thumbnail_url = f"{thumbnail_base_url}/{video_date}/{filename}"

            item = BrowseMediaSource(
                domain=DOMAIN,
                identifier=f"{identifier.identifier}/{video_date}",
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
    async def _async_build_videos(self, identifier: MediaSourceItemIdentifier) -> list[BrowseMediaSource]:
        """Build list of media sources from Shinobi Video Server."""
        items: list[BrowseMediaSource] = []

        videos = await self.api.get_videos(identifier.monitor_id, identifier.day)

        if videos is None:
            _LOGGER.debug(f"No video files found for {identifier.identifier}")

        else:
            _LOGGER.debug(
                f"Building video directory, "
                f"Monitor: {identifier.monitor_id}, "
                f"Day: {identifier.day}, "
                f"Videos: {len(videos)}"
            )

            time_lapse_items = await self.api.async_get_time_lapse_images(identifier.monitor_id, identifier.day)
            time_lapse_items_count = len(time_lapse_items)

            for video in videos:
                video_time_iso = video.start_time_iso
                video_start_time = video.video_start_time.timestamp()
                video_end_time = video.video_end_time.timestamp()

                is_valid_file = video_end_time > video_start_time

                if is_valid_file:
                    video_start_time_tz = video.video_start_time.tzinfo.utcoffset(video.video_start_time)
                    tz_seconds = video_start_time_tz.total_seconds()

                    day = identifier.day

                    thumbnail_url = None

                    if time_lapse_items_count > 0:
                        for time_lapse_item in time_lapse_items:
                            time_lapse_item_time: str | None = time_lapse_item.get(TIME_LAPSE_TIME)

                            if time_lapse_item_time is not None:
                                item_time = get_date(time_lapse_item_time)
                                item_time_ts = item_time.timestamp() + tz_seconds

                                if video_end_time >= item_time_ts >= video_start_time:
                                    filename = time_lapse_item.get(TIME_LAPSE_FILE_NAME)

                                    thumbnail_base_url = self.api.build_url(URL_TIME_LAPSE, identifier.monitor_id)
                                    thumbnail_url = f"{thumbnail_base_url}/{day}/{filename}"

                                    break

                    item = BrowseMediaSource(
                        domain=DOMAIN,
                        identifier=f"{identifier.identifier}/{video_time_iso}/{video.extension}",
                        media_class=MediaClass.VIDEO,
                        media_content_type=MediaType.VIDEO,
                        title=video.start_time,
                        can_play=True,
                        can_expand=False,
                        thumbnail=thumbnail_url,
                    )

                    items.append(item)

            return items
