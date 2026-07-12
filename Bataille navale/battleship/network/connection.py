"""Socket plumbing for LAN play.

Everything here follows one recurring shape: a background thread does the
one thing that's allowed to block (recv/accept/connect), and hands its
result to the main thread through a queue.Queue, which is safe to share
between threads without any manual locking. The main (pygame) thread never
blocks — it polls once per frame.
"""

import json
import queue
import socket
import threading

_DISCONNECTED = object()  # distinct from None, so "disconnected" can't be mistaken for "nothing yet"


class Connection:
    """Wraps one already-connected socket and turns it into a stream of
    decoded JSON messages, fed by a background reader thread.
    """

    def __init__(self, sock):
        self._sock = sock
        self._incoming = queue.Queue()
        self._buffer = b""
        threading.Thread(target=self._read_loop, daemon=True).start()

    def _read_loop(self):
        while True:
            try:
                chunk = self._sock.recv(4096)
            except OSError:
                self._incoming.put(_DISCONNECTED)
                return
            if not chunk:
                self._incoming.put(_DISCONNECTED)
                return
            self._buffer += chunk
            while b"\n" in self._buffer:
                line, self._buffer = self._buffer.split(b"\n", 1)
                self._incoming.put(json.loads(line))

    def send(self, message):
        self._sock.sendall((json.dumps(message) + "\n").encode())

    def poll(self):
        """Non-blocking: returns the next message dict, or None if nothing
        has arrived yet. Raises ConnectionError once the peer disconnects.
        """
        try:
            message = self._incoming.get_nowait()
        except queue.Empty:
            return None
        if message is _DISCONNECTED:
            raise ConnectionError("The other player disconnected.")
        return message

    def close(self):
        self._sock.close()


class HostListener:
    """Starts listening immediately; poll() until someone connects."""

    def __init__(self, port):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(("0.0.0.0", port))
        self._socket.listen(1)
        self._result = queue.Queue(maxsize=1)
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self):
        peer_socket, _address = self._socket.accept()  # blocks until someone joins
        self._result.put(Connection(peer_socket))

    def poll(self):
        """Non-blocking: returns a Connection once a peer has joined, else None."""
        try:
            return self._result.get_nowait()
        except queue.Empty:
            return None


class ConnectAttempt:
    """Starts connecting immediately; poll() until it succeeds or fails."""

    def __init__(self, host, port, timeout=5):
        self._result = queue.Queue(maxsize=1)
        threading.Thread(target=self._connect, args=(host, port, timeout), daemon=True).start()

    def _connect(self, host, port, timeout):
        try:
            sock = socket.create_connection((host, port), timeout=timeout)
        except OSError as error:
            self._result.put(error)
            return
        sock.settimeout(None)  # drop the connect timeout — the reader thread should block indefinitely
        self._result.put(Connection(sock))

    def poll(self):
        """Non-blocking: returns a Connection on success, an OSError on
        failure, or None while still trying.
        """
        try:
            return self._result.get_nowait()
        except queue.Empty:
            return None


def get_local_ip():
    """Best-effort LAN IP for this machine, for display on the host screen.

    Opens a UDP socket "connected" to a public address — nothing is actually
    sent — purely so the OS tells us which local interface it would route
    through. A machine can have several interfaces (Wi-Fi, Ethernet, VPN),
    so there's no simpler direct way to ask "what's my LAN IP".
    """
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()
