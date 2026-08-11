import paho.mqtt.client as mqtt
from cairosvg import svg2png
import threading
import signal
import json
import sys
import re
from StreamDeck.ImageHelpers import PILHelper
from PIL import Image, ImageDraw, ImageFont
import io
import requests
import defusedxml.ElementTree as ET


DEFAULT_BRIGHTNESS = 60
DEFAULT_ICON_COLOR = "blue"
DEFAULT_LABEL_COLOR = "white"
DEFAULT_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
DEFAULT_FONT_SIZE = 14
ICON_HEIGHT_RATIO = 0.65
ICON_DOWNLOAD_TIMEOUT = 5
CONFIG_FILE = "data.json"

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
            self.config = {"brightness": DEFAULT_BRIGHTNESS, "keys": []}
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {CONFIG_FILE}: {e}")
            self.config = {"brightness": DEFAULT_BRIGHTNESS, "keys": []}
        except Exception as e:
            print(f"Error loading configuration: {e}")
            self.config = {"brightness": DEFAULT_BRIGHTNESS, "keys": []}

        for i in range(self.deck.key_count()):
            if i >= len(self.config["keys"]):
                self.config["keys"].append({})

        self.init()

        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        print("\nShutting down...")
        self.running = False
        self.stop()
        sys.exit(0)

    def stop(self):
        if hasattr(self, 'deck') and self.deck:
            try:
                self.deck.reset()
                self.deck.close()
            except Exception:
                pass
        if hasattr(self, 'mqtt_client'):
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()

    def _save_config(self):
        with self.config_lock:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)

    def init(self):
        self.deck.reset()
        self.deck.set_brightness(self.config.get("brightness", DEFAULT_BRIGHTNESS))

        serialNumber = self.deck.get_serial_number()

        topics = [
            "streamdeck/brightness",
            f"streamdeck/{serialNumber}/brightness",
            "streamdeck/sleep",
            f"streamdeck/{serialNumber}/sleep",
            "streamdeck/wake",
            f"streamdeck/{serialNumber}/wake",
            "streamdeck/config",
            f"streamdeck/{serialNumber}/config",
        ]
        for t in topics:
            self.mqtt_client.subscribe(t)

        for idx in range(0, self.deck.key_count()):
            self.mqtt_client.subscribe(f"streamdeck/config/{idx}")
            self.mqtt_client.subscribe(f"streamdeck/{serialNumber}/config/{idx}")

        self.deck.set_key_callback(self.key_change_callback)
        self.update_keys()
        self.mqtt_client.on_message = self.on_message

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        try:
            if topic.endswith("/brightness"):
                self.update_brightness(int(msg.payload))
            elif topic.endswith("/sleep"):
                self.sleep()
            elif topic.endswith("/wake"):
                self.wake()
            elif topic.endswith("/config"):
                self.update_config(msg.payload)
            elif any(topic.endswith(f"/config/{x}") for x in range(0, self.deck.key_count())):
                self.update_config_key(msg.payload, int(topic.split('/').pop()))
        except Exception as e:
            print(f"Error handling message on topic {topic}: {e}")

    def update_brightness(self, brightness):
        try:
            brightness_int = int(brightness)
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
            if not 0 <= key < self.deck.key_count():
                print(f"Error: key index {key} out of range")
                return
            with self.config_lock:
                self.config["keys"][key] = config
            self._save_config()
            self.update_key(key)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON payload for key {key}: {e}")
        except Exception as e:
            print(f"Error updating key {key}: {e}")

    def _render_icon(self, icon_string, color, width, height):
        """Render an SVG icon (mdi: reference or raw SVG) to a PIL Image."""
        if icon_string.startswith("mdi:"):
            icon_name = icon_string.split(":").pop()
            if not re.match(r'^[a-z0-9-]+$', icon_name):
                raise ValueError(f"Invalid icon name '{icon_name}'")
            response = requests.get(
                iconDownloadPath.format(icon_name),
                timeout=ICON_DOWNLOAD_TIMEOUT
            )
            response.raise_for_status()
            et = ET.fromstring(response.content)
            et.attrib["fill"] = color
            svg_bytes = ET.tostring(et)
        else:
            svg_bytes = icon_string.encode() if isinstance(icon_string, str) else icon_string

        png_bytes = svg2png(bytestring=svg_bytes, output_width=width, output_height=height, scale=2)
        return Image.open(io.BytesIO(png_bytes))

    def _get_font(self):
        try:
            return ImageFont.truetype(DEFAULT_FONT_PATH, DEFAULT_FONT_SIZE)
        except Exception:
            return ImageFont.load_default()

    def _draw_label(self, key_image, label, label_color, key_width, y_position):
        """Draw centered text label(s) starting at the given y position. Supports multi-line via \\n."""
        font = self._get_font()
        draw = ImageDraw.Draw(key_image)
        lines = label.split("\n")

        # Consistent line height regardless of which characters are in each line
        line_bbox = draw.textbbox((0, 0), "Ag", font=font)
        line_height = line_bbox[3] - line_bbox[1] + 2

        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            text_x = max(0, (key_width - text_width) // 2)
            text_y = y_position + (i * line_height)
            draw.text((text_x, text_y), line, fill=label_color, font=font)

    def update_key(self, key):
        key_width, key_height = self.deck.key_image_format()['size']
        with self.config_lock:
            key_config = self.config["keys"][key]
        if not key_config:
            return

        icon_string = key_config.get("icon")
        label = key_config.get("label")

        if not icon_string and not label:
            return

        try:
            key_image = PILHelper.create_key_image(self.deck)
            color = key_config.get("color", DEFAULT_ICON_COLOR)
            label_color = key_config.get("label_color", DEFAULT_LABEL_COLOR)

            if icon_string and label:
                # Icon + label: shrink icon to top portion, label below
                icon_h = int(key_height * ICON_HEIGHT_RATIO)
                icon = self._render_icon(icon_string, color, key_width, icon_h)
                paste_x = (key_width - icon.width) // 2
                key_image.paste(icon, (paste_x, 0))
                label_y = icon_h + 2
                self._draw_label(key_image, label, label_color, key_width, label_y)
            elif icon_string:
                # Icon only
                icon = self._render_icon(icon_string, color, key_width, key_height)
                key_image.paste(icon)
            else:
                # Label only: center vertically (handles multi-line)
                font = self._get_font()
                draw = ImageDraw.Draw(key_image)
                line_bbox = draw.textbbox((0, 0), "Ag", font=font)
                line_height = line_bbox[3] - line_bbox[1] + 2
                num_lines = len(label.split("\n"))
                total_height = line_height * num_lines
                label_y = max(0, (key_height - total_height) // 2)
                self._draw_label(key_image, label, label_color, key_width, label_y)

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
        with deck:
            if state == False:
                self.mqtt_client.publish(f"streamdeck/{key}")
                self.mqtt_client.publish(f"streamdeck/{deck.get_serial_number()}/{key}")
            self.mqtt_client.publish(f"streamdeck/{key}/{'down' if state else 'up'}")
            self.mqtt_client.publish(f"streamdeck/{deck.get_serial_number()}/{key}/{'down' if state else 'up'}")
