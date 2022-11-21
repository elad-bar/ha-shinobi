# Shinobi Video NVR

## Description

Integration with Shinobi Video NVR. Creates the following components:

* Camera - per-monitor defined.
* Binary Sensors (MOTION, SOUND) - per-monitor defined.
* Support HLS Streams instead of H264.
* Support SSL with self-signed certificate.
* Support Face-Recognition plugin as an event
* Select to set the monitor mode
* Switch to set the monitor's detectors (motion / sound) - per-monitor defined.

[Changelog](https://github.com/elad-bar/ha-shinobi/blob/master/CHANGELOG.md)

#### Requirements
- Shinobi Video Server
- Dashboard user with API Key (with all permissions)
- JPEG API enabled
- Optional: Motion detection - [How to use Motion Detection](https://hub.shinobi.video/articles/view/LKdcgcgWy9RJfUh)

## How to

#### Generate permanent API Key:
In Shinobi Video Dashboard, click your username in the top left.
A menu will appear, click API.
Add new token - IP: 0.0.0.0, Permissions - Select all

#### Installations via HACS
- In HACS, look for "Shinobi Video NVR" and install
- In Settings  --> Devices & Services - (Lower Right) "Add Integration"

#### Integration settings
###### Basic configuration
| Fields name | Type      | Required | Default   | Description                                                             |
|-------------|-----------|----------|-----------|-------------------------------------------------------------------------|
| Host        | Texbox    | +        | None      | Hostname or IP address of the Shinobi Video server                      |
| Port        | Textbox   | +        | 0         | HTTP Port to access Shinobi Video server                                |
| Path        | Textbox   | -        | Empty     | If Shinobi Video Server NVR has non default path, please adjust it here |
| SSL         | Check-box | +        | Unchecked | Is SSL supported?                                                       |
| Username    | Textbox   | -        |           | Username of dashboard user for Shinobi Video server                     |
| Password    | Textbox   | -        |           | Password of dashboard user for Shinobi Video server                     |

###### Integration options
| Fields name | Type      | Required | Default              | Description                                                             |
|-------------|-----------|----------|----------------------|-------------------------------------------------------------------------|
| Host        | Texbox    | +        | ast stored hostname  | Hostname or IP address of the Shinobi Video server                      |
| Port        | Textbox   | +        | 0ast stored port     | HTTP Port to access Shinobi Video server                                |
| Path        | Textbox   | -        | Empty                | If Shinobi Video Server NVR has non default path, please adjust it here |
| SSL         | Check-box | +        | Last stored SSL flag | Is SSL supported?                                                       |
| Username    | Textbox   | -        | Last stored username | Username of dashboard user for Shinobi Video server                     |
| Password    | Textbox   | -        | Last stored password | Password of dashboard user for Shinobi Video server                     |

###### Configuration validations
Upon submitting the form of creating an integration or updating options,

Component will try to log in into the Shinobi Video server to verify new settings, following errors can appear:
- Integration already configured with the same title
- Invalid server details - Cannot reach the server

###### Encryption key got corrupted
If a persistent notification popped up with the following message:
```
Encryption key got corrupted, please remove the integration and re-add it
```

It means that encryption key was modified from outside the code,
Please remove the integration and re-add it to make it work again.

## Components

#### Binary Sensors
Each binary sensor will have the name pattern - {Integration Title} {Monitor Name} {Sound / Motion},
Once triggered, the following details will be added to the attributes of the binary sensor:

###### Audio
Represents whether the monitor is triggered for noise or not

###### Motion
Represents whether the monitor is triggered for motion or not

###### Camera
State: Idle

| Attributes | Available values                                     |
|------------|------------------------------------------------------|
| Status     | Recording,                                           |
| Mode       | stop (Disabled), start (Watch-Only), record (Record) |
| Type       | H264, MJPEG,                                         |
| FPS        | -                                                    |


#### Select
Allow to control the monitor mode:
- stop (Disabled)
- start (Watch-Only)
- record (Record)

#### Switch

###### Enable / Disable Sound / Motion detection
Each switch will have the name pattern - {Integration Title} {Monitor Name} {Sound / Motion}:
- Toggle off detector (motion / sound) will remove the entity
- Toggle on will restore the entity
- Switch for sound detection will not be available if monitor has no audio channel

###### Use original Stream
- Toggle on to use the original stream directly from the camera
- Toggle off / or leave as default for default stream from the NVR

#### Media Source
Shinobi Camera -> Camera -> Day -> List of all videos from that day

**Thumbnails support**

Shinobi Video does not provide dedicated thumbnails endpoint per video file,
Integration is using the time-lapse endpoint to calculate which time-lapse image is suitable for the video based on the range of start / end recording time of the video,
to enable thumbnails in the Media Source, please enable `time-lapse` module per monitor:
- Open Shinobi Video Dashboard
- Monitors -> Choose Monitor -> Timelapse
- Change `Enabled` to `Yes`
- Set the `Creation interval` to `1 minute` (or at most - 1 minute less than the duration of recording)
- Copy to other monitors

## Events

Any Shinobi Video NVR event from type `detector_trigger` will be sent as an HA event as well with the same payload

## API

| Endpoint Name               | Method | Description                                                                                         |
|-----------------------------|--------|-----------------------------------------------------------------------------------------------------|
| /api/shinobi/list           | GET    | List all the endpoints available (supporting multiple integrations), available once for integration |
| /api/shinobi/{ENTRY_ID}/api | GET    | JSON of all raw data from the Shinobi API, per integration                                          |
| /api/shinobi/{ENTRY_ID}/ws  | GET    | JSON of all raw data from the Shinobi WebSocket, per integration                                    |

**Authentication: Requires long-living token from HA**

### Examples

#### List

*Request*
```bash
curl https://ha_url:8123/api/shinobi/list
   -H "Accept: application/json"
   -H "Authorization: Bearer {token}"
```

*[Response](/docs/examples/list.json)*

#### WebSockets Data

*Request*
```bash
curl https://ha_url:8123/api/shinobi/{ENTRY_ID}/ws
   -H "Accept: application/json"
   -H "Authorization: Bearer {token}"
```

*[Response](/docs/examples/ws_data.json)*

#### API Data

```bash
curl https://ha_url:8123/api/shinobi/{ENTRY_ID}/api
   -H "Accept: application/json"
   -H "Authorization: Bearer {token}"
```

*[Response](/docs/examples/api_data.json)*


## Troubleshooting

Before opening an issue, please provide logs related to the issue,
For debug log level, please add the following to your config.yaml
```yaml
logger:
  default: warning
  logs:
    custom_components.shinobi: debug
```
