"""Support for interfacing with NAD receivers through RS-232."""

import logging
import os
import time

import requests
from aiodiscover.discovery import _LOGGER
from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TYPE
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import NADReceiverCoordinator, log_status_dict
from .const import (
    CONF_DEFAULT_MAX_VOLUME,
    CONF_DEFAULT_MIN_VOLUME,
    CONF_DEFAULT_VOLUME_STEP,
    CONF_MAX_VOLUME,
    CONF_MIN_VOLUME,
    DOMAIN,
)
from .NADReceiver import NADReceiverSerial, NADReceiverTCP, NADReceiverTelnet

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the NAD Receiver media player."""
    # _LOGGER.debug("NAD MediaPlayer -- async_setup_entry %s", config_entry)

    coordinators: dict = config_entry.runtime_data  # ✅ Dict mit allen Coordinators
    # Fetch initial data so we have data when entities subscribe
    await coordinators["Main"].async_config_entry_first_refresh()
    await coordinators["Zone2"].async_config_entry_first_refresh()

    if isinstance(coordinators["Main"].receiver, NADReceiverTCP):
        async_add_entities([NADtcp(coordinators["Main"])])
    elif isinstance(coordinators["Main"].receiver, NADReceiverTelnet) or isinstance(
        coordinators["Main"].receiver, NADReceiverSerial
    ):
        async_add_entities(
            [
                NADMain(coordinators["Main"]),  # ✅ Main-Entity nutzt Main-Coordinator
                NADZone2(
                    coordinators["Zone2"]
                ),  # ✅ Zone2-Entity nutzt Zone2-Coordinator
            ]
        )


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration."""
    local_www = hass.config.path(f"custom_components/{DOMAIN}/www")

    if os.path.isdir(local_www):
        # Macht den Ordner unter http://deine-hass-ip:8123/local/deine_integration/ verfügbar
        hass.http.register_static_path(f"/local/{DOMAIN}", local_www, rue)
        _LOGGER.info("Source-PNGs erfolgreich für das Frontend freigegeben.")
    else:
        _LOGGER.error(f"Der www-Ordner wurde unter {local_www} nicht gefunden!")

    return True


class NAD(CoordinatorEntity, MediaPlayerEntity):
    """Representation of a NAD Receiver."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_device_class = MediaPlayerDeviceClass.RECEIVER

    zone = ""

    def __init__(self, coordinator: NADReceiverCoordinator):
        """
        Initialize the NAD Receiver device.
        """
        # _LOGGER.debug("INIT -boot- NAD MediaPlayer - coordinator %s", coordinator)
        super().__init__(coordinator, self.zone + ".Power")

        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = (
            f"{coordinator.unique_id}-mediaplayer-{self.zone.lower()}"
        )
        self._min_volume = coordinator.options.get(
            CONF_MIN_VOLUME, CONF_DEFAULT_MIN_VOLUME
        )
        self._max_volume = coordinator.options.get(
            CONF_MAX_VOLUME, CONF_DEFAULT_MAX_VOLUME
        )

        self._add_listener_for_media_player(coordinator, "Power")
        self._add_listener_for_media_player(coordinator, "Mute")
        self._add_listener_for_media_player(coordinator, "Volume")
        self._add_listener_for_media_player(coordinator, "Source")

        self._source_dict = coordinator.sources
        self._reverse_mapping = {value: key for key, value in self._source_dict.items()}
        self.coordinator.initialized = True

        _LOGGER.info("NAD MediaPlayer %s initialized and ready", self.zone)

    @property
    def should_poll(
        self,
    ) -> bool:  # möglicherweise überflüssig, aber doppelt gemoppelt hält besser.
        """Kein Pollinng für NAD-MediaPlayer"""
        return False

    def _add_listener_for_media_player(
        self, coordinator: NADReceiverCoordinator, cmd
    ) -> None:
        """
        Add MediaPlayer-specific listener command
        (here: Mute, Volume, Source
        [- and ListeningMode <- for Main only -] )
        """
        command = self.zone + "." + cmd
        # _LOGGER.debug("INIT -boot- NAD MediaPlayer - command %s", command)
        if coordinator.supports_command(command):
            coordinator.add_listener_command(command)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """
        Handle updated data from the coordinator.
        """
        # _LOGGER.debug("_handle_coordinator_update NAD >>> %s ", self.coordinator.receiver.transport.last_received)
        self._attr_available = False
        self._attr_state = None

        if self.coordinator.receiver.available:
            # Der Receiver hat den vollständigen Status des AVR immer parar.
            # den nutzen wir:
            data = self.coordinator.receiver.data

            self._attr_available = True
            self._attr_state = data.get(self.zone + ".Power")

            self._attr_is_volume_muted = (
                data.get(self.zone + ".Mute", "").lower() == "on"
            )
            self._attr_volume_level = self.calc_volume(data.get(self.zone + ".Volume"))
            self._attr_source = self._source_dict.get(
                int(data.get(self.zone + ".Source"))
            )

        # self.async_write_ha_state()
        # wird von den abgeleiteten Klassen Main und ZoneX mit ff. Methoden-Aufbau übernommen:
        #     # @callback
        #     # def _handle_coordinator_update(self) -> None:
        #     #     """Handle updated data from the coordinator."""
        #     #
        #     #     super()._handle_coordinator_update()
        #     #
        #     #     # spezifische Zustände setzten:
        #     #     _attr_<SPECIFIC_STATE_NAME> = <STATE>
        #     #
        #     #     self.schedule_update_ha_state()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self._attr_available:
            return self._attr_available
        return self.coordinator.last_update_success

    def turn_off(self) -> None:
        """Implementaion of MediaPlayerEntityFeature:
        Turn the media player off.   -"""
        self.coordinator.write_command(self.zone + ".Power", "=", "Off")

    def turn_on(self) -> None:
        """Implementaion of MediaPlayerEntityFeature:
        Turn the media player on"""
        self.coordinator.write_command(self.zone + ".Power", "=", "On")

    def volume_up(self) -> None:
        """Implementaion of MediaPlayerEntityFeature:
        Volume up the media player."""
        self.coordinator.write_command(self.zone + ".Volume", "+", None)

    def volume_down(self) -> None:
        """Implementaion of MediaPlayerEntityFeature:
        Volume down the media player."""
        self.coordinator.write_command(self.zone + ".Volume", "-", None)

    def set_volume_level(self, volume: float) -> None:
        """Implementaion of MediaPlayerEntityFeature:
        Set volume level, range 0..1."""
        vol_db = int(self.calc_db(volume))
        self.coordinator.write_command(self.zone + ".Volume", "=", vol_db)

    def mute_volume(self, mute: bool) -> None:
        """Implementaion of MediaPlayerEntityFeature:
        Mute (true) or unmute (false) media player."""
        if mute:
            self.coordinator.write_command(self.zone + ".Mute", "=", "On")
        else:
            self.coordinator.write_command(self.zone + ".Mute", "=", "Off")

    def select_source(self, source: str) -> None:
        """Implementaion of MediaPlayerEntityFeature:
        Select input source."""
        if source in self._reverse_mapping:
            source_id = self._reverse_mapping[source]
        elif source.isnumeric() and int(source) in self._source_dict:
            source_id = source
        else:
            raise HomeAssistantError(f"Source {source} invalid")
        self.coordinator.write_command(self.zone + ".Source", "=", source_id)

    @property
    def media_image_url(self) -> str | None:
        """Gibt dynamisch das Bild passend zur aktiven Quelle zurück."""
        source_name = self._attr_source.lower()
        source_name = source_name.replace(" ", "-")
        # path = f"./wwww/{source_name}.png"
        url = f"/assets/nad/{source_name}.png"

        # _LOGGER.debug("Source: %s FileName: %s File&Path: %s", self._attr_source, source_name, path)

        # try:
        # # Ein HEAD-Request lädt nicht die ganze Datei, schont also Datenvolumen und Zeit
        #     requests.head(url, allow_redirects=True, timeout=5)
        # except:
        #     # path = f"./www/hdmi.png"
        #     url = f"/assets/nad/hdmi.png"

        # # if os.path.isfile(path):
        # #     _LOGGER.debug("Source found")
        # #     url = f"/assets/nad/{source_name}.png"
        # # else:
        # #     # Standard-Bild oder None, falls kein Bild für die Quelle existiert
        # #     path = f"./www/hdmi.png"
        # #     url = f"/assets/nad/hdmi.png"

        # _LOGGER.debug("Source: %s FileName: %s Path: %s URL:%s", self._attr_source, source_name, path, url)

        # WICHTIG: Füge einen Zeitstempel an (?v=12345678),
        # damit der Browser das Bild bei einem Quellenwechsel garantiert neu lädt!
        timestamp = int(time.time())
        return f"{url}?v={timestamp}"

    @property
    def source_list(self):
        """List of available input sources."""
        return list(self._reverse_mapping)

    def calc_volume(self, decibel):
        """Calculate the volume given the decibel.
        Return the volume (0..1).
        """
        return abs(self._min_volume - decibel) / abs(
            self._min_volume - self._max_volume
        )

    def calc_db(self, volume):
        """Calculate the decibel given the volume.
        Return the dB.
        """
        return self._min_volume + round(
            abs(self._min_volume - self._max_volume) * volume
        )


#####################################################################################
#   IMPLEMENTING TWO MEDIA PLAYER. ONE FOR EACH ZONE
#   - Main
#   - Zone 2
class NADMain(NAD):
    """Representation of a NAD Receiver - Main."""

    _attr_name = "Main"

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
        "None",
        "ProLogic",
        "PLIIMovie",
        "PLIIMusic",
        "NEO6Cinema",
        "NEO6Music",
        "EARS",
        "EnhancedStereo",
        "AnalogBypass",
        "StereoDownmix",
        "SurroundEX",
    ]

    def __init__(self, coordinator: NADReceiverCoordinator):
        """Initialize the NAD Receiver - Main."""
        self.zone = "Main"
        super().__init__(coordinator)

        self._add_listener_for_media_player(coordinator, "ListeningMode")

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        super()._handle_coordinator_update()

        data = self.coordinator.receiver.data
        listeningMode = data.get(self.zone + ".ListeningMode")
        if listeningMode is not None:
            self._attr_sound_mode = listeningMode

        self.schedule_update_ha_state()

    def select_sound_mode(self, sound_mode: str) -> None:
        """Select sound mode.   - Implementaion of MediaPlayerEntityFeature"""
        self.coordinator.write_command(self.zone + ".ListeningMode", "=", sound_mode)


class NADZone2(NAD):
    """Representation of a NAD Receiver - Zone 2."""

    _attr_name = "Zone 2"
    _attr_supported_features = (
        MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.SELECT_SOURCE
    )

    def __init__(self, coordinator: NADReceiverCoordinator):
        """Initialize the NAD Receiver device."""
        self.zone = "Zone2"
        super().__init__(coordinator)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # _LOGGER.debug("_handle_coordinator_update NADZone2")
        super()._handle_coordinator_update()
        self.schedule_update_ha_state()


class NADtcp(NAD):
    """Dummy Representation of a NAD Receiver via tcp - why so ever"""
