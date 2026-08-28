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

    def write(self, command: str) -> None:
        """Write a command to the serial port."""
        with self.lock:
            if not self.ser.is_open:
                self.ser.open()
                _LOGGER.debug("serial open: %s", self.ser.is_open)
            self.ser.reset_input_buffer()
            self.ser.write(f"\r{command}\r".encode("utf-8"))
            _LOGGER.debug("Serial sent: '%s'", command)

    def read_response(self) -> str:
        """Read a single response from the serial port."""
        with self.lock:
            if not self.ser.is_open:
                return ""
            try:
                msg = self.ser.read_until(serial.CR)
                if not msg.strip():
                    msg = self.ser.read_until(serial.CR)
                return msg.strip().decode()
            except serial.SerialTimeoutException:
                return ""
            except Exception as e:
                _LOGGER.debug("Serial read error: %s", e)
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
        self.write(command)
        return ""


class TelnetTransport:
    """Transport for NAD protocol over Telnet."""

    def __init__(self, host: str, port: int, timeout: int = DEFAULT_TIMEOUT) -> None:
        """Create Telnet connection."""
        self.telnet: Optional[Telnet] = None
        self.host = host
        self.port = port
        self.timeout = timeout
        self.coordinator = None
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_reading = False

    def write(self, cmd: str) -> None:
        """Write a command to the telnet connection."""
        if not self.telnet:
            self._open_connection()
        if self.telnet:
            try:
                _LOGGER.debug("Telnet sending: '%s'", cmd)
                self.telnet.write(f"\n{cmd}\r".encode())
            except (EOFError, BrokenPipeError, ConnectionResetError):
                self.close_connection()

    def read_response(self) -> str:
        """Read a single response from the telnet connection."""
        if not self.telnet:
            self._open_connection()
        if not self.telnet:
            return ""
        try:
            rsp = self.telnet.read_until(b"\r", self.timeout)
            return rsp.strip().decode()
        except (EOFError, BrokenPipeError, ConnectionResetError):
            self.close_connection()
            return ""
        except UnicodeError:
            return ""

    def _open_connection(self) -> None:
        if self.telnet:
            return
        _LOGGER.debug("Opening telnet connection to: '%s:%s'", self.host, self.port)
        self.telnet = Telnet(self.host, self.port, self.timeout)

    def close_connection(self) -> None:
        if self.telnet:
            self.telnet.close()
            self.telnet = None

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
        _LOGGER.debug("Started telnet reader thread")

    def stop_reader(self) -> None:
        """Stop background reader thread."""
        self._stop_reading = True
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=0.5)
        self._reader_thread = None
        _LOGGER.debug("Stopped telnet reader thread")

    def _reader_loop(self) -> None:
        """Continuous reader loop."""
        _LOGGER.debug("Telnet reader loop started")
        while not self._stop_reading:
            try:
                response = self.read_response()
                if response and self.coordinator:
                    self.coordinator._add_to_queue(response)
                    # Trigger coordinator update
                    self.coordinator.async_set_updated_data({})
            except Exception as e:
                _LOGGER.debug("Reader error: %s", e)
            time.sleep(0.01)
        _LOGGER.debug("Telnet reader loop stopped")

    def communicate(self, cmd: str) -> str:
        """Write command (alias for write)."""
        self.write(cmd)
        return ""


class TelnetTransportWrapper:
    """Wrapper for TelnetTransport with graceful error handling."""

    def __init__(self, host: str, port: int, timeout: int = DEFAULT_TIMEOUT, coordinator=None) -> None:
        self.nad_telnet = TelnetTransport(host, port, timeout)
        self.nad_telnet.coordinator = coordinator
        self.coordinator = coordinator

    def write(self, cmd: str) -> None:
        self.nad_telnet.write(cmd)

    def start_reader(self) -> None:
        self.nad_telnet.start_reader()

    def stop_reader(self) -> None:
        self.nad_telnet.stop_reader()

    def communicate(self, cmd: str) -> str:
        """Write command (alias for write)."""
        self.write(cmd)
        return ""
