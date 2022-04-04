"""
Support for Shinobi Video.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.shinobi/
"""
from datetime import timedelta

from homeassistant.components.binary_sensor import (
    DOMAIN as DOMAIN_BINARY_SENSOR,
    BinarySensorDeviceClass,
)
from homeassistant.components.camera import DOMAIN as DOMAIN_CAMERA
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PATH,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    STATE_OFF,
    STATE_ON,
)

CONF_SUPPORT_STREAM = "support_stream"
CONF_USE_ORIGINAL_STREAM = "use_original_stream"

CONF_ARR = [CONF_USERNAME, CONF_PASSWORD, CONF_HOST, CONF_PORT, CONF_SSL, CONF_PATH, CONF_USE_ORIGINAL_STREAM]

ENTRY_PRIMARY_KEY = CONF_NAME

CONFIG_FLOW_DATA = "config_flow_data"
CONFIG_FLOW_OPTIONS = "config_flow_options"
CONFIG_FLOW_INIT = "config_flow_init"

VERSION = "1.0.0"

DOMAIN = "shinobi"
PASSWORD_MANAGER = f"pm_{DOMAIN}"
DATA = f"data_{DOMAIN}"
DATA_API = f"{DATA}_API"
DATA_HA = f"{DATA}_HA"
DEFAULT_NAME = "Shinobi Video"
DEFAULT_PORT = 8080

DOMAIN_KEY_FILE = f"{DOMAIN}.key"
JSON_DATA_FILE = f"custom_components/{DOMAIN}/data/[NAME].json"

SCAN_INTERVAL_WS_TIMEOUT = timedelta(seconds=60)

SHINOBI_WS_ENDPOINT = "socket.io/?EIO=[VERSION]&transport=websocket"

SHINOBI_WS_CONNECTION_ESTABLISHED_MESSAGE = "0"
SHINOBI_WS_PING_MESSAGE = "2"
SHINOBI_WS_PONG_MESSAGE = "3"
SHINOBI_WS_CONNECTION_READY_MESSAGE = "40"
SHINOBI_WS_ACTION_MESSAGE = "42"

AUTHENTICATION_BASIC = "basic"

DEFAULT_ICON = "mdi:alarm-light"
ATTR_FRIENDLY_NAME = "friendly_name"

PROTOCOLS = {True: "https", False: "http"}
WS_PROTOCOLS = {True: "wss", False: "ws"}

SCAN_INTERVAL = timedelta(seconds=60)
HEARTBEAT_INTERVAL_SECONDS = timedelta(seconds=25)
TRIGGER_INTERVAL = timedelta(seconds=1)

DEFAULT_FORCE_UPDATE = False

MAX_MSG_SIZE = 0
DISCONNECT_INTERVAL = 5
RECONNECT_INTERVAL = 30

DISCOVERY = f"{DOMAIN}_discovery"

UPDATE_SIGNAL_CAMERA = f"{DOMAIN}_{DOMAIN_CAMERA}_UPDATE_SIGNAL"
UPDATE_SIGNAL_BINARY_SENSOR = f"{DOMAIN}_{DOMAIN_BINARY_SENSOR}_UPDATE_SIGNAL"

SUPPORTED_DOMAINS = [DOMAIN_BINARY_SENSOR, DOMAIN_CAMERA]

SIGNALS = {
    DOMAIN_BINARY_SENSOR: UPDATE_SIGNAL_BINARY_SENSOR,
    DOMAIN_CAMERA: UPDATE_SIGNAL_CAMERA,
}

ENTITY_ID = "id"
ENTITY_NAME = "name"
ENTITY_STATE = "state"
ENTITY_ATTRIBUTES = "attributes"
ENTITY_ICON = "icon"
ENTITY_UNIQUE_ID = "unique-id"
ENTITY_BINARY_SENSOR_DEVICE_CLASS = "binary-sensor-device-class"
ENTITY_DEVICE_NAME = "device-name"
ENTITY_CAMERA_DETAILS = "camera-details"
ENTITY_DISABLED = "disabled"

ENTITY_STATUS = "entity-status"
ENTITY_STATUS_EMPTY = None
ENTITY_STATUS_READY = f"{ENTITY_STATUS}-ready"
ENTITY_STATUS_CREATED = f"{ENTITY_STATUS}-created"

CONF_CONTENT_TYPE = "content_type"
CONF_LIMIT_REFETCH_TO_URL_CHANGE = "limit_refetch_to_url_change"
CONF_STILL_IMAGE_URL = "still_image_url"
CONF_STREAM_SOURCE = "stream_source"
CONF_FRAMERATE = "framerate"
CONF_MOTION_DETECTION = "motion_detection"

URL_LOGIN = "?json=true"
URL_MONITORS = "[AUTH_TOKEN]/monitor/[GROUP_ID]"
URL_API_KEYS = "[AUTH_TOKEN]/api/[GROUP_ID]/list"
URL_SOCKET_IO_V4 = "libs/js/socket.io.min.js"

RESPONSE_CHECK = {
    URL_LOGIN: True,
    URL_MONITORS: False,
    URL_API_KEYS: True
}

AUTH_TOKEN = "[AUTH_TOKEN]"
GROUP_ID = "[GROUP_ID]"
MONITOR_ID = "[MONITOR_ID]"

LOGIN_USERNAME = "mail"
LOGIN_PASSWORD = "pass"

DEFAULT_ACCESS_DETAILS = {
                "auth_socket": False,
                "get_monitors": True,
                "control_monitors": False,
                "get_logs": False,
                "watch_stream": True,
                "watch_snapshot": True,
                "watch_videos": True,
                "delete_videos": False
            }

ATTR_CAMERA_MONITOR_ID = "mid"
ATTR_CAMERA_GROUP_ID = "ke"
ATTR_CAMERA_NAME = "name"
ATTR_CAMERA_STATUS = "status"
ATTR_ORIGINAL_STREAM = "auto_host"
ATTR_STREAM_PASSWORD = "mpass"
ATTR_STREAM_USERNAME = "muser"
ATTR_CAMERA_SNAPSHOT = "snapshot"
ATTR_CAMERA_STREAMS = "streams"
ATTR_CAMERA_DETAILS = "details"
ATTR_CAMERA_DETAILS_FPS = "stream_fps"
ATTR_CAMERA_DETAILS_AUDIO_CODEC = "acodec"
ATTR_CAMERA_DETAILS_DETECTOR = "detector"
ATTR_CAMERA_DETAILS_DETECTOR_AUDIO = "detector_audio"
ATTR_CAMERA_MODE = "mode"
ATTR_FPS = "fps"

STREAM_PROTOCOL_SUFFIX = "://"

CAMERA_ATTRIBUTES = {
    "status": "Status",
    "mode": "Mode",
    "type": "Type"
}

CAMERA_DETAILS_ATTRIBUTES = {
    ATTR_CAMERA_DETAILS_FPS: ATTR_FPS
}

TRIGGER_STARTS_WITH = "[\"f\",{\"f\":\""

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
    REASON_SOUND: BinarySensorDeviceClass.SOUND
}

SENSOR_AUTO_OFF_INTERVAL = {
    BinarySensorDeviceClass.MOTION: 20,
    BinarySensorDeviceClass.SOUND: 10
}

TRIGGER_DEFAULT = {
    TRIGGER_STATE: STATE_OFF
}

BINARY_SENSOR_ATTRIBUTES = []

INVALID_JSON_FORMATS = {
    "\":,\"": "\": null,\"",
    "\":,}": "\": null}"
}
