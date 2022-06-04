"""Expose Radio Browser as a media source."""
from __future__ import annotations

from abc import ABC
import logging

from homeassistant.components.media_player.const import (
    MEDIA_CLASS_CHANNEL,
    MEDIA_CLASS_DIRECTORY,
    MEDIA_CLASS_VIDEO,
    MEDIA_TYPE_VIDEO,
)
from homeassistant.components.media_source.models import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .component.api.shinobi_api import ShinobiApi
from .component.helpers import get_ha
from .component.helpers.const import *
from .component.models.video_data import VideoData

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

    ha = None

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize CameraMediaSource."""
        _LOGGER.debug(f"Loading Shinobi Media Source")

        super().__init__(DOMAIN)
        self.hass = hass
        self.entry = entry

        self.hass = hass

        self.ha = get_ha(self.hass, entry.entry_id)

    @property
    def api(self) -> ShinobiApi:
        return self.ha.api

    @property
    def videos(self) -> list[VideoData] | None:
        """Return the radio browser."""
        return self.api.video_list

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Resolve selected Video to a streaming URL."""
        url, _, mime_type = item.identifier.partition("|")

        return PlayMedia(url, mime_type)

    async def async_browse_media(
        self,
        item: MediaSourceItem,
    ) -> BrowseMediaSource:
        """Return media."""
        _LOGGER.debug(f"Browse media: {item.identifier if item.identifier else 'Root'}")

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=None,
            media_class=MEDIA_CLASS_CHANNEL,
            media_content_type=MEDIA_TYPE_VIDEO,
            title=self.entry.title,
            can_play=False,
            can_expand=True,
            children_media_class=MEDIA_CLASS_DIRECTORY,
            children=[
                *await self._async_build_by_monitor(item),
            ],
        )

    @callback
    def _async_build_videos(self, videos: list[VideoData]) -> list[BrowseMediaSource]:
        """Build list of media sources from Shinobi Video Server."""
        items: list[BrowseMediaSource] = []

        for video in videos:
            _LOGGER.debug(video)

            identifier = self.api.build_url(video.identifier)

            item = BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=identifier,
                    media_class=MEDIA_CLASS_VIDEO,
                    media_content_type=video.mime_type,
                    title=video.title,
                    can_play=True,
                    can_expand=False,
                    # thumbnail=identifier,
                )

            items.append(item)

        return items

    async def _async_build_by_monitor(
        self, item: MediaSourceItem
    ) -> list[BrowseMediaSource]:
        """Handle browsing radio stations by country."""
        video_list = self.api.video_list
        result: list[BrowseMediaSource] = []

        category, _, monitor_id = (item.identifier or "").partition("/")

        if monitor_id:
            videos = []

            for video in video_list:
                if video.monitor_id == monitor_id:
                    videos.append(video)

            result = self._async_build_videos(videos)

            _LOGGER.info(
                f"Build media source list for monitor: {monitor_id}, "
                f"Total videos: {len(video_list)}, "
                f"Relevant videos: {len(videos)}, "
                f"Media items: {len(result)}"
            )

        else:
            # We show monitor in the root additionally, when there is no item
            if not item.identifier or category == DOMAIN_CAMERA:
                for monitor_id in self.api.monitors:
                    monitor = self.api.monitors.get(monitor_id)

                    item = BrowseMediaSource(
                        domain=DOMAIN,
                        identifier=f"{DOMAIN_CAMERA}/{monitor.id}",
                        media_class=MEDIA_CLASS_DIRECTORY,
                        media_content_type=MEDIA_TYPE_VIDEO,
                        title=monitor.name,
                        can_play=False,
                        can_expand=True,
                        thumbnail=self.api.build_url(monitor.snapshot),
                    )

                    result.append(item)

        return result
