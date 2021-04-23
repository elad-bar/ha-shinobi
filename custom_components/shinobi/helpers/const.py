"""
Support for Shinobi Video.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.shinobi/
"""
from datetime import timedelta

from homeassistant.components.binary_sensor import DOMAIN as DOMAIN_BINARY_SENSOR
from homeassistant.components.camera import DOMAIN as DOMAIN_CAMERA
from homeassistant.components.mqtt import DATA_MQTT
from homeassistant.components.switch import DOMAIN as DOMAIN_SWITCH
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    STATE_OFF,
    STATE_ON,
)

CONF_LOG_LEVEL = "log_level"

CONF_SUPPORT_STREAM = "support_stream"

CONF_ARR = [CONF_USERNAME, CONF_PASSWORD, CONF_HOST, CONF_PORT, CONF_SSL]

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
DATA_HA_ENTITIES = f"{DATA}_HA_Entities"
DEFAULT_NAME = "Shinobi Video"
DEFAULT_PORT = 8080

DOMAIN_KEY_FILE = f"{DOMAIN}.key"
JSON_DATA_FILE = f"custom_components/{DOMAIN}/data/[NAME].json"

DOMAIN_LOGGER = "logger"
SERVICE_SET_LEVEL = "set_level"

SHINOBI_AUTH_ERROR = "Authorization required"

AUTHENTICATION_BASIC = "basic"

NOTIFICATION_ID = f"{DOMAIN}_notification"
NOTIFICATION_TITLE = f"{DEFAULT_NAME} Setup"

DEFAULT_ICON = "mdi:alarm-light"
SCHEDULE_ICON = "mdi:calendar-clock"
ATTR_FRIENDLY_NAME = "friendly_name"

PROTOCOLS = {True: "https", False: "http"}

SCAN_INTERVAL = timedelta(seconds=60)

DEFAULT_FORCE_UPDATE = False

SENSOR_MAIN_NAME = "Main"

MQTT_ALL_TOPIC = "shinobi"
DEFAULT_QOS = 0

ATTR_STATUS = [
]

DISCOVERY = f"{DOMAIN}_discovery"
DISCOVERY_BINARY_SENSOR = f"{DISCOVERY}_{DOMAIN_BINARY_SENSOR}"
DISCOVERY_CAMERA = f"{DISCOVERY}_{DOMAIN_CAMERA}"
DISCOVERY_SWITCH = f"{DISCOVERY}_{DOMAIN_SWITCH}"

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
ENTITY_EVENT = "event-type"
ENTITY_TOPIC = "topic"
ENTITY_DEVICE_CLASS = "device-class"
ENTITY_DEVICE_NAME = "device-name"
ENTITY_CAMERA_DETAILS = "camera-details"
ENTITY_BINARY_SENSOR_TYPE = "binary-sensor-type"
ENTITY_DISABLED = "disabled"


ENTITY_STATUS = "entity-status"
ENTITY_STATUS_EMPTY = None
ENTITY_STATUS_READY = f"{ENTITY_STATUS}-ready"
ENTITY_STATUS_CREATED = f"{ENTITY_STATUS}-created"

CONF_CLEAR_CREDENTIALS = "clear-credentials"

DOMAIN_LOAD = "load"
DOMAIN_UNLOAD = "unload"

CONF_CONTENT_TYPE = "content_type"
CONF_LIMIT_REFETCH_TO_URL_CHANGE = "limit_refetch_to_url_change"
CONF_STILL_IMAGE_URL = "still_image_url"
CONF_STREAM_SOURCE = "stream_source"
CONF_FRAMERATE = "framerate"

LOG_LEVEL_DEFAULT = "Default"
LOG_LEVEL_DEBUG = "Debug"
LOG_LEVEL_INFO = "Info"
LOG_LEVEL_WARNING = "Warning"
LOG_LEVEL_ERROR = "Error"

LOG_LEVELS = [
    LOG_LEVEL_DEFAULT,
    LOG_LEVEL_DEBUG,
    LOG_LEVEL_INFO,
    LOG_LEVEL_WARNING,
    LOG_LEVEL_ERROR,
]

URL_LOGIN = "?json=true"
URL_MONITORS = "[AUTH_TOKEN]/monitor/[GROUP_ID]"
URL_API_KEYS = "[AUTH_TOKEN]/api/[GROUP_ID]/list"

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
LOGIN_FUNCTION = "function"
LOGIN_DASH = "dash"

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
ATTR_CAMERA_TYPE = "type"
ATTR_CAMERA_EXTENSION = "ext"
ATTR_CAMERA_PROTOCOL = "protocol"
ATTR_CAMERA_HOST = "host"
ATTR_CAMERA_PATH = "path"
ATTR_CAMERA_PORT = "port"
ATTR_CAMERA_MODE = "mode"
ATTR_CAMERA_STATUS = "status"
ATTR_CAMERA_SNAPSHOT = "snapshot"
ATTR_CAMERA_STREAMS = "streams"
ATTR_CAMERA_DETAILS = "details"
ATTR_CAMERA_DETAILS_FPS = "stream_fps"
ATTR_CAMERA_DETAILS_AUDIO_CODEC = "acodec"
ATTR_CAMERA_DETAILS_DETECTOR = "detector"
ATTR_CAMERA_DETAILS_DETECTOR_AUDIO = "detector_audio"
ATTR_FPS = "fps"

CAMERA_ATTRIBUTES = {
    "status": "Status",
    "mode": "Mode",
    "type": "Type"
}

CAMERA_DETAILS_ATTRIBUTES = {
    ATTR_CAMERA_DETAILS_FPS: ATTR_FPS
}

TRIGGER_NAME = "name"
TRIGGER_DETAILS = "details"
TRIGGER_DETAILS_PLUG = "plug"
TRIGGER_DETAILS_REASON = "reason"
TRIGGER_DETAILS_MATRICES = "matrices"
TRIGGER_DETAILS_MATRICES_TAG = "tag"

TRIGGER_PLUG_YOLO = "Yolo"
TRIGGER_PLUG_DB = "audio"

TRIGGER_TAGS = "tags"
TRIGGER_STATE = "state"
TRIGGER_TIMESTAMP = "timestamp"

MOTION_DETECTION = "Motion Detection"
SOUND_DETECTION = "Sound Detection"

SENSOR_DEVICE_CLASS = {
    TRIGGER_PLUG_YOLO: "motion",
    TRIGGER_PLUG_DB: "sound"
}

TRIGGER_DURATION = {
    TRIGGER_PLUG_YOLO: 20,
    TRIGGER_PLUG_DB: 10
}

TRIGGER_DEFAULT = {
    TRIGGER_STATE: STATE_OFF
}

BINARY_SENSOR_ATTRIBUTES = [TRIGGER_NAME, TRIGGER_DETAILS_REASON, TRIGGER_TAGS]
