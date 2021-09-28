from datetime import datetime
import logging
import sys
from typing import Optional

from custom_components.shinobi.api.shinobi_api import ShinobiApi
from custom_components.shinobi.helpers.const import *
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

_LOGGER = logging.getLogger(__name__)


def _get_camera_binary_sensor_key(topic, event_type):
    key = f"{topic}_{event_type}".lower()

    return key


class EventManager:
    remove_subscription = None
    hass: Optional[HomeAssistant] = None
    message_handler = None
    states: dict
    api: ShinobiApi

    def __init__(self, hass: HomeAssistant, callback):
        self.remove_subscription = None
        self.hass = hass
        self.callback = callback
        self.states = {}
        self._remove_async_track_time = None

    async def initialize(self):
        self._remove_async_track_time = async_track_time_interval(
            self.hass, self._check_triggers, TRIGGER_INTERVAL
        )

    def terminate(self):
        if self._remove_async_track_time is not None:
            self._remove_async_track_time()
            self._remove_async_track_time = None

    def message_received(self, topic, payload):
        try:
            trigger_details = payload.get(TRIGGER_DETAILS, {})
            trigger_reason = trigger_details.get(TRIGGER_DETAILS_REASON)

            if trigger_reason in PLUG_SENSOR_TYPE.keys():
                self._handle_sensor_event(topic, payload)

            else:
                _LOGGER.debug(f"Shinobi Video {trigger_reason} event: {payload}")
                self.callback(trigger_reason, payload)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to handle received message, Topic {topic}, Payload: {payload}, "
                f"Error: {ex}, Line: {line_number}"
            )

    def _handle_sensor_event(self, topic, payload):
        try:
            trigger_details = payload.get(TRIGGER_DETAILS, {})
            trigger_reason = trigger_details.get(TRIGGER_DETAILS_REASON)

            trigger_name = payload.get(TRIGGER_NAME)
            trigger_plug = trigger_details.get(TRIGGER_DETAILS_PLUG)
            trigger_matrices = trigger_details.get(TRIGGER_DETAILS_MATRICES, [])

            if trigger_matrices is None:
                _LOGGER.warning(f"Empty trigger matrices, payload: {payload}")
                return

            if trigger_name is None:
                trigger_name = trigger_details.get(TRIGGER_NAME)

            trigger_tags = []

            for trigger_object in trigger_matrices:
                if trigger_object is None:
                    _LOGGER.debug(f"Ignoring empty trigger object")

                else:
                    trigger_tag = trigger_object.get(TRIGGER_DETAILS_MATRICES_TAG)

                    if trigger_tag not in trigger_tags:
                        trigger_tags.append(trigger_tag)

            sensor_type = PLUG_SENSOR_TYPE.get(trigger_reason, None)

            value = {
                TRIGGER_NAME: trigger_name,
                TRIGGER_PLUG: trigger_plug,
                TRIGGER_DETAILS_REASON: trigger_reason,
                TRIGGER_TAGS: trigger_tags,
                TRIGGER_STATE: STATE_ON,
                TRIGGER_TIMESTAMP: datetime.now().timestamp(),
                TRIGGER_TOPIC: topic
            }

            if len(trigger_tags) == 0 and sensor_type == REASON_MOTION:
                _LOGGER.warning(f"No tags found for the event, Data: {payload}")

            previous_data = self.get_state(topic, sensor_type)
            previous_state = previous_data.get(TRIGGER_STATE, STATE_OFF)

            self.set_state(topic, sensor_type, value)

            if previous_state == STATE_OFF:
                self.callback(sensor_type, payload)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to handle sensor message, Error: {ex}, Line: {line_number}")

    def _check_triggers(self, now):
        self.hass.async_create_task(self._async_check_triggers(now))

    async def _async_check_triggers(self, event_time):
        try:
            current_time = datetime.now().timestamp()

            all_keys = self.states.keys()
            changed = False

            for key in all_keys:
                data = self.states.get(key)

                if data is not None:
                    topic = data.get(TRIGGER_TOPIC, None)
                    trigger_reason = data.get(TRIGGER_DETAILS_REASON, None)
                    trigger_timestamp = data.get(TRIGGER_TIMESTAMP, None)
                    trigger_state = data.get(TRIGGER_STATE, STATE_OFF)

                    if topic is not None and trigger_state == STATE_ON:
                        sensor_type = PLUG_SENSOR_TYPE[trigger_reason]

                        diff = current_time - trigger_timestamp
                        event_duration = SENSOR_AUTO_OFF_INTERVAL.get(sensor_type, 20)

                        if diff >= event_duration:
                            changed = True
                            data[TRIGGER_STATE] = STATE_OFF

                            self.set_state(topic, sensor_type, data)

            if changed:
                self.callback()
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to check triggers (async) at {event_time}, Error: {ex}, Line: {line_number}"
            )

    def get_state(self, topic, event_type):
        key = _get_camera_binary_sensor_key(topic, event_type)

        state = self.states.get(key, TRIGGER_DEFAULT)

        return state

    def set_state(self, topic, event_type, value):
        _LOGGER.debug(f"Set {event_type} state: {value} for {topic}")

        key = _get_camera_binary_sensor_key(topic, event_type)

        self.states[key] = value
