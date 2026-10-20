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
from .. import const
from typing import Protocol

_LOGGER = logging.getLogger(__name__)

class NADTransport():
    """Basis-Klasse für alle NAD-Transport-Klassen."""
    def __init__(self, receiver: NADReceiever, timeout: int ) -> None:
        """Create Telnet connection."""
        self.channel = None
        self.receiver = receiver
        self.timeout = timeout

        self.lock = threading.Lock()
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_reading = False
        self._last_line = ""
        self.available = False

    ####################################################################################
    # Die Kombination aus _reader_loop und _read_reponse ist Herz der Verbindung zum AVR.
    #   Es wird kontinierlich am Socket gelauscht. 
    #       Wird in _readResponse ein EndeToken "\n" im Stream gefunden,
    #       wird der gesammlete String decoded, danach 
    #       wird das Lesen zunächst unterbochen, indem 
    #       der String an _reader_loop zurückgegeben wird 
    #   _readser_loop gibt das Lesergebnis an den angemeldeten Receiver, 
    #       damit dieser aus dem String ein Update seines Status vornimmt.
    #   danach wird weiter gelauscht
    

    #############################################################################
    # CONNECTION HANDLING
    #       - Open
    #       - Close
    def open_connection(self) -> None:
        """PROTOTYPE: to be implemented in derived class.
        """
        pass

    def close_connection(self) -> None:
        """
            close a typed connection.
        """
        if self.channel:
            self.channel.close()
            self.channel = None

    #############################################################################
    # BASIC COMMUNICATION
    #       - Write
    #       - Read
    #       - Exec
    def write_command(self, cmd: str) -> None:
        """
            Write a command to the telnet connection.
        """
        if not self.channel:
            self.open_connection()
        if self.channel:
            try:
                # _LOGGER.debug("%s sending: '%s'", self.connection_type, cmd)
                self.channel.write(f"\n{cmd}\r".encode())
            except (EOFError, BrokenPipeError, ConnectionResetError):
                self.close_connection()

    def _read_response(self) -> str:
        """
            Read a single response from the telnet connection.
        """
        if not self.channel:
            self.open_connection()
        if not self.channel:
            return ""
        try:
            with self.lock: 
                # read the next line from telenet-stream if avy available
                rsp = self.channel.read_until(b"\n", self.timeout)
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

    def exec_command(self, cmd: str) -> str:
        """
            Write a command to the telnet connection.
            Read the respone following this format
                <command> = <result>
            return its result only
        """
        self.write_command(cmd)
        line = self._read_response()
        if line:
            self.receiver.update_status_data(line)
            # _LOGGER.debug("Line received @ %s: %s", self.connection_type, line)
            return line.split("=", 1)[1]
        else:
            return ''
        
    #############################################################################
    # READER LOOP
    #       - Start
    #       - Stop
    #       - Loop
    def start_reader(self) -> None:
        """
            Start background reader thread.
        """
        if self._reader_thread is not None and self._reader_thread.is_alive():
            return
        
        self._stop_reading = False
        self._reader_thread = threading.Thread(
            target=self._reader_loop,
            daemon=True
        )
        self._reader_thread.start()
        # _LOGGER.debug("Started %s reader thread", self.connection_type)

    def stop_reader(self) -> None:
        """
            Stop background reader thread.
        """
        self._stop_reading = True
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=0.5)
        self._reader_thread = None
        _LOGGER.info("Stopped %s reader thread", self.connection_type)

    def _reader_loop(self) -> None:
        """
            Continuous reader loop.
        """
        # _LOGGER.debug("Telnet reader loop started ")
        while not self._stop_reading:
            try:
                line = self._read_response()
                if line:
                    with self.lock: 
                        self.receiver.update_status_data(line)
            except Exception as e:
                _LOGGER.info("Reader error: %s", e)
            time.sleep(0.01)
        _LOGGER.info("Telnet reader loop stopped")


class SerialPortTransport(NADTransport):
    """
    Transport for NAD protocol over RS-232.
    """
    def __init__(self, receiver: NADReceiever, serial_port: str, timeout: int = const.CONF_DEFAULT_TIMEOUT):
        """Create RS232 connection."""
        super().__init__(receiver, timeout)
        self.channel: Optional[serial.Serial] = None
        self.port = serial_port
        self.baudrate = 115200
        self.connection_type= const.CONF_TYPE_SERIAL

    def open_connection(self) -> None:
        if self.channel:
            return
        # _LOGGER.debug("Opening %s connection to: '%s:%s'", self.connection_type, self.host, self.port)
        self.channel = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
            write_timeout=self.timeout,
        )
        # self._pre_read()
        self.available = True




class TelnetTransport(NADTransport):
    """
    Transport for NAD protocol over Telnet.
    """
    def __init__(self, receiver: NADReceiever, host: str, port: int, timeout: int = const.CONF_DEFAULT_TIMEOUT) -> None:
        """Create Telnet connection."""
        super().__init__(receiver, timeout)
        self.channel: Optional[Telnet] = None
        self.host = host
        self.port = port
        self.connection_type= const.CONF_TYPE_TELNET

    def _pre_read(self) -> bool:
        # On initial connection
        # some firmwares sends nothing
        # some firmwares sends e.g. b'\rMain.Model=T787\r\n'
        # some firmwares sends multiple lines (BlueOS settings dump ?)
        #    including blank lines between data lines
        # At least clear the row "\rMain.Model=T787\r\n"
        try:
            self.channel.read_until("\n".encode())
            # Could raise eg. EOFError, UnicodeError
        except EOFError as cc:
            # Connection closed, no recovery
            _LOGGER.info("Connection closed: %s", cc)
            self.close_connection()
            return False
        except UnicodeError as ue:
            # Some unicode error, but connection is open
            _LOGGER.info("Unicode error: %s", ue)
            return True
        return True

    def open_connection(self) -> None:
        if self.channel:
            return
        # _LOGGER.debug("Opening %s connection to: '%s:%s'", self.connection_type, self.host, self.port)
        self.channel = Telnet(self.host, self.port, self.timeout)
        self._pre_read()
        self.available = True



class TCPTransport:
    """
    Transport for NAD protocol over Telnet.
    """
    def __init__(self, receiver: NADReceiever, host: str, port: int, timeout: int = const.CONF_DEFAULT_TIMEOUT) -> None:
        """Create TCP connection."""


        self.receiver = receiver
        self.channel: Optional[TCPTransport] = None
        self.host = host
        self.port = port
        self.timeout = timeout

        self.lock = threading.Lock()
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_reading = False
        self._last_line = ""
        self.connection_type= const.CONF_TYPE_TCP
