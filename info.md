# Shinobi Video NVR

## Description

Integration with Shinobi Video NVR. Creates the following components:

* Camera - per-camera defined.
* Binary Sensors (MOTION, SOUND) - per-camera defined.
* Support HLS Streams instead of H264.
* Support SSL with self-signed certificate.

[Changelog](https://github.com/elad-bar/ha-shinobi/blob/master/CHANGELOG.md)

## How to

#### Requirements
- Shinobi Video Server available with credentials
- MQTT Integration is optional - it will allow listening to Shinobi Video event

#### Shinobi links:
- [Using MQTT to receive and trigger events](https://hub.shinobi.video/articles/view/xEMps3O4y4VEaYk)
- [How to use Motion Detection](https://hub.shinobi.video/articles/view/LKdcgcgWy9RJfUh)


#### Installations via HACS
Currently, repository is not under official HACS repo, in order to install, you will need to add manually the repository

Look for "Shinobi Video NVR" and install

#### Integration settings
###### Basic configuration (Configuration -> Integrations -> Add Shinobi Video NVR)
Fields name | Type | Required | Default | Description
--- | --- | --- | --- | --- |
Host | Texbox | + | None | Hostname or IP address of the Shinobi Video server
Port | Textbox | + | 0 | HTTP Port to access Shinobi Video server
SSL | Check-box | + | Unchecked | Is SSL supported?
Username | Textbox | - | | Username of admin user for Shinobi Video server
Password | Textbox | - | | Password of admin user for Shinobi Video server

###### Integration options (Configuration -> Integrations -> Shinobi Video NVR Integration -> Options)
Fields name | Type | Required | Default | Description
--- | --- | --- | --- | --- |
Host | Texbox | + | ast stored hostname | Hostname or IP address of the Shinobi Video server
Port | Textbox | + | 0ast stored port | HTTP Port to access Shinobi Video server
SSL | Check-box | + | Last stored SSL flag | Is SSL supported?
Username | Textbox | - | Last stored username | Username of admin user for Shinobi Video server
Password | Textbox | - | Last stored password | Password of admin user for Shinobi Video server
Log level | Drop-down | + | Default | Changes component's log level (more details below)

**Log Level's drop-down**
New feature to set the log level for the component without need to set log_level in `customization:` and restart or call manually `logger.set_level` and loose it after restart.

Upon startup or integration's option update, based on the value chosen, the component will make a service call to `logger.set_level` for that component with the desired value,

In case `Default` option is chosen, flow will skip calling the service, after changing from any other option to `Default`, it will not take place automatically, only after restart

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
Binary sensor are relying on MQTT, you will need to set up in Shinobi Video Server MQTT plugin and configure each of the monitors to trigger MQTT message.

Each binary sensor will have the name pattern - {Integration Title} {Camera Name} {Sound / Motion},
Once triggered, the following details will be added to the attributes of the binary sensor:

Attributes | Description |
--- | --- |
name | Event name - Yolo / audio
reason | Event details - object / soundChange
tags | relevant for motion only with object detection, will represent the detected object


###### Audio
Represents whether the camera is triggered for noise or not

###### Motion
Represents whether the camera is triggered for motion or not

###### Camera
State: Idle

Attributes | Available values |
--- | --- |
Status | Recording,
Mode | stop (Disabled), start (Watch-Only), record (Record)
Type | H264, MJPEG,
FPS | -
