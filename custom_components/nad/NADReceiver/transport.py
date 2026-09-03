"""Local NAD transport implementation based on nad_receiver library.

Includes FIFO queue with timestamps and background reader for async response handling.
"""

import serial
import threading
from telnetlib3.telnetlib import Telnet
from datetime import datetime
from typing import Optional, Protocol, runtime_checkable 
import logging
import time

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 1

from typing import Protocol

class NADTransport(Protocol):
    """Interface für alle NAD-Transport-Klassen."""
    data = None

    def open_connection(self) -> None: ...
    def close_connection(self) -> None: ...
    def exec_command(self, cmd: str) -> str: ...
    def write_command(self, cmd: str) -> None: ...
    def start_reader(self) -> None: ...
    def stop_reader(self) -> None: ...


class SerialPortTransport:
    """Transport for NAD protocol over RS-232."""
    coordinators = {}
    data = {}

    def __new__(cls, *args, **kwargs):
        """Insure to have a singleton"""
        if not hasattr(cls, 'inst'):
            cls.inst=super().__new__(cls)
        return cls.inst

    def __init__(self, serial_port: str, coordinator=None, timeout: int = DEFAULT_TIMEOUT) -> None:
        """Create RS232 connection."""
        self.ser: Optional[serial] = None
        self.serial_port = serial_port
        self.baudrate=115200
        self.timeout = timeout
        self.coordinators.setdefault(coordinator.zone, coordinator)
        self.data = {}
        self.lock = threading.Lock()
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_reading = False
        self._last_line = ""

    def open_connection(self) -> None:
        if self.telnet:
            return
        _LOGGER.debug("Opening serial connection to: '%s:%s'", self.host, self.port)
        self.ser = serial.Serial(
            port=self.serial_port,
            baudrate=self.baudrate,
            timeout=self.timeout,
            write_timeout=self.timeout,
        )
        # self._pre_read()

    def close_connection(self) -> None:
        if self.ser:
            self.ser.close()
            self.ser = None

    def exec_command(self, cmd: str) -> str:
        """Write command (alias for write)."""
        self.write_command(cmd)
        return ""

    def write_command(self, cmd: str) -> None:
        """Write a command to the serial port."""
        # _LOGGER.debug("Serial write REQ: %s", cmd)
        with self.lock:
            if not self.ser.is_open:
                self.ser.open()
                # _LOGGER.debug("Serial open: %s", self.ser.is_open)
            self.ser.reset_input_buffer()
            # _LOGGER.debug("Serial write READY: %s", cmd)
            self.ser.write_command(f"\r{cmd}\r".encode("utf-8"))
            # _LOGGER.debug("Serial sent: '%s'", cmd)

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

    def _read_response(self) -> str:
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

    def _reader_loop(self) -> None:
        """Continuous reader loop."""
        _LOGGER.debug("Serial reader loop started")
        while not self._stop_reading:
            try:
                response = self._read_response()
                if response and self.coordinator:
                    self.coordinator._add_to_queue(response)
                    # Trigger coordinator update
                    self.coordinator.async_set_updated_data({})
            except Exception as e:
                _LOGGER.debug("Reader error: %s", e)
            time.sleep(0.01)  # Small delay to prevent CPU overload
        _LOGGER.debug("Serial reader loop stopped")


class TelnetTransport:
    """Transport for NAD protocol over Telnet."""
    coordinators = {}
    data = {}

    def __new__(cls, *args, **kwargs):
        """Insure to have a singleton"""
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
        self.coordinators.setdefault(coordinator.zone, coordinator)
        self.data = {}
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_reading = False
        self._last_line = ""

    def open_connection(self) -> None:
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
        """
            Write a command to the telnet connection.
        """
        if not self.telnet:
            self.open_connection()
        if self.telnet:
            try:
                # _LOGGER.debug("Telnet sending: '%s'", cmd)
                self.telnet.write(f"\n{cmd}\r".encode())
            except (EOFError, BrokenPipeError, ConnectionResetError):
                self.close_connection()

    def exec_command(self, cmd: str) -> str:
        """
            Write command, read respone and return its result.
        """
        self.write_command(cmd)
        line = self._read_response()
        if line:
            self._update_status_data(line)
            return line.split("=", 1)[1]
        else:
            return ''

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
        """
            Stop background reader thread.
        """
        self._stop_reading = True
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=0.5)
        self._reader_thread = None
        _LOGGER.debug("Stopped telnet reader thread")

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

    def _update_status_data (self, line: str) -> None:
        """Read the received Line and push it as key/value into data as status-update."""
        if line: 
            key = line.split("=", 1)[0]
            val = line.split("=", 1)[1]   
            self.data[key]=val

    def _read_response(self) -> str:
        """Read a single response from the telnet connection."""
        if not self.telnet:
            self.open_connection()
        if not self.telnet:
            return ""
        try:
            # read the next line from telenet-stream if avy available
            rsp = self.telnet.read_until(b"\n", self.timeout)
            # if  rsp.strip().decode() == "" or rsp == self._last_line:
            # ignore the line if it ia doublette
            if rsp == self._last_line:
                return ""
            # return the line read
            self._last_line = rsp
            self.last_received = rsp.strip().decode()
            return rsp.strip().decode()
        except (EOFError, BrokenPipeError, ConnectionResetError):
            self.close_connection()
            return ""
        except UnicodeError:
            return ""

    def _reader_loop(self) -> None:
        """Continuous reader loop."""
        _LOGGER.debug("Telnet reader loop started ")
        while not self._stop_reading:
            try:
                line = self._read_response()
                if line:
                    self._update_status_data(line)

                    # detect te right coordinator
                    coordinator_name = line.split(".", 1)[0]  # z. B. "Main"
                    coordinator = self.coordinators[coordinator_name]
                    if not coordinator:
                        coordinator = self.coordinators["Main"]
                    coordinator.hass.add_job(coordinator.async_set_updated_data, self.data.copy())

            except Exception as e:
                _LOGGER.debug("Reader error: %s", e)
            time.sleep(0.01)
        _LOGGER.debug("Telnet reader loop stopped")

