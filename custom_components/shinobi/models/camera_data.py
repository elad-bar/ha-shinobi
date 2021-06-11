import json

from ..helpers.const import *


class CameraData:
    monitorId: str
    name: str
    details: dict
    has_audio: bool
    has_audio_detector: bool
    has_motion_detector: bool
    fps: int
    jpeg_api_enabled: bool

    def __init__(self, camera):
        self.monitorId = camera.get(ATTR_CAMERA_MONITOR_ID)
        self.name = camera.get(ATTR_CAMERA_NAME)
        self.status = camera.get(ATTR_CAMERA_STATUS)
        self.snapshot = camera.get(ATTR_CAMERA_SNAPSHOT)
        self.streams = camera.get(ATTR_CAMERA_STREAMS)
        self.details = camera
        self.jpeg_api_enabled = self.snapshot is not None and self.snapshot != ""

        monitor_details = camera.get("details", {})

        fps = monitor_details.get(ATTR_CAMERA_DETAILS_FPS, "1")

        if "." in fps:
            fps = fps.split(".")[0]

        self.fps = 1 if fps == "" else int(fps)
        self.has_audio = monitor_details.get(ATTR_CAMERA_DETAILS_AUDIO_CODEC, "no") != "no"
        self.has_audio_detector = monitor_details.get(ATTR_CAMERA_DETAILS_DETECTOR_AUDIO, "0") != "0"
        self.has_motion_detector = monitor_details.get(ATTR_CAMERA_DETAILS_DETECTOR, "0") != "0"

    def __repr__(self):
        obj = {
            ATTR_CAMERA_MONITOR_ID: self.monitorId,
            ATTR_CAMERA_NAME: self.name,
            ATTR_CAMERA_STATUS: self.name,
            ATTR_CAMERA_SNAPSHOT: self.snapshot,
            ATTR_CAMERA_STREAMS: self.streams,
            ATTR_CAMERA_DETAILS: self.details,
            MOTION_DETECTION: self.has_motion_detector,
            SOUND_DETECTION: self.has_audio_detector,
            TRIGGER_PLUG_DB: self.has_audio,
            ATTR_FPS: self.fps
        }

        to_string = f"{obj}"

        return to_string
