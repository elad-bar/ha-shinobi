from copy import copy
from dataclasses import dataclass
from typing import Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.components.camera import CameraEntityDescription
from homeassistant.components.number import NumberEntityDescription
from homeassistant.components.select import SelectEntityDescription
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.const import Platform, UnitOfTime
from homeassistant.helpers.entity import EntityCategory, EntityDescription

from ..models.monitor_data import MonitorData
from .consts import (
    DATA_KEY_CAMERA,
    DATA_KEY_EVENT_DURATION_MOTION,
    DATA_KEY_EVENT_DURATION_SOUND,
    DATA_KEY_MONITOR_MODE,
    DATA_KEY_MONITOR_STATUS,
    DATA_KEY_MOTION,
    DATA_KEY_MOTION_DETECTION,
    DATA_KEY_ORIGINAL_STREAM,
    DATA_KEY_PROXY_RECORDINGS,
    DATA_KEY_SOUND,
    DATA_KEY_SOUND_DETECTION,
)
from .enums import MonitorMode


@dataclass(frozen=True, kw_only=True)
class IntegrationEntityDescription(EntityDescription):
    platform: Platform | None = None
    is_system: bool = False
    filter: Callable[[MonitorData | None], bool] | None = lambda m: m is not None


@dataclass(frozen=True, kw_only=True)
class IntegrationBinarySensorEntityDescription(
    BinarySensorEntityDescription, IntegrationEntityDescription
):
    platform: Platform | None = Platform.BINARY_SENSOR
    on_value: str | bool | None = None
    attributes: list[str] | None = None


@dataclass(frozen=True, kw_only=True)
class IntegrationCameraEntityDescription(
    CameraEntityDescription, IntegrationEntityDescription
):
    platform: Platform | None = Platform.CAMERA


@dataclass(frozen=True, kw_only=True)
class IntegrationSensorEntityDescription(
    SensorEntityDescription, IntegrationEntityDescription
):
    platform: Platform | None = Platform.SENSOR


@dataclass(frozen=True, kw_only=True)
class IntegrationSelectEntityDescription(
    SelectEntityDescription, IntegrationEntityDescription
):
    platform: Platform | None = Platform.SELECT


@dataclass(frozen=True, kw_only=True)
class IntegrationSwitchEntityDescription(
    SwitchEntityDescription, IntegrationEntityDescription
):
    platform: Platform | None = Platform.SWITCH
    on_value: str | bool | None = None


@dataclass(frozen=True, kw_only=True)
class IntegrationNumberEntityDescription(
    NumberEntityDescription, IntegrationEntityDescription
):
    platform: Platform | None = Platform.NUMBER


ENTITY_DESCRIPTIONS: list[IntegrationEntityDescription] = [
    IntegrationCameraEntityDescription(
        key=DATA_KEY_CAMERA,
        name="",
        translation_key=DATA_KEY_CAMERA,
    ),
    IntegrationSensorEntityDescription(
        key=DATA_KEY_MONITOR_STATUS,
        name=DATA_KEY_MONITOR_STATUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key=DATA_KEY_MONITOR_STATUS,
    ),
    IntegrationSelectEntityDescription(
        key=DATA_KEY_MONITOR_MODE,
        name=DATA_KEY_MONITOR_MODE,
        options=MonitorMode.get_list(),
        entity_category=EntityCategory.CONFIG,
        translation_key=DATA_KEY_MONITOR_MODE,
    ),
    IntegrationBinarySensorEntityDescription(
        key=DATA_KEY_MOTION,
        name=DATA_KEY_MOTION,
        device_class=BinarySensorDeviceClass.MOTION,
        translation_key=DATA_KEY_MOTION,
    ),
    IntegrationBinarySensorEntityDescription(
        key=DATA_KEY_SOUND,
        name=DATA_KEY_SOUND,
        device_class=BinarySensorDeviceClass.SOUND,
        translation_key=DATA_KEY_SOUND,
        filter=lambda m: m is not None and m.has_audio,
    ),
    IntegrationSwitchEntityDescription(
        key=DATA_KEY_MOTION_DETECTION,
        name=DATA_KEY_MOTION_DETECTION,
        translation_key=DATA_KEY_MOTION_DETECTION,
    ),
    IntegrationSwitchEntityDescription(
        key=DATA_KEY_SOUND_DETECTION,
        name=DATA_KEY_SOUND_DETECTION,
        translation_key=DATA_KEY_SOUND_DETECTION,
        filter=lambda m: m is not None and m.has_audio,
    ),
    IntegrationSwitchEntityDescription(
        key=DATA_KEY_ORIGINAL_STREAM,
        name=DATA_KEY_ORIGINAL_STREAM,
        translation_key=DATA_KEY_ORIGINAL_STREAM,
        filter=lambda m: m is None,
    ),
    IntegrationSwitchEntityDescription(
        key=DATA_KEY_PROXY_RECORDINGS,
        name=DATA_KEY_PROXY_RECORDINGS,
        translation_key=DATA_KEY_PROXY_RECORDINGS,
        filter=lambda m: m is None,
    ),
    IntegrationNumberEntityDescription(
        key=DATA_KEY_EVENT_DURATION_MOTION,
        name=DATA_KEY_EVENT_DURATION_MOTION,
        translation_key=DATA_KEY_EVENT_DURATION_MOTION,
        filter=lambda m: m is None,
        native_max_value=600,
        native_min_value=0,
        native_unit_of_measurement=UnitOfTime.SECONDS,
    ),
    IntegrationNumberEntityDescription(
        key=DATA_KEY_EVENT_DURATION_SOUND,
        name=DATA_KEY_EVENT_DURATION_SOUND,
        translation_key=DATA_KEY_EVENT_DURATION_SOUND,
        filter=lambda m: m is None,
        native_max_value=600,
        native_min_value=0,
        native_unit_of_measurement=UnitOfTime.SECONDS,
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
