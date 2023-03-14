"""
Support for Shinobi Video.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.shinobi/
"""
from datetime import timedelta

import aiohttp

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import STATE_OFF

from ...configuration.helpers.const import DEFAULT_NAME
from ...core.helpers.const import ATTR_STREAM_FPS

CONF_SUPPORT_STREAM = "support_stream"

VERSION = "1.0.0"

API_DATA_MONITORS = "monitors"
API_DATA_USER_ID = "user-id"
API_DATA_GROUP_ID = "group-id"
API_DATA_API_KEY = "api-key"
API_DATA_LAST_UPDATE = "last-update"
API_DATA_SOCKET_IO_VERSION = "socket-io-version"
API_DATA_DAYS = "days"

MEDIA_BROWSER_NAME = f"{DEFAULT_NAME} Browser"

WS_TIMEOUT = timedelta(seconds=60)
WS_COMPRESSION_DEFLATE = 15

WS_CLOSING_MESSAGE = [
    aiohttp.WSMsgType.CLOSE,
    aiohttp.WSMsgType.CLOSED,
    aiohttp.WSMsgType.CLOSING,
]

SHINOBI_WS_CONNECTION_ESTABLISHED_MESSAGE = "0"
SHINOBI_WS_PING_MESSAGE = "2"
SHINOBI_WS_PONG_MESSAGE = "3"
SHINOBI_WS_CONNECTION_READY_MESSAGE = "40"
SHINOBI_WS_ACTION_MESSAGE = "42"

DEFAULT_ICON = "mdi:alarm-light"
ATTR_FRIENDLY_NAME = "friendly_name"

SCAN_INTERVAL = timedelta(seconds=60)
REPAIR_INTERVAL = timedelta(seconds=60)
HEARTBEAT_INTERVAL_SECONDS = timedelta(seconds=25)
TRIGGER_INTERVAL = timedelta(seconds=1)
WS_RECONNECT_INTERVAL = timedelta(seconds=30)

MAX_MSG_SIZE = 0
DISCONNECT_INTERVAL = 5
RECONNECT_INTERVAL = 30
REPAIR_REPAIR_RECORD_INTERVAL = 5
REPAIR_UPDATE_STATUS_INTERVAL = 10
REPAIR_UPDATE_STATUS_ATTEMPTS = 12  # Up to 2 minutes of retries

URL_PARAMETER_BASE_URL = "base_url"
URL_PARAMETER_API_KEY = "api_key"
URL_PARAMETER_GROUP_ID = "group_id"
URL_PARAMETER_MONITOR_ID = "monitor_id"
URL_PARAMETER_VERSION = "version"

URL_LOGIN = "{base_url}?json=true"

URL_SOCKET_IO_V4 = "{base_url}assets/vendor/js/socket.io.min.js"
SHINOBI_WS_ENDPOINT = "{base_url}socket.io/?EIO={version}&transport=websocket"

URL_MONITORS = "{base_url}{api_key}/monitor/{group_id}"
URL_VIDEOS = "{base_url}{api_key}/videos/{group_id}/{monitor_id}"
URL_VIDEO_WALL = "{base_url}{api_key}/videoBrowser/{group_id}"
URL_VIDEO_WALL_MONITOR = f"{URL_VIDEO_WALL}/{{monitor_id}}"
URL_API_KEYS = "{base_url}{api_key}/api/{group_id}/list"
URL_UPDATE_MONITOR = "{base_url}{api_key}/configureMonitor/{group_id}/{monitor_id}"
URL_TIME_LAPSE = "{base_url}{api_key}/timelapse/{group_id}/{monitor_id}"

URL_UPDATE_MODE = f"{URL_MONITORS}/{{monitor_id}}"

LOGIN_USERNAME = "mail"
LOGIN_PASSWORD = "pass"

ATTR_MONITOR_ID = "mid"
ATTR_MONITOR_GROUP_ID = "ke"
ATTR_MONITOR_NAME = "name"
ATTR_MONITOR_STATUS = "status"
ATTR_ORIGINAL_STREAM = "auto_host"
ATTR_STREAM_PASSWORD = "mpass"
ATTR_STREAM_USERNAME = "muser"
ATTR_MONITOR_SNAPSHOT = "snapshot"
ATTR_MONITOR_STREAMS = "streams"
ATTR_MONITOR_DETAILS = "details"
ATTR_MONITOR_DETAILS_AUDIO_CODEC = "acodec"
ATTR_MONITOR_DETAILS_DETECTOR = "detector"
ATTR_MONITOR_DETAILS_DETECTOR_AUDIO = "detector_audio"
ATTR_MONITOR_MODE = "mode"
ATTR_FPS = "fps"
ATTR_DISABLED = "disabled"

STREAM_PROTOCOL_SUFFIX = "://"

MONITOR_ATTRIBUTES = {"status": "Status", "mode": "Mode", "type": "Type"}

MONITOR_DETAILS_ATTRIBUTES = {ATTR_STREAM_FPS: ATTR_FPS}

TRIGGER_STARTS_WITH = '["f",{"f":"'

TRIGGER_PLUG = "plug"
TRIGGER_NAME = "name"
TRIGGER_DETAILS = "details"
TRIGGER_DETAILS_PLUG = "plug"
TRIGGER_DETAILS_REASON = "reason"

TRIGGER_PLUG_DB = "audio"

TRIGGER_STATE = "state"
TRIGGER_TIMESTAMP = "timestamp"
TRIGGER_TOPIC = "topic"

MOTION_DETECTION = "Motion Detection"
SOUND_DETECTION = "Sound Detection"

SHINOBI_EVENT = "shinobi/"

REASON_MOTION = "motion"
REASON_SOUND = "soundChange"

PLUG_SENSOR_TYPE = {
    REASON_MOTION: BinarySensorDeviceClass.MOTION,
    REASON_SOUND: BinarySensorDeviceClass.SOUND,
}

SENSOR_AUTO_OFF_INTERVAL = {
    BinarySensorDeviceClass.MOTION: 20,
    BinarySensorDeviceClass.SOUND: 10,
}

TRIGGER_DEFAULT = {TRIGGER_STATE: STATE_OFF}

BINARY_SENSOR_ATTRIBUTES = []

INVALID_JSON_FORMATS = {
    '":,"': '": null,"',
    '":.': '": 0.',
    '":,}': '": null}',
    '":}': '": null}',
}

VIDEO_DETAILS_MONITOR_ID = "mid"
VIDEO_DETAILS_TIME = "time"
VIDEO_DETAILS_END_TIME = "end"
VIDEO_DETAILS_URL = "actionUrl"
VIDEO_DETAILS_EXTENSION = "ext"
VIDEO_DETAILS_TIME_INVALID_CHAR = "z"
VIDEO_DETAILS_MIME_TYPE = "mime-type"
VIDEO_DETAILS_IDENTIFIER = "identifier"
VIDEO_DETAILS_TITLE = "title"

VIDEO_DETAILS_TIME_FORMAT = "%X"
VIDEO_DETAILS_TIME_ISO_FORMAT = "%H-%M-%S"
VIDEO_DETAILS_DATE_FORMAT = "%x"
DATE_FORMAT_WEEKDAY = "%A"
MEDIA_SOURCE_ITEM_IDENTIFIER_MODE = "mode"
MEDIA_SOURCE_ITEM_IDENTIFIER_KEY = "key"
MEDIA_SOURCE_ITEM_IDENTIFIER_CATEGORY = "category"
MEDIA_SOURCE_ITEM_IDENTIFIER_MONITOR_ID = "monitor"
MEDIA_SOURCE_ITEM_IDENTIFIER_DAY = "day"
MEDIA_SOURCE_ITEM_IDENTIFIER_VIDEO_TIME = "video_time"
MEDIA_SOURCE_ITEM_IDENTIFIER_VIDEO_EXTENSION = "video_extension"

TIME_LAPSE_FILE_NAME = "filename"
TIME_LAPSE_TIME = "time"

MONITOR_MODE_STOP = "stop"
MONITOR_MODE_START = "start"
MONITOR_MODE_RECORD = "record"

ICON_MONITOR_MODES = {
    MONITOR_MODE_STOP: "mdi:cctv-off",
    MONITOR_MODE_START: "mdi:cctv",
    MONITOR_MODE_RECORD: "mdi:record-rec",
}

STORAGE_DATA_USE_ORIGINAL_STREAM = "useOriginalStream"

STORAGE_DATA_FILE_CONFIG = "config"

STORAGE_DATA_FILES = [STORAGE_DATA_FILE_CONFIG]

MEDIA_SOURCE_SPECIAL_DAYS = {0: "Today", 1: "Yesterday"}
