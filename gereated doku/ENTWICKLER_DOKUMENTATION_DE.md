# Home Assistant NAD Receiver Integration - Entwicklerdokumentation

## 📋 Einleitung

Diese Dokumentation richtet sich an **Entwickler**, die die NAD Receiver Integration für Home Assistant verstehen, erweitern oder anpassen möchten. Hier finden Sie detaillierte technische Informationen über die Architektur, den Codeaufbau und die Implementierungsdetails.

---

## 🏗️ Systemarchitektur

### 1. Komponentenhierarchie

```
┌───────────────────────────────────────────────────--──────┐
│                  Home Assistant Core                      │
└───────────────────────────────────────────-────────--─────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────--────┐
│                 custom_components/nad/                    │
│  ┌────────-──────┐  ┌──────────-────┐  ┌────────────────┐ │
│  │  __init__.py  │  │  const.py     │  │ manifest.json  │ │
│  └─────────-─────┘  └─────────-─────┘  └────────────────┘ │
│  ┌────────-──────┐  ┌──────────-────┐  ┌────────────────┐ │
│  │config_flow.py │  │media_player.py│  │   switch.py    │ │
│  └─────────-─────┘  └─────────-─────┘  └────────────────┘ │
│  ┌────────-──────┐  ┌──────────-────┐  ┌────────────────┐ │
│  │  number.py    │  │  select.py    │  │   sensor.py    │ │
│  └─────────-─────┘  └─────────-─────┘  └────────────────┘ │
└──────────────────────────────────────────────────────--───┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────┐
│                 nad_receiver Library                      │
│  (NADReceiver, NADReceiverTCP, NADReceiverTelnet)         │
└───────────────────────────────────────────────────────-───┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────┐
│                 NAD Receiver Hardware                     │
│  (RS-232 / Telnet / TCP)                                  │
└───────────────────────────────────────────────────────────┘
```

---

## 📦 Dateistruktur im Detail

### 1. `__init__.py` - Hauptintegrationsmodul

**Zweck:** Hauptsetup, Coordinator, Verbindungshandling

**Wichtige Klassen:**

#### `CommandNotSupportedError`
```python
class CommandNotSupportedError(Exception):
    """Error to indicate a command is not supported."""
```
- Wird ausgelöst, wenn ein Befehl vom NAD-Gerät nicht unterstützt wird
- Wird in `exec_command()` gefangen und behandelt

#### `NADReceiverCoordinator`
```python
class NADReceiverCoordinator(DataUpdateCoordinator):
```

**Vererbung:** `DataUpdateCoordinator` (von Home Assistant)

**Zweck:**
- Zentraler Daten- und Verbindungsmanager
- Handhabt alle Kommunikation mit dem NAD-Gerät
- Verwaltet den Zustand und die Datenaktualisierung

**Wichtige Attribute:**

```python
# Verbindung
receiver: NADReceiver = None  # Instanz der nad_receiver-Bibliothek
config: dict = None            # Konfiguration aus ConfigEntry
options: dict = None           # Optionen aus ConfigEntry
unique_id: str = None          # Eindeutige ID der Integration

# Geräteinformationen
device_info: DeviceInfo = None  # Home Assistant DeviceInfo
model: str = None               # Modellname des NAD-Geräts
version: str = None             # Firmware-Version

# Zustand
power_state = None             # Aktueller Power-Status (ON/OFF)
data: dict = None               # Gecachte Daten von allen Befehlen
sources: dict = None            # Verfügbare Quellen {id: name}

# Listener
_listener_commands: list = []   # Liste der Befehle, die abgefragt werden
```

**Wichtige Methoden:**

##### `__init__(self, hass, entry: ConfigEntry)`
```python
def __init__(self, hass, entry: ConfigEntry):
    super().__init__(
        hass,
        _LOGGER,
        name=__name__,
        update_interval=timedelta(seconds=5),  # Polling alle 5 Sekunden
    )
    
    self.config = entry.data
    self.options = entry.options
    self.unique_id = entry.entry_id
    
    # Erstellen der passenden Receiver-Instanz
    config_type = self.config[CONF_TYPE]
    if config_type == CONF_TYPE_SERIAL:
        serial_port = self.config[CONF_SERIAL_PORT]
        self.receiver = NADReceiver(serial_port)
    elif config_type == CONF_TYPE_TELNET:
        host = self.config[CONF_HOST]
        port = self.config[CONF_PORT]
        self.receiver = NADReceiverTelnet(host, port)
    elif config_type == CONF_TYPE_TCP:
        host = self.config[CONF_HOST]
        self.receiver = NADReceiverTCP(host)
```

##### `async def connect(self) -> bool`
```python
async def connect(self) -> bool:
    if not self.model:
        try:
            # Modell und Version abfragen
            self.model = self.exec_command("Main.Model", "?")
            self.version = self.exec_command("Main.Version", "?")
        except CommandNotSupportedError:
            return False
        
        # DeviceInfo für Home Assistant erstellen
        identifiers = {(DOMAIN, self.unique_id)}
        if self.config[CONF_TYPE] == CONF_TYPE_SERIAL:
            identifiers.add((DOMAIN, self.config[CONF_SERIAL_PORT]))
        
        self.device_info = DeviceInfo(
            identifiers=identifiers,
            name=f"NAD {self.model}",
            model=self.model,
            manufacturer="NAD",
            sw_version=self.version,
        )
        
        # Verfügbare Quellen abfragen
        self.sources = self.get_sources()
        
        return True
```

##### `def exec_command(self, command: str, operator: str, value: Optional = None)`
```python
def exec_command(self, command: str, operator: str, value: Optional = None):
    # Befehlsstring erstellen
    cmd = f"{command}{operator}"
    if value:
        cmd = f"{cmd}{value}"
    
    # Puffer leeren für serielle Verbindung
    if self.config[CONF_TYPE] == CONF_TYPE_SERIAL:
        self.receiver.transport.ser.reset_input_buffer()
    
    try:
        # Befehl senden und Antwort empfangen
        msg = self.receiver.transport.communicate(cmd)
        _LOGGER.debug("sent: '%s' reply: '%s'", command, msg)
        
        # Leere Antwort = Befehl nicht unterstützt
        if msg == "":
            raise CommandNotSupportedError()
        
        # Antwort parsen (Format: "Befehl=Wert")
        if msg.lower().startswith(command.lower() + "="):
            return msg.split("=")[1]
            
    except UnicodeDecodeError as ex:
        _LOGGER.error(ex)
    
    return None
```

##### `def supports_command(self, command: str)`
```python
def supports_command(self, command: str):
    try:
        response = self.exec_command(command, "?")
    except CommandNotSupportedError:
        _LOGGER.debug("%s not supported", command)
        return False
    
    _LOGGER.debug("%s supported", command)
    if not self.data:
        self.data = {}
    self.data[command] = response
    
    return True
```

##### `def get_sources(self) -> {}`
```python
def get_sources(self) -> {}:
    sources = {}
    
    # Bis zu 12 Quellen prüfen (NAD-Standard)
    for i in range(1, 13):
        try:
            # Prüfen ob Quelle aktiviert ist
            response = self.exec_command(f"Source{i}.Enabled", "?")
            if response is not None and response.lower() == "yes":
                # Namen der Quelle abfragen
                response = self.exec_command(f"Source{i}.Name", "?")
                sources[i] = response
        except CommandNotSupportedError:
            break  # Keine weiteren Quellen verfügbar
    
    return sources
```

##### `async def _async_update_data(self)`
```python
async def _async_update_data(self):
    """Fetch data from NAD Receiver."""
    try:
        power_state = self.exec_command("Main.Power", "?")
    except CommandNotSupportedError:
        self.power_state = None
        raise UpdateFailed("Error communicating with NAD Receiver")
    except IOError as ex:
        self.power_state = None
        raise UpdateFailed("Error communicating with NAD Receiver", ex)
    
    _LOGGER.debug("power_state: %s", power_state)
    if not power_state:
        self.power_state = None
        raise UpdateFailed("Error communicating with NAD Receiver")
    
    # Power-Status parsen
    if power_state.lower() == "on":
        self.power_state = MediaPlayerState.ON
    else:
        self.power_state = MediaPlayerState.OFF
    
    # Daten-Dictionary erstellen
    data = {}
    data["Main.Power"] = power_state
    
    # Alle registrierten Listener-Befehle abfragen
    for command in self._listener_commands:
        if command not in data:
            data[command] = self.exec_command(command, "?")
    
    return data
```

##### `async def async_add_listener(self, update_callback, context)`
```python
@callback
def async_add_listener(self, update_callback: CALLBACK_TYPE, context: Any = None):
    remove_listener = super().async_add_listener(update_callback, context)
    
    _LOGGER.debug("Adding listener for %s", context)
    if context:
        self.add_listener_command(context)
    
    return remove_listener


def add_listener_command(self, command):
    _LOGGER.debug("Adding command %s", command)
    if command not in self._listener_commands:
        self._listener_commands.append(command)
```

---

### 2. `const.py` - Konstanten

```python
"""Constants for the NAD Receiver integration."""

from typing import Final

# Domain
DOMAIN: Final = "nad"

# Verbindungstypen
CONF_TYPE_SERIAL: Final = "RS232"
CONF_TYPE_TELNET: Final = "Telnet"
CONF_TYPE_TCP: Final = "TCP"

# Konfigurationsparameter
CONF_SERIAL_PORT: Final = "serial_port"
CONF_DEFAULT_PORT: Final = 53

# Lautstärke-Einstellungen
CONF_MIN_VOLUME: Final = "min_volume"
CONF_MAX_VOLUME: Final = "max_volume"
CONF_VOLUME_STEP: Final = "volume_step"
CONF_SOURCE_DICT: Final = "sources"

# Standardwerte
CONF_DEFAULT_MIN_VOLUME: Final = -92
CONF_DEFAULT_MAX_VOLUME: Final = -20
CONF_DEFAULT_VOLUME_STEP: Final = 4
```

---

### 3. `config_flow.py` - Konfigurations-Assistent

**Zweck:** Benutzerfreundliche Konfiguration über die Home Assistant UI

**Wichtige Klassen:**

#### `NADReceiverConfigFlow`

**Vererbung:** `ConfigFlow` (von Home Assistant)

**Wichtige Methoden:**

##### `async def async_step_user(self, user_input)`
```python
async def async_step_user(self, user_input: dict[str, Any] | None = None):
    """Handle the initial step."""
    return self.async_show_menu(
        step_id="user",
        menu_options=["setup_serial", "setup_telnet", "setup_tcp"],
    )
```
- Zeigt das Menü mit den Verbindungstypen an

##### `async def async_step_setup_serial(self, user_input)`
```python
async def async_step_setup_serial(self, user_input: dict[str, Any] | None = None):
    """Handle the setup serial step."""
    errors: dict[str, str] = {}
    
    if user_input is not None:
        title, data, options = await self.validate_input_setup_serial(user_input, errors)
        if not errors:
            return self.async_create_entry(title=title, data=data, options=options)
    
    # Verfügbare serielle Ports abfragen
    ports = await self.hass.async_add_executor_job(serial.tools.list_ports.comports)
    list_of_ports = {}
    for port in ports:
        list_of_ports[port.device] = (
            f"{port}, s/n: {port.serial_number or 'n/a'}"
            + (f" - {port.manufacturer}" if port.manufacturer else "")
        )
    
    # Schema für das Formular erstellen
    self._step_setup_serial_schema = vol.Schema({
        vol.Required(CONF_SERIAL_PORT, default=""): SelectSelector(
            SelectSelectorConfig(
                options=[SelectOptionDict(value=k, label=v) for k, v in list_of_ports.items()],
                mode=SelectSelectorMode.DROPDOWN,
                custom_value=True,
                sort=True,
            )
        ),
    })
    
    return self.async_show_form(
        step_id="setup_serial",
        data_schema=self._step_setup_serial_schema,
        errors=errors,
    )
```

##### `async def validate_input_setup_serial(self, data, errors)`
```python
async def validate_input_setup_serial(self, data: dict[str, Any], errors: dict[str, str]):
    """Validate the user input allows us to connect."""
    self._step_setup_serial_schema(data)
    
    serial_port = data.get(CONF_SERIAL_PORT)
    if serial_port is None:
        raise vol.error.RequiredFieldInvalid("No serial port configured")
    
    # Port-Pfad normalisieren
    serial_port = await self.hass.async_add_executor_job(get_serial_by_id, serial_port)
    
    # Prüfen ob Port existiert
    if not os.path.exists(serial_port):
        errors[CONF_SERIAL_PORT] = "nonexisting_serial_port"
    
    # Prüfen ob Gerät bereits konfiguriert ist
    await self.async_set_unique_id(serial_port)
    self._abort_if_unique_id_configured()
    
    if errors.get(CONF_SERIAL_PORT) is None:
        try:
            # Testverbindung
            receiver = NADReceiver(serial_port)
            model = receiver.main_model("?")
            assert model is not None, "Failed to retrieve receiver model"
            _LOGGER.info("Device %s available", serial_port)
        except (serial.SerialException, CommandNotSupportedError):
            errors["base"] = "cannot_connect"
    
    return (
        f"NAD {model}",
        {
            CONF_TYPE: CONF_TYPE_SERIAL,
            CONF_SERIAL_PORT: serial_port,
        },
        {
            CONF_MIN_VOLUME: CONF_DEFAULT_MIN_VOLUME,
            CONF_MAX_VOLUME: CONF_DEFAULT_MAX_VOLUME,
            CONF_VOLUME_STEP: CONF_DEFAULT_VOLUME_STEP,
        },
    )
```

#### `NADReceiverOptionsFlowHandler`

**Vererbung:** `OptionsFlow` (von Home Assistant)

**Zweck:** Handhabt die Optionen-Konfiguration

```python
class NADReceiverOptionsFlowHandler(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage the options."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            STEP_CONFIG_VOLUME_SCHEMA(user_input)
            user_input[CONF_MIN_VOLUME] = int(user_input[CONF_MIN_VOLUME])
            user_input[CONF_MAX_VOLUME] = int(user_input[CONF_MAX_VOLUME])
            return self.async_create_entry(title="", data=user_input)
        
        # Formular mit aktuellen Werten füllen
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                STEP_CONFIG_VOLUME_SCHEMA, self.config_entry.options
            ),
            errors=errors
        )
```

---

### 4. `media_player.py` - Media Player Entitäten

**Zweck:** Implementierung der Media Player Funktionalität

**Wichtige Klassen:**

#### `NAD` (Basisklasse)

**Vererbung:** `CoordinatorEntity, MediaPlayerEntity`

**Wichtige Attribute:**
```python
_attr_has_entity_name = True      # Verwendet Entity-Namen
_attr_name = None                  # Name wird aus Zone abgeleitet
_attr_device_class = MediaPlayerDeviceClass.RECEIVER
zone = "Main"                      # Zone (Main oder Zone2)
```

**Wichtige Methoden:**

##### `__init__(self, coordinator)`
```python
def __init__(self, coordinator: NADReceiverCoordinator):
    """Initialize the NAD Receiver device."""
    super().__init__(coordinator, self.zone + ".Power")
    
    self._attr_device_info = coordinator.device_info
    self._attr_unique_id = f"{coordinator.unique_id}-mediaplayer-{self.zone.lower()}"
    
    # Lautstärke-Bereich aus Optionen
    self._min_volume = coordinator.options.get(CONF_MIN_VOLUME, CONF_DEFAULT_MIN_VOLUME)
    self._max_volume = coordinator.options.get(CONF_MAX_VOLUME, CONF_DEFAULT_MAX_VOLUME)
    
    # Quellen-Mapping
    self._source_dict = coordinator.sources
    self._reverse_mapping = {value: key for key, value in self._source_dict.items()}
    
    # Listener für wichtige Befehle registrieren
    coordinator.add_listener_command(self.zone + ".Mute")
    coordinator.add_listener_command(self.zone + ".Volume")
    coordinator.add_listener_command(self.zone + ".Source")
```

##### `async def async_added_to_hass(self)`
```python
async def async_added_to_hass(self) -> None:
    await super().async_added_to_hass()
    self._handle_coordinator_update()
```

##### `@callback def _handle_coordinator_update(self)`
```python
@callback
def _handle_coordinator_update(self) -> None:
    """Handle updated data from the coordinator."""
    power_state = self.coordinator.data.get(self.zone + ".Power")
    
    if power_state is None:
        self._attr_state = None
        self._attr_available = False
    elif power_state.lower() == "off":
        self._attr_state = MediaPlayerState.OFF
        self._attr_available = True
    elif power_state.lower() == "on":
        self._attr_state = MediaPlayerState.ON
        self._attr_available = True
        
        # Mute-Status
        self._attr_is_volume_muted = (
            self.coordinator.data.get(self.zone + ".Mute", "").lower() == "on"
        )
        
        # Lautstärke
        volume = self.coordinator.data.get(self.zone + ".Volume")
        if volume is not None and volume.lstrip("-").isnumeric():
            volume = float(volume)
            self._attr_volume_level = self.calc_volume(volume)
        else:
            self._attr_volume_level = None
        
        # Quelle
        source = int(self.coordinator.data.get(self.zone + ".Source"))
        self._attr_source = self._source_dict.get(source)
    
    self.async_write_ha_state()
```

##### `turn_on(self)` / `turn_off(self)`
```python
def turn_off(self) -> None:
    """Turn the media player off."""
    response = self.coordinator.exec_command(self.zone + ".Power", "=", "Off")
    if response.lower() == "off":
        self._attr_state = MediaPlayerState.OFF
        self.schedule_update_ha_state()

def turn_on(self) -> None:
    """Turn the media player on."""
    response = self.coordinator.exec_command(self.zone + ".Power", "=", "On")
    if response.lower() == "on":
        self._attr_state = MediaPlayerState.ON
        self.schedule_update_ha_state()
```

##### `volume_up(self)` / `volume_down(self)`
```python
def volume_up(self) -> None:
    """Volume up the media player."""
    response = self.coordinator.exec_command(self.zone + ".Volume", "+")
    if response is not None and response.lstrip("-").isnumeric():
        self._attr_volume_level = self.calc_volume(float(response))
        self.schedule_update_ha_state()

def volume_down(self) -> None:
    """Volume down the media player."""
    response = self.coordinator.exec_command(self.zone + ".Volume", "-")
    if response is not None and response.lstrip("-").isnumeric():
        self._attr_volume_level = self.calc_volume(float(response))
        self.schedule_update_ha_state()
```

##### `set_volume_level(self, volume)`
```python
def set_volume_level(self, volume: float) -> None:
    """Set volume level, range 0..1."""
    response = self.coordinator.exec_command(
        self.zone + ".Volume", "=", int(self.calc_db(volume))
    )
    if response is not None and response.lstrip("-").isnumeric():
        self._attr_volume_level = self.calc_volume(float(response))
        self.schedule_update_ha_state()
```

##### `mute_volume(self, mute)`
```python
def mute_volume(self, mute: bool) -> None:
    """Mute (true) or unmute (false) media player."""
    if mute:
        response = self.coordinator.exec_command(self.zone + ".Mute", "=", "On")
    else:
        response = self.coordinator.exec_command(self.zone + ".Mute", "=", "Off")
    
    if mute and response.lower() != "on":
        _LOGGER.error("Failed to mute volume")
    elif not mute and response.lower() != "off":
        _LOGGER.error("Failed to unmute volume")
    else:
        _LOGGER.debug("Volume %s", "muted" if mute else "unmuted")
        self._attr_is_volume_muted = mute
        self.schedule_update_ha_state()
```

##### `select_source(self, source)`
```python
def select_source(self, source: str) -> None:
    """Select input source."""
    if source in self._reverse_mapping:
        source_id = self._reverse_mapping[source]
    elif source.isnumeric() and int(source) in self._source_dict:
        source_id = source
    else:
        raise HomeAssistantError(f"Source {source} invalid")
    
    response = self.coordinator.exec_command(self.zone + ".Source", "=", source_id)
    if response.isnumeric():
        self._attr_source = self._source_dict.get(int(response))
        self.schedule_update_ha_state()
```

##### `calc_volume(self, decibel)` / `calc_db(self, volume)`
```python
def calc_volume(self, decibel):
    """Calculate the volume given the decibel. Return the volume (0..1)."""
    return abs(self._min_volume - decibel) / abs(self._min_volume - self._max_volume)

def calc_db(self, volume):
    """Calculate the decibel given the volume. Return the dB."""
    return self._min_volume + round(abs(self._min_volume - self._max_volume) * volume)
```

#### `NADMain` (Hauptzone)

**Vererbung:** `NAD`

**Zusätzliche Funktionen:**
```python
_attr_supported_features = (
    MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.SELECT_SOURCE
    | MediaPlayerEntityFeature.SELECT_SOUND_MODE
)

_attr_sound_mode_list = [
    "None", "ProLogic", "PLIIMovie", "PLIIMusic", "NEO6Cinema",
    "NEO6Music", "EARS", "EnhancedStereo", "AnalogBypass",
    "StereoDownmix", "SurroundEX",
]

zone = "Main"
```

**Zusätzliche Methode:**
```python
def select_sound_mode(self, sound_mode: str) -> None:
    """Select sound mode."""
    response = self.coordinator.exec_command(
        self.zone + ".ListeningMode", "=", sound_mode
    )
    if response is not None:
        self._attr_sound_mode = sound_mode
        self.schedule_update_ha_state()
```

#### `NADZone2` (Zone 2)

**Vererbung:** `NAD`

**Besonderheiten:**
```python
_attr_name = "Zone 2"
_attr_entity_registry_enabled_default = False  # Standardmäßig deaktiviert
_attr_supported_features = (
    MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.SELECT_SOURCE
)

zone = "Zone2"
```

---

### 5. `switch.py` - Schalter-Entitäten

**Zweck:** Implementierung von Schalter-Funktionalität für binäre Einstellungen

**Wichtige Klassen:**

#### `NADReceiverSwitch`

**Vererbung:** `CoordinatorEntity, SwitchEntity`

**Wichtige Attribute:**
```python
_attr_has_entity_name = True
_attr_device_class = SwitchDeviceClass.SWITCH
_attr_available = False
_attr_is_on = None
```

**Entitätsbeschreibungen:**
```python
entity_descriptions = [
    SwitchEntityDescription(
        key="Main.Dimmer",
        name="Front VFD Dimmer",
        icon="mdi:text-short",
        entity_category=EntityCategory.CONFIG,
    ),
    SwitchEntityDescription(
        key="Main.Speaker.Sub",
        name="Subwoofer",
    ),
    # ... weitere Beschreibungen
]
```

**Wichtige Methoden:**

##### `__init__(self, coordinator, entity_description)`
```python
def __init__(self, coordinator, entity_description):
    super().__init__(coordinator, entity_description.key)
    
    self._attr_device_info = coordinator.device_info
    self._attr_unique_id = f"{coordinator.unique_id}-{entity_description.key.lower()}"
    self.entity_description = entity_description
```

##### `@callback def _handle_coordinator_update(self)`
```python
@callback
def _handle_coordinator_update(self) -> None:
    if (self.coordinator.data and 
        (new_state := self.coordinator.data.get(self.entity_description.key)) and
        (new_state := new_state.lower()) and
        new_state in ["on", "off"]):
        self._attr_is_on = new_state == "on"
        self._attr_available = True
    else:
        self._attr_available = False
    
    self.async_write_ha_state()
```

##### `async def async_turn_on(self, **kwargs)`
```python
async def async_turn_on(self, **kwargs) -> None:
    _LOGGER.debug("Turning on %s", self.name)
    response = self.coordinator.exec_command(
        self.entity_description.key, "=", "On"
    )
    if response.lower() == "on":
        self._attr_is_on = True
        self._attr_available = True
    else:
        _LOGGER.error("Failed to switch on %s", self.name)
        self._attr_available = False
    
    self.async_write_ha_state()
```

##### `async def async_turn_off(self, **kwargs)`
```python
async def async_turn_off(self, **kwargs) -> None:
    _LOGGER.debug("Turning off %s", self.name)
    response = self.coordinator.exec_command(
        self.entity_description.key, "=", "Off"
    )
    if response.lower() == "off":
        self._attr_is_on = False
        self._attr_available = True
    else:
        _LOGGER.error("Failed to switch off %s", self.name)
        self._attr_available = False
    
    self.async_write_ha_state()
```

---

### 6. `number.py` - Zahlen-Entitäten

**Zweck:** Implementierung von Zahlen-Eingaben für verschiedene Parameter

**Wichtige Klassen:**

#### `NADReceiverNumber`

**Vererbung:** `CoordinatorEntity, NumberEntity`

**Wichtige Attribute:**
```python
_attr_has_entity_name = True
_attr_available = False
```

**Entitätsbeschreibungen:**
```python
entity_descriptions = [
    NumberEntityDescription(
        key="Main.Bass",
        name="Bass Tone Control",
        native_unit_of_measurement=UnitOfSoundPressure.DECIBEL,
        native_min_value=-10,
        native_max_value=10,
    ),
    NumberEntityDescription(
        key="Main.Volume",
        name="Volume",
        # ... weitere Parameter
    ),
    # ... viele weitere Beschreibungen
]
```

**Wichtige Methoden:**

##### `@callback def _handle_coordinator_update(self)`
```python
@callback
def _handle_coordinator_update(self) -> None:
    if (self.coordinator.data and 
        (new_value := self.coordinator.data.get(self.entity_description.key)) and
        new_value.lstrip("-").replace(".", "", 1).isnumeric()):
        self._attr_native_value = float(new_value)
        self._attr_available = True
    else:
        self._attr_available = False
    
    self.async_write_ha_state()
```

##### `async def async_set_native_value(self, value)`
```python
async def async_set_native_value(self, value: float) -> None:
    _LOGGER.debug("async_set_native_value")
    
    if self.coordinator.power_state == MediaPlayerState.ON:
        if self._attr_native_value == value:
            return
        
        # Je nach Schrittweite unterschiedlich behandeln
        if self.step < 1:
            response = self.coordinator.exec_command(
                self.entity_description.key, "=", value
            )
        else:
            response = self.coordinator.exec_command(
                self.entity_description.key, "=", int(value)
            )
        
        if response.lstrip("-").replace(".", "", 1).isnumeric():
            self._attr_native_value = float(response)
            self._attr_available = True
        else:
            _LOGGER.error("Failed to set %s to %s", self.name, value)
            self._attr_available = False
    else:
        self._attr_available = False
    
    self.async_write_ha_state()
```

---

### 7. `select.py` - Auswahl-Entitäten

**Zweck:** Implementierung von Auswahl-Feldern für verschiedene Optionen

**Wichtige Klassen:**

#### `NADReceiverSelect`

**Vererbung:** `CoordinatorEntity, SelectEntity`

**Wichtige Attribute:**
```python
_attr_has_entity_name = True
_attr_available = False
_attr_current_option = None
```

**Entitätsbeschreibungen:**
```python
entity_descriptions = [
    SelectEntityDescription(
        key="Main.ListeningMode.Analog",
        name="Analog Signal Listening Mode",
        options=["None", "ProLogic", "PLIIMovie", ...],
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    SelectEntityDescription(
        key="Main.VideoMode",
        name="Video Mode",
        options=["NTSC", "PAL"],
        entity_category=EntityCategory.CONFIG,
    ),
    # ... weitere Beschreibungen
]
```

**Wichtige Methoden:**

##### `@callback def _handle_coordinator_update(self)`
```python
@callback
def _handle_coordinator_update(self) -> None:
    if self.coordinator.data and (
        new_state := self.coordinator.data.get(self.entity_description.key)
    ):
        self._attr_current_option = new_state
        self._attr_available = True
    else:
        _LOGGER.debug("%s is not available", self.entity_description.key)
        self._attr_available = False
    
    self.async_write_ha_state()
```

##### `async def async_select_option(self, option)`
```python
async def async_select_option(self, option: str) -> None:
    """Change the selected option."""
    if self.coordinator.power_state == MediaPlayerState.ON:
        if self._attr_current_option == option:
            return
        
        response = self.coordinator.exec_command(
            self.entity_description.key, "=", option
        )
        if response is not None:
            self._attr_current_option = response
            self._attr_available = True
        else:
            _LOGGER.error("Failed to set %s to %s", self.name, option)
            self._attr_available = False
    else:
        self._attr_available = False
    
    self.async_write_ha_state()
```

---

### 8. `sensor.py` - Sensor-Entitäten

**Zweck:** Implementierung von Sensoren für verschiedene Informationen

**Wichtige Klassen:**

#### `NADReceiverSensor`

**Vererbung:** `CoordinatorEntity, SensorEntity`

**Wichtige Attribute:**
```python
_attr_has_entity_name = True
_attr_available = False
_attr_native_value = None
```

**Entitätsbeschreibungen:**
```python
entity_descriptions = [
    SensorEntityDescription(
        key="DSP.Version",
        name="DSP Version",
        entity_registry_enabled_default=False
    ),
    SensorEntityDescription(
        key="Tuner.FM.RDSName",
        name="FM RDS Name",
        entity_registry_enabled_default=False
    ),
    # ... weitere Beschreibungen
]
```

---

## 🔌 Kommunikationsprotokoll

### 1. Befehlsformat

Die Kommunikation mit NAD-Geräten erfolgt über ein einfaches **Textprotokoll**:

**Abfrage:**
```
<Befehl>?
```

**Antwort (erfolgreich):**
```
<Befehl>=<Wert>
```

**Antwort (nicht unterstützt):**
```
(leere Zeichenkette)
```

**Setzen:**
```
<Befehl>=<Wert>
```

**Antwort:**
```
<Befehl>=<Wert>  (Bestätigung)
```

### 2. Befehlskategorien

#### Power & Grundfunktionen
- `Main.Power` - Ein/Aus (On/Off)
- `Main.Volume` - Lautstärke (dB-Wert, z.B. -30)
- `Main.Mute` - Stummschaltung (On/Off)
- `Main.Source` - Quelle (Nummer, z.B. 1, 2, 3)

#### Klangmodi
- `Main.ListeningMode` - Klangmodus (z.B. ProLogic, PLIIMovie)
- `Main.ListeningMode.Analog` - Analog-Klangmodus
- `Main.ListeningMode.Digital` - Digital-Klangmodus
- `Main.ListeningMode.DolbyDigital` - Dolby Digital Klangmodus
- `Main.ListeningMode.DTS` - DTS Klangmodus

#### Lautsprecher-Einstellungen
- `Main.Speaker.Sub` - Subwoofer (On/Off)
- `Main.Speaker.A` - Lautsprecher A (On/Off)
- `Main.Speaker.B` - Lautsprecher B (On/Off)
- `Main.Speaker.Back.Config2` - Lautsprechergröße Rückseite
- `Main.Speaker.Center.Config` - Lautsprechergröße Center
- `Main.Speaker.Front.Config` - Lautsprechergröße Front
- `Main.Speaker.Surround.Config` - Lautsprechergröße Surround

#### Lautstärke & Pegel
- `Main.Level.*` - Pegel für verschiedene Lautsprecher (-12 bis +12 dB)
- `Main.Trim.*` - Trim für verschiedene Kanäle (-6 bis +6)
- `Main.Bass` - Bass-Regler (-10 bis +10 dB)
- `Main.Treble` - Höhen-Regler (-10 bis +10 dB)

#### Abstände
- `Main.Distance.*` - Abstand für verschiedene Lautsprecher (0-30 Fuß)

#### Crossover-Frequenzen
- `Main.Speaker.*.Frequency` - Crossover-Frequenz (40-200 Hz)

#### Dolby-Einstellungen
- `Main.Dolby.CenterWidth` - Center-Breite (0-7)
- `Main.Dolby.Dimension` - Dimension (-7 bis +7)
- `Main.Dolby.DRC` - Dynamic Range Control (25-100%)

#### DTS-Einstellungen
- `Main.DTS.CenterGain` - Center-Verstärkung (0-0.5)
- `Main.DTS.DRC` - Dynamic Range Control (25-100%)

#### Trigger
- `Main.Trigger*.Out` - Trigger-Ausgang
- `Main.Trigger*.Delay` - Trigger-Verzögerung (0-15 s)
- `Main.AutoTrigger` - Auto-Trigger-Eingang

#### Anzeige
- `Main.Dimmer` - VFD-Dimmer
- `Main.VFD.Display` - VFD-Anzeige
- `Main.VFD.Line*` - VFD-Zeilen
- `Main.VFD.TempLine` - VFD-Temperaturzeile
- `Main.OSD.TempDisplay` - OSD-Temperaturanzeige

#### Tuner
- `Tuner.Band` - Band (AM/FM/XM/DAB)
- `Tuner.FM.Frequency` - FM-Frequenz (87.5-108.5 MHz)
- `Tuner.AM.Frequency` - AM-Frequenz (530-1710 kHz)
- `Tuner.Preset` - Vorwahl (1-40)
- `Tuner.FM.RDSName` - RDS Stationname
- `Tuner.FM.RDSText` - RDS Text
- `Tuner.DAB.*` - DAB-Informationen
- `Tuner.XM.*` - XM-Informationen

#### System
- `Main.Model` - Modellname
- `Main.Version` - Firmware-Version
- `DSP.Version` - DSP-Version
- `UART.Version` - UART-Version
- `Source*.Enabled` - Quelle aktiviert (Yes/No)
- `Source*.Name` - Quellenname

---

## 📊 Datenfluss

### 1. Initialisierung

```
1. Benutzer fügt Integration über Config Flow hinzu
   ↓
2. config_flow.py validiert Verbindung und erstellt ConfigEntry
   ↓
3. __init__.py: async_setup_entry() wird aufgerufen
   ↓
4. NADReceiverCoordinator wird erstellt
   ↓
5. connect() wird aufgerufen:
   - Modell und Version abfragen
   - DeviceInfo erstellen
   - Quellen abfragen
   ↓
6. Plattformen werden geladen (media_player, switch, number, select, sensor)
   ↓
7. Jede Plattform erstellt ihre Entitäten
   ↓
8. Entitäten registrieren Listener beim Coordinator
   ↓
9. Coordinator startet Update-Zyklus (alle 5 Sekunden)
```

### 2. Daten-Update-Zyklus

```
1. Coordinator._async_update_data() wird aufgerufen (alle 5s)
   ↓
2. Power-Status abfragen: exec_command("Main.Power", "?")
   ↓
3. Für jeden registrierten Listener-Befehl:
   - exec_command(befehl, "?") aufrufen
   - Ergebnis in data-Dictionary speichern
   ↓
4. data-Dictionary wird zurückgegeben
   ↓
5. Coordinator benachrichtigt alle Listener
   ↓
6. Jede Entität ruft _handle_coordinator_update() auf
   ↓
7. Entität aktualisiert ihren Zustand basierend auf den neuen Daten
   ↓
8. async_write_ha_state() wird aufgerufen
   ↓
9. Home Assistant aktualisiert den Entity-Status
```

### 3. Befehlsausführung

```
1. Benutzer interagiert mit Entität (z.B. Lautstärke ändern)
   ↓
2. Entitätsmethode wird aufgerufen (z.B. volume_up())
   ↓
3. Entität ruft coordinator.exec_command() auf
   ↓
4. Coordinator sendet Befehl an NAD-Gerät:
   - Für seriell: Puffer leeren, Befehl senden
   - Für Telnet/TCP: Befehl senden
   ↓
5. NAD-Gerät antwortet
   ↓
6. Coordinator parst Antwort
   ↓
7. Entität aktualisiert ihren Zustand
   ↓
8. schedule_update_ha_state() oder async_write_ha_state() aufrufen
   ↓
9. Home Assistant aktualisiert den Entity-Status
```

---

## 🔧 Entwicklungsrichtlinien

### 1. Neue Entitäten hinzufügen

Um eine neue Entität hinzuzufügen:

1. **Entscheiden Sie den Entitätstyp:**
   - Schalter (switch) - für binäre Einstellungen (Ein/Aus)
   - Zahl (number) - für numerische Werte
   - Auswahl (select) - für Auswahl aus Optionen
   - Sensor (sensor) - für schreibgeschützte Informationen

2. **Fügen Sie die Entitätsbeschreibung hinzu:**
   ```python
   entity_descriptions = [
       # ... bestehende Beschreibungen
       NumberEntityDescription(
           key="Main.NewSetting",
           name="Neue Einstellung",
           native_unit_of_measurement=UnitOfSoundPressure.DECIBEL,
           native_min_value=-10,
           native_max_value=10,
           entity_category=EntityCategory.CONFIG,
           entity_registry_enabled_default=False,
       ),
   ]
   ```

3. **Prüfen Sie die Unterstützung:**
   ```python
   if coordinator.supports_command(entity_description.key):
       entities.append(NADReceiverNumber(coordinator, entity_description))
   ```

4. **Testen Sie die neue Entität**

### 2. Neue Befehle unterstützen

1. **Fügen Sie den Befehl zur Entitätsbeschreibung hinzu**
2. **Testen Sie ob der Befehl unterstützt wird**
3. **Implementieren Sie ggf. spezielle Logik**

### 3. Code-Stil

- **Namen:** Verwenden Sie `snake_case` für Variablen und Funktionen
- **Typen:** Verwenden Sie Typen-Hints (Type Annotations)
- **Logging:** Verwenden Sie `_LOGGER.debug()`, `_LOGGER.info()`, `_LOGGER.error()`
- **Dokumentation:** Fügen Sie Docstrings zu allen öffentlichen Methoden hinzu

### 4. Fehlerbehandlung

- **Fangen Sie Ausnahmen** mit try/except
- **Verwenden Sie spezifische Ausnahmen** (z.B. `CommandNotSupportedError`)
- **Loggen Sie Fehler** mit `_LOGGER.error()`
- **Setzen Sie _attr_available = False** bei Fehlern

---

## 🧪 Testen

### 1. Manuelles Testen

1. **Installieren Sie die Integration** in Ihrer Home Assistant Instanz
2. **Aktivieren Sie Debug-Logging:**
   ```yaml
   logger:
     logs:
       custom_components.nad: debug
       nad_receiver: debug
   ```
3. **Testen Sie alle Funktionen** manuell über die UI
4. **Prüfen Sie die Logs** auf Fehler

### 2. Automatisiertes Testen

Die Integration hat derzeit keine automatisierten Tests. Sie können jedoch:

1. **Unit-Tests** für einzelne Funktionen schreiben
2. **Mock-Tests** für die Kommunikation mit dem NAD-Gerät erstellen
3. **Integration-Tests** für die Home Assistant Integration schreiben

### 3. Testdaten

Für Tests können Sie Mock-Daten verwenden:

```python
# Mock für NADReceiver
class MockNADReceiver:
    def __init__(self):
        self.data = {
            "Main.Power": "On",
            "Main.Volume": "-30",
            "Main.Mute": "Off",
            "Main.Source": "1",
            "Main.Model": "T 758",
            "Main.Version": "1.0.0",
        }
    
    def communicate(self, cmd):
        if cmd == "Main.Power?":
            return "Main.Power=On"
        elif cmd == "Main.Volume?":
            return "Main.Volume=-30"
        # ... weitere Mock-Antworten
        return ""
```

---

## 📝 Changelog & Versionierung

Die Integration folgt **Semantic Versioning** (SemVer):

- **MAJOR**: Brechende Änderungen (z.B. API-Änderungen)
- **MINOR**: Neue Funktionen (rückwärtskompatibel)
- **PATCH**: Bugfixes (rückwärtskompatibel)

**Aktuelle Version:** 0.0.3 (aus manifest.json)

---

## 🔮 Zukunftspläne

### 1. Geplante Funktionen

- [ ] Unterstützung für weitere NAD-Modelle
- [ ] Bessere Fehlerbehandlung und Wiederverbindungslogik
- [ ] Automatische Erkennung von unterstützten Befehlen
- [ ] Performance-Optimierungen (z.B. weniger häufiges Polling)
- [ ] Unterstützung für mehr Zonen (Zone 3, Zone 4)

### 2. Mögliche Erweiterungen

- [ ] Web-Interface für erweiterte Konfiguration
- [ ] Integration mit anderen Diensten (z.B. Spotify, Tidal)
- [ ] Sprachsteuerung (z.B. über Alexa, Google Assistant)
- [ ] Automatische Kalibrierung
- [ ] Benutzerdefinierte Befehle

---

## 📚 Ressourcen

### 1. Offizielle Dokumentation

- [Home Assistant Developer Documentation](https://developers.home-assistant.io/)
- [NAD Receiver Protocol Documentation](https://nadelectronics.com/)

### 2. Nützliche Links

- [Home Assistant GitHub](https://github.com/home-assistant/core)
- [NAD Receiver Library](https://github.com/rrooggiieerr/nad_receiver)
- [Python Serial Library](https://pyserial.readthedocs.io/)

### 3. Community

- [Home Assistant Community Forum](https://community.home-assistant.io/)
- [Home Assistant Discord](https://discord.gg/c5x8XKm)
- [GitHub Discussions](https://github.com/rrooggiieerr/homeassistant-nad/discussions)

---

## 🙏 Beitrag leisten

### 1. Code-Beiträge

1. **Forken Sie das Repository**
2. **Erstellen Sie einen Feature-Branch** (`git checkout -b feature/neue-funktion`)
3. **Commiten Sie Ihre Änderungen** (`git commit -m 'Füge neue Funktion hinzu'`)
4. **Pushen Sie zum Branch** (`git push origin feature/neue-funktion`)
5. **Erstellen Sie einen Pull Request**

### 2. Richtlinien für Pull Requests

- **Beschreiben Sie Ihre Änderungen** detailliert
- **Fügen Sie Tests hinzu** (falls möglich)
- **Aktualisieren Sie die Dokumentation**
- **Folgen Sie dem Code-Stil** der bestehenden Codebasis
- **Testen Sie Ihre Änderungen** gründlich

### 3. Review-Prozess

1. **Automatisierte Prüfungen** (CI/CD) werden ausgeführt
2. **Manueller Review** durch den Maintainer
3. **Feedback und Anpassungen** bei Bedarf
4. **Merge** bei Erfolg

---

## 📄 Lizenz

Diese Integration steht unter der **MIT-Lizenz**. Siehe [LICENSE](LICENSE) für Details.

---

*Diese Entwicklerdokumentation wurde für die deutsche Home Assistant Community erstellt. Letzte Aktualisierung: 2024*
