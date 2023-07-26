from datetime import timedelta

import aiohttp

from homeassistant.components.binary_sensor import BinarySensorDeviceClass

DEFAULT_NAME = "Shinobi Video"
DOMAIN = "shinobi"

DEFAULT_PORT = 8080
CONF_TITLE = "title"

LEGACY_KEY_FILE = f"{DOMAIN}.key"
CONFIGURATION_FILE = f"{DOMAIN}.config.json"

SIGNAL_MONITOR_DISCOVERED = f"{DOMAIN}_MONITOR_DISCOVERED_SIGNAL"
SIGNAL_MONITOR_ADDED = f"{DOMAIN}_MONITOR_ADDED_SIGNAL"
SIGNAL_MONITOR_UPDATED = f"{DOMAIN}_MONITOR_UPDATED_SIGNAL"
SIGNAL_MONITOR_STATUS_CHANGED = f"{DOMAIN}_MONITOR_STATUS_SIGNAL"
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

DATA_KEY_CAMERA = "camera"
DATA_KEY_MONITOR_MODE = "mode"
DATA_KEY_MONITOR_STATUS = "status"
DATA_KEY_MOTION = "motion"
DATA_KEY_SOUND = "sound"
DATA_KEY_MOTION_DETECTION = "motion_detector"
DATA_KEY_SOUND_DETECTION = "sound_detector"
DATA_KEY_ORIGINAL_STREAM = "use_original_stream"
DATA_KEY_PROXY_RECORDINGS = "use_proxy_for_recordings"

ATTR_IS_ON = "is_on"

ATTR_DISABLED = "disabled"

ATTR_ATTRIBUTES = "attributes"
ATTR_ACTIONS = "actions"

STORAGE_DATA_KEY = "key"

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

UPDATE_API_INTERVAL = timedelta(seconds=30)
HEARTBEAT_INTERVAL = timedelta(seconds=25)
TRIGGER_INTERVAL = timedelta(seconds=1)
WS_RECONNECT_INTERVAL = timedelta(seconds=30)
API_RECONNECT_INTERVAL = timedelta(seconds=30)
UPDATE_ENTITIES_INTERVAL = timedelta(seconds=1)

MAX_MSG_SIZE = 0
DISCONNECT_INTERVAL = 5

URL_PARAMETER_BASE_URL = "base_url"
URL_PARAMETER_API_KEY = "api_key"
URL_PARAMETER_GROUP_ID = "group_id"
URL_PARAMETER_MONITOR_ID = "monitor_id"
URL_PARAMETER_VERSION = "version"

BASE_PROXY_URL = f"/api/{DOMAIN}"
PROXY_PREFIX = f"/api/{DOMAIN}/{{entry_id:.+}}"

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
ATTR_MONITOR_STATUS_CODE = "code"
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

INVALID_JSON_FORMATS = {
    '":,"': '": null,"',
    '":.': '": 0.',
    '":,}': '": null}',
    '":}': '": null}',
}

VIDEO_DETAILS_TIME = "time"
VIDEO_DETAILS_EXTENSION = "ext"
VIDEO_DETAILS_TIME_INVALID_CHAR = "z"

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

MEDIA_SOURCE_SPECIAL_DAYS = {0: "Today", 1: "Yesterday"}

MONITOR_STATUS_CODE_DISABLED = "0"
MONITOR_STATUS_CODE_STARTING = "1"
MONITOR_STATUS_CODE_WATCHING = "2"
MONITOR_STATUS_CODE_RECORDING = "3"
MONITOR_STATUS_CODE_RESTARTING = "4"
MONITOR_STATUS_CODE_STOPPED = "5"
MONITOR_STATUS_CODE_IDLE = "6"
MONITOR_STATUS_CODE_DIED = "7"
MONITOR_STATUS_CODE_STOPPING = "8"
MONITOR_STATUS_CODE_STARTED = "9"

MONITOR_STATUS = {
    MONITOR_STATUS_CODE_DISABLED: {
        "name": "disabled",
        "is_online": False,
        "is_recording": False,
        "icon": None,
        "sensors": False,
    },
    MONITOR_STATUS_CODE_STARTING: {
        "name": "starting",
        "is_online": False,
        "is_recording": False,
        "icon": None,
        "sensors": False,
    },
    MONITOR_STATUS_CODE_WATCHING: {
        "name": "watching",
        "is_online": True,
        "is_recording": False,
        "icon": None,
        "sensors": True,
    },
    MONITOR_STATUS_CODE_RECORDING: {
        "name": "recording",
        "is_online": True,
        "is_recording": True,
        "icon": None,
        "sensors": True,
    },
    MONITOR_STATUS_CODE_RESTARTING: {
        "name": "restarting",
        "is_online": False,
        "is_recording": False,
        "icon": None,
        "sensors": False,
    },
    MONITOR_STATUS_CODE_STOPPED: {
        "name": "stopped",
        "is_online": False,
        "is_recording": False,
        "icon": None,
        "sensors": False,
    },
    MONITOR_STATUS_CODE_IDLE: {
        "name": "idle",
        "is_online": False,
        "is_recording": False,
        "icon": None,
        "sensors": False,
    },
    MONITOR_STATUS_CODE_DIED: {
        "name": "died",
        "is_online": False,
        "is_recording": False,
        "icon": None,
        "sensors": False,
    },
    MONITOR_STATUS_CODE_STOPPING: {
        "name": "stopping",
        "is_online": False,
        "is_recording": False,
        "icon": None,
        "sensors": False,
    },
    MONITOR_STATUS_CODE_STARTED: {
        "name": "started",
        "is_online": True,
        "is_recording": False,
        "icon": None,
        "sensors": True,
    },
}
