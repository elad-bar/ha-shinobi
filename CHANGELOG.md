# Changelog

## 1.1.1

- Improve WebSocket reconnect mechanism

## 1.1.0

**Breaking change**

A new version rely on WebSocket instead of MQTT,
Permanent API Key must support WebSocket connection, otherwise, integration will not work,

**What's new**
- Switched from MQTT to WebSocket events
- Motion sensors rely on motion detection instead of object detection
- Object detection and Face identification are being represented as an event

## 1.0.7

- Added code protection, logs and documentation for API Key usage [#3](https://github.com/elad-bar/ha-shinobi/issues/3)

## v1.0.6

- More instructions in README
- Fix lint errors

## v1.0.5

- Fix README and Strings

## v1.0.4

- Added support of Shinobi Video plugin for DeepStack Face Recognition
- Added support of Shinobi Video plugin for DeepStack Object Detection
- Added `shinobi/face_recognition` event to trigger once face identified

## v1.0.3

- Improved MQTT sensor auto off logic

## v1.0.2

- Support Tensorflow plugin as motion sensor

## v1.0.1

- Fix hassfest validation error - Added iot_class=local_polling to manifest

## v1.0.0

Initial release
