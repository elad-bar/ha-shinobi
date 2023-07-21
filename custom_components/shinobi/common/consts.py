from datetime import timedelta

import aiohttp

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PATH,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
)

DEFAULT_NAME = "Shinobi Video"
DOMAIN = "shinobi"

DEFAULT_PORT = 8080

DATA_KEYS = [CONF_HOST, CONF_PATH, CONF_PORT, CONF_SSL, CONF_USERNAME, CONF_PASSWORD]

DATA = f"{DOMAIN}_DATA"
LEGACY_KEY_FILE = f"{DOMAIN}.key"
CONFIGURATION_FILE = f"{DOMAIN}.config.json"

SIGNAL_MONITOR_DISCOVERED = f"{DOMAIN}_MONITOR_DISCOVERED_SIGNAL"
SIGNAL_MONITOR_ADDED = f"{DOMAIN}_MONITOR_ADDED_SIGNAL"
SIGNAL_MONITOR_UPDATED = f"{DOMAIN}_MONITOR_UPDATED_SIGNAL"
SIGNAL_MONITOR_TRIGGER = f"{DOMAIN}_MONITOR_TRIGGERED_SIGNAL"

SIGNAL_SERVER_DISCOVERED = f"{DOMAIN}_SERVER_DISCOVERED_SIGNAL"
SIGNAL_SERVER_ADDED = f"{DOMAIN}_SERVER_ADDED_SIGNAL"

SIGNAL_WS_STATUS = f"{DOMAIN}_WS_STATUS_SIGNAL"
SIGNAL_API_STATUS = f"{DOMAIN}_API_STATUS_SIGNAL"

MONITOR_SIGNALS = {True: SIGNAL_MONITOR_DISCOVERED, False: SIGNAL_MONITOR_UPDATED}
ADD_COMPONENT_SIGNALS = [SIGNAL_MONITOR_ADDED, SIGNAL_SERVER_ADDED]


PROTOCOLS = {True: "https", False: "http"}
WS_PROTOCOLS = {True: "wss", False: "ws"}

INVALID_TOKEN_SECTION = "https://github.com/elad-bar/ha-shinobi#invalid-token"

ENTRY_ID_CONFIG = "config"

DATA_KEY_CAMERA = "Camera"
DATA_KEY_MONITOR_MODE = "Mode"
DATA_KEY_MONITOR_STATUS = "Status"
DATA_KEY_MOTION = "Motion"
DATA_KEY_SOUND = "Sound"
DATA_KEY_MOTION_DETECTION = "Motion Detector"
DATA_KEY_SOUND_DETECTION = "Sound Detector"
DATA_KEY_ORIGINAL_STREAM = "Use Original Stream"

ATTR_IS_ON = "is_on"
ATTR_FRIENDLY_NAME = "friendly_name"
ATTR_START_TIME = "start_time"

ATTR_ENABLE = "enable"
ATTR_DISABLED = "disabled"

DEFAULT_ENABLE = False

WS_LAST_UPDATE = "last-update"

BLOCK_SIZE = 16

MQTT_QOS_0 = 0
MQTT_QOS_1 = 1

MQTT_MESSAGE_ENCODING = "utf-8"

ATTR_ATTRIBUTES = "attributes"
ATTR_ACTIONS = "actions"

STORAGE_DATA_KEY = "key"
STORAGE_DATA_LOCATING = "locating"

STORAGE_DATA_FILE_CONFIG = "config"

STORAGE_DATA_FILES = [STORAGE_DATA_FILE_CONFIG]

ACTION_ENTITY_TURN_ON = "turn_on"
ACTION_ENTITY_TURN_OFF = "turn_off"
ACTION_ENTITY_SELECT_OPTION = "select_option"

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

UPDATE_API_INTERVAL = timedelta(seconds=60)
HEARTBEAT_INTERVAL = timedelta(seconds=25)
TRIGGER_INTERVAL = timedelta(seconds=1)
WS_RECONNECT_INTERVAL = timedelta(seconds=30)
API_RECONNECT_INTERVAL = timedelta(seconds=30)
UPDATE_ENTITIES_INTERVAL = timedelta(seconds=1)

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
ATTR_STREAM_FPS = "fps"

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

TRIGGER_DEFAULT = {TRIGGER_STATE: False, TRIGGER_TIMESTAMP: 0}

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

SINGLE_FRAME_PS = 1

STORAGE_DATA_USE_ORIGINAL_STREAM = "useOriginalStream"

STORAGE_DATA_FILE_CONFIG = "config"

MEDIA_SOURCE_SPECIAL_DAYS = {0: "Today", 1: "Yesterday"}

CONF_SUPPORT_STREAM = "support_stream"

VERSION = "1.0.0"

URL_MONITORS = "{base_url}{api_key}/monitor/{group_id}"
URL_VIDEO_WALL = "{base_url}{api_key}/videoBrowser/{group_id}"
ATTR_FPS = "fps"

TRIGGER_STATE = "state"

REASON_MOTION = "motion"
REASON_SOUND = "soundChange"