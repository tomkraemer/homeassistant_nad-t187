"""The NAD Receiver component."""

import logging
import threading
# ------------START-----------------
# [v1.0.2][FIX: Response-Queue mit Timestamps]
# datetime Import für Timestamp-Verwaltung in der Queue
# <CODE CHANGED>
# from datetime import timedelta
# to:
# from datetime import datetime, timedelta
# ------------END-----------------
from datetime import datetime, timedelta
from typing import Any, Callable

import homeassistant.helpers.config_validation as cv
import serial
import voluptuous as vol
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.media_player.const import MediaPlayerState
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (CONF_DEVICE_ID, CONF_HOST, CONF_NAME,
                                 CONF_PORT, CONF_TYPE, Platform)
from homeassistant.core import (CALLBACK_TYPE, HomeAssistant, ServiceCall,
                                callback)
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (DataUpdateCoordinator,
                                                      UpdateFailed)

from .const import (CONF_COUNT_OF_SOURCES, CONF_SERIAL_PORT, CONF_TYPE_SERIAL,
                    CONF_TYPE_TCP, CONF_TYPE_TELNET, DOMAIN)
# from .NADReceiver import NADReceiver, NADReceiverSerial, NADReceiverTCP, NADReceiverTelnet
from .NADReceiver import (NADReceiver, NADReceiverSerial, NADReceiverTCP,
                          NADReceiverTelnet)
from .NADReceiver.exceptions import CommandNotSupportedError

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.MEDIA_PLAYER,
    Platform.NUMBER,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.SENSOR,
]


def log_properties(obj, name):
    # print(f"--- Eigenschaften von {name} ---")
    _LOGGER.debug("--- Eigenschaften von %s ---", name)
    for attr in dir(obj):
        # Ignoriere private/geschützte Attribute und Methoden
        if not attr.startswith("_"):
            try:
                value = getattr(obj, attr)
                # Prüfe, ob es sich um eine Methode/Funktion handelt
                if not callable(value):
                    # print(f"{attr}: {type(value).__name__} = {value}")
                    _LOGGER.debug("%s: [%s] - %s", attr, type(value).__name__, value)
            except Exception as e:
                # print(f"{attr}: Konnte Wert nicht lesen ({e})")
                _LOGGER.debug("%s: Konnte Wert nicht lesen (%s)", attr, e)


def log_status_dict(data, name):
    _LOGGER.debug("--- Inhalt von %s:", name)
    for k, v in data.items():
        _LOGGER.debug("DATA CONTENT - key: %s value: %s", k, v)


class NADReceiverCoordinator(DataUpdateCoordinator):
    """NAD Receiver Data Update Coordinator"""

    receiver: NADReceiver = None
    # should_poll = False

    unique_id = None
    model: str = None
    version: str = None
    device_info: DeviceInfo = None

    _listener_commands = []

    def __init__(self, hass, entry: ConfigEntry, zone: str = "Main"):
        """Initialize NAD Receiver Data Update Coordinator"""
        self.zone = zone
        self.initialized = False

        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name=__name__,
            # Polling interval. Will only be polled if there are subscribers.
            # update_interval=timedelta(seconds=25),
            update_interval=None,
        )

        # _LOGGER.debug("INIT -boot- NADReceiverCoordinator - config_entry: %s", entry)
        # _LOGGER.debug("INIT -boot- NADReceiverCoordinator - self: %s", self)

        self.config = entry.data
        self.options = entry.options
        self.unique_id = entry.entry_id
        self.hass = hass

        config_type = self.config[CONF_TYPE]
        if config_type == CONF_TYPE_SERIAL:
            serial_port = self.config[CONF_SERIAL_PORT]
            self.receiver = NADReceiverSerial(serial_port, coordinator=self)

        elif config_type == CONF_TYPE_TELNET:
            host = self.config[CONF_HOST]
            port = self.config[CONF_PORT]
            self.receiver = NADReceiverTelnet(host, port, coordinator=self)

        elif config_type == CONF_TYPE_TCP:
            host = self.config[CONF_HOST]
            self.receiver = NADReceiverTCP(host, coordinator=self)

    @property
    def available(self) -> bool:
        try:
            res = self.receiver.available
        except:
            res = False
        return res

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

    async def _async_update_data(self):
        return self.receiver.data or {}

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

    def get_sources(self) -> {}:
        sources = {}

        for i in range(1, CONF_COUNT_OF_SOURCES + 1):
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
            self.exec_command(command, "?")
        except CommandNotSupportedError:
            _LOGGER.warning("%s not supported", command)
            return False
        return True

    def write_command(self, command: str, operator: str, value: str):
        cmd = f"{command}{operator}"
        if value:
            cmd = f"{cmd}{value}"
        return self.receiver.write_command(cmd)

    def exec_command(self, command: str, operator: str, value: str = None):
        cmd = f"{command}{operator}"
        if value:
            cmd = f"{cmd}{value}"
        res = self.receiver.exec_command(cmd)
        # _LOGGER.debug("exec_command: '%s' -> '%s", cmd, res)
        return res


#####################################################################################
#   IMPLEMENTING THE BASIC HA-FUNCTIONS
#   - async_setup_entry
#   - async_unload_entry
#   -update_listener
#
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up NAD Receiver from a config entry."""

    @callback
    def _async_migrate_entity_entry(
        registry_entry: entity_registry.RegistryEntry,
    ) -> dict[str, Any] | None:
        """Migrates old unique ID to the new unique ID."""
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
    # _LOGGER.debug("NADReceiverCoordinator -boot- async_setup_entry - configEntry:%s", entry)

    # Building the zones. F.t.t.b we introduce two zones (Main, Zone2) as fixed
    try:
        coordinators = {
            "Main": NADReceiverCoordinator(hass, entry, zone="Main"),
            "Zone2": NADReceiverCoordinator(hass, entry, zone="Zone2"),
        }
        if not await coordinators["Main"].connect():
            raise ConfigEntryNotReady(f"Unable to connect to NAD receiver Main")
        _LOGGER.info("NAD receiver Main is available")
        if not await coordinators["Zone2"].connect():
            raise ConfigEntryNotReady(f"Unable to connect to NAD receiver Zone2")
        _LOGGER.info("NAD receiver Zone2 is available")

    except serial.SerialException as ex:
        raise ConfigEntryNotReady(f"Unable to connect to NAD receiver") from ex

    entry.runtime_data = coordinators

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # _LOGGER.debug("NADReceiverCoordinator -boot- after async_forward_entry_setups")

    # Start the reader thread for this transport
    # We only need ONE Read-Loop. Choosing "Main" as the always present zone
    # Start the reader thread for this transport (if available)
    receiver = coordinators["Main"].receiver
    if hasattr(receiver, "start_reader"):
        receiver.start_reader()

    # provide an overview of the data collected so far in the status:
    # if _LOGGER.level == logging.DEBUG:
    #     # log_status_dict (receiver.transport.data, "NAD-Status")
    #     log_status_dict (receiver.data, "NAD-Status")

    entry.async_on_unload(entry.add_update_listener(update_listener))
    # _LOGGER.debug("NADReceiverCoordinator -boot- async_setup_entry DONE - configEntry:%s", entry)

    # Um ein Status-Bild auf der Oberflche zu zeigen, müssen
    #  der Pfad zu den PNGs an einer zentrlen Stelle gemountet/bekanntgeben werden
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                f"/assets/{DOMAIN}",  # Die URL im Frontend
                hass.config.path(
                    f"custom_components/{DOMAIN}/www"
                ),  # Der echte Pfad auf der Festplatte
                False,  # cache_headers (wird als positionelles Argument übergeben)
            )
        ]
    )
    # add_extra_js_url(hass, f"/local/{DOMAIN}")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # ------------START-----------------
    # [v1.0.0][FEATURE: Zwei Coordinator-Instanzen]
    # wir müssen wählen und nehmen "Main"
    receiver_coordinator: NADReceiverCoordinator = entry.runtime_data["Main"]
    await receiver_coordinator.disconnect()
    # -------------END-----------------
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.debug("Configuration options updated, reloading NAD receiver integration")
    hass.config_entries.async_schedule_reload(entry.entry_id)(entry.entry_id)
