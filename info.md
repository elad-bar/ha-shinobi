# Shinobi Video NVR

## Description

Integration with Shinobi Video NVR to present and control camera (monitor) including plugin events.

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
- In Settings --> Devices & Services - (Lower Right) "Add Integration"

#### Integration settings

###### Integration configuration

| Fields name | Type      | Required | Default   | Description                                                             |
| ----------- | --------- | -------- | --------- | ----------------------------------------------------------------------- |
| Host        | Texbox    | +        | None      | Hostname or IP address of the Shinobi Video server                      |
| Port        | Textbox   | +        | 0         | HTTP Port to access Shinobi Video server                                |
| Path        | Textbox   | -        | Empty     | If Shinobi Video Server NVR has non default path, please adjust it here |
| SSL         | Check-box | +        | Unchecked | Is SSL supported?                                                       |
| Username    | Textbox   | -        |           | Username of dashboard user for Shinobi Video server                     |
| Password    | Textbox   | -        |           | Password of dashboard user for Shinobi Video server                     |

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
| ---------- | ---------------------------------------------------- |
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

#### Media Browser

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

_Support for new endpoint of video browser in Shinobi Video NVR will be introduced on December 1st 2022_

#### Number

Each number will have the name pattern - {Integration Title} {Sound / Motion} Event Duration,
Defaults are 20 seconds for motion event, 10 seconds for sound event,
Valid values are between 0 and 600 represents seconds.

## Events

Any Shinobi Video NVR event from type `detector_trigger` will be sent as an HA event as well with the same payload

## Troubleshooting

Before opening an issue, please provide logs related to the issue,
For debug log level, please add the following to your config.yaml

```yaml
logger:
  default: warning
  logs:
    custom_components.shinobi: debug
```

Please attach also diagnostic details of the integration, available in:
Settings -> Devices & Services -> Shinobi Video NVR -> 3 dots menu -> Download diagnostics

### Invalid Token

In case you have referenced to that section, something went wrong with the encryption key,
Encryption key should be located in `.storage/shinobi.config.json` file under `data.key` property,
below are the steps to solve that issue.

#### File not exists or File exists, data.key is not

Please report as issue

#### File exists, data.key is available

Example:

```json
{
  "version": 1,
  "minor_version": 1,
  "key": "shinobi.config.json",
  "data": {
    "key": "ox-qQsAiHb67Kz3ypxY19uU2_YwVcSjvdbaBVHZJQFY="
  }
}
```

OR

```json
{
  "version": 1,
  "minor_version": 1,
  "key": "shinobi.config.json",
  "data": {
    "key": "ox-qQsAiHb67Kz3ypxY19uU2_YwVcSjvdbaBVHZJQFY="
  }
}
```

1. Remove the integration
2. Delete the file
3. Restart HA
4. Try to re-add the integration
5. If still happens - report as issue

#### File exists, key is available under one of the entry configurations

Example:

```json
{
  "version": 1,
  "minor_version": 1,
  "key": "shinobi.config.json",
  "data": {
    "b8fa11c50331d2647b8aa7e37935efeb": {
      "key": "ox-qQsAiHb67Kz3ypxY19uU2_YwVcSjvdbaBVHZJQFY="
    }
  }
}
```

1. Move the `key` to the root of the JSON
2. Restart HA
3. Try to re-add the integration
4. If still happens - follow instructions of section #1 (_i._)
