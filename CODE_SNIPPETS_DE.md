# NAD Receiver Integration - Code Snippets & Muster

## 📋 Einleitung

Diese Sammlung enthält **praktische Code-Snippets** und **Entwicklungsmuster** für die Arbeit mit der NAD Receiver Integration. Ideal für Entwickler, die die Integration erweitern oder anpassen möchten.

---

## 🏗️ Grundlegende Architektur-Muster

### 1. Coordinator-Pattern

Der **NADReceiverCoordinator** ist das zentrale Element, das alle Kommunikation verwaltet:
 
```python
class NADReceiverCoordinator(DataUpdateCoordinator):
    """Zentraler Daten- und Verbindungsmanager."""
    
    def __init__(self, hass, entry: ConfigEntry):
        super().__init__(
            hass,
            _LOGGER,
            name=__name__,
            update_interval=timedelta(seconds=5),  # Polling alle 5 Sekunden
        )
        
        # Verbindung konfigurieren
        self.config = entry.data
        self.options = entry.options
        self.unique_id = entry.entry_id
        
        # Receiver-Instanz erstellen
        config_type = self.config[CONF_TYPE]
        if config_type == CONF_TYPE_SERIAL:
            self.receiver = NADReceiver(self.config[CONF_SERIAL_PORT])
        elif config_type == CONF_TYPE_TELNET:
            self.receiver = NADReceiverTelnet(self.config[CONF_HOST], self.config[CONF_PORT])
        elif config_type == CONF_TYPE_TCP:
            self.receiver = NADReceiverTCP(self.config[CONF_HOST])
```

### 2. Entity-Pattern

Alle Entitäten erben von `CoordinatorEntity` und dem jeweiligen Entity-Typ:

```python
class NADReceiverSwitch(CoordinatorEntity, SwitchEntity):
    """Schalter-Entität für NAD Receiver."""
    
    _attr_has_entity_name = True
    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_available = False
    _attr_is_on = None
    
    def __init__(self, coordinator, entity_description):
        super().__init__(coordinator, entity_description.key)
        
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.unique_id}-{entity_description.key.lower()}"
        self.entity_description = entity_description
```

---

## 🔌 Kommunikations-Muster

### 1. Befehl ausführen

```python
def exec_command(self, command: str, operator: str, value: Optional = None):
    """Führt einen Befehl aus und gibt die Antwort zurück."""
    
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

### 2. Befehlsunterstützung prüfen

```python
def supports_command(self, command: str):
    """Prüft ob ein Befehl vom Gerät unterstützt wird."""
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

### 3. Daten-Update

```python
async def _async_update_data(self):
    """Holt Daten vom NAD Receiver."""
    try:
        power_state = self.exec_command("Main.Power", "?")
    except CommandNotSupportedError:
        self.power_state = None
        raise UpdateFailed("Error communicating with NAD Receiver")
    except IOError as ex:
        self.power_state = None
        raise UpdateFailed("Error communicating with NAD Receiver", ex)
    
    if not power_state:
        self.power_state = None
        raise UpdateFailed("Error communicating with NAD Receiver")
    
    # Power-Status parsen
    if power_state.lower() == "on":
        self.power_state = MediaPlayerState.ON
    else:
        self.power_state = MediaPlayerState.OFF
    
    # Daten-Dictionary erstellen
    data = {"Main.Power": power_state}
    
    # Alle registrierten Listener-Befehle abfragen
    for command in self._listener_commands:
        if command not in data:
            data[command] = self.exec_command(command, "?")
    
    return data
```

---

## 🎛️ Media Player Muster

### 1. Media Player Basisklasse

```python
class NAD(CoordinatorEntity, MediaPlayerEntity):
    """Basisklasse für NAD Media Player."""
    
    _attr_has_entity_name = True
    _attr_name = None
    _attr_device_class = MediaPlayerDeviceClass.RECEIVER
    zone = "Main"
    
    def __init__(self, coordinator: NADReceiverCoordinator):
        super().__init__(coordinator, self.zone + ".Power")
        
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.unique_id}-mediaplayer-{self.zone.lower()}"
        
        # Lautstärke-Bereich
        self._min_volume = coordinator.options.get(CONF_MIN_VOLUME, CONF_DEFAULT_MIN_VOLUME)
        self._max_volume = coordinator.options.get(CONF_MAX_VOLUME, CONF_DEFAULT_MAX_VOLUME)
        
        # Quellen
        self._source_dict = coordinator.sources
        self._reverse_mapping = {value: key for key, value in self._source_dict.items()}
        
        # Listener registrieren
        coordinator.add_listener_command(self.zone + ".Mute")
        coordinator.add_listener_command(self.zone + ".Volume")
        coordinator.add_listener_command(self.zone + ".Source")
```

### 2. Volumen-Berechnung

```python
def calc_volume(self, decibel):
    """Konvertiert dB in 0.0-1.0 Bereich."""
    return abs(self._min_volume - decibel) / abs(self._min_volume - self._max_volume)

def calc_db(self, volume):
    """Konvertiert 0.0-1.0 in dB."""
    return self._min_volume + round(abs(self._min_volume - self._max_volume) * volume)
```

### 3. Media Player Methoden

```python
def turn_off(self) -> None:
    """Schaltet den Media Player aus."""
    response = self.coordinator.exec_command(self.zone + ".Power", "=", "Off")
    if response.lower() == "off":
        self._attr_state = MediaPlayerState.OFF
        self.schedule_update_ha_state()

def turn_on(self) -> None:
    """Schaltet den Media Player ein."""
    response = self.coordinator.exec_command(self.zone + ".Power", "=", "On")
    if response.lower() == "on":
        self._attr_state = MediaPlayerState.ON
        self.schedule_update_ha_state()

def volume_up(self) -> None:
    """Erhöht die Lautstärke."""
    response = self.coordinator.exec_command(self.zone + ".Volume", "+")
    if response is not None and response.lstrip("-").isnumeric():
        self._attr_volume_level = self.calc_volume(float(response))
        self.schedule_update_ha_state()

def set_volume_level(self, volume: float) -> None:
    """Setzt die Lautstärke absolut (0.0-1.0)."""
    response = self.coordinator.exec_command(
        self.zone + ".Volume", "=", int(self.calc_db(volume))
    )
    if response is not None and response.lstrip("-").isnumeric():
        self._attr_volume_level = self.calc_volume(float(response))
        self.schedule_update_ha_state()

def select_source(self, source: str) -> None:
    """Wählt eine Quelle aus."""
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

---

## 🔘 Switch Entity Muster

### 1. Switch Entity erstellen

```python
class NADReceiverSwitch(CoordinatorEntity, SwitchEntity):
    """Schalter-Entität für NAD Receiver."""
    
    _attr_has_entity_name = True
    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_available = False
    _attr_is_on = None
    
    def __init__(self, coordinator, entity_description):
        super().__init__(coordinator, entity_description.key)
        
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.unique_id}-{entity_description.key.lower()}"
        self.entity_description = entity_description
    
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._handle_coordinator_update()
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Aktualisiert den Zustand basierend auf den Coordinator-Daten."""
        if (self.coordinator.data and 
            (new_state := self.coordinator.data.get(self.entity_description.key)) and
            (new_state := new_state.lower()) and
            new_state in ["on", "off"]):
            self._attr_is_on = new_state == "on"
            self._attr_available = True
        else:
            self._attr_available = False
        
        self.async_write_ha_state()
    
    async def async_turn_on(self, **kwargs) -> None:
        """Schaltet die Entität ein."""
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
    
    async def async_turn_off(self, **kwargs) -> None:
        """Schaltet die Entität aus."""
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

### 2. Switch Entitäten registrieren

```python
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Richtet die NAD Receiver Schalter ein."""
    coordinator: NADReceiverCoordinator = config_entry.runtime_data
    
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
    
    entities = []
    for entity_description in entity_descriptions:
        if coordinator.supports_command(entity_description.key):
            entities.append(NADReceiverSwitch(coordinator, entity_description))
    
    async_add_entities(entities)
```

---

## 🔢 Number Entity Muster

### 1. Number Entity erstellen

```python
class NADReceiverNumber(CoordinatorEntity, NumberEntity):
    """Zahlen-Entität für NAD Receiver."""
    
    _attr_has_entity_name = True
    _attr_available = False
    
    def __init__(self, coordinator, entity_description):
        super().__init__(coordinator, entity_description.key)
        
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.unique_id}-{entity_description.key.lower()}"
        self.entity_description = entity_description
    
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._handle_coordinator_update()
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Aktualisiert den Wert basierend auf den Coordinator-Daten."""
        if (self.coordinator.data and 
            (new_value := self.coordinator.data.get(self.entity_description.key)) and
            new_value.lstrip("-").replace(".", "", 1).isnumeric()):
            self._attr_native_value = float(new_value)
            self._attr_available = True
        else:
            self._attr_available = False
        
        self.async_write_ha_state()
    
    async def async_set_native_value(self, value: float) -> None:
        """Setzt den Wert."""
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

### 2. Number Entitäten registrieren

```python
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Richtet die NAD Receiver Zahlen-Entitäten ein."""
    coordinator: NADReceiverCoordinator = config_entry.runtime_data
    
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
            native_unit_of_measurement=UnitOfSoundPressure.DECIBEL,
            native_min_value=-92,
            native_max_value=-20,
        ),
        # ... weitere Beschreibungen
    ]
    
    entities = []
    for entity_description in entity_descriptions:
        if coordinator.supports_command(entity_description.key):
            entities.append(NADReceiverNumber(coordinator, entity_description))
    
    async_add_entities(entities)
```

---

## 📋 Select Entity Muster

### 1. Select Entity erstellen

```python
class NADReceiverSelect(CoordinatorEntity, SelectEntity):
    """Auswahl-Entität für NAD Receiver."""
    
    _attr_has_entity_name = True
    _attr_available = False
    _attr_current_option = None
    
    def __init__(self, coordinator, entity_description):
        super().__init__(coordinator, entity_description.key)
        
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.unique_id}-{entity_description.key.lower()}"
        self.entity_description = entity_description
    
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._handle_coordinator_update()
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Aktualisiert die Auswahl basierend auf den Coordinator-Daten."""
        if self.coordinator.data and (
            new_state := self.coordinator.data.get(self.entity_description.key)
        ):
            self._attr_current_option = new_state
            self._attr_available = True
        else:
            _LOGGER.debug("%s is not available", self.entity_description.key)
            self._attr_available = False
        
        self.async_write_ha_state()
    
    async def async_select_option(self, option: str) -> None:
        """Ändert die ausgewählte Option."""
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

## 📊 Sensor Entity Muster

### 1. Sensor Entity erstellen

```python
class NADReceiverSensor(CoordinatorEntity, SensorEntity):
    """Sensor-Entität für NAD Receiver."""
    
    _attr_has_entity_name = True
    _attr_available = False
    _attr_native_value = None
    
    def __init__(self, coordinator, entity_description):
        super().__init__(coordinator, entity_description.key)
        
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.unique_id}-{entity_description.key.lower()}"
        self.entity_description = entity_description
    
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._handle_coordinator_update()
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Aktualisiert den Wert basierend auf den Coordinator-Daten."""
        if self.coordinator.data and (
            new_value := self.coordinator.data.get(self.entity_description.key)
        ):
            self._attr_native_value = new_value
            self._attr_available = True
        else:
            self._attr_available = False
        
        self.async_write_ha_state()
```

---

## 🔧 Config Flow Muster

### 1. Config Flow Grundstruktur

```python
class NADReceiverConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config Flow für NAD Receiver."""
    
    VERSION = 1
    
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Erster Schritt: Verbindungstyp auswählen."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["setup_serial", "setup_telnet", "setup_tcp"],
        )
    
    async def async_step_setup_serial(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Setup für serielle Verbindung."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            title, data, options = await self.validate_input_setup_serial(
                user_input, errors
            )
            if not errors:
                return self.async_create_entry(title=title, data=data, options=options)
        
        # Verfügbare Ports abfragen
        ports = await self.hass.async_add_executor_job(
            serial.tools.list_ports.comports
        )
        
        # Formular erstellen
        return self.async_show_form(
            step_id="setup_serial",
            data_schema=self._create_serial_schema(ports),
            errors=errors,
        )
```

### 2. Validierung

```python
async def validate_input_setup_serial(
    self, data: dict[str, Any], errors: dict[str, str]
) -> dict[str, Any]:
    """Validiert die Benutzereingabe für serielle Verbindung."""
    self._step_setup_serial_schema(data)
    
    serial_port = data.get(CONF_SERIAL_PORT)
    if serial_port is None:
        raise vol.error.RequiredFieldInvalid("No serial port configured")
    
    # Port-Pfad normalisieren
    serial_port = await self.hass.async_add_executor_job(
        get_serial_by_id, serial_port
    )
    
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

---

## 🎯 Entity Setup Muster

### 1. Plattform-Setup

```python
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Richtet die Plattform ein."""
    coordinator: NADReceiverCoordinator = config_entry.runtime_data
    
    # Initialen Datenabruf durchführen
    await coordinator.async_config_entry_first_refresh()
    
    # Entitäten erstellen und registrieren
    entities = []
    
    # Beispiel: Media Player
    if isinstance(coordinator.receiver, NADReceiverTCP):
        entities.append(NADtcp(coordinator))
    else:
        entities.append(NADMain(coordinator))
        entities.append(NADZone2(coordinator))
    
    async_add_entities(entities)
```

### 2. Dynamische Entitäts-Erstellung

```python
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Richtet die Plattform mit dynamischer Entitäts-Erstellung ein."""
    coordinator: NADReceiverCoordinator = config_entry.runtime_data
    
    # Entitätsbeschreibungen
    entity_descriptions = [
        SwitchEntityDescription(
            key="Main.Dimmer",
            name="Front VFD Dimmer",
            icon="mdi:text-short",
            entity_category=EntityCategory.CONFIG,
        ),
        # ... weitere Beschreibungen
    ]
    
    # Nur unterstützte Entitäten erstellen
    entities = []
    for entity_description in entity_descriptions:
        if coordinator.supports_command(entity_description.key):
            entities.append(NADReceiverSwitch(coordinator, entity_description))
    
    async_add_entities(entities)
```

---

## 🔄 Update & Migration Muster

### 1. Entity Migration

```python
@callback
def _async_migrate_entity_entry(
    registry_entry: entity_registry.RegistryEntry,
) -> dict[str, Any] | None:
    """Migriert alte Unique IDs zu neuen Unique IDs."""
    if entry.data[CONF_TYPE] == CONF_TYPE_SERIAL:
        if registry_entry.unique_id.startswith(f"{entry.data[CONF_SERIAL_PORT]}-"):
            new_unique_id = registry_entry.unique_id.replace(
                f"{entry.data[CONF_SERIAL_PORT]}-",
                f"{registry_entry.config_entry_id}-",
            )
            _LOGGER.debug("Migrating entity unique id to %s", new_unique_id)
            return {"new_unique_id": new_unique_id}
    
    # Keine Migration nötig
    return None

# Migration aufrufen
await entity_registry.async_migrate_entries(
    hass, entry.entry_id, _async_migrate_entity_entry
)
```

### 2. Options Flow

```python
class NADReceiverOptionsFlowHandler(OptionsFlow):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Verwaltet die Optionen."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            STEP_CONFIG_VOLUME_SCHEMA(user_input)
            user_input[CONF_MIN_VOLUME] = int(user_input[CONF_MIN_VOLUME])
            user_input[CONF_MAX_VOLUME] = int(user_input[CONF_MAX_VOLUME])
            return self.async_create_entry(title="", data=user_input)
        
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                STEP_CONFIG_VOLUME_SCHEMA, self.config_entry.options
            ),
            errors=errors
        )
```

---

## 🛠️ Hilfsfunktionen

### 1. Serielle Ports abfragen

```python
ports = await self.hass.async_add_executor_job(serial.tools.list_ports.comports)
list_of_ports = {}
for port in ports:
    list_of_ports[port.device] = (
        f"{port}, s/n: {port.serial_number or 'n/a'}"
        + (f" - {port.manufacturer}" if port.manufacturer else "")
    )
```

### 2. Port-Pfad normalisieren

```python
def get_serial_by_id(dev_path: str) -> str:
    """Gibt einen /dev/serial/by-id Match für das Gerät zurück, falls verfügbar."""
    by_id = "/dev/serial/by-id"
    if not os.path.isdir(by_id):
        return dev_path
    
    for path in (entry.path for entry in os.scandir(by_id) if entry.is_symlink()):
        if os.path.realpath(path) == dev_path:
            return path
    return dev_path
```

### 3. Quellen abfragen

```python
def get_sources(self) -> {}:
    sources = {}
    for i in range(1, 13):
        try:
            response = self.exec_command(f"Source{i}.Enabled", "?")
            if response is not None and response.lower() == "yes":
                response = self.exec_command(f"Source{i}.Name", "?")
                sources[i] = response
        except CommandNotSupportedError:
            break
    return sources
```

---

## 📝 Schema-Definitionen

### 1. Config Flow Schemas

```python
# Telnet Setup Schema
STEP_SETUP_TELNET_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): TextSelector(),
    vol.Required(CONF_PORT, default=CONF_DEFAULT_PORT): NumberSelector(
        NumberSelectorConfig(min=1, max=65535, mode=NumberSelectorMode.BOX)
    ),
})

# TCP Setup Schema
STEP_SETUP_TCP_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): TextSelector(),
})

# Volume Config Schema
STEP_CONFIG_VOLUME_SCHEMA = vol.Schema({
    vol.Required(
        CONF_MIN_VOLUME,
        default=CONF_DEFAULT_MIN_VOLUME,
    ): NumberSelector(
        NumberSelectorConfig(
            min=-92,
            max=20,
            mode=NumberSelectorMode.BOX,
            unit_of_measurement=UnitOfSoundPressure.DECIBEL,
        )
    ),
    vol.Required(
        CONF_MAX_VOLUME,
        default=CONF_DEFAULT_MAX_VOLUME,
    ): NumberSelector(
        NumberSelectorConfig(
            min=-92,
            max=20,
            mode=NumberSelectorMode.BOX,
            unit_of_measurement=UnitOfSoundPressure.DECIBEL,
        )
    ),
})
```

---

## 🎯 Service Call Muster

### 1. Media Player Services

```python
# Lautstärke setzen
await hass.services.async_call(
    DOMAIN_MEDIA_PLAYER,
    SERVICE_VOLUME_SET,
    {
        "entity_id": "media_player.nad_main",
        "volume_level": 0.5,
    },
)

# Quelle auswählen
await hass.services.async_call(
    DOMAIN_MEDIA_PLAYER,
    SERVICE_SELECT_SOURCE,
    {
        "entity_id": "media_player.nad_main",
        "source": "TV",
    },
)
```

### 2. Switch Services

```python
# Schalter einschalten
await hass.services.async_call(
    DOMAIN_SWITCH,
    SERVICE_TURN_ON,
    {
        "entity_id": "switch.nad_speaker_sub",
    },
)
```

### 3. Number Services

```python
# Wert setzen
await hass.services.async_call(
    DOMAIN_NUMBER,
    SERVICE_SET_VALUE,
    {
        "entity_id": "number.nad_main_bass",
        "value": 5.0,
    },
)
```

---

## 🔍 Debugging Muster

### 1. Debug-Logging

```python
_LOGGER.debug("Debug-Meldung: %s", variable)
_LOGGER.info("Info-Meldung: %s", variable)
_LOGGER.error("Fehler-Meldung: %s", error)
```

### 2. Daten inspizieren

```python
# Coordinator-Daten anzeigen
_LOGGER.debug("Coordinator data: %s", self.coordinator.data)

# Entity-Status anzeigen
_LOGGER.debug("Entity state: %s", self._attr_state)

# Befehlsantwort anzeigen
_LOGGER.debug("Command response: %s", response)
```

### 3. Exception Handling

```python
try:
    response = self.coordinator.exec_command(command, "?")
    if response is None:
        _LOGGER.error("No response for command: %s", command)
        return
except CommandNotSupportedError:
    _LOGGER.debug("Command not supported: %s", command)
    self._attr_available = False
except Exception as ex:
    _LOGGER.error("Error executing command %s: %s", command, ex)
    self._attr_available = False
```

---

## 📊 Datenverarbeitung

### 1. String zu Boolean

```python
# "On" / "Off" zu True / False
is_on = response.lower() == "on"
```

### 2. String zu Float

```python
# Prüfen ob String eine Zahl ist
if value.lstrip("-").replace(".", "", 1).isnumeric():
    float_value = float(value)
```

### 3. String zu Integer

```python
# Prüfen ob String eine Ganzzahl ist
if value.lstrip("-").isnumeric():
    int_value = int(value)
```

### 4. Volumen-Berechnung

```python
# dB zu 0.0-1.0
def calc_volume(self, decibel):
    return abs(self._min_volume - decibel) / abs(self._min_volume - self._max_volume)

# 0.0-1.0 zu dB
def calc_db(self, volume):
    return self._min_volume + round(abs(self._min_volume - self._max_volume) * volume)
```

---

## 🎨 UI-Elemente

### 1. SelectSelector

```python
SelectSelector(
    SelectSelectorConfig(
        options=[
            SelectOptionDict(value="on", label="Ein"),
            SelectOptionDict(value="off", label="Aus"),
        ],
        mode=SelectSelectorMode.DROPDOWN,
        custom_value=True,
        sort=True,
    )
)
```

### 2. NumberSelector

```python
NumberSelector(
    NumberSelectorConfig(
        min=-10,
        max=10,
        mode=NumberSelectorMode.BOX,
        unit_of_measurement=UnitOfSoundPressure.DECIBEL,
        step=1,
    )
)
```

### 3. TextSelector

```python
TextSelector(
    TextSelectorConfig(
        type=TextSelectorType.TEXT,
        placeholder="Geben Sie einen Wert ein",
    )
)
```

---

## 📝 Best Practices

### 1. Fehlerbehandlung

✅ **Gut:**
```python
try:
    response = self.coordinator.exec_command(command, "?")
    if response is None:
        self._attr_available = False
        return
except CommandNotSupportedError:
    _LOGGER.debug("%s not supported", command)
    self._attr_available = False
except Exception as ex:
    _LOGGER.error("Error: %s", ex)
    self._attr_available = False
```

❌ **Schlecht:**
```python
# Keine Fehlerbehandlung
response = self.coordinator.exec_command(command, "?")
self._attr_native_value = float(response)  # Kann fehlschlagen!
```

### 2. Verfügbarkeit prüfen

✅ **Gut:**
```python
@property
def available(self) -> bool:
    """Return if entity is available."""
    if not self._attr_available:
        return self._attr_available
    return self.coordinator.last_update_success
```

❌ **Schlecht:**
```python
@property
def available(self) -> bool:
    return True  # Immer verfügbar - nicht realistisch!
```

### 3. Zustand aktualisieren

✅ **Gut:**
```python
self._attr_native_value = new_value
self._attr_available = True
self.async_write_ha_state()
```

❌ **Schlecht:**
```python
self._attr_native_value = new_value
# Vergessen, async_write_ha_state() aufzurufen!
```

### 4. Listener registrieren

✅ **Gut:**
```python
# Im __init__ der Entität
coordinator.add_listener_command(self.entity_description.key)
```

❌ **Schlecht:**
```python
# Listener nie registriert - Daten werden nicht aktualisiert!
```

### 5. Dynamische Entitäts-Erstellung

✅ **Gut:**
```python
if coordinator.supports_command(entity_description.key):
    entities.append(MyEntity(coordinator, entity_description))
```

❌ **Schlecht:**
```python
# Alle Entitäten erstellen, auch wenn sie nicht unterstützt werden
entities.append(MyEntity(coordinator, entity_description))
```

---

## 🔧 Häufige Code-Muster

### 1. Einfache Entität mit Ein/Aus

```python
class SimpleSwitch(CoordinatorEntity, SwitchEntity):
    _attr_has_entity_name = True
    
    def __init__(self, coordinator, command):
        super().__init__(coordinator, command)
        self._attr_unique_id = f"{coordinator.unique_id}-{command.lower()}"
        self.command = command
        coordinator.add_listener_command(command)
    
    @callback
    def _handle_coordinator_update(self) -> None:
        if self.coordinator.data and (state := self.coordinator.data.get(self.command)):
            self._attr_is_on = state.lower() == "on"
            self._attr_available = True
        else:
            self._attr_available = False
        self.async_write_ha_state()
    
    async def async_turn_on(self, **kwargs) -> None:
        response = self.coordinator.exec_command(self.command, "=", "On")
        self._attr_is_on = response.lower() == "on"
        self.async_write_ha_state()
    
    async def async_turn_off(self, **kwargs) -> None:
        response = self.coordinator.exec_command(self.command, "=", "Off")
        self._attr_is_on = response.lower() == "off"
        self.async_write_ha_state()
```

### 2. Entität mit numerischem Wert

```python
class SimpleNumber(CoordinatorEntity, NumberEntity):
    _attr_has_entity_name = True
    
    def __init__(self, coordinator, command, min_val, max_val, step=1):
        super().__init__(coordinator, command)
        self._attr_unique_id = f"{coordinator.unique_id}-{command.lower()}"
        self.command = command
        self._attr_native_min_value = min_val
        self._attr_native_max_value = max_val
        self._attr_native_step = step
        coordinator.add_listener_command(command)
    
    @callback
    def _handle_coordinator_update(self) -> None:
        if self.coordinator.data and (value := self.coordinator.data.get(self.command)):
            if value.lstrip("-").replace(".", "", 1).isnumeric():
                self._attr_native_value = float(value)
                self._attr_available = True
        else:
            self._attr_available = False
        self.async_write_ha_state()
    
    async def async_set_native_value(self, value: float) -> None:
        if self.coordinator.power_state == MediaPlayerState.ON:
            response = self.coordinator.exec_command(self.command, "=", value)
            if response.lstrip("-").replace(".", "", 1).isnumeric():
                self._attr_native_value = float(response)
        self.async_write_ha_state()
```

---

## 📚 Ressourcen

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [NAD Receiver Library](https://github.com/rrooggiieerr/nad_receiver)
- [Python Serial Library](https://pyserial.readthedocs.io/)
- [Voluptuous Validation](https://github.com/alecthomas/voluptuous)

---

*Diese Code-Snippets-Sammlung wurde für Entwickler der NAD Receiver Integration erstellt. Letzte Aktualisierung: 2024*
