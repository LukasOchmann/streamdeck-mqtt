# Streamdeck MQTT

I created this project because i wanted to have an stream deck as an controller for
home assistant. I found (this streamdeck)[https://github.com/timothycrosley/streamdeck-ui].


## Usage

Use a Raspberry Pi or Raspberry Pi Zero W and connect the Stream Deck.

### Docker Images

Pre-built Docker images are available from GitHub Container Registry for multiple architectures:
- `linux/amd64` (x86_64)
- `linux/arm64` (Raspberry Pi 4, Pi 400)
- `linux/arm/v7` (Raspberry Pi 3, Pi Zero 2 W)

Available tags:
- `latest` - Latest stable release from main branch
- `main` - Latest commit on main branch
- `develop` - Latest commit on develop branch
- `v1.0.0` - Specific version tags
- `<branch-name>` - Latest commit from any branch

### Using Docker Run

```sh
docker run -d \
  --device /dev/bus/usb:/dev/bus/usb \
  --cap-add=SYS_RAWIO \
  --env-file .env \
  -v ./data.json:/app/data.json \
  ghcr.io/lukasochmann/streamdeck-mqtt:latest
```

### Using Docker Compose

```yaml
services:
  streamdeck:
    image: ghcr.io/lukasochmann/streamdeck-mqtt:latest
    devices:
      - /dev/bus/usb:/dev/bus/usb
    cap_add:
      - SYS_RAWIO
    volumes:
      - ./data.json:/app/data.json
    env_file:
      - .env
    restart: unless-stopped
```

You can either mount all USB devices or just the one you need.
Create a data.json file (can be empty initially), this will persist the config of the keys.


## Data.json

| key | type |  | description |
| --- | --- | --- | --- |
| brightness | number[0 - 100] | required | The brightness that should be displayed |
| keys | array | required | Configuration per key |


### keys

| key | type | | description |
| ---| --- |  --- | --- |
| type | enum("icon") | required | currently unused, but required to be "icon" |
| icon | string | required | a mdi string from home assistant like mdi:lightbulb or actual svg content |
| color | hex color or color name | optional | that color will be set to fill the mdi icon or svg. Defaults to "blue" |

## MQTT settings

To Configure the MQTT-Client there are Environment Variables.

|name||Description|
| --- | --- | --- |
| MQTT_HOST | required | the host address of what MQTT Broker you will use |
| MQTT_PORT| optional; default 1883 | If you do different port then 1883 u can use this to change it |
| MQTT_USER | required | The user-name that is registered at the broker |
| MQTT_PASS | optional (i guess) | You can omit the password if you have an unsecured broker |

## Topics

### Subscribe

The service subscribes the main topic `streamdeck/` and `streamdeck/<serialNumber>/`.
If you want to run multiple instances you should send the versions with <serialNumber>.

#### `streamdeck/brightness` & `streamdeck/<serialNumber>/brightness`

It updates the brightness. Valid are values between 0 and 100 where 0 means off and 100 means full brightness.
Payload type Int.

The value will be persisted in the `data.json`.

#### `streamdeck/sleep` & `streamdeck/<serialNumber>/sleep`

Just a shortcut to set the brightness to 0.

#### `streamdeck/wake` & `streamdeck/<serialNumber>/wake`

Sets the brightness to the last set brightness from the `data.json`.

#### `streamdeck/config` & `streamdeck/<serialNumber>/config`

Will override all keys. The payload has the same Schema as the Keys in the `data.json`.

#### `streamdeck/config/<keyIdx>` & `streamdeck/<serialNumber>/config/<keyIdx>`

It updates the one key by the index. Please see the key-schema.

### Publish

Every key-press will publish the following Topics

Use
`streamdeck/<key>` or 
`streamdeck/<key>/<serialNumber>`
for regular button push events.

If you want to use keys as a e.g. dimmer you can listen to
`streamdeck/<key>/down`
`streamdeck/<key>/<serialNumber>/down`
and
`streamdeck/<key>/up`
`streamdeck/<key>/<serialNumber>/up`

