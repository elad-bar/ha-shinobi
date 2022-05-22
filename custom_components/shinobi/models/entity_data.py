from typing import Optional

from ..helpers.const import *


class EntityData:
    id: str
    unique_id: str
    name: str
    state: str
    attributes: dict
    icon: str
    device_name: str
    status: str
    binary_sensor_device_class: Optional[BinarySensorDeviceClass]
    details: dict
    disabled: bool
    domain: str

    def __init__(self):
        self.id = ""
        self.unique_id = ""
        self.name = ""
        self.state = ""
        self.attributes = {}
        self.icon = ""
        self.device_name = ""
        self.status = ENTITY_STATUS_CREATED
        self.binary_sensor_device_class = None
        self.details = {}
        self.disabled = False
        self.domain = ""

    def __repr__(self):
        obj = {
            ENTITY_ID: self.id,
            ENTITY_UNIQUE_ID: self.unique_id,
            ENTITY_NAME: self.name,
            ENTITY_STATE: self.state,
            ENTITY_ATTRIBUTES: self.attributes,
            ENTITY_ICON: self.icon,
            ENTITY_DEVICE_NAME: self.device_name,
            ENTITY_STATUS: self.status,
            ENTITY_BINARY_SENSOR_DEVICE_CLASS: self.binary_sensor_device_class,
            ENTITY_MONITOR_DETAILS: self.details,
            ENTITY_DISABLED: self.disabled,
            ENTITY_DOMAIN: self.domain
        }

        to_string = f"{obj}"

        return to_string
