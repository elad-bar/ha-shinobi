from datetime import datetime
import json
import logging
import sys
from typing import Optional

from custom_components.shinobi.api.shinobi_api import ShinobiApi
from custom_components.shinobi.helpers.const import *
from homeassistant.components.mqtt import Message, async_subscribe
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval

_LOGGER = logging.getLogger(__name__)


def _get_camera_binary_sensor_key(topic, event_type):
    key = f"{topic}_{event_type}".lower()

    return key


class MQTTManager:
    remove_subscription = None
    hass: Optional[HomeAssistant] = None
    message_handler = None
    mqtt_states: dict
    api: ShinobiApi

    def __init__(self, hass: HomeAssistant, api: ShinobiApi, event_handler):
        self.remove_subscription = None
        self.hass = hass
        self.event_handler = event_handler
        self.mqtt_states = {}
        self.api = api
        self._remove_async_track_time = None

    @property
    def is_supported(self) -> bool:
        return DATA_MQTT in self.hass.data

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

        self._remove_async_track_time = async_track_time_interval(
            self.hass, self._check_triggers, TRIGGER_INTERVAL
        )

    def terminate(self):
        if self.remove_subscription is not None:
            self.remove_subscription()
            self.remove_subscription = None

        if self._remove_async_track_time is not None:
            self._remove_async_track_time()
            self._remove_async_track_time = None

    def _state_message_received(self, message: Message):
        try:
            topic = message.topic
            payload = json.loads(message.payload)

            trigger_name = payload.get(TRIGGER_NAME)
            trigger_details = payload.get(TRIGGER_DETAILS, {})
            trigger_plug = trigger_details.get(TRIGGER_DETAILS_PLUG)
            trigger_reason = trigger_details.get(TRIGGER_DETAILS_REASON)
            trigger_matrices = trigger_details.get(TRIGGER_DETAILS_MATRICES, [])

            trigger_tags = []

            for trigger_object in trigger_matrices:
                trigger_tag = trigger_object.get(TRIGGER_DETAILS_MATRICES_TAG)

                if trigger_tag not in trigger_tags:
                    trigger_tags.append(trigger_tag)

            value = {
                TRIGGER_NAME: trigger_name,
                TRIGGER_PLUG: trigger_plug,
                TRIGGER_DETAILS_REASON: trigger_reason,
                TRIGGER_TAGS: trigger_tags,
                TRIGGER_STATE: STATE_ON,
                TRIGGER_TIMESTAMP: datetime.now().timestamp(),
                TRIGGER_TOPIC: topic
            }

            sensor_type = PLUG_SENSOR_TYPE.get(trigger_plug, None)

            if sensor_type is not None:
                if sensor_type == EVENT_FACE_RECOGNITION:
                    previous_state = STATE_OFF
                    _LOGGER.debug(f"Face recognition event: {payload}")

                else:
                    previous_data = self.get_state(topic, sensor_type)
                    previous_state = previous_data.get(TRIGGER_STATE, STATE_OFF)

                    self.set_state(topic, sensor_type, value)

                if previous_state == STATE_OFF:
                    self.event_handler(sensor_type, payload)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to _state_message_received, Error: {ex}, Line: {line_number}")

    def _check_triggers(self, now):
        self.hass.async_create_task(self._async_check_triggers(now))

    async def _async_check_triggers(self, event_time):
        try:
            current_time = datetime.now().timestamp()

            all_keys = self.mqtt_states.keys()
            changed = False

            for key in all_keys:
                data = self.mqtt_states.get(key)

                if data is not None:
                    topic = data.get(TRIGGER_TOPIC, None)
                    trigger_plug = data.get(TRIGGER_PLUG, None)
                    trigger_timestamp = data.get(TRIGGER_TIMESTAMP, None)
                    trigger_state = data.get(TRIGGER_STATE, STATE_OFF)

                    if topic is not None and trigger_state == STATE_ON:
                        sensor_type = PLUG_SENSOR_TYPE[trigger_plug]

                        diff = current_time - trigger_timestamp
                        event_duration = SENSOR_AUTO_OFF_INTERVAL.get(sensor_type, 20)

                        if diff >= event_duration:
                            changed = True
                            data[TRIGGER_STATE] = STATE_OFF

                            self.set_state(topic, sensor_type, data)

            if changed:
                self.event_handler()
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to _async_check_triggers, Error: {ex}, Line: {line_number}")

    def get_state(self, topic, event_type):
        key = _get_camera_binary_sensor_key(topic, event_type)

        state = self.mqtt_states.get(key, TRIGGER_DEFAULT)

        return state

    def set_state(self, topic, event_type, value):
        _LOGGER.debug(f"Set {event_type} state: {value} for {topic}")

        key = _get_camera_binary_sensor_key(topic, event_type)

        self.mqtt_states[key] = value
