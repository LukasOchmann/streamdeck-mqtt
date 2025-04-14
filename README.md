# Streamdeck MQTT

I created this project because i wanted to have an stream deck as an controller for 
home assistant. I found (this streamdeck)[https://github.com/timothycrosley/streamdeck-ui].


## Usage 

Use an Raspberry PI or Raspberry Pi Zero W and connect the streamdeck.
There is a docker-image:

```sh
  docker run -t -i --privileged -v /dev/bus/usb:/dev/bus/usb -v ./data.json:/app/data.json streamdeck-mqtt:latest
```

You can either mount all usb devices or just the one you need.
Create a data.json that is empty, this wipp persist the config of the Keys.


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

#### `streamdeck/brightness` & `streandeck/<serialNumber>/brightness`

It updates the brightness. Valid are values between 0 and 100 where 0 means off and 100 means full brightness.
Payload type Int.

The value will be persisted in the `data.json`. 

#### `streamdeck/sleep` & `streandeck/<serialNumber>/sleep`

Just a shortcut to set the brightness to 0.

#### `streamdeck/wake` & `streandeck/<serialNumber>/wake`

Sets the brightness to te last set brightness from the `data.json`.

#### `streamdeck/config` & `streandeck/<serialNumber>/config`

Will override all keys. The payload has the same Schema as the Keys in the `data.json`.

#### `streamdeck/config/<keyIdx>` & `streandeck/<serialNumber>/config/<keyIdx>`

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

