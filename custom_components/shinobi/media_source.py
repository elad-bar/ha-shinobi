"""Expose Radio Browser as a media source."""
from __future__ import annotations

from datetime import datetime
import logging
import mimetypes
from typing import List

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

from . import get_ha
from .api.shinobi_api import ShinobiApi
from .helpers.const import *

_LOGGER = logging.getLogger(__name__)


async def async_get_media_source(hass: HomeAssistant) -> ShinobiMediaSource:
    """Set up Radio Browser media source."""
    # Shinobi Video browser support only a single config entry
    entries = hass.config_entries.async_entries(DOMAIN)

    for entry in entries:
        return ShinobiMediaSource(hass, entry)


class ShinobiMediaSource(MediaSource):
    """Provide Radio stations as media sources."""

    name = MEDIA_BROWSER_NAME

    hass: HomeAssistant = None

    ha = None
    api: ShinobiApi = None

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize CameraMediaSource."""
        _LOGGER.debug(f"Loading Shinobi Media Source")

        super().__init__(DOMAIN)
        self.hass = hass
        self.entry = entry

        self.hass = hass

        self.ha = get_ha(self.hass, entry.entry_id)
        self.api = self.ha.api

    @property
    def videos(self) -> List[dict] | None:
        """Return the radio browser."""
        return self.api.video_list

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Resolve selected Radio station to a streaming URL."""
        url = item.identifier
        mime_type = self._async_get_video_mime_type(url)

        _LOGGER.info(f"Starting to play video, URL: {url}")

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
                *await self._async_build_by_camera(item),
            ],
        )

    @callback
    @staticmethod
    def _async_get_video_mime_type(url: str) -> str | None:
        """Determine mime type of video."""
        url_parts = url.split(".")
        ext = url_parts[len(url_parts) - 1]

        mime_type = CODEC_TO_MIMETYPE.get(ext)

        if not mime_type:
            mime_type, _ = mimetypes.guess_type(url)

        if not mime_type:
            _LOGGER.warning(f"Mime Type for {url} was not found")

        return mime_type

    @callback
    def _async_build_videos(self, camera_name: str, videos: list[dict]) -> list[BrowseMediaSource]:
        """Build list of media sources from Shinobi Video Server."""
        items: list[BrowseMediaSource] = []

        for video in videos:
            timestamp_str = video.get(VIDEO_DETAILS_TIME)
            timestamp = datetime.fromisoformat(timestamp_str)
            timestamp_formatted = datetime.strftime(timestamp, VIDEO_DETAILS_TIME_FORMAT)

            title = f"{camera_name} {timestamp_formatted}"

            action_url = video.get(VIDEO_DETAILS_URL)
            identifier = f"{self.api.base_url}{action_url[1:]}"

            mime_type = self._async_get_video_mime_type(identifier)

            if not mime_type:
                continue

            items.append(
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=identifier,
                    media_class=MEDIA_CLASS_VIDEO,
                    media_content_type=mime_type,
                    title=title,
                    can_play=True,
                    can_expand=False,
                    # thumbnail=station.favicon,
                )
            )

        return items

    def _get_camera_mapping(self):
        camera_list = self.api.camera_list
        result = {}

        for camera in camera_list:
            result[camera.monitorId] = camera

        return result

    async def _async_build_by_camera(
        self, item: MediaSourceItem
    ) -> list[BrowseMediaSource]:
        """Handle browsing radio stations by country."""
        camera_mapping = self._get_camera_mapping()
        video_list = self.api.video_list
        result: list[BrowseMediaSource] = []

        category, _, camera_id = (item.identifier or "").partition("/")

        if camera_id:
            videos = []
            camera = camera_mapping.get(camera_id)

            for video in video_list:
                mid = video.get(VIDEO_DETAILS_MONITOR_ID)

                if mid == camera_id:
                    videos.append(video)

            result = self._async_build_videos(camera.name, videos)

            _LOGGER.debug(
                f"Build media source list for camera: {camera_id}, "
                f"Total videos: {len(video_list)}, "
                f"Relevant videos: {len(videos)}, "
                f"Media items: {len(result)}"
            )

        else:
            # We show camera in the root additionally, when there is no item
            if not item.identifier or category == DOMAIN_CAMERA:
                for camera_id in camera_mapping.keys():
                    camera = camera_mapping.get(camera_id)
                    snapshot = f"{self.api.base_url}{camera.snapshot[1:]}"

                    item = BrowseMediaSource(
                        domain=DOMAIN,
                        identifier=f"{DOMAIN_CAMERA}/{camera_id}",
                        media_class=MEDIA_CLASS_DIRECTORY,
                        media_content_type=MEDIA_TYPE_VIDEO,
                        title=camera.name,
                        can_play=False,
                        can_expand=True,
                        thumbnail=snapshot,
                    )

                    result.append(item)

        return result
