from copy import copy
from dataclasses import dataclass
from typing import Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.components.camera import CameraEntityDescription
from homeassistant.components.select import SelectEntityDescription
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.const import Platform
from homeassistant.helpers.entity import EntityCategory, EntityDescription
from homeassistant.util import slugify

from .consts import (
    DATA_KEY_CAMERA,
    DATA_KEY_MONITOR_MODE,
    DATA_KEY_MONITOR_STATUS,
    DATA_KEY_MOTION,
    DATA_KEY_MOTION_DETECTION,
    DATA_KEY_ORIGINAL_STREAM,
    DATA_KEY_SOUND,
    DATA_KEY_SOUND_DETECTION,
)
from .enums import MonitorMode
from .monitor_data import MonitorData


@dataclass(slots=True)
class IntegrationEntityDescription(EntityDescription):
    platform: Platform | None = None
    is_system: bool = False
    filter: Callable[[MonitorData | None], bool] | None = lambda m: m is not None


@dataclass(slots=True)
class IntegrationBinarySensorEntityDescription(
    BinarySensorEntityDescription, IntegrationEntityDescription
):
    platform: Platform | None = Platform.BINARY_SENSOR
    on_value: str | bool | None = None
    attributes: list[str] | None = None


@dataclass(slots=True)
class IntegrationCameraEntityDescription(
    CameraEntityDescription, IntegrationEntityDescription
):
    platform: Platform | None = Platform.CAMERA


@dataclass(slots=True)
class IntegrationSensorEntityDescription(
    SensorEntityDescription, IntegrationEntityDescription
):
    platform: Platform | None = Platform.SENSOR


@dataclass(slots=True)
class IntegrationSelectEntityDescription(
    SelectEntityDescription, IntegrationEntityDescription
):
    platform: Platform | None = Platform.SELECT


@dataclass(slots=True)
class IntegrationSwitchEntityDescription(
    SwitchEntityDescription, IntegrationEntityDescription
):
    platform: Platform | None = Platform.SWITCH
    on_value: str | bool | None = None


ENTITY_DESCRIPTIONS: list[IntegrationEntityDescription] = [
    IntegrationCameraEntityDescription(
        key=slugify(DATA_KEY_CAMERA),
        name="",
        translation_key=slugify(DATA_KEY_CAMERA),
    ),
    IntegrationSensorEntityDescription(
        key=slugify(DATA_KEY_MONITOR_STATUS),
        name=DATA_KEY_MONITOR_STATUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key=slugify(DATA_KEY_MONITOR_STATUS),
    ),
    IntegrationSelectEntityDescription(
        key=slugify(DATA_KEY_MONITOR_MODE),
        name=DATA_KEY_MONITOR_MODE,
        options=MonitorMode.get_list(),
        entity_category=EntityCategory.CONFIG,
        translation_key=slugify(DATA_KEY_MONITOR_MODE),
    ),
    IntegrationBinarySensorEntityDescription(
        key=slugify(DATA_KEY_MOTION),
        name=DATA_KEY_MOTION,
        device_class=BinarySensorDeviceClass.MOTION,
        translation_key=slugify(DATA_KEY_MOTION),
    ),
    IntegrationBinarySensorEntityDescription(
        key=slugify(DATA_KEY_SOUND),
        name=DATA_KEY_SOUND,
        device_class=BinarySensorDeviceClass.SOUND,
        translation_key=slugify(DATA_KEY_SOUND),
        filter=lambda m: m is not None and m.has_audio,
    ),
    IntegrationSwitchEntityDescription(
        key=slugify(DATA_KEY_MOTION_DETECTION),
        name=DATA_KEY_MOTION_DETECTION,
        translation_key=slugify(DATA_KEY_MOTION_DETECTION),
    ),
    IntegrationSwitchEntityDescription(
        key=slugify(DATA_KEY_SOUND_DETECTION),
        name=DATA_KEY_SOUND_DETECTION,
        translation_key=slugify(DATA_KEY_SOUND_DETECTION),
        filter=lambda m: m is not None and m.has_audio,
    ),
    IntegrationSwitchEntityDescription(
        key=slugify(DATA_KEY_ORIGINAL_STREAM),
        name=DATA_KEY_ORIGINAL_STREAM,
        translation_key=slugify(DATA_KEY_ORIGINAL_STREAM),
        filter=lambda m: m is None,
    ),
]


def get_entity_descriptions(
    platform: Platform, monitor: MonitorData | None
) -> list[IntegrationEntityDescription]:
    entity_descriptions = copy(ENTITY_DESCRIPTIONS)

    result = [
        entity_description
        for entity_description in entity_descriptions
        if entity_description.platform == platform
        and entity_description.filter(monitor)
    ]

    return result


def get_platforms() -> list[str]:
    platforms = {
        entity_description.platform: None for entity_description in ENTITY_DESCRIPTIONS
    }
    result = list(platforms.keys())

    return result


PLATFORMS = get_platforms()
