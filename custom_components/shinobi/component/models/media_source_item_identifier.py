from __future__ import annotations

from ..helpers.const import *


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

    def to_dict(self):
        obj = {
            MEDIA_SOURCE_ITEM_IDENTIFIER_MODE: self.current_mode,
            MEDIA_SOURCE_ITEM_IDENTIFIER_KEY: self.identifier,
            MEDIA_SOURCE_ITEM_IDENTIFIER_CATEGORY: self.category,
            MEDIA_SOURCE_ITEM_IDENTIFIER_MONITOR_ID: self.monitor_id,
            MEDIA_SOURCE_ITEM_IDENTIFIER_DAY: self.day,
            MEDIA_SOURCE_ITEM_IDENTIFIER_VIDEO_TIME: self.video_time,
            MEDIA_SOURCE_ITEM_IDENTIFIER_VIDEO_EXTENSION: self.video_extension
        }

        return obj

    def __repr__(self):
        to_string = f"{self.to_dict()}"

        return to_string
