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
import codecs
import xml.etree.ElementTree



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

        try:
            with open('data.json') as f:
                self.config = json.load(f)
        except Exception:
            print("No data.json sry", Exception)
            self.config = {
                "brightness": 60,
                "keys": []
            }

            for i in range(self.deck.key_count()):
                print("create {}".format(i))
                self.config["keys"].append({})
                
            pass
        finally:
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

    # Rest des Codes bleibt gleich...
    # [Previous methods: render_key_image, key_change_callback, set_button_action, etc.]

    def stop(self):
        if hasattr(self, 'deck') and self.deck:
            self.deck.reset()
            self.deck.close()
        if hasattr(self, 'mqtt_client'):
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()

    def init(self):
        if self.deck:
            print("with deck")
            self.deck.open()
            self.deck.reset()
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
            self.mqtt_client.loop_forever()
        

            # Wait until all application threads have terminated (for this example,
            # this is when all deck handles are closed).
            for t in threading.enumerate():
                try:
                    t.join()
                except RuntimeError:
                    pass
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
        self.deck.set_brightness(brightness)
        self.config["brightness"] = brightness
        with open('data.json', 'w') as f:
            json.dump(self.config, f)
    
    def sleep(self):
        self.deck.set_brightness(0)
    
    def wake(self):
        self.update_brightness(self.config["brightness"])

    def update_config(self, payload):
        try:
            config = json.loads(payload)
            self.config["keys"] = config
            with open('data.json', 'w') as f:
                json.dump(self.config, f)
            self.update_keys()
        except Exception as e:
            print("could not validate Payload", e)

    def update_config_key(self, payload, key):
        try: 
            config = json.loads(payload)
            self.config["keys"][key] = config
            self.update_key(key)
            with open('data.json', 'w') as f:
                json.dump(self.config, f)
        except Exception as e:
            print("could not validate Payload", e)

    def update_key(self, key):
        key_width, key_height = self.deck.key_image_format()['size']
        key_config = self.config["keys"][key]
        icon_string = key_config["icon"]
        try: 
            if icon_string.startswith("mdi:"):
                response = requests.get(iconDownloadPath.format(icon_string.split(":").pop()))
                icon = response.content
                et = xml.etree.ElementTree.fromstring(response.content)
                if "color" in key_config:
                    color = key_config["color"]
                else:
                    color = "blue"
                et.attrib["fill"] = color

                icon = xml.etree.ElementTree.tostring(et)
                icon_image = svg2png(bytestring=icon, output_height=key_height, output_width=key_width, scale=2)
            else:
                icon_image = svg2png(bytestring=icon_string, output_height=key_height, output_width=key_width, scale=2)
            icon = Image.open(io.BytesIO(icon_image))
            key_image = PILHelper.create_key_image(self.deck)
            key_image.paste(icon)
            self.deck.set_key_image(key, PILHelper.to_native_key_format(self.deck, key_image))
        except Exception as e:
            print("could not update key {}".format(key), e)

    def update_keys(self):
        keys_config = self.config["keys"]
        for idx, c in enumerate(keys_config):
            if bool(c):
                self.update_key(idx)
            

    def key_change_callback(self, deck, key, state):
        # Use a scoped-with on the deck to ensure we're the only thread using it
        # right now.
        with deck:
            self.mqtt_client.publish("streamdeck/{}".format(key))
            self.mqtt_client.publish("streamdeck/{}/{}".format(key, "down" if state else "up"))
            self.mqtt_client.publish("streamdeck/{}/{}".format(deck.get_serial_number(), key))
            self.mqtt_client.publish("streamdeck/{}/{}/{}".format(deck.get_serial_number(), key, "down" if state else "up"))

    
        