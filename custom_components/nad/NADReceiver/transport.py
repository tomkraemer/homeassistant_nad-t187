"""Local NAD transport implementation based on nad_receiver library.

Includes FIFO queue with timestamps and background reader for async response handling.
"""

import serial
import threading
from telnetlib3.telnetlib import Telnet
from datetime import datetime
from typing import Optional
import logging
import time

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 1

class SerialPortTransport:
    """Transport for NAD protocol over RS-232."""

    def __init__(self, serial_port: str, coordinator=None, timeout: int = DEFAULT_TIMEOUT) -> None:
        """Create RS232 connection."""
        self.coordinator = coordinator
        self.serial_port = serial_port
        self.ser = serial.Serial(
            serial_port,
            baudrate=115200,
            timeout=timeout,
            write_timeout=timeout,
        )
        self.lock = threading.Lock()
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_reading = False

    def write_command(self, command: str) -> None:
        """Write a command to the serial port."""
        # _LOGGER.debug("Serial write REQ: %s", command)
        with self.lock:
            if not self.ser.is_open:
                self.ser.open()
                # _LOGGER.debug("Serial open: %s", self.ser.is_open)
            self.ser.reset_input_buffer()
            # _LOGGER.debug("Serial write READY: %s", command)
            self.ser.write_command(f"\r{command}\r".encode("utf-8"))
            # _LOGGER.debug("Serial sent: '%s'", command)

    def read_response(self) -> str:
        """Read a single response from the serial port."""
        # _LOGGER.debug("Serial read REQ:")
        with self.lock:
            if not self.ser.is_open:
                return ""
            try:
                # _LOGGER.debug("Serial read READY:")
                msg = self.ser.read_until(serial.CR)
                if not msg.strip():
                    msg = self.ser.read_until(serial.CR)
                # _LOGGER.debug("Serial read READ: %s", msg)
                # if line.startswith(expected_prefix):
                return msg.strip().decode()
            except serial.SerialTimeoutException:
                return ""
            except Exception as e:
                # _LOGGER.debug("Serial read error: %s", e)
                return ""

    def start_reader(self) -> None:
        """Start background reader thread."""
        if self._reader_thread is not None and self._reader_thread.is_alive():
            return
        
        self._stop_reading = False
        self._reader_thread = threading.Thread(
            target=self._reader_loop,
            daemon=True
        )
        self._reader_thread.start()
        _LOGGER.debug("Started serial reader thread")

    def stop_reader(self) -> None:
        """Stop background reader thread."""
        self._stop_reading = True
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=0.5)
        self._reader_thread = None
        _LOGGER.debug("Stopped serial reader thread")

    def _reader_loop(self) -> None:
        """Continuous reader loop."""
        _LOGGER.debug("Serial reader loop started")
        while not self._stop_reading:
            try:
                response = self.read_response()
                if response and self.coordinator:
                    self.coordinator._add_to_queue(response)
                    # Trigger coordinator update
                    self.coordinator.async_set_updated_data({})
            except Exception as e:
                _LOGGER.debug("Reader error: %s", e)
            time.sleep(0.01)  # Small delay to prevent CPU overload
        _LOGGER.debug("Serial reader loop stopped")

    def communicate(self, command: str) -> str:
        """Write command (alias for write)."""
        self.write_command(command)
        return ""


class TelnetTransport:
    """Transport for NAD protocol over Telnet."""

    coordinators = {}

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, 'inst'):
            cls.inst=super().__new__(cls)
        return cls.inst

    def __init__(self, host: str, port: int, timeout: int = DEFAULT_TIMEOUT, coordinator=None) -> None:
#    def __init__(self, host: str, port: int, timeout: int = DEFAULT_TIMEOUT) -> None:
        """Create Telnet connection."""

        self.telnet: Optional[Telnet] = None
        self.host = host
        self.port = port
        self.timeout = timeout

        # self.coordinator = None
        self.coordinator = coordinator
        self.coordinators.setdefault(coordinator.zone, coordinator)

        self.data = {}
        
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_reading = False
        self._last_line = ""

    def _pre_read(self) -> bool:
        # On initial connection
        # some firmwares sends nothing
        # some firmwares sends e.g. b'\rMain.Model=T787\r\n'
        # some firmwares sends multiple lines (BlueOS settings dump ?)
        #    including blank lines between data lines
        # At least clear the row "\rMain.Model=T787\r\n"
        try:
            self.telnet.read_until("\n".encode())
            # Could raise eg. EOFError, UnicodeError
        except EOFError as cc:
            # Connection closed, no recovery
            _LOGGER.debug("Connection closed: %s", cc)
            self.telnet.close_connection()
            return False
        except UnicodeError as ue:
            # Some unicode error, but connection is open
            _LOGGER.debug("Unicode error: %s", ue)
            return True

        return True

    def _open_connection(self) -> None:
        if self.telnet:
            return
        _LOGGER.debug("Opening telnet connection to: '%s:%s'", self.host, self.port)
        self.telnet = Telnet(self.host, self.port, self.timeout)
        self._pre_read()

    def close_connection(self) -> None:
        if self.telnet:
            self.telnet.close()
            self.telnet = None

    def write_command(self, cmd: str) -> None:
        """Write a command to the telnet connection."""
        # _LOGGER.debug("Telnet write REQ: %s", cmd)
        if not self.telnet:
            self._open_connection()
        if self.telnet:
            try:
                # _LOGGER.debug("Telnet sending: '%s'", cmd)
                self.telnet.write(f"\n{cmd}\r".encode())
            except (EOFError, BrokenPipeError, ConnectionResetError):
                self.close_connection()

    def start_reader(self) -> None:
        """Start background reader thread."""
        if self._reader_thread is not None and self._reader_thread.is_alive():
            return
        
        self._stop_reading = False
        self._reader_thread = threading.Thread(
            target=self._reader_loop,
            daemon=True
        )
        self._reader_thread.start()
        # _LOGGER.debug("Started telnet reader thread")

    def stop_reader(self) -> None:
        """Stop background reader thread."""
        self._stop_reading = True
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=0.5)
        self._reader_thread = None
        _LOGGER.debug("Stopped telnet reader thread")

    def read_response(self) -> str:
        """Read a single response from the telnet connection."""
        # _LOGGER.debug("Telnet read REQ:")
        if not self.telnet:
            self._open_connection()
        if not self.telnet:
            return ""
        try:
            # _LOGGER.debug("Telnet read READY with timeout: %s", self.timeout)
            rsp = self.telnet.read_until(b"\n", self.timeout)
            # _LOGGER.debug("Telnet read READ: %s", rsp)
            # _LOGGER.debug("Telnet read STRIP_DECODE: %s", rsp.strip().decode())
            if  rsp == self._last_line:
                return ""
            self._last_line = rsp
            self.last_received = rsp.strip().decode()
            return rsp.strip().decode()
        except (EOFError, BrokenPipeError, ConnectionResetError):
            self.close_connection()
            return ""
        except UnicodeError:
            return ""

    def _update_status_data (self, line: str) -> None:
        """Read the received Line and push it as key/value into data as status-update."""
        if line: 
            key = line.split("=", 1)[0]
            val = line.split("=", 1)[1]   
            self.data[key]=val

            # if self.coordinator.data:
            #     self.coordinator.data[key]=val
            # else:
            #     _LOGGER.debug("No coordinator.data for - key: %s value: %s", key, val)
            # # Debug-Ausgabe: Inhalt von self.coordinator.data zeilenweise
            # print("Telnet - Inhalt von self.coordinator.data:")
            # for k, v in self.data.items():
            #     _LOGGER.debug("DATA CONTENT - key: %s value: %s", k, v)
            #     # print(f"{k} = {v}")
        
    def _reader_loop(self) -> None:
        """Continuous reader loop."""
        _LOGGER.debug("Telnet reader loop started ")
        while not self._stop_reading:
            try:
                line = self.read_response()
                if line:
                    self._update_status_data(line)

                    # detect te right coordinator
                    coordinator_name = line.split(".", 1)[0]  # z. B. "Main"
                    coordinator = self.coordinators[coordinator_name]
                    if not coordinator:
                        coordinator = self.coordinators["Main"]

                    data_updated = self.data.copy()
                    # data_updated = coordinator.data.copy()
                    coordinator.hass.add_job(coordinator.async_set_updated_data, data_updated)
                    # if self.coordinator:
                    #     data_updated = self.data.copy()
                    #     # data_updated = self.coordinator.data.copy()
                    #     self.coordinator.hass.add_job(self.coordinator.async_set_updated_data, data_updated)

            except Exception as e:
                _LOGGER.debug("Reader error: %s", e)
            time.sleep(0.01)
        _LOGGER.debug("Telnet reader loop stopped")

    def communicate(self, cmd: str) -> str:
        """Write command (alias for write)."""

        # _LOGGER.debug("Telnet communicate WRITE: %s", cmd)
        self.write_command(cmd)
        # _LOGGER.debug("Telnet communicate READ")
        line = self.read_response()
        self._update_status_data(line)
        if line:
            res =  line.split("=", 1)[1]
            # _LOGGER.debug("Telnet communicate READ: %s", res)
            return res
        else:
            # _LOGGER.info("Telnet communicate NOTHING READ: %s", cmd)
            return ''

class TelnetTransportWrapper:
    """Wrapper for TelnetTransport with graceful error handling."""

    def __init__(self, host: str, port: int, timeout: int = DEFAULT_TIMEOUT, coordinator=None) -> None:
        self.nad_telnet = TelnetTransport(host, port, timeout)
        self.nad_telnet.coordinator = coordinator
        self.coordinator = coordinator
        self.data = {}

    def write_command(self, cmd: str) -> None:
        _LOGGER.debug("Wrapper write REQ: %s", cmd)
        self.nad_telnet.write_command(cmd)

    def read_response(self) -> str:
        _LOGGER.debug("Wrapper read REQ ...")
        return self.nad_telnet.read_response()

    def start_reader(self) -> None:
        self.nad_telnet.start_reader()

    def stop_reader(self) -> None:
        self.nad_telnet.stop_reader()

    def communicate(self, cmd: str) -> str:
        """Write command (alias for write)."""
        _LOGGER.debug("Wrapper communicate WRITE: %s", cmd)
        self.write_command(cmd)
        _LOGGER.debug("Wrapper communicate READ")
        line = self.read_response()
        res =  line.split("=", 1)[1]
        _LOGGER.debug("Wrapper communicate READ: %s", res)
        return res
