from homeassistant.core import HomeAssistant

from .const import *


def clear_ha(hass: HomeAssistant, entry_id):
    if DATA not in hass.data:
        hass.data[DATA] = dict()

    del hass.data[DATA][entry_id]


def get_ha(hass: HomeAssistant, entry_id):
    ha_data = hass.data.get(DATA, dict())
    ha = ha_data.get(entry_id)

    return ha
