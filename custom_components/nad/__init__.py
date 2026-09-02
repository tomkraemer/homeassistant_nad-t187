"""The NAD Receiver component."""

import logging
import threading
#------------START-----------------
# [v1.0.2][FIX: Response-Queue mit Timestamps]
# datetime Import für Timestamp-Verwaltung in der Queue
# <CODE CHANGED>
# from datetime import timedelta
# to:
# from datetime import datetime, timedelta
#------------END-----------------
from datetime import datetime, timedelta
from typing import Any, Callable

import homeassistant.helpers.config_validation as cv
import serial
import voluptuous as vol
from homeassistant.components.media_player.const import MediaPlayerState
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_TYPE,
    Platform,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .NADReceiver import NADReceiver, NADReceiverTCP, NADReceiverTelnet
from .NADReceiver.exceptions import CommandNotSupportedError

from .const import (
    CONF_SERIAL_PORT,
    CONF_TYPE_SERIAL,
    CONF_TYPE_TCP,
    CONF_TYPE_TELNET,
    DOMAIN,
    CONF_COUNT_OF_SOURCES,
    #------------START-----------------
    # [v1.0.2][FIX: Response-Queue Alterungsbegrenzung]
    # Import der Queue-Lebensdauer-Konstante
    # <CODE ADDED>
    # CONF_MAX_READ_QUEUE_LAYTIME,
    #------------END-----------------
    CONF_MAX_READ_QUEUE_LAYTIME,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.MEDIA_PLAYER,
    Platform.NUMBER,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.SENSOR,
]


def log_properties(obj, name):
    #print(f"--- Eigenschaften von {name} ---")
    _LOGGER.debug("--- Eigenschaften von %s ---", name)
    for attr in dir(obj):
        # Ignoriere private/geschützte Attribute und Methoden
        if not attr.startswith('_'):
            try:
                value = getattr(obj, attr)
                # Prüfe, ob es sich um eine Methode/Funktion handelt
                if not callable(value):
                    #print(f"{attr}: {type(value).__name__} = {value}")
                    _LOGGER.debug("%s: [%s] - %s", attr, type(value).__name__, value)
            except Exception as e:
                #print(f"{attr}: Konnte Wert nicht lesen ({e})")
                _LOGGER.debug("%s: Konnte Wert nicht lesen (%s)", attr, e)

def log_status_dict (data, name):
    _LOGGER.debug("--- Inhalt von %s:", name)
    for k, v in data.items():
        _LOGGER.debug("DATA CONTENT - key: %s value: %s", k, v)

class NADReceiverCoordinator(DataUpdateCoordinator):
    """NAD Receiver Data Update Coordinator"""

    receiver: NADReceiver = None

    should_poll = False

    unique_id = None
    model: str = None
    version: str = None
    device_info: DeviceInfo = None

    power_state = None

    _listener_commands = []

    def __init__(self, hass, entry: ConfigEntry, zone: str = "Main"):
        # [v1.0.0][FEATURE: Zwei Coordinator-Instanzen]
        # Default-Zone eingeführt
        self.zone = zone
        self.data = {}
    
        """Initialize NAD Receiver Data Update Coordinator"""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name=__name__,
            # Polling interval. Will only be polled if there are subscribers.
            #update_interval=timedelta(seconds=25),
        )

        self.config = entry.data
        self.options = entry.options
        self.unique_id = entry.entry_id
        self.hass = hass

        config_type = self.config[CONF_TYPE]
        if config_type == CONF_TYPE_SERIAL:
            serial_port = self.config[CONF_SERIAL_PORT]
            self.receiver = NADReceiver(serial_port, coordinator=self)

        elif config_type == CONF_TYPE_TELNET:
            host = self.config[CONF_HOST]
            port = self.config[CONF_PORT]
            self.receiver = NADReceiverTelnet(host, port, coordinator=self)

        elif config_type == CONF_TYPE_TCP:
            host = self.config[CONF_HOST]
            self.receiver = NADReceiverTCP(host, coordinator=self)

    async def connect(self) -> bool:
        if not self.model:
            # Open the connection by requesting the model
            try:
                self.model = self.exec_command("Main.Model", "?")
                self.version = self.exec_command("Main.Version", "?")
            except CommandNotSupportedError:
                return False

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

            self.sources = self.get_sources()

            return True

    async def disconnect(self):
        pass

    @callback
    def async_add_listener(
        self, update_callback: CALLBACK_TYPE, context: Any = None
    ) -> Callable[[], None]:
        remove_listener = super().async_add_listener(update_callback, context)

        _LOGGER.debug("Adding listener for %s", context)
        if context:
            self.add_listener_command(context)

        return remove_listener

    def add_listener_command(self, command):
        _LOGGER.debug("Adding command %s", command)
        if command not in self._listener_commands:
            self._listener_commands.append(command)
            # initialize status with the current value
            self.exec_command(command, "?")

    def _fetch_listener_data(self, data: dict, zone: str) -> dict:
        """Fetch data for all listener commands. Synchronous method to be run in executor."""
        for command in self._listener_commands:
            if command not in data and command.startswith(f"{zone}."):
                data[command] = self.exec_command(command, "?")
        return data

    def get_sources(self) -> {}:
        sources = {}

        #------------START-----------------
        # [v1.0.2][FIX: Anzahl der Quellen]
        # Mein NAD hat nur 10 Quellen
        # Ist in const.py hinterlegt
        for i in range(1, CONF_COUNT_OF_SOURCES):
        #------------END-------------------
            try:
                response = self.exec_command(f"Source{i}.Enabled", "?")
                if response is not None and response.lower() == "yes":
                    response = self.exec_command(f"Source{i}.Name", "?")
                    sources[i] = response
            except CommandNotSupportedError:
                break
        return sources

    def supports_command(self, command: str):
        try:
            response = self.exec_command(command, "?")
        except CommandNotSupportedError:
            _LOGGER.warning("%s not supported", command)
            return False

        _LOGGER.debug("%s supported", command)
        # initialize status with the current value
        # if not self.data:
        #     self.data = {}
        self.data[command] = response

        return True

    def write_command(self, command: str, operator: str, value: str = None):
        cmd = f"{command}{operator}"
        if value:
            cmd = f"{cmd}{value}"
        if self.config[CONF_TYPE] == CONF_TYPE_SERIAL:
            self.receiver.transport.ser.reset_input_buffer()
        return self.receiver.transport.write_command(cmd)
    
    def exec_command(self, command: str, operator: str, value: str = None):
        cmd = f"{command}{operator}"
        #------------START-----------------
        # [v1.0.2][FIX: Response-Queue für konkurrierende Lesezugriffe]
        # expected_prefix vorab berechnen für Queue-Suche
        # <CODE ADDED>
        # expected_prefix = f"{command}="  # z. B. "Main.Power="
        #------------END-----------------
        expected_prefix = f"{command}="  # z. B. "Main.Power="
        if value:
            cmd = f"{cmd}{value}"

        if self.config[CONF_TYPE] == CONF_TYPE_SERIAL:
            self.receiver.transport.ser.reset_input_buffer()

        return self.receiver.transport.communicate(cmd)

        
    
        try:
            # With the new writer/reader pattern, communicate() just writes the command
            # The reader thread handles reading responses and adds them to the queue
            # The reader calls async_set_updated_data() when new data arrives
            self.receiver.transport.communicate(cmd)
            _LOGGER.debug("sent: '%s'", cmd)

            # Suche in der Queue nach der Antwort (falls bereits da)
            result = self._search_in_queue(expected_prefix)
            if result is not None:
                _LOGGER.debug("sent: '%s' found in queue: '%s'", cmd, result)
                return result

            # -- Falls keine passende Zeile gefunden wurde
            _LOGGER.warning("No response found in queue for command: '%s'", cmd)
            raise CommandNotSupportedError()
            
        #------------START-----------------
        # [v1.0.0][FIX: Timeouts abfangen]
        # Timeouts können gelegentlich auftreten (z. B. bei langsamer serieller Verbindung)
        # und werden hier bewusst ignoriert, aber als Debug-Info geloggt, um den
        # normalen Flow nicht zu unterbrechen. Rückgabe: None
        except (TimeoutError, serial.SerialTimeoutException) as ex:
            _LOGGER.debug("Timeout in exec_command for '%s': %s", cmd, ex)
            return None
        #------------END-------------------
        except UnicodeDecodeError as ex:
            _LOGGER.error("Decode error in exec_command: %s", ex)
            raise CommandNotSupportedError()

    async def _async_update_data(self):
        _LOGGER.info(" Async Update ")

    
    async def _async_update_data(self):
        """return Status of NAD Receiver."""
        
        data = self.receiver.transport.data

        # Debug-Ausgabe: Inhalt von data zeilenweise
        # log_status_dict (data, "NAD-Data")

        # power_state = data[f"{self.zone}.Power"]

        # if not power_state:
        #     self.power_state = None
        #     raise UpdateFailed("Error communicating with NAD Receiver") 
    
        # """Fetch data from NAD Receiver."""

        try:
            #------------START-----------------
            # [v1.0.0][FEATURE: Zwei Coordinator-Instanzen]
            # jetzt muss auch dei richtige Zone genommen werden
            #power_state = self.exec_command("Main.Power", "?")
            power_state = self.exec_command(f"{self.zone}.Power", "?")
            #------------END-------------------
        except CommandNotSupportedError:
            self.power_state = None
            _LOGGER.error("Error communicating with NAD Receiver (CommandNotSupportedError). Tried '%s'.power? received: '%s'", self.zone, power_state)
            raise UpdateFailed("Error communicating with NAD Receiver (CommandNotSupportedError). Tried '%s'.power?", self.zone)
        except IOError as ex:
            self.power_state = None
            _LOGGER.error("Error communicating with NAD Receiver (IOError). Tried '%s'.power?", self.zone)
            raise UpdateFailed("Error communicating with NAD Receiver (IOError)", ex)

        if power_state.lower() == "on":
            self.power_state = MediaPlayerState.ON
        else:
            self.power_state = MediaPlayerState.OFF

        return data

        data = {}
        #------------START-----------------
        # [v1.0.0][FEATURE: Zwei Coordinator-Instanzen]
        # jetzt muss auch dei richtige Zone genommen werden
        data[f"{self.zone}.Power"] = power_state
        #------------END-------------------

        #------------START-----------------
        # [v1.0.2][FIX: Schleifen-Block asynchron ausfuehren]
        # Der Schleifen-Block wird als synchrone Methode ueber den Executor ausgefuehrt
        data = await self.hass.async_add_executor_job(
            self._fetch_listener_data, data, self.zone
        )
        #------------END-------------------

        return data
        return data


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up NAD Receiver from a config entry."""

    @callback
    def _async_migrate_entity_entry(
        registry_entry: entity_registry.RegistryEntry,
    ) -> dict[str, Any] | None:
        """ Migrates old unique ID to the new unique ID. """
        if entry.data[CONF_TYPE] == CONF_TYPE_SERIAL:
            if registry_entry.unique_id.startswith(f"{entry.data[CONF_SERIAL_PORT]}-"):
                new_unique_id = registry_entry.unique_id.replace(
                    f"{entry.data[CONF_SERIAL_PORT]}-",
                    f"{registry_entry.config_entry_id}-",
                )
                _LOGGER.debug("Migrating entity unique id to %s", new_unique_id)
                return {"new_unique_id": new_unique_id}

        # No migration needed
        return None

    await entity_registry.async_migrate_entries(hass, entry.entry_id, _async_migrate_entity_entry)

    try:
        #------------START-----------------
        # [v1.0.0][FEATURE: Zwei Coordinator-Instanzen]
        # Erstelle einen Coordinator pro Zone (mir langt Main und Zone2)
        coordinators = {
            "Main": NADReceiverCoordinator(hass, entry, zone="Main"),
            "Zone2": NADReceiverCoordinator(hass, entry, zone="Zone2"),
        }
        #receiver_coordinator = NADReceiverCoordinator(hass, entry)
        #-------------END-----------------
        
        # Open the connection.
        #if not await receiver_coordinator.connect():
        if not await coordinators["Main"].connect():
            raise ConfigEntryNotReady(f"Unable to connect to NAD receiver Main")
        _LOGGER.info("NAD receiver Main is available")

        #------------START-----------------
        # [v1.0.0][FEATURE: Zwei Coordinator-Instanzen]
        if not await coordinators["Zone2"].connect():
            raise ConfigEntryNotReady(f"Unable to connect to NAD receiver Zone2")
        _LOGGER.info("NAD receiver Zone2 is available")
        #-------------END-----------------

    except serial.SerialException as ex:
        raise ConfigEntryNotReady(f"Unable to connect to NAD receiver") from ex

    #------------START-----------------
    # [v1.0.0][FEATURE: Zwei Coordinator-Instanzen]
    # Speichere alle Coordinators in runtime_data
    entry.runtime_data = coordinators  # ✅ Nicht nur ein Coordinator, sondern ein Dict!
    # ursprünglich: ein Coordinator:
    #entry.runtime_data = receiver_coordinator
    #-------------END-----------------
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # config_type = coordinators["Main"].config[CONF_TYPE]
    # Start the reader thread for this transport
    # We only need ONE Read-Loop. Choosing "Main" as the always present zone
    # Start the reader thread for this transport (if available)
    receiver = coordinators["Main"].receiver
    if hasattr(receiver, 'transport') and hasattr(receiver.transport, 'start_reader'):
        receiver.transport.start_reader()

    data = receiver.transport.data
    # provide an overview of the data collected so far in the status:
    log_status_dict (data, "NAD-Status")

    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    #------------START-----------------
    # [v1.0.0][FEATURE: Zwei Coordinator-Instanzen]
    # wir müssen wählen und nehmen "Main"
    receiver_coordinator: NADReceiverCoordinator = entry.runtime_data["Main"]
    await receiver_coordinator.disconnect()
    #-------------END-----------------
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.debug("Configuration options updated, reloading NAD receiver integration")
    hass.config_entries.async_schedule_reload(entry.entry_id)(entry.entry_id)
