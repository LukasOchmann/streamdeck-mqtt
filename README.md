# Streamdeck MQTT

I created this project because i wanted to have an stream deck as an controller for
home assistant. It is using this [library](https://github.com/abcminiuser/python-elgato-streamdeck#python-elgato-stream-deck-library)


## Hardware

| Part | Notes |
| --- | --- |
| Elgato Stream Deck | Original, Original V2, MK.2, Mini, Mini MK.2, XL, XL V2, Neo, Plus and Pedal are supported by the underlying [python-elgato-streamdeck](https://github.com/abcminiuser/python-elgato-streamdeck) library |
| Raspberry Pi | Anything that can run the prebuilt images: `arm64` (Pi 3/4/5, Pi Zero 2 W with a 64-bit OS) or `arm/v7` (Pi 2/3, Pi Zero 2 W with a 32-bit OS). The **original** Pi Zero / Zero W is ARMv6 and is *not* covered by the prebuilt images — you would have to build the image yourself on that hardware |
| microSD card | 8 GB or more, for Raspberry Pi OS Lite |
| Power supply | The official supply for your Pi model |
| USB OTG adapter | Only for the Pi Zero 2 W: micro-USB (male) to USB-A (female), plugged into the **middle** port labelled `USB`, not the one labelled `PWR` |
| Powered USB hub | Recommended, especially for the larger decks (XL, MK.2). The Stream Deck is fed from the Pi's USB port, and an unpowered Zero 2 W port can be marginal — if the deck resets or is not detected reliably, a powered hub usually fixes it |

Everything below uses a Raspberry Pi Zero 2 W as the example, but the steps are
identical on any other Pi.

## Setting up a Raspberry Pi Zero 2 W

### 1. Flash the OS

Use the [Raspberry Pi Imager](https://www.raspberrypi.com/software/) and pick
**Raspberry Pi OS Lite (64-bit)** — no desktop needed, and the 64-bit build pulls
the `arm64` image. In the Imager's settings dialog (the gear / "Edit settings")
configure before writing:

- hostname (e.g. `streamdeck`)
- username and password
- Wi-Fi SSID and password — the Zero 2 W only supports **2.4 GHz** networks
- enable SSH

Write the card, put it into the Pi, connect the Stream Deck through the OTG
adapter (or the powered hub) and power the Pi up.

### 2. Log in and update

```sh
ssh <user>@streamdeck.local
sudo apt update && sudo apt full-upgrade -y
```

### 3. Install Docker

```sh
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

Log out and back in so the group membership applies.

### 4. Allow access to the Stream Deck

The container runs as a non-root user, so the USB device node has to be
readable/writable for it. Add a udev rule on the **host** for Elgato's vendor id
`0fd9`:

```sh
sudo tee /etc/udev/rules.d/99-streamdeck.rules > /dev/null <<'EOF'
SUBSYSTEM=="usb", ATTRS{idVendor}=="0fd9", MODE="0666"
EOF

sudo udevadm control --reload-rules
sudo udevadm trigger
```

Unplug and replug the Stream Deck afterwards, then verify it is there:

```sh
lsusb | grep -i elgato
```

### 5. Configure and start the service

```sh
mkdir -p ~/streamdeck && cd ~/streamdeck
echo '{}' > data.json
```

Create a `.env` file (see [MQTT settings](#mqtt-settings)) and a `compose.yaml`
as shown below, then:

```sh
docker compose up -d
docker compose logs -f
```

The log prints the deck type, key count and the serial number — you need that
serial number if you want to address this deck individually via MQTT.

## Usage

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


