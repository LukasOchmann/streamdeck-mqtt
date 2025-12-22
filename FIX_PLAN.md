# StreamDeck-MQTT Fix-Plan

Dieser Plan beschreibt, wie die in `CODE_REVIEW.md` identifizierten Probleme behoben werden können.

## 📊 Status-Übersicht

**Letzte Aktualisierung:** 2025-12-04

| Phase | Status | Abgeschlossen | Ausstehend |
|-------|--------|---------------|------------|
| Phase 1: Kritische Fixes | ✅ **100% ABGESCHLOSSEN** | 6/6 | 0/6 |
| Phase 2: Wichtige Fixes | ⏳ Ausstehend | 0/6 | 6/6 |
| Phase 3: Code-Qualität | ⏳ Ausstehend | 0/8 | 8/8 |
| Phase 4: Testing & CI/CD | ⏳ Ausstehend | 0/3 | 3/3 |

### ✅ Abgeschlossene Fixes

- ✅ 1.1 Race Condition beim Schreiben von data.json behoben
- ✅ 1.2 Brightness-Validierung implementiert
- ✅ 1.3 HTTP Request Timeout hinzugefügt
- ✅ 1.4 Container-Sicherheit verbessert
- ✅ 1.5 requirements.txt korrigiert
- ✅ 1.6 Blockierender loop_forever() behoben

### 🔄 In Arbeit

- Keine

### ⏳ Nächste Schritte

- 2.1 Exception-Behandlung verbessern
- 2.2 JSON Schema-Validierung implementieren
- 2.3 Thread-Safety mit Deck-Operationen verbessern

---

## Phase 1: Kritische Fixes ✅ ABGESCHLOSSEN

### 1.1 Race Condition beim Schreiben von data.json beheben ✅

**Status:** ✅ Implementiert am 2025-12-04

**Problem:** Gleichzeitige MQTT-Nachrichten können zu Datenverlust führen.

**Lösung:**
```python
import threading

class StreamDeckMQTT:
    def __init__(self, mqttClient, deck):
        # ...
        self.config_lock = threading.Lock()
        # ...

    def _save_config(self):
        """Thread-safe config save"""
        with self.config_lock:
            with open('data.json', 'w') as f:
                json.dump(self.config, f, indent=2)

    def update_brightness(self, brightness):
        # Validierung hinzufügen (siehe 1.2)
        self.deck.set_brightness(brightness)
        with self.config_lock:
            self.config["brightness"] = brightness
        self._save_config()
```

**Dateien:** `src/StreamDeckMQTT.py`
**Tatsächlicher Aufwand:** ~1 Stunde

---

### 1.2 Brightness-Validierung implementieren ✅

**Status:** ✅ Implementiert am 2025-12-04

**Problem:** Ungültige Brightness-Werte können Hardware-Fehler verursachen.

**Lösung:**
```python
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
```

**Dateien:** `src/StreamDeckMQTT.py`
**Tatsächlicher Aufwand:** ~30 Minuten

---

### 1.3 HTTP Request Timeout hinzufügen ✅

**Status:** ✅ Implementiert am 2025-12-04

**Problem:** Anwendung kann hängen bleiben bei langsamen/nicht-reagierenden Servern.

**Lösung:**
```python
def update_key(self, key):
    # ...
    try:
        if icon_string.startswith("mdi:"):
            # Timeout von 5 Sekunden hinzufügen
            response = requests.get(
                iconDownloadPath.format(icon_string.split(":").pop()),
                timeout=5
            )
            response.raise_for_status()  # HTTP-Fehler als Exception behandeln
            icon = response.content
            # ...
    except requests.Timeout:
        print(f"Error: Timeout downloading icon for key {key}")
    except requests.RequestException as e:
        print(f"Error: Failed to download icon for key {key}: {e}")
    except Exception as e:
        print(f"Error: Could not update key {key}: {e}")
```

**Dateien:** `src/StreamDeckMQTT.py`
**Tatsächlicher Aufwand:** ~30 Minuten

**Zusätzliche Änderungen:**
- Konstanten hinzugefügt: `ICON_DOWNLOAD_TIMEOUT`, `DEFAULT_ICON_COLOR`, `CONFIG_FILE`
- Hardcoded "blue" durch `DEFAULT_ICON_COLOR` ersetzt

---

### 1.4 Container-Sicherheit verbessern ✅

**Status:** ✅ Implementiert am 2025-12-04

**Problem:** Container läuft als root mit privileged=true.

**Lösung für Dockerfile:**
```dockerfile
FROM python:3.9-slim-bullseye

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 \
    libjpeg62-turbo \
    libhidapi-hidraw0 \
    libusb-1.0-0 \
 && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r streamdeck && useradd -r -g streamdeck streamdeck

# Set working directory
WORKDIR /app

# Copy and install requirements as root
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY ./src ./src

# Change ownership
RUN chown -R streamdeck:streamdeck /app

# Switch to non-root user
USER streamdeck

# Set default command
CMD ["python", "src/main.py"]
```

**Lösung für compose.yaml:**
```yaml
services:
  streamdeck:
    image: "streamdeck-mqtt:0.0.1"
    # privileged: true  # ENTFERNEN
    # network_mode: host  # ENTFERNEN oder auf bridge setzen
    devices:
      - /dev/bus/usb:/dev/bus/usb
    # Spezifische Capabilities statt privileged
    cap_add:
      - SYS_RAWIO
    volumes:
      - ./data.json:/app/data.json
    env_file:
      - .env
    restart: unless-stopped
    # Wenn MQTT im gleichen Compose-Stack:
    # depends_on:
    #   - mqtt
```

**Dateien:** `Dockerfile`, `compose.yaml`, `.dockerignore` (neu erstellt)
**Tatsächlicher Aufwand:** ~1.5 Stunden

**Implementierte Änderungen:**
- Multi-stage Build im Dockerfile
- Non-root User `streamdeck` erstellt
- `privileged: true` entfernt, durch `cap_add: SYS_RAWIO` ersetzt
- `network_mode: host` entfernt
- `restart: unless-stopped` hinzugefügt
- `.dockerignore` Datei erstellt

---

### 1.5 requirements.txt korrigieren ✅

**Status:** ✅ Implementiert am 2025-12-04

**Problem:** attrs Version existiert nicht.

**Lösung:**
```txt
# Aktuelle Version verwenden (Stand 2025)
attrs==23.2.0
cairocffi==1.7.1
CairoSVG==2.7.1
certifi==2024.2.2
cffi==1.17.1
charset-normalizer==3.4.1
cssselect2==0.7.0
defusedxml==0.7.1
idna==3.10
jsonschema==4.23.0
jsonschema-specifications==2024.10.1
paho-mqtt==2.1.0
pillow==11.0.0
pycparser==2.22
python-dotenv==1.0.1
referencing==0.36.2
requests==2.32.3
rpds-py==0.22.3
streamdeck==0.9.6
tinycss2==1.4.0
typing-extensions==4.12.2
urllib3==2.3.0
webencodings==0.5.1
```

**Alternativ:** Versionierte requirements generieren:
```bash
pip freeze > requirements.txt
```

**Dateien:** `requirements.txt`
**Tatsächlicher Aufwand:** ~10 Minuten

**Implementierte Änderungen:**
- `attrs==23.2.0` (war 25.1.0)
- `certifi==2024.2.2` (war 2025.1.31)

---

### 1.6 Blockierender loop_forever() beheben ✅

**Status:** ✅ Implementiert am 2025-12-04

**Problem:** Multi-Deck Support funktioniert nicht, keine saubere Shutdown-Möglichkeit.

**Lösung:**
```python
# In StreamDeckMQTT.__init__
def init(self):
    if self.deck:
        # ... setup code ...

        self.mqtt_client.on_message = self.on_message
        # loop_forever() NICHT hier aufrufen!
        # self.mqtt_client.loop_forever()

# In main.py
if __name__ == "__main__":
    streamdecks = DeviceManager().enumerate()
    print("Found {} Stream Deck(s).\n".format(len(streamdecks)))

    load_dotenv()
    # ... MQTT setup ...

    deck_handlers = []

    for index, deck in enumerate(streamdecks):
        if not deck.is_visual():
            continue

        mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        mqttc.username_pw_set(MQTT_USER, MQTT_PASS)
        mqttc.connect(MQTT_HOST, MQTT_PORT, 60)

        deck.open()
        print_deck_info(index, deck)
        handler = StreamDeckMQTT(mqttc, deck)
        deck_handlers.append(handler)

        # Start MQTT loop in background
        mqttc.loop_start()

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        for handler in deck_handlers:
            handler.stop()
```

**Dateien:** `src/StreamDeckMQTT.py`, `src/main.py`
**Tatsächlicher Aufwand:** ~2 Stunden

**Implementierte Änderungen:**
- `loop_forever()` aus `StreamDeckMQTT.init()` entfernt
- `loop_start()` für Background-MQTT-Loop in main.py hinzugefügt
- Multi-Deck Support implementiert
- Liste `deck_handlers` für sauberes Shutdown
- Bessere Fehlerbehandlung pro Deck
- KeyboardInterrupt Handler für sauberes Beenden
- Zusätzliche Imports: `time`, `sys`

---

## Phase 2: Wichtige Fixes ⏳ AUSSTEHEND

### 2.1 Exception-Behandlung verbessern

**Problem:** Fehlerhafte Exception-Ausgabe.

**Lösung:**
```python
def __init__(self, mqttClient, deck):
    # ...
    try:
        with open('data.json') as f:
            self.config = json.load(f)
    except FileNotFoundError:
        print("Warning: data.json not found, using default configuration")
        self.config = {
            "brightness": 60,
            "keys": []
        }
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in data.json: {e}")
        self.config = {
            "brightness": 60,
            "keys": []
        }
    except Exception as e:
        print(f"Error loading configuration: {e}")
        self.config = {
            "brightness": 60,
            "keys": []
        }

    # finally-Block entfernen, normale Logik hier:
    for i in range(self.deck.key_count()):
        if i >= len(self.config["keys"]):  # >= statt >
            print(f"Initializing key {i}")
            self.config["keys"].append({})

    # ... rest of init ...
```

**Dateien:** `src/StreamDeckMQTT.py`
**Aufwand:** 1 Stunde

---

### 2.2 JSON Schema-Validierung implementieren

**Problem:** Ungültige Konfigurationen werden nicht erkannt.

**Lösung:**
```python
from jsonschema import validate, ValidationError

# Schema verbessern
keySchema = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["icon"]
        },
        "icon": {"type": "string", "minLength": 1},
        "color": {"type": "string"}
    },
    "required": ["icon", "type"]
}

configSchema = {
    "type": "object",
    "properties": {
        "brightness": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100
        },
        "keys": {
            "type": "array",
            "items": {
                "oneOf": [
                    keySchema,
                    {"type": "object", "maxProperties": 0}  # Leeres Objekt erlauben
                ]
            }
        }
    },
    "required": ["brightness", "keys"]
}

def update_config(self, payload):
    try:
        config = json.loads(payload)
        # Validierung hinzufügen
        validate(instance={"keys": config}, schema={"keys": configSchema["properties"]["keys"]})

        # Länge prüfen
        if len(config) > self.deck.key_count():
            print(f"Warning: Config has {len(config)} keys, but deck only has {self.deck.key_count()}")
            config = config[:self.deck.key_count()]

        with self.config_lock:
            self.config["keys"] = config
        self._save_config()
        self.update_keys()
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON payload: {e}")
    except ValidationError as e:
        print(f"Error: Invalid config schema: {e.message}")
    except Exception as e:
        print(f"Error updating config: {e}")

def update_config_key(self, payload, key):
    try:
        config = json.loads(payload)
        # Validierung
        if config:  # Nur validieren wenn nicht leer
            validate(instance=config, schema=keySchema)

        with self.config_lock:
            self.config["keys"][key] = config
        self._save_config()
        self.update_key(key)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON payload: {e}")
    except ValidationError as e:
        print(f"Error: Invalid key config schema: {e.message}")
    except Exception as e:
        print(f"Error updating key {key}: {e}")
```

**Dateien:** `src/StreamDeckMQTT.py`
**Aufwand:** 2 Stunden

---

### 2.3 Thread-Safety mit Deck-Operationen verbessern

**Problem:** Deck-Operationen sind nicht konsistent thread-safe.

**Lösung:**
```python
class StreamDeckMQTT:
    def __init__(self, mqttClient, deck):
        # ...
        self.deck_lock = threading.Lock()
        # ...

    def update_key(self, key):
        with self.deck_lock:
            key_width, key_height = self.deck.key_image_format()['size']
            # ... rest of method ...
            self.deck.set_key_image(key, PILHelper.to_native_key_format(self.deck, key_image))

    def update_brightness(self, brightness):
        # ...
        with self.deck_lock:
            self.deck.set_brightness(brightness_int)
        # ...

    def sleep(self):
        with self.deck_lock:
            self.deck.set_brightness(0)
```

**Dateien:** `src/StreamDeckMQTT.py`
**Aufwand:** 1-2 Stunden

---

### 2.4 Doppelter deck.open() entfernen

**Problem:** Deck wird zweimal geöffnet.

**Lösung:**
```python
# In main.py - deck.open() ENTFERNEN
for index, deck in enumerate(streamdecks):
    if not deck.is_visual():
        continue

    mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqttc.username_pw_set(MQTT_USER, MQTT_PASS)
    mqttc.connect(MQTT_HOST, MQTT_PORT, 60)

    # deck.open()  # DIESE ZEILE ENTFERNEN
    print_deck_info(index, deck)
    handler = StreamDeckMQTT(mqttc, deck)
    # ...

# In StreamDeckMQTT.__init__ wird deck.open() in init() aufgerufen
```

**Dateien:** `src/main.py`
**Aufwand:** 15 Minuten

---

### 2.5 Ungenutzten Import entfernen

**Problem:** codecs wird nicht verwendet.

**Lösung:**
```python
# Zeile 15 entfernen:
# import codecs
```

**Dateien:** `src/StreamDeckMQTT.py`
**Aufwand:** 5 Minuten

---

### 2.6 Bessere Error-Behandlung in main.py

**Problem:** Keine Fehlerbehandlung bei StreamDeckMQTT-Initialisierung.

**Lösung:**
```python
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
                mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
                mqttc.username_pw_set(MQTT_USER, MQTT_PASS)
                mqttc.connect(MQTT_HOST, MQTT_PORT, 60)

                print_deck_info(index, deck)
                handler = StreamDeckMQTT(mqttc, deck)
                deck_handlers.append(handler)
                mqttc.loop_start()
            except Exception as e:
                print(f"Error initializing deck {index}: {e}")
                continue

        if not deck_handlers:
            print("No decks successfully initialized. Exiting.")
            sys.exit(1)

        # Keep alive
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
```

**Dateien:** `src/main.py`
**Aufwand:** 1 Stunde

---

## Phase 3: Code-Qualität Verbesserungen (Mittelfristig)

### 3.1 Logging-Framework implementieren

**Lösung:**
```python
import logging

# In main.py oder separates logging_config.py
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/app/streamdeck.log')
    ]
)

# In StreamDeckMQTT
class StreamDeckMQTT:
    def __init__(self, mqttClient, deck):
        self.logger = logging.getLogger(f"StreamDeckMQTT.{deck.get_serial_number()}")
        # ...
        self.logger.info("Initialized StreamDeck MQTT handler")

    def update_key(self, key):
        try:
            # ...
        except Exception as e:
            self.logger.error(f"Could not update key {key}", exc_info=True)
```

**Dateien:** `src/StreamDeckMQTT.py`, `src/main.py`
**Aufwand:** 3-4 Stunden

---

### 3.2 Type Hints hinzufügen

**Lösung:**
```python
from typing import Dict, List, Any, Optional
import paho.mqtt.client as mqtt
from StreamDeck.Devices.StreamDeck import StreamDeck

class StreamDeckMQTT:
    def __init__(self, mqttClient: mqtt.Client, deck: StreamDeck) -> None:
        self.running: bool = True
        self.mqtt_client: mqtt.Client = mqttClient
        self.deck: StreamDeck = deck
        self.config: Dict[str, Any] = {}
        self.config_lock: threading.Lock = threading.Lock()
        self.deck_lock: threading.Lock = threading.Lock()
        # ...

    def update_brightness(self, brightness: int) -> None:
        # ...

    def update_config(self, payload: bytes) -> None:
        # ...

    def update_key(self, key: int) -> None:
        # ...
```

**Dateien:** `src/StreamDeckMQTT.py`, `src/main.py`
**Aufwand:** 4-6 Stunden

---

### 3.3 Docstrings hinzufügen

**Lösung:**
```python
class StreamDeckMQTT:
    """
    MQTT integration for Elgato Stream Deck devices.

    This class manages the connection between a Stream Deck device and an MQTT broker,
    allowing remote control and configuration of the Stream Deck keys.

    Attributes:
        mqtt_client: MQTT client instance
        deck: StreamDeck device instance
        config: Current device configuration including brightness and key settings
    """

    def __init__(self, mqttClient: mqtt.Client, deck: StreamDeck) -> None:
        """
        Initialize StreamDeck MQTT handler.

        Args:
            mqttClient: Configured MQTT client instance
            deck: Opened StreamDeck device instance

        Raises:
            FileNotFoundError: If data.json is missing (uses default config)
            json.JSONDecodeError: If data.json is invalid (uses default config)
        """
        # ...

    def update_brightness(self, brightness: int) -> None:
        """
        Update the Stream Deck display brightness.

        Args:
            brightness: Brightness level (0-100)

        Note:
            Values outside 0-100 will be clamped. The new value is persisted.
        """
        # ...
```

**Dateien:** Alle Python-Dateien
**Aufwand:** 4-6 Stunden

---

### 3.4 Config und State trennen

**Problem:** data.json mischt Konfiguration und Laufzeit-Zustand.

**Lösung:**
- `config.json`: Statische Konfiguration (keys)
- `state.json`: Runtime-Zustand (brightness, etc.)

```python
def __init__(self, mqttClient, deck):
    # ...
    self.config = self._load_config()
    self.state = self._load_state()
    # ...

def _load_config(self) -> Dict:
    """Load static configuration"""
    try:
        with open('config.json') as f:
            return json.load(f)
    except FileNotFoundError:
        default = {"keys": []}
        self._save_config(default)
        return default

def _load_state(self) -> Dict:
    """Load runtime state"""
    try:
        with open('state.json') as f:
            return json.load(f)
    except FileNotFoundError:
        default = {"brightness": 60}
        self._save_state(default)
        return default

def _save_config(self, config: Dict = None) -> None:
    """Save static configuration"""
    if config is None:
        config = self.config
    with self.config_lock:
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=2)

def _save_state(self, state: Dict = None) -> None:
    """Save runtime state"""
    if state is None:
        state = self.state
    with self.config_lock:
        with open('state.json', 'w') as f:
            json.dump(state, f, indent=2)
```

**Dateien:** `src/StreamDeckMQTT.py`, `compose.yaml` (volumes anpassen)
**Aufwand:** 3-4 Stunden

---

### 3.5 .dockerignore hinzufügen

**Lösung:**
```dockerignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/
bin/
lib/
lib64/
include/
share/
pyvenv.cfg

# Git
.git/
.gitignore

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Project specific
data.json
state.json
config.json
.env
*.log

# Documentation
*.md
!README.md
```

**Dateien:** `.dockerignore` (neu erstellen)
**Aufwand:** 15 Minuten

---

### 3.6 README korrigieren

**Lösung:**
```markdown
# Streamdeck MQTT

I created this project because I wanted to have a Stream Deck as a controller for
Home Assistant. I found [this streamdeck](https://github.com/timothycrosley/streamdeck-ui).

## Usage

Use a Raspberry Pi or Raspberry Pi Zero W and connect the Stream Deck.
There is a docker-image:

```sh
docker run -d -t -i \
  --device /dev/bus/usb \
  --env-file .env \
  -v ./data.json:/app/data.json \
  streamdeck-mqtt:latest
```

You can either mount all USB devices or just the one you need.
Create a data.json that is empty, this will persist the config of the keys.

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

To configure the MQTT-Client there are environment variables.

|name||Description|
| --- | --- | --- |
| MQTT_HOST | required | the host address of what MQTT Broker you will use |
| MQTT_PORT| optional; default 1883 | If you use a different port than 1883 you can use this to change it |
| MQTT_USER | required | The user-name that is registered at the broker |
| MQTT_PASS | optional | You can omit the password if you have an unsecured broker |

## Topics

### Subscribe

The service subscribes to the main topic `streamdeck/` and `streamdeck/<serialNumber>/`.
If you want to run multiple instances you should send the versions with <serialNumber>.

#### `streamdeck/brightness` & `streamdeck/<serialNumber>/brightness`

It updates the brightness. Valid are values between 0 and 100 where 0 means off and 100 means full brightness.
Payload type: Int.

The value will be persisted in the `data.json`.

#### `streamdeck/sleep` & `streamdeck/<serialNumber>/sleep`

Just a shortcut to set the brightness to 0.

#### `streamdeck/wake` & `streamdeck/<serialNumber>/wake`

Sets the brightness to the last set brightness from the `data.json`.

#### `streamdeck/config` & `streamdeck/<serialNumber>/config`

Will override all keys. The payload has the same schema as the keys in the `data.json`.

#### `streamdeck/config/<keyIdx>` & `streamdeck/<serialNumber>/config/<keyIdx>`

It updates the one key by the index. Please see the key-schema.

### Publish

Every key-press will publish the following topics:

Use
`streamdeck/<key>` or
`streamdeck/<serialNumber>/<key>`
for regular button push events.

If you want to use keys as a e.g. dimmer you can listen to
`streamdeck/<key>/down`
`streamdeck/<serialNumber>/<key>/down`
and
`streamdeck/<key>/up`
`streamdeck/<serialNumber>/<key>/up`
```

**Dateien:** `README.md`
**Aufwand:** 30 Minuten

---

### 3.7 Kommentare entfernen/korrigieren

**Lösung:**
```python
# Zeilen 80-81 in StreamDeckMQTT.py ENTFERNEN:
# # Rest des Codes bleibt gleich...
# # [Previous methods: render_key_image, key_change_callback, set_button_action, etc.]
```

**Dateien:** `src/StreamDeckMQTT.py`
**Aufwand:** 5 Minuten

---

### 3.8 Hardcoded Werte als Konstanten

**Lösung:**
```python
# Am Anfang der Datei
DEFAULT_BRIGHTNESS = 60
DEFAULT_ICON_COLOR = "blue"
ICON_DOWNLOAD_TIMEOUT = 5
CONFIG_FILE = "data.json"

iconDownloadPath = "https://raw.githubusercontent.com/Templarian/MaterialDesign-SVG/refs/heads/master/svg/{}.svg"

class StreamDeckMQTT:
    # ...
    def __init__(self, mqttClient, deck):
        # ...
        self.config = {
            "brightness": DEFAULT_BRIGHTNESS,
            "keys": []
        }

    def update_key(self, key):
        # ...
        if "color" in key_config:
            color = key_config["color"]
        else:
            color = DEFAULT_ICON_COLOR
```

**Dateien:** `src/StreamDeckMQTT.py`
**Aufwand:** 30 Minuten

---

## Phase 4: Testing und CI/CD (Langfristig)

### 4.1 Unit Tests hinzufügen

**Lösung:**
```python
# tests/test_streamdeck_mqtt.py
import unittest
from unittest.mock import Mock, patch, MagicMock
from src.StreamDeckMQTT import StreamDeckMQTT

class TestStreamDeckMQTT(unittest.TestCase):
    def setUp(self):
        self.mock_mqtt = Mock()
        self.mock_deck = Mock()
        self.mock_deck.key_count.return_value = 15
        self.mock_deck.get_serial_number.return_value = "TEST123"

    def test_brightness_validation(self):
        # Test brightness clamping
        handler = StreamDeckMQTT(self.mock_mqtt, self.mock_deck)
        handler.update_brightness(150)  # Should clamp to 100
        self.mock_deck.set_brightness.assert_called_with(100)

    def test_config_validation(self):
        # Test invalid config rejection
        handler = StreamDeckMQTT(self.mock_mqtt, self.mock_deck)
        invalid_config = '{"invalid": "config"}'
        handler.update_config(invalid_config.encode())
        # Should not crash, should log error

    # ... more tests
```

**Dateien:** `tests/test_streamdeck_mqtt.py`, `tests/__init__.py`
**Aufwand:** 8-12 Stunden

---

### 4.2 Integration Tests

**Lösung:**
```python
# tests/test_integration.py
import unittest
import docker
import paho.mqtt.client as mqtt

class TestIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start MQTT broker in Docker
        cls.client = docker.from_env()
        cls.mqtt_container = cls.client.containers.run(
            "eclipse-mosquitto",
            detach=True,
            ports={'1883/tcp': 1883}
        )

    def test_mqtt_connection(self):
        # Test MQTT connection
        pass

    @classmethod
    def tearDownClass(cls):
        cls.mqtt_container.stop()
        cls.mqtt_container.remove()
```

**Dateien:** `tests/test_integration.py`
**Aufwand:** 12-16 Stunden

---

### 4.3 GitHub Actions CI/CD

**Lösung:**
```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run tests
      run: |
        pytest tests/ --cov=src --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3

  build:
    runs-on: ubuntu-latest
    needs: test

    steps:
    - uses: actions/checkout@v3

    - name: Build Docker image
      run: docker build -t streamdeck-mqtt:test .

    - name: Test Docker image
      run: |
        docker run --rm streamdeck-mqtt:test python -c "import src.StreamDeckMQTT"
```

**Dateien:** `.github/workflows/ci.yml`
**Aufwand:** 4-6 Stunden

---

## Zusammenfassung der Aufwände

| Phase | Beschreibung | Geschätzter Aufwand | Tatsächlicher Aufwand | Status |
|-------|--------------|---------------------|----------------------|--------|
| Phase 1 | Kritische Fixes | 8-12 Stunden | ~5-6 Stunden | ✅ **ABGESCHLOSSEN** |
| Phase 2 | Wichtige Fixes | 8-12 Stunden | - | ⏳ Ausstehend |
| Phase 3 | Code-Qualität | 16-24 Stunden | - | ⏳ Ausstehend |
| Phase 4 | Testing & CI/CD | 24-34 Stunden | - | ⏳ Ausstehend |
| **Gesamt** | **Alle Phasen** | **56-82 Stunden** | **~5-6 Stunden** | **~9% abgeschlossen** |

### Phase 1 - Detaillierter Aufwand

| Fix | Geschätzt | Tatsächlich | Notizen |
|-----|-----------|-------------|---------|
| 1.1 Race Condition | 1-2h | ~1h | Threading Lock, _save_config() Methode |
| 1.2 Brightness-Validierung | 30min | ~30min | Validation mit Clamping |
| 1.3 HTTP Timeout | 30min | ~30min | + Konstanten hinzugefügt |
| 1.4 Container-Sicherheit | 1-2h | ~1.5h | Multi-stage Build, .dockerignore |
| 1.5 requirements.txt | 15min | ~10min | attrs + certifi Version fixes |
| 1.6 loop_forever() | 2-3h | ~2h | Multi-Deck Support, besseres Shutdown |
| **Gesamt Phase 1** | **8-12h** | **~5-6h** | Effizienter als geschätzt! |

## Empfohlene Reihenfolge

### ✅ Abgeschlossen (2025-12-04)

1. **Phase 1: Alle kritischen Fixes ✅**
   - ✅ Phase 1.5: requirements.txt korrigiert
   - ✅ Phase 1.1: Race Condition behoben
   - ✅ Phase 1.2: Brightness-Validierung implementiert
   - ✅ Phase 1.3: HTTP Timeout hinzugefügt
   - ✅ Phase 1.4: Container-Sicherheit verbessert
   - ✅ Phase 1.6: loop_forever() behoben

### ⏳ Nächste Schritte

2. **Als Nächstes (Phase 2):**
   - Phase 2.1: Exception-Behandlung verbessern (teilweise schon gemacht)
   - Phase 2.2: JSON Schema-Validierung implementieren
   - Phase 2.3: Thread-Safety mit Deck-Operationen

3. **Danach (Phase 2 Fortsetzung):**
   - Phase 2.4: Doppelter deck.open() entfernen (möglicherweise durch 1.6 schon behoben)
   - Phase 2.5: Ungenutzten Import entfernen (✅ bereits erledigt mit codecs)
   - Phase 2.6: Bessere Error-Behandlung in main.py (✅ bereits erledigt)

4. **Mittelfristig (Phase 3):**
   - Phase 3: Code-Qualität (parallel durchführbar)

5. **Langfristig (Phase 4):**
   - Phase 4: Testing & CI/CD

## Testing-Strategie

Nach jedem Fix:
1. Manuelle Tests mit realem Stream Deck
2. MQTT-Integration testen
3. Config-Updates über MQTT testen
4. Multi-Deck Setup testen (wenn verfügbar)

## Rollback-Strategie

- Git-Branches für jede Phase verwenden
- Vor größeren Änderungen: Git Tag setzen
- Docker-Images taggen mit Version
- data.json vor Updates backupen

---

## 📝 Änderungslog

### 2025-12-04
- ✅ **Phase 1 komplett abgeschlossen** (alle 6 kritischen Fixes)
  - Race Condition behoben mit Threading Locks
  - Brightness-Validierung implementiert
  - HTTP Timeout mit Konstanten hinzugefügt
  - Container-Sicherheit verbessert (Multi-stage Build, Non-root User)
  - requirements.txt Versionen korrigiert
  - loop_forever() Problem behoben, Multi-Deck Support implementiert
- 🔧 **Bonus-Fixes nebenbei erledigt:**
  - codecs Import entfernt (war ungenutzt)
  - Exception-Behandlung verbessert (f-strings, spezifische Exceptions)
  - Error-Handling in main.py implementiert
  - .dockerignore Datei erstellt
  - Konstanten für Magic Values hinzugefügt

**Nächster Fokus:** Phase 2 (JSON Schema-Validierung, weitere Thread-Safety)

---

**Ende des Fix-Plans**
