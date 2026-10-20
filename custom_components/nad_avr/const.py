"""Constants for the NAD Receiver integration."""

from typing import Final

DOMAIN: Final = "nad_avr"

CONF_TYPE_SERIAL: Final = "RS232"
CONF_TYPE_TELNET: Final = "Telnet"
CONF_TYPE_TCP: Final = "TCP"
CONF_DEFAULT_TIMEOUT = 1

CONF_SERIAL_PORT: Final = "serial_port"  # for NADReceiver
CONF_DEFAULT_PORT: Final = 23  # 53 does not work for us

CONF_MIN_VOLUME: Final = "min_volume"
CONF_MAX_VOLUME: Final = "max_volume"
CONF_VOLUME_STEP: Final = "volume_step"  # for NADReceiverTCP
CONF_SOURCE_DICT: Final = "sources"  # for NADReceiver

CONF_DEFAULT_MIN_VOLUME: Final = -97  # -92
CONF_DEFAULT_MAX_VOLUME: Final = -19  # -20
CONF_DEFAULT_VOLUME_STEP: Final = 4

CONF_COUNT_OF_SOURCES: Final = 10  # for NAD T187

# ------------START-----------------
# [v1.0.2][FIX: Response-Queue Alterungsbegrenzung]
# Hinzufügen einer Konfiguration für die maximale Lebensdauer von Queue-Einträgen
# <CODE ADDED>
# CONF_MAX_READ_QUEUE_LAYTIME: Final = 60  # seconds - max age of queue entries
# ------------END-----------------
CONF_MAX_READ_QUEUE_LAYTIME: Final = 60  # seconds - max age of queue entries
