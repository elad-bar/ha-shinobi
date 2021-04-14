"""
Support for Shinobi Video binary sensors.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/binary_sensor.shinobi/
"""
import logging
from datetime import datetime

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later

from .helpers.const import *
from .managers.mqtt_manager import MQTTManager
from .models.base_entity import async_setup_base_entry, BaseEntity
from .models.entity_data import EntityData

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = [DOMAIN, "mqtt"]

CURRENT_DOMAIN = DOMAIN_BINARY_SENSOR


def get_binary_sensor(hass: HomeAssistant, host: str, entity: EntityData):
    binary_sensor = BaseBinarySensor()
    binary_sensor.initialize(hass, host, entity, CURRENT_DOMAIN)

    return binary_sensor


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up the Shinobi Video Binary Sensor."""
    await async_setup_base_entry(
        hass, config_entry, async_add_devices, CURRENT_DOMAIN, get_binary_sensor
    )


async def async_unload_entry(hass, config_entry):
    _LOGGER.info(f"async_unload_entry {CURRENT_DOMAIN}: {config_entry}")

    return True


class BaseBinarySensor(BinarySensorEntity, BaseEntity):
    """Representation a binary sensor that is updated by MQTT."""

    def __init__(self):
        super().__init__()

        self._last_alert = None

    @property
    def mqtt_manager(self) -> MQTTManager:
        """Force update."""
        return self.entity_manager.mqtt_manager

    @property
    def topic(self):
        """Return the polling state."""
        return self.entity.topic

    @property
    def event_type(self):
        """Return the polling state."""
        return self.entity.event

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self.entity.state == STATE_ON

    @property
    def device_class(self):
        """Return the class of this sensor."""
        return self.entity.device_class

    @property
    def force_update(self):
        """Force update."""
        return DEFAULT_FORCE_UPDATE

    @property
    def event_duration(self):
        return TRIGGER_DURATION.get(self.event_type, 20)

    async def async_added_to_hass_local(self):
        _LOGGER.info(f"Added new {self.name}")

    def _immediate_update(self, previous_state: bool):
        is_on = self.entity.state == STATE_ON
        was_changed = self.state != previous_state

        if was_changed:
            _LOGGER.debug(
                f"{self.name} updated from {previous_state} to {self.state}"
            )

        def turn_off_automatically(now):
            mqtt_state = self.mqtt_manager.get_state(self.topic, self.event_type)

            last_alert = mqtt_state.get(TRIGGER_TIMESTAMP)
            action_timestamp = datetime.now().timestamp()

            if last_alert is None:
                diff = self.event_duration
            else:
                diff = action_timestamp - last_alert

            if diff >= self.event_duration:
                timeline = f"Started: {last_alert}, Ended: {action_timestamp}"
                _LOGGER.info(f"Turn off {self.name} after {diff} seconds, {timeline}")

                self.mqtt_manager.set_state(self.topic, self.event_type, TRIGGER_DEFAULT)
                self.ha.mqtt_event_handler()

        if is_on:
            trigger_state = self.mqtt_manager.get_state(self.topic, self.event_type)
            trigger_alert = trigger_state.get(TRIGGER_TIMESTAMP)

            _LOGGER.debug(f"{self.name} triggered at {trigger_alert}")

            async_call_later(self.hass, self.event_duration, turn_off_automatically)

            if was_changed:
                _LOGGER.info(f"First {self.event_type} event to turn on {self.name}")

                super()._immediate_update(previous_state)

        else:
            super()._immediate_update(previous_state)
