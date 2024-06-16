# Changelog

## v3.0.10

- Fix blocking call on startup

## v3.0.9

- Fix async dispatcher send

## v3.0.8

- Fix warning - StrEnum is a deprecated alias which will be removed in HA Core 2025.5. Use enum.StrEnum instead

## v3.0.7

_Minimum HA Version: 2024.1.0b0_

- Set minimum HA version for component to 2024.1.0b0

## 3.0.6

_Minimum HA Version: 2024.1.0_

- Fix media browser when no snapshot available by @chemelli74 in https://github.com/elad-bar/ha-shinobi/pull/60
- Adjust code to 2024.1.0 - [Issue #62](https://github.com/elad-bar/ha-shinobi/issues/62)

## 3.0.5

- Fix missing camera when no snapshot available by @chemelli74 in https://github.com/elad-bar/ha-shinobi/pull/57
- Fix Non-thread-safe operation invoked by @chemelli74 in https://github.com/elad-bar/ha-shinobi/pull/56

## 3.0.4

- Redact sensitive information from diagnostic file

## 3.0.3

### New features

- Add number components to server device to control event durations:
  - Motion defaults to 20 seconds
  - Sound defaults to 10 seconds

### Bug fixes

- Fix type in logs when storing configuration of proxy for recording
- Avoid saving default (config) entry id

## 3.0.2

### New features

- Support multiple instances of integrations for media source of Shinobi Video

### Bug fixes

- Motion detection stopped working since 3.x [#49](https://github.com/elad-bar/ha-shinobi/issues/50)
- Latest home assistant update (2023.08.1) seems broken shinobi integration [#50](https://github.com/elad-bar/ha-shinobi/issues/50)

## 3.0.1

- Fix translations for options
- Fix configuration storing process when changing server's switches
- Media Source
  - Fix typos in logs
  - Fix support when Video Wall API is not available
- Better handling disconnection for WebSockets

## 3.0.0

### Major refactor to integration

- Removed previous infrastructure for creating and managing components, switched to native UpdateCoordinator
- Support translations for entity names
- Add more components (see below)
- Add proxy view for recordings
- Improve camera component
- Remove repair process introduced in v2.0.34

### BREAKING CHANGES

- Unique IDs format for entities and devices, also password storage flow changed, If integration is not working after upgrade, it is recommended to remove and re-integrate.
- `Use Original Stream` local storage key name changed, by default it is off, if you enabled it in the past, please re-enable to make it work again.

### Components

#### Camera

- Fix wrong usage of mode vs. status
- Snapshot image is taken directly from the server
- HA State aligned to Monitor status:

  | Monitor Status | HA Camera State |
  | -------------- | --------------- |
  | recording      | Recording       |
  | watching       | Streaming       |
  | rest           | Idle            |

#### Media Source

- In monitor / camera wall changed the displayed name to camera name instead of ID
- Add HA Proxy View for thumbnails and videos

#### Binary Sensor

- Motion, Sound - set default state to `off` when camera is not online (watching or recording)

#### Switch

- Add HA Proxy for server device, defines whether to use local proxy for `Media Sources` thumbnails and videos, Default: off

#### Sensor

- Add `status` sensor per camera to present the camera status

## 2.0.34

- Fix camera stream flags
- Throttle repair process when camera `died` to 60 seconds

## 2.0.33

- Upgrade pre-commit-configuration by [@tetienne](https://github.com/tetienne)

## 2.0.32

- Add support for Home Assistant integration and device diagnostics
- Removed debug API

## 2.0.31

- Avoid sending ping when no active WebSockets connection [#44](https://github.com/elad-bar/ha-shinobi/issues/44)

## 2.0.30

- Skip Shinobi Video WebSockets non-textual message handling

## 2.0.29

- Fix `No API key associated with user` warning message when restarting HA

## 2.0.28

- Add potential fix for cases when `aiohttp` throws `server disconnected` error while the server is up and running, based on [aiohttp issue #4549](https://github.com/aio-libs/aiohttp/issues/4549)

## 2.0.27

- [Fix extraction of days to keep video files when settings were not changed (default)]() [#39](https://github.com/elad-bar/ha-shinobi/issues/39)

## 2.0.26

- Hotfix for Media Browser missing validation

## 2.0.25

- Fix connectivity issues introduced in v2.0.23 [#39](https://github.com/elad-bar/ha-shinobi/issues/39)
- More improvements for the Media Source based on the new endpoint of `videoBrowser` of Shinobi Video NVR

### More details about Media Browser

Media Browser supports 3 modes:

- `Backward compatibility` - getting the list of videos from the video endpoint in Shinobi Video
- `Video browser` - getting the list of videos from the new endpoint of video browser in Shinobi Video NVR
- `Video browser with thumbnails` - getting (in addition to the videos from video browser endpoints) also the time-lapse images to present as thumbnails

Main difference between `Backward compatibility` mode to the 2 others are:

- Endpoint of videos is less efficient for building the Media Browser
- For specific monitor without videos on specific days, there will be `day` directory, although it's empty.

How to enable `time-lapse` per monitor in Shinobi Video NVR:

- Open Shinobi Video Dashboard
- Monitors -> Choose Monitor -> Timelapse
- Change `Enabled` to `Yes`
- Set the `Creation interval` to `1 minute` (or at most - 1 minute less than the duration of recording)
- Copy to other monitors

_Support for new endpoint of video browser in Shinobi Video NVR will be introduced on December 1st 2022, or manually by using the `dev` branch of Shinobi Video_

## 2.0.24

- Media Source thumbnails is now working with time-lapse images API instead of customAutoLoad script `shinobi-thumbnails`, more details available in [README](README.md)
- Browsing now support all videos available for the monitor based on the days to keep videos in Shinobi Video dashboard

## 2.0.23

- Change log level of warning to debug level for session closed on HA restart
- Core fix: remove session close request, being handled by HA

## 2.0.22

- Fix media source camera and calendar thumbnails by snapshot

## 2.0.21

- Core fix: wrongfully reported logs of entities getting updated when no update perform

## 2.0.20

- Add test file to run locally (requires environment variables)
- Extend Core BaseAPI to handle session initialization and termination
- Hide error in log when thumbnails API is not supported by Shinobi Video Server
- Cleaner code to resolve URLs
- Remove unused constants

## 2.0.19

- Fix media play for Media Source
- Code cleanup

## 2.0.18

Major refactor for the media source component:

- Browsing now support up to 7 days of videos per camera
- Navigation model changed - Shinobi Camera -> Camera -> Day -> List of all videos from that day
- Thumbnails support added (requires Shinobi Thumbnail customAutoLoad script, more details in README)
- Performance improvement Loading the videos is now on demand and not every update of the integration (every 60 seconds)

**Thumbnails support**

Shinobi Video does not provide out of the box thumbnails endpoint, to add that support, please follow the instructions in [shinobi-thumbnails](https://gitlab.com/elad.bar/shinobi-thumbnails) repository.

## 2.0.17

- Fix issue with new Select options

## 2.0.16

**Version requires HA v2022.11.0 and above**

- Aligned _Core Select_ according to new HA _SelectEntityDescription_ object

## 2.0.15

- Better WS connection handling
- Expose any Shinobi Video NVR event from type `detector_trigger` as HA event (begins with `shinobi/`)
- Documentation

## 2.0.14

- Fix broken integration [#38](https://github.com/elad-bar/ha-shinobi/issues/38)

## 2.0.13

- Fix error when monitor was deleted its videos are still available
- API Documentation and examples

## 2.0.12

- Better handling WebSockets disconnections
- Fix parsing of Camera FPS [#37](https://github.com/elad-bar/ha-shinobi/issues/37)
- Removed configuration and service parameter of `store debug data`, add API instead:

## Endpoints

| Endpoint Name               | Method | Description                                                                                         |
| --------------------------- | ------ | --------------------------------------------------------------------------------------------------- |
| /api/shinobi/list           | GET    | List all the endpoints available (supporting multiple integrations), available once for integration |
| /api/shinobi/{ENTRY_ID}/api | GET    | JSON of all raw data from the Shinobi API, per integration                                          |
| /api/shinobi/{ENTRY_ID}/ws  | GET    | JSON of all raw data from the Shinobi WebSocket, per integration                                    |

**Authentication: Requires long-living token from HA**

## 2.0.11

- Fix core wrong reference

## 2.0.10

- Update core to latest

## 2.0.9

- Update core features

## 2.0.8

- Another fix json serialization when saving debug data

## 2.0.7

- Fix json serialization when saving debug data

## 2.0.6

- Added debug data to file switch
- Support future version of HA v2022.11

## 2.0.5

- Fix deleting components when being removed, wrong parameter was sent to be deleted
- Removed status change for API once not getting results from endpoint
- Fix documentation ([#33](https://github.com/elad-bar/ha-shinobi/issues/33))
- Set API and WS initial status to connecting once initializing ([#34](https://github.com/elad-bar/ha-shinobi/issues/34))

## 2.0.4

- Fix core issue while deleting entities

## 2.0.3

- Repair non-working monitors only when initialization process completed
- Moved local configuration to additional Storage API
- Core protect unsupported domains

## 2.0.2

- Fix icons for binary sensor, switch and select
- Fix core functionality

## 2.0.1

- Fix core entities creation when not in use
- Move `use_original_stream` to switch config control and removed it from setup

## 2.0.0

- Refactor core entities and functionality

## 1.3.2

- Add auto reconnect monitor when fails
- Add "\_" to make private functions of Shinobi API - private

## 1.3.1

- Upgraded pre-commit to support Python 3.10
- Removed unused `ConfigData.name`
- Fix support for Shinobi Video v3 (Socket.io JS resource moved to another path)

## 1.3.0

- Code reorganize

## 1.2.3

- Device and Entity registry - `async_get_registry` is deprecated, change to `async_get`

## 1.2.2

- Add support to control monitor motion / sound detection using switch per monitor

  - Toggle off detector (motion / sound) will remove the entity
  - Toggle on will restore the entity
  - Switch for sound detection will not be available if monitor has no audio channel
  - Any action will be logged with response from Shinobi Video Server

- Unique ID is now being calculated automatically based on the entity's domain and name
- Improved camera component creation
  - Reduced the data of camera component
  - Reduced the amount of updates for camera component

## 1.2.1

- Align terminology of Shinobi Video (Camera for HA component, Monitor for Shinobi Video device)

## 1.2.0

- Add support to control camera mode using Select Entity, available options are Disabled (stop), Watch Only (start), Record (record)
- When camera mode is Disabled, all entities will be removed (Camera and Binary Sensors), Mode Select Entity will remain available
- When Motion detection is turned off, No Motion detection sensors will be available for the specific camera
- When Sound detection is turned off, No sound detection sensors will be available for the specific camera
- Fix camera state (calculated wrongly before)
- Improved entity update mechanism (update only if relevant as opposed to update anyway)
- Improved Shinobi Video events handler
- Code cleanup

## 1.1.29

- Fix video date and time parsing when TZ is not available
- Video data code separation
- Code cleanup

## 1.1.28

- Fix error message when using Shinobi Video with non dashboard-v3 branch (SocketIO=v3)
- Fix ping attempt while WebSocket connection is closed

## 1.1.27

- Add Media Browser support ([#23](https://github.com/elad-bar/ha-shinobi/issues/23))

## 1.1.26

- Added Enable / Disable motion detection per camera ([#22](https://github.com/elad-bar/ha-shinobi/issues/22))

## 1.1.25

- Added WebSocket message inspection to make sure only TEXT messages are being handled

## 1.1.24

- Fixed 'Failed to parse message' error when the message is bytes based (by ignoring that message)

## 1.1.23

- Fixed invalid event JSON from Shinobi video when confidence level is between 0 and 1 with decimal number - confidence level is lack of leading 0.

## 1.1.22

- Added support for dashboard-v3 (using SocketIO v4.4.1)

## 1.1.21

- Removed entity / device delete upon restarting HA

## 1.1.20

- Fixed disabled by wrong parameter

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

  `JPEG API is not enabled for {monitor.name}, Camera will not be created`

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
