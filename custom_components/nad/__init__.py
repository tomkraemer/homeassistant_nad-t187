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


class NADReceiverCoordinator(DataUpdateCoordinator):
    """NAD Receiver Data Update Coordinator"""

    receiver: NADReceiver = None

    unique_id = None
    model: str = None
    version: str = None
    device_info: DeviceInfo = None

    power_state = None

    _listener_commands = []
    #------------START-----------------
    # [v1.0.2][FIX: Response-Stack zu FIFO-Queue]
    # Umbenennung von Stack zu Queue für FIFO-Verhalten
    # <CODE CHANGED>
    # _response_stack = []  # Globaler Stack für alle empfangenen Antwortzeilen
    # to:
    # _response_queue = []  # FIFO-Schlange für alle empfangenen Antwortzeilen
    #------------END-----------------
    _response_queue = []  # FIFO-Schlange für alle empfangenen Antwortzeilen
    _stack_lock = None    # Thread-Lock für Queue-Zugriff

    def __init__(self, hass, entry: ConfigEntry, zone: str = "Main"):
        # [v1.0.0][FEATURE: Zwei Coordinator-Instanzen]
        # Default-Zone eingeführt
        self.zone = zone
        
        # [v1.0.2][FIX: Response-Queue für konkurrierende Lesezugriffe]
        # FIFO-Schlange für alle Antworten, um Zwischenantworten nicht zu verlieren
        #------------START-----------------
        # [v1.0.2][FIX: Response-Queue für konkurrierende Lesezugriffe]
        # Initialisierung der FIFO-Queue und des Locks
        # <CODE ADDED>
        # self._response_queue = []
        # self._stack_lock = threading.Lock()
        #------------END-----------------
        self._response_queue = []
        self._stack_lock = threading.Lock()
    
        """Initialize NAD Receiver Data Update Coordinator"""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name=__name__,
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=25),
        )

        self.config = entry.data
        self.options = entry.options
        self.unique_id = entry.entry_id

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

    def _fetch_listener_data(self, data: dict, zone: str) -> dict:
        """Fetch data for all listener commands. Synchronous method to be run in executor."""
        for command in self._listener_commands:
            if command not in data and command.startswith(f"{zone}."):
                data[command] = self.exec_command(command, "?")
        return data

    #------------START-----------------
    # [v1.0.2][FIX: Response-Queue für konkurrierende Lesezugriffe]
    # Thread-sicheres Hinzufügen von Antwortzeilen zur Queue mit Timestamp
    # <CODE ADDED>
    # def _add_to_queue(self, line: str):
    #     """Füge eine Antwortzeile der FIFO-Queue hinzu (thread-safe)."""
    #     with self._stack_lock:
    #         self._response_queue.append((datetime.now(), line))
    #         _LOGGER.debug("Queue: added '%s'", line)
    #------------END-----------------
    def _add_to_queue(self, line: str):
        """Füge eine Antwortzeile der FIFO-Queue hinzu (thread-safe)."""
        with self._stack_lock:
            self._response_queue.append((datetime.now(), line))
            _LOGGER.debug("Queue: added '%s'", line)

    #------------START-----------------
    # [v1.0.2][FIX: Response-Queue Alterungsbegrenzung]
    # Thread-sicheres Suchen in der Queue mit automatischer Bereinigung 
    # alter Einträge (>CONF_MAX_READ_QUEUE_LAYTIME)
    # <CODE ADDED>
    # def _search_in_queue(self, prefix: str) -> str | None:
    #     """Suche nach Antwort in der Queue (FIFO), entferne sie und gib den Wert zurück.
    #     Entfernt vorher alle Einträge, die älter als CONF_MAX_READ_QUEUE_LAYTIME Sekunden sind."""
    #     with self._stack_lock:
    #         # Bereinige Queue: Entferne Einträge älter als CONF_MAX_READ_QUEUE_LAYTIME Sekunden
    #         cutoff = datetime.now() - timedelta(seconds=CONF_MAX_READ_QUEUE_LAYTIME)
    #         self._response_queue = [(ts, line) for ts, line in self._response_queue if ts >= cutoff]
    #         
    #         # FIFO: Durchsuche von vorne nach hinten
    #         for i, (ts, line) in enumerate(self._response_queue):
    #             if line.startswith(prefix):
    #                 # Entferne das Element an Position i
    #                 del self._response_queue[i]
    #                 return line.split("=", 1)[1]
    #         _LOGGER.warning("Queue: NOTHING found for prefix '%s'", prefix)
    #         return None
    #------------END-----------------
    def _search_in_queue(self, prefix: str) -> str | None:
        """Suche nach Antwort in der Queue (FIFO), entferne sie und gib den Wert zurück.
        Entfernt vorher alle Einträge, die älter als CONF_MAX_READ_QUEUE_LAYTIME Sekunden sind."""
        with self._stack_lock:
            # Bereinige Queue: Entferne Einträge älter als CONF_MAX_READ_QUEUE_LAYTIME Sekunden
            cutoff = datetime.now() - timedelta(seconds=CONF_MAX_READ_QUEUE_LAYTIME)
            self._response_queue = [(ts, line) for ts, line in self._response_queue if ts >= cutoff]
            
            # FIFO: Durchsuche von vorne nach hinten
            for i, (ts, line) in enumerate(self._response_queue):
                if line.startswith(prefix):
                    # Entferne das Element an Position i
                    del self._response_queue[i]
                    return line.split("=", 1)[1]
            _LOGGER.warning("Queue: NOTHING found for prefix '%s'", prefix)
            return None

    def get_sources(self) -> {}:
        sources = {}

        #------------START-----------------
        # [v1.0.2][FIX: Anzahl der Quellen]
        # Mein NAD hat nur 10 Quellen
        # Ist in const.py hinterlegt
        #for i in range(1, 13):
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
        if not self.data:
            self.data = {}
        self.data[command] = response

        return True

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

        try:
            #------------START-----------------
            # [v1.0.2][FIX: Response-Stack für konkurrierende Lesezugriffe]
            # Alle Zeilen aus raw_response werden in den globalen Stack geschrieben,
            # um Zwischenantworten nicht zu verlieren. Danach wird im Stack nach
            # der passenden Antwort gesucht (auch wenn raw_response leer war).
            #------------END-------------------
            
            raw_response = self.receiver.transport.communicate(cmd)
            _LOGGER.debug("sent: '%s' raw reply: '%s'", cmd, raw_response)

            # Alle Zeilen aus der Antwort in den Stack schieben
            if raw_response:
                for line in raw_response.splitlines():
                    line = line.strip()
                    if line:  # Leere Zeilen ignorieren
                        #------------START-----------------
                        # [v1.0.2][FIX: Response-Queue für konkurrierende Lesezugriffe]
                        # Verwendung der neuen Queue-Methode statt Stack
                        # <CODE CHANGED>
                        # self._add_to_stack(line)
                        # to:
                        # self._add_to_queue(line)
                        #------------END-----------------
                        self._add_to_queue(line)

            # Suche in der Queue nach der Antwort (inkl. der gerade hinzugefügten Zeilen)
            # expected_prefix = f"{command}="  # z. B. "Main.Power="
            #------------START-----------------
            # [v1.0.2][FIX: Response-Queue für konkurrierende Lesezugriffe]
            # Verwendung der neuen Queue-Methode statt Stack
            # <CODE CHANGED>
            # result = self._search_in_stack(expected_prefix)
            # to:
            # result = self._search_in_queue(expected_prefix)
            #------------END-----------------
            result = self._search_in_queue(expected_prefix)
            if result is not None:
                _LOGGER.debug("sent: '%s' found in stack: '%s'", cmd, result)
                return result

            # Falls nicht im Stack gefunden, in raw_response suchen (für immediate Antworten)
            if raw_response:
                for line in raw_response.splitlines():
                    line = line.strip()
                    if line.startswith(expected_prefix):
                        return line.split("=", 1)[1]

            # -- Falls keine passende Zeile gefunden wurde
            if not raw_response:
                raise CommandNotSupportedError()
            
            _LOGGER.error("Error communicating with NAD Receiver (CommandNotSupportedError)")
            _LOGGER.error("tried '%s'", cmd)
            _LOGGER.error("received (raw): '%s'", raw_response)
            raise CommandNotSupportedError()
            #------------END-------------------

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
        """Fetch data from NAD Receiver."""
        #------------START-----------------
        # [v1.0.2][FEATURE: Queue-Size Logging]
        # Logausgabe der aktuellen Queue-Länge zu Debug-Zwecken
        # <CODE ADDED>
        # _LOGGER.info("Queue size at start of _async_update_data: %d", len(self._response_queue))
        #------------END-----------------
        _LOGGER.info("Queue size at start of _async_update_data: %d", len(self._response_queue))

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

        _LOGGER.debug("power_state: %s", power_state)

        if not power_state:
            self.power_state = None
            raise UpdateFailed("Error communicating with NAD Receiver") 

        if power_state.lower() == "on":
            self.power_state = MediaPlayerState.ON
        else:
            self.power_state = MediaPlayerState.OFF


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
        """
        Migrates old unique ID to the new unique ID.
        """
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

    await entity_registry.async_migrate_entries(
        hass, entry.entry_id, _async_migrate_entity_entry
    )

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
