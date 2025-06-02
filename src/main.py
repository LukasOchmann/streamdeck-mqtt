
#!/usr/bin/env python3

#         Python Stream Deck Library
#      Released under the MIT license
#
#   dean [at] fourwalledcubicle [dot] com
#         www.fourwalledcubicle.com
#

# Example script showing how to tile a larger image across multiple buttons, by
# first generating an image suitable for the entire deck, then cropping out and
# applying key-sized tiles to individual keys of a StreamDeck.

import os
import threading
import json

from dotenv import load_dotenv
from PIL import Image, ImageOps
from StreamDeck.DeviceManager import DeviceManager
from StreamDeckMQTT import StreamDeckMQTT

import paho.mqtt.client as mqtt

streamdeckConfiguration = {}


def print_deck_info(index, deck):
    key_image_format = deck.key_image_format()
    touchscreen_image_format = deck.touchscreen_image_format()

    flip_description = {
        (False, False): "not mirrored",
        (True, False): "mirrored horizontally",
        (False, True): "mirrored vertically",
        (True, True): "mirrored horizontally/vertically",
    }

    print("Deck {} - {}.".format(index, deck.deck_type()))
    print("\t - ID: {}".format(deck.id()))
    print("\t - Serial: '{}'".format(deck.get_serial_number()))
    print("\t - Firmware Version: '{}'".format(deck.get_firmware_version()))
    print("\t - Key Count: {} (in a {}x{} grid)".format(
        deck.key_count(),
        deck.key_layout()[0],
        deck.key_layout()[1]))
    if deck.is_visual():
        print("\t - Key Images: {}x{} pixels, {} format, rotated {} degrees, {}".format(
            key_image_format['size'][0],
            key_image_format['size'][1],
            key_image_format['format'],
            key_image_format['rotation'],
            flip_description[key_image_format['flip']]))

        if deck.is_touch():
            print("\t - Touchscreen: {}x{} pixels, {} format, rotated {} degrees, {}".format(
                touchscreen_image_format['size'][0],
                touchscreen_image_format['size'][1],
                touchscreen_image_format['format'],
                touchscreen_image_format['rotation'],
                flip_description[touchscreen_image_format['flip']]))
    else:
        print("\t - No Visual Output")


if __name__ == "__main__":
    streamdecks = DeviceManager().enumerate()

    print("Found {} Stream Deck(s).\n".format(len(streamdecks)))

    load_dotenv()

    REQUIRED_VARS = ["MQTT_USER", "MQTT_PASS", "MQTT_HOST"]

    for var in REQUIRED_VARS:
        if not os.getenv(var):
            raise EnvironmentError(f"Missing required environment variable: {var}")

    MQTT_USER = os.getenv("MQTT_USER")
    MQTT_PASS = os.getenv("MQTT_PASS")
    MQTT_HOST = os.getenv("MQTT_HOST")
    MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

    for index, deck in enumerate(streamdecks):
        # This example only works with devices that have screens.
        if not deck.is_visual():
            continue
        
        mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        mqttc.username_pw_set(MQTT_USER, MQTT_PASS)


        mqttc.connect(MQTT_HOST, MQTT_PORT, 60)

        deck.open()
        print_deck_info(index, deck)
        StreamDeckMQTT(mqttc, deck)
        

        