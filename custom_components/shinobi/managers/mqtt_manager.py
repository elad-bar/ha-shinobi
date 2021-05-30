import json
import logging
import sys
from typing import Optional

from custom_components.shinobi.api.shinobi_api import ShinobiApi
from custom_components.shinobi.helpers.const import *
from custom_components.shinobi.managers.event_manager import EventManager
from homeassistant.components.mqtt import Message, async_subscribe
from homeassistant.core import HomeAssistant, callback

_LOGGER = logging.getLogger(__name__)


def _get_camera_binary_sensor_key(topic, event_type):
    key = f"{topic}_{event_type}".lower()

    return key


class MQTTManager:
    remove_subscription = None
    hass: Optional[HomeAssistant] = None
    event_manager = None
    api: ShinobiApi

    def __init__(self, hass: HomeAssistant, api: ShinobiApi, event_manager: EventManager):
        self.remove_subscription = None
        self.hass = hass
        self.event_manager = event_manager
        self.api = api

    @property
    def is_supported(self) -> bool:
        return False and DATA_MQTT in self.hass.data

    async def initialize(self):
        """Subscribe MQTT events."""
        self.terminate()

        mqtt_topic = f"{MQTT_ALL_TOPIC}/{self.api.group_id}/#"

        _LOGGER.info(
            f"Subscribing to MQTT topics '{mqtt_topic}', QOS: {DEFAULT_QOS}"
        )

        @callback
        def state_message_received(message: Message):
            """Handle a new received MQTT state message."""
            _LOGGER.debug(
                f"Received Shinobi Video Message - {message.topic}: {message.payload}"
            )

            self._state_message_received(message)

        self.remove_subscription = await async_subscribe(
            self.hass, mqtt_topic, state_message_received, DEFAULT_QOS
        )

    def terminate(self):
        if self.remove_subscription is not None:
            self.remove_subscription()
            self.remove_subscription = None

    def _state_message_received(self, message: Message):
        try:
            payload = json.loads(message.payload)

            self.event_manager.message_received(message.topic, payload)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to _state_message_received, Error: {ex}, Line: {line_number}")
