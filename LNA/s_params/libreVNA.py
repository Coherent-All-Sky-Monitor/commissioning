"""
LibreVNA SCPI Helper Class
---------------------------
TCP socket-based interface for communicating with the LibreVNA-GUI
SCPI server. Based on the official helper from:
https://github.com/jankae/LibreVNA/tree/master/Documentation/UserManual/SCPI_Examples

The LibreVNA-GUI must be running with the SCPI server enabled
(Window -> Preferences -> General). Default port: 19542.

Usage:
    from libreVNA import libreVNA
    vna = libreVNA('localhost', 19542)
    print(vna.query("*IDN?"))
"""

import socket
import time
from asyncio import IncompleteReadError


class SocketStreamReader:
    """Buffered reader for non-blocking TCP sockets."""

    def __init__(self, sock: socket.socket, default_timeout=1):
        self._sock = sock
        self._sock.setblocking(0)
        self._recv_buffer = bytearray()
        self.default_timeout = default_timeout

    def read(self, num_bytes: int = -1) -> bytes:
        raise NotImplementedError

    def readexactly(self, num_bytes: int) -> bytes:
        buf = bytearray(num_bytes)
        pos = 0
        while pos < num_bytes:
            n = self._recv_into(memoryview(buf)[pos:])
            if n == 0:
                raise IncompleteReadError(bytes(buf[:pos]), num_bytes)
            pos += n
        return bytes(buf)

    def readline(self, timeout=None) -> bytes:
        return self.readuntil(b"\n", timeout=timeout)

    def readuntil(self, separator: bytes = b"\n", timeout=None) -> bytes:
        if len(separator) != 1:
            raise ValueError("Only separators of length 1 are supported.")
        if timeout is None:
            timeout = self.default_timeout

        chunk = bytearray(4096)
        start = 0
        buf = bytearray(len(self._recv_buffer))
        bytes_read = self._recv_into(memoryview(buf))
        assert bytes_read == len(buf)

        time_limit = time.time() + timeout
        while True:
            idx = buf.find(separator, start)
            if idx != -1:
                break
            elif time.time() > time_limit:
                raise Exception("Timed out waiting for response from GUI")

            start = len(self._recv_buffer)
            bytes_read = self._recv_into(memoryview(chunk))
            buf += memoryview(chunk)[:bytes_read]

        result = bytes(buf[: idx + 1])
        self._recv_buffer = b"".join(
            (memoryview(buf)[idx + 1 :], self._recv_buffer)
        )
        return result

    def _recv_into(self, view: memoryview) -> int:
        bytes_read = min(len(view), len(self._recv_buffer))
        view[:bytes_read] = self._recv_buffer[:bytes_read]
        self._recv_buffer = self._recv_buffer[bytes_read:]
        if bytes_read == len(view):
            return bytes_read
        try:
            bytes_read += self._sock.recv_into(view[bytes_read:], 0)
        except BlockingIOError:
            pass
        return bytes_read


class libreVNA:
    """
    Interface to LibreVNA-GUI SCPI server via TCP socket.

    Args:
        host (str): Hostname of the SCPI server (default: 'localhost').
        port (int): TCP port (default: 19542).
    """

    def __init__(self, host='localhost', port=19542):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((host, port))
        except ConnectionRefusedError:
            raise ConnectionError(
                f"Could not connect to LibreVNA-GUI at {host}:{port}. "
                "Make sure LibreVNA-GUI is running with the SCPI server enabled "
                "(Window → Preferences → General)."
            )
        self.reader = SocketStreamReader(self.sock, default_timeout=10)

    def cmd(self, command):
        """Send a SCPI command (no response expected)."""
        self.sock.sendall((command + "\n").encode())

    def query(self, command, timeout=None):
        """
        Send a SCPI query and return the response string.

        Args:
            command (str): SCPI query (should end with '?').
            timeout (float): Timeout in seconds (default: reader default).

        Returns:
            str: Response from the instrument, stripped of whitespace.
        """
        self.sock.sendall((command + "\n").encode())
        response = self.reader.readline(timeout=timeout)
        return response.decode().strip()

    def parse_VNA_trace_data(self, data):
        """
        Parse raw trace data from :VNA:TRAC:DATA? into a list of
        (frequency, complex_value) tuples.

        Args:
            data (str): Raw response string from :VNA:TRAC:DATA? query.

        Returns:
            list[tuple[float, complex]]: Parsed trace points.
        """
        points = []
        if not data or data.strip() == "":
            return points
            
        # The LibreVNA GUI returns data like: [freq,real,imag],[freq,real,imag]
        # Remove all brackets to make it a flat comma-separated list
        clean_data = data.replace("[", "").replace("]", "")
        values = clean_data.split(",")
        # Data format: freq1,real1,imag1,freq2,real2,imag2,...
        i = 0
        while i + 2 < len(values):
            try:
                freq = float(values[i].strip())
                real = float(values[i + 1].strip())
                imag = float(values[i + 2].strip())
                points.append((freq, complex(real, imag)))
                i += 3
            except (ValueError, IndexError):
                break
        return points

    def close(self):
        """Close the TCP connection."""
        try:
            self.sock.close()
        except Exception:
            pass
