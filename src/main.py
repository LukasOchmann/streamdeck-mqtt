#!/usr/bin/env python3

import os
import threading
import time
import sys

from dotenv import load_dotenv
from StreamDeck.DeviceManager import DeviceManager
from StreamDeckMQTT import StreamDeckMQTT

import paho.mqtt.client as mqtt


def print_deck_info(index, deck):
    print("Deck {} - {}.".format(index, deck.deck_type()))
    print("\t - ID: {}".format(deck.id()))
    print("\t - Serial: '{}'".format(deck.get_serial_number()))
    print("\t - Firmware Version: '{}'".format(deck.get_firmware_version()))
    print("\t - Key Count: {} (in a {}x{} grid)".format(
        deck.key_count(),
        deck.key_layout()[0],
        deck.key_layout()[1]))


if __name__ == "__main__":
    try:
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

        deck_handlers = []

        for index, deck in enumerate(streamdecks):
            if not deck.is_visual():
                continue

            try:
                deck.open()

                mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
                mqttc.username_pw_set(MQTT_USER, MQTT_PASS)

                connected_event = threading.Event()

                def on_connect(client, userdata, flags, reason_code, properties):
                    if reason_code == 0:
                        print(f"MQTT connected (rc={reason_code})")
                        connected_event.set()
                    else:
                        print(f"MQTT connect failed (rc={reason_code})")

                mqttc.on_connect = on_connect
                mqttc.connect(MQTT_HOST, MQTT_PORT, 60)
                mqttc.loop_start()

                if not connected_event.wait(timeout=10):
                    print(f"Error: MQTT connection timeout for deck {index}")
                    continue

                print_deck_info(index, deck)
                handler = StreamDeckMQTT(mqttc, deck)
                deck_handlers.append(handler)

            except Exception as e:
                print(f"Error initializing deck {index}: {e}")
                continue

        if not deck_handlers:
            print("No decks successfully initialized. Exiting.")
            sys.exit(1)

        print("\nStreamDeck MQTT bridge running. Press Ctrl+C to exit.\n")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            for handler in deck_handlers:
                handler.stop()

    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
