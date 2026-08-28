"""Local NAD transport implementation based on nad_receiver library.

Includes FIFO queue with timestamps and auto-cleanup from existing implementation.
"""

import abc
import serial
import threading
from telnetlib3.telnetlib import Telnet
from datetime import datetime, timedelta
from typing import Optional
import logging

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 1


class NadTransport(abc.ABC):
    """Abstract base class for NAD transport."""
    
    @abc.abstractmethod
    def communicate(self, command: str) -> str:
        """Send a command and return the response."""
        pass


class SerialPortTransport(NadTransport):
    """Transport for NAD protocol over RS-232."""

    def __init__(self, serial_port: str, coordinator=None, timeout: int = DEFAULT_TIMEOUT) -> None:
        """Create RS232 connection."""
        self.coordinator = coordinator
        self.ser = serial.Serial(
            serial_port,
            baudrate=115200,
            timeout=timeout,
            write_timeout=timeout,
        )
        self.lock = threading.Lock()
        self.serial_port = serial_port

    def _open_connection(self) -> None:
        if not self.ser.is_open:
            self.ser.open()
            _LOGGER.debug("serial open: %s", self.ser.is_open)

    def communicate(self, command: str) -> str:
        """Send command and return response. Adds responses to coordinator queue if available."""
        with self.lock:
            self._open_connection()
            self.ser.reset_input_buffer()
            
            # Send command with NAD protocol format (\r before and after)
            self.ser.write(f"\r{command}\r".encode("utf-8"))
            
            # Read response - NAD responses end with \r
            msg = self.ser.read_until(serial.CR)
            if not msg.strip():  # discard '\r' if it was sent
                msg = self.ser.read_until(serial.CR)
            
            assert isinstance(msg, bytes)
            response = msg.strip().decode()
            
            # Add to coordinator queue if available (FIFO with timestamps)
            if self.coordinator and response:
                self.coordinator._add_to_queue(response)
            
            _LOGGER.debug("Serial sent: '%s' reply: '%s'", command, response)
            return response


class TelnetTransport(NadTransport):
    """
    Support NAD amplifiers that use telnet for communication.
    Known supported model: Nad T787.
    """

    def __init__(self, host: str, port: int, timeout: int = DEFAULT_TIMEOUT) -> None:
        """Create NADTelnet."""
        self.telnet: Optional[Telnet] = None
        self.host = host
        self.port = port
        self.timeout = timeout
        self.coordinator = None

    def __del__(self) -> None:
        try:
            self.close_connection()
        except Exception:
            pass

    def is_open(self) -> bool:
        return True if self.telnet else False

    def open_connection(self) -> None:
        if self.telnet:
            raise Exception("Connection already open for host '%s:%s'" % (self.host, self.port))

        _LOGGER.debug("Open connection to: '%s:%s'", self.host, self.port)
        self.telnet = Telnet(self.host, self.port, self.timeout)

    def close_connection(self) -> None:
        telnet = self.telnet
        self.telnet = None
        if telnet:
            _LOGGER.debug("Close connection to: '%s:%s'", self.host, self.port)
            telnet.close()

    def read_until(self, data) -> None:
        if not self.telnet:
            raise Exception("Connection is closed")
        self.telnet.read_until(data, self.timeout)

    def communicate(self, cmd: str) -> str:
        """Send command and return response. Handles connection automatically."""
        if not self.telnet:
            self.open_connection()
        
        try:
            _LOGGER.debug("Telnet sending command: '%s'", cmd)
            self.telnet.write(f"\n{cmd}\r".encode())

            # Notice NAD response to command ends with \r and starts with \n
            # E.g. b'\nMain.Power=On\r'
            rsp = self.telnet.read_until(b"\r", self.timeout)
            _LOGGER.debug("Telnet read response: '%s'", str(rsp))
            
            response = rsp.strip().decode()
            
            # Add to coordinator queue if available
            if self.coordinator and response:
                self.coordinator._add_to_queue(response)
            
            return response
            
        except (EOFError, BrokenPipeError, ConnectionResetError) as cc:
            # Connection closed
            _LOGGER.debug("Connection closed: %s", cc)
            self.close_connection()
            return ""
        except UnicodeError as ue:
            # Some unicode error, but connection is open
            _LOGGER.debug("Unicode error: %s", ue)
            return ""


class TelnetTransportWrapper(NadTransport):
    """
    Wrapper for TelnetTransport to handle connection issues gracefully.
    A class to wrap the TelnetTransport in such a way that Home Assistant will not
    receive any exceptions.
    """
    
    def __init__(self, host: str, port: int, timeout: int = DEFAULT_TIMEOUT, coordinator=None) -> None:
        """Create NADTelnet."""
        self.nad_telnet = TelnetTransport(host, port, timeout)
        self.coordinator = coordinator
        # Pass coordinator to the underlying transport
        self.nad_telnet.coordinator = coordinator

    def __del__(self) -> None:
        """Destroy NADTelnet."""
        if hasattr(self, 'nad_telnet') and self.nad_telnet:
            del self.nad_telnet

    def _pre_read(self) -> bool:
        """Clear initial connection data (e.g., Main.Model response)."""
        try:
            self.nad_telnet.read_until("\n".encode())
        except EOFError as cc:
            _LOGGER.debug("Connection closed: %s", cc)
            self.nad_telnet.close_connection()
            return False
        except UnicodeError as ue:
            _LOGGER.debug("Unicode error: %s", ue)
            return True
        return True

    def _open_connection(self) -> bool:
        if self.nad_telnet.is_open():
            return True

        try:
            self.nad_telnet.open_connection()
        except Exception as e:
            _LOGGER.debug("Connection failed to open: %s", e)
            return False

        return self._pre_read()

    def communicate(self, cmd: str) -> str:
        """Send command and return response."""
        rsp = ""
        if not self._open_connection():
            return rsp

        try:
            rsp = self.nad_telnet.communicate(cmd)
        except (EOFError, BrokenPipeError, ConnectionResetError) as cc:
            _LOGGER.debug("Connection closed: %s", cc)
            self.nad_telnet.close_connection()
        except UnicodeError as ue:
            _LOGGER.debug("Unicode error: %s", ue)

        return rsp
