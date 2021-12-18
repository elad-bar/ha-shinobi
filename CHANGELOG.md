# Changelog

## 1.1.19

- Fixed shinobi video configuration port validation, changed from string to integer

## 1.1.18

- Fixed camera's timeout warning message

## 1.1.17

- Upgraded code to support breaking changes of HA v2012.12.0

## 1.1.16

- Added support to use original stream directly from the camera (Integration's installation / options --> Use original stream)
- If stream is not set in Shinobi Video Server, will use original stream
- Disabled monitors in Shinobi Video Server will be created as disabled

## 1.1.15

- Better handling error message due to invalid WebSocket message

## 1.1.14

- Code and logs cleanup
- Added `Troubleshooting` section in README

## 1.1.13

- Fix error due to unsupported event messages [#17](https://github.com/elad-bar/ha-shinobi/issues/17)
- Change message's log level of empty matrices to `DEBUG`

## 1.1.12

- Added support for single camera (response of an object instead of array) [#16](https://github.com/elad-bar/ha-shinobi/issues/16)

## 1.1.11

- Added more logs for debugging invalid monitor's loading
- Camera properties added - `is_recording` and `motion_detection_enabled`
- Unused imports cleanup
- Added `requirements.txt`

## 1.1.10

- Added `detector_trigger` motion event validation to avoid corrupted data

## 1.1.9

- Missing Binary Motion Sensors due to wrong motion detection parameter [#15](https://github.com/elad-bar/ha-shinobi/issues/15)

## 1.1.8

- Support HA v2021.9.0 breaking change - `Camera` component
- Support `SensorEntity` instead of `Entity`

## 1.1.7

- Path parameter causing issues for WebSocket (add protection in case virtual path is `/`) [#14](https://github.com/elad-bar/ha-shinobi/issues/14)

## 1.1.6

- Path parameter causing issues (add protection in case virtual path is `/`) [#14](https://github.com/elad-bar/ha-shinobi/issues/14)

## 1.1.5

- Fix motion binary sensor is now relying on detector_pam settings [#10](https://github.com/elad-bar/ha-shinobi/issues/10)
- JPEG API must be enabled to create camera entity [#7](https://github.com/elad-bar/ha-shinobi/issues/7), in addition, will present warning log message:

  `JPEG API is not enabled for {camera.name}, Camera will not be created`

## 1.1.4

- Better handling FPS values
    - Empty: default value of HA will be 1FPS [#6](https://github.com/elad-bar/ha-shinobi/issues/6)
    - Decimal: ignore decimal numbers

## 1.1.3

- Fix error while loading caused by a listener of `home assistant stop` event

## 1.1.2

- Graceful WebSocket disconnect upon HA shutdown / restart

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
