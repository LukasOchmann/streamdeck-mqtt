from StreamDeck.DeviceManager import DeviceManager
import paho.mqtt.client as mqtt
from cairosvg import svg2png
import threading
import signal
import json
import sys
import os
from types import SimpleNamespace
from jsonschema import validate
from StreamDeck.ImageHelpers import PILHelper
from PIL import Image
import io
import requests
import xml.etree.ElementTree



# Configuration constants
DEFAULT_BRIGHTNESS = 60
DEFAULT_ICON_COLOR = "blue"
ICON_DOWNLOAD_TIMEOUT = 5
CONFIG_FILE = "data.json"

keySchema = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",

        },
        "icon": {"type": "string"},
    },
    "required": ["icon", "type"]
}

keyCollectionSchema = {
    "type": "array",
    "items": keySchema
}


iconDownloadPath = "https://raw.githubusercontent.com/Templarian/MaterialDesign-SVG/refs/heads/master/svg/{}.svg"

class StreamDeckMQTT:
    def __init__(self, mqttClient, deck):
        self.running = True
        self.mqtt_client = mqttClient
        self.deck = deck
        self.config_lock = threading.Lock()

        try:
            with open(CONFIG_FILE) as f:
                self.config = json.load(f)
        except FileNotFoundError:
            print(f"Warning: {CONFIG_FILE} not found, using default configuration")
            self.config = {
                "brightness": DEFAULT_BRIGHTNESS,
                "keys": []
            }
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {CONFIG_FILE}: {e}")
            self.config = {
                "brightness": DEFAULT_BRIGHTNESS,
                "keys": []
            }
        except Exception as e:
            print(f"Error loading configuration: {e}")
            self.config = {
                "brightness": DEFAULT_BRIGHTNESS,
                "keys": []
            }

        # Initialize missing keys (fixed off-by-one error: i >= instead of i >)
        for i in range(self.deck.key_count()):
            if i >= len(self.config["keys"]):
                print(f"Initializing key {i}")
                self.config["keys"].append({})

        print("continue")
        # Stream Deck Setup
        self.init()

        # Signal Handler
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)



    def signal_handler(self, signum, frame):
        print("\nShutting down...")
        self.running = False
        self.stop()
        sys.exit(0)

    def stop(self):
        if hasattr(self, 'deck') and self.deck:
            self.deck.reset()
            self.deck.close()
        if hasattr(self, 'mqtt_client'):
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()

    def _save_config(self):
        """Thread-safe config save"""
        with self.config_lock:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)

    def init(self):
        if self.deck:
            print("with deck")
            
            #self.deck.reset()
            self.deck.set_brightness(100)

            serialNumber = self.deck.get_serial_number()
            self.mqtt_client.subscribe("streamdeck/")
            self.mqtt_client.subscribe("streamdeck/{}".format(serialNumber))

            self.mqtt_client.subscribe("streamdeck/brightness")
            self.mqtt_client.subscribe("streamdeck/{}/brightness".format(serialNumber))

            self.mqtt_client.subscribe("streamdeck/sleep")
            self.mqtt_client.subscribe("streamdeck/{}/sleep".format(serialNumber))

            self.mqtt_client.subscribe("streamdeck/wake")
            self.mqtt_client.subscribe("streamdeck/{}/wake".format(serialNumber))

            self.mqtt_client.subscribe("streamdeck/config")
            self.mqtt_client.subscribe("streamdeck/{}/config".format(serialNumber))

            for idx in range(0, self.deck.key_count()):
                self.mqtt_client.subscribe("streamdeck/config/{}".format(idx))
                self.mqtt_client.subscribe("streamdeck/{}/config/{}".format(serialNumber, idx))
           
            
            self.deck.open()
            self.deck.reset()
            self.deck.set_key_callback(self.key_change_callback)

            
                

            self.update_keys()

            self.mqtt_client.on_message = self.on_message
        else:
            print("no deck")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        if topic.endswith("/brightness"):
            self.update_brightness(int(msg.payload))
        elif topic.endswith("/sleep"):
            self.sleep()
        elif topic.endswith("/wake"):
            self.wake()
        elif topic.endswith("/config"):
            self.update_config(msg.payload)
        elif any(True for x in range(0, self.deck.key_count()) if topic.endswith("/config/{}".format(x))):
            self.update_config_key(msg.payload, int(topic.split('/').pop()))
    
    def update_brightness(self, brightness):
        """Update brightness with validation"""
        try:
            brightness_int = int(brightness)
            if not 0 <= brightness_int <= 100:
                print(f"Warning: Brightness {brightness_int} out of range [0, 100], clamping")
                brightness_int = max(0, min(100, brightness_int))

            self.deck.set_brightness(brightness_int)
            with self.config_lock:
                self.config["brightness"] = brightness_int
            self._save_config()
        except (ValueError, TypeError) as e:
            print(f"Error: Invalid brightness value '{brightness}': {e}")
    
    def sleep(self):
        self.deck.set_brightness(0)
    
    def wake(self):
        with self.config_lock:
            brightness = self.config["brightness"]
        self.update_brightness(brightness)

    def update_config(self, payload):
        try:
            config = json.loads(payload)
            with self.config_lock:
                self.config["keys"] = config
            self._save_config()
            self.update_keys()
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON payload: {e}")
        except Exception as e:
            print(f"Error updating config: {e}")

    def update_config_key(self, payload, key):
        try:
            config = json.loads(payload)
            with self.config_lock:
                self.config["keys"][key] = config
            self._save_config()
            self.update_key(key)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON payload for key {key}: {e}")
        except Exception as e:
            print(f"Error updating key {key}: {e}")

    def update_key(self, key):
        key_width, key_height = self.deck.key_image_format()['size']
        with self.config_lock:
            key_config = self.config["keys"][key]
        icon_string = key_config["icon"]
        try:
            if icon_string.startswith("mdi:"):
                response = requests.get(
                    iconDownloadPath.format(icon_string.split(":").pop()),
                    timeout=ICON_DOWNLOAD_TIMEOUT
                )
                response.raise_for_status()
                icon = response.content
                et = xml.etree.ElementTree.fromstring(response.content)
                if "color" in key_config:
                    color = key_config["color"]
                else:
                    color = DEFAULT_ICON_COLOR
                et.attrib["fill"] = color

                icon = xml.etree.ElementTree.tostring(et)
                icon_image = svg2png(bytestring=icon, output_height=key_height, output_width=key_width, scale=2)
            else:
                icon_image = svg2png(bytestring=icon_string, output_height=key_height, output_width=key_width, scale=2)
            icon = Image.open(io.BytesIO(icon_image))
            key_image = PILHelper.create_key_image(self.deck)
            key_image.paste(icon)
            self.deck.set_key_image(key, PILHelper.to_native_key_format(self.deck, key_image))
        except requests.Timeout:
            print(f"Error: Timeout downloading icon for key {key}")
        except requests.RequestException as e:
            print(f"Error: Failed to download icon for key {key}: {e}")
        except Exception as e:
            print(f"Error: Could not update key {key}: {e}")

    def update_keys(self):
        with self.config_lock:
            keys_config = self.config["keys"].copy()
        for idx, c in enumerate(keys_config):
            if c:
                self.update_key(idx)
            

    def key_change_callback(self, deck, key, state):
        # Use a scoped-with on the deck to ensure we're the only thread using it
        # right now.
        with deck:
            if state == False:
                self.mqtt_client.publish("streamdeck/{}".format(key))
                self.mqtt_client.publish("streamdeck/{}/{}".format(deck.get_serial_number(), key))
            
            self.mqtt_client.publish("streamdeck/{}/{}".format(key, "down" if state else "up"))
            self.mqtt_client.publish("streamdeck/{}/{}/{}".format(deck.get_serial_number(), key, "down" if state else "up"))

    
        