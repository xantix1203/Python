import json
import socket
import time

from battleship.config import NETWORK_PORT
from battleship.network.connection import Connection, HostListener, loopback_pair


def _poll_until_message(connection, timeout=2):
    """The reader thread is genuinely asynchronous, so poll() may need a
    few milliseconds before a message shows up — this retries instead of
    asserting on the very first call.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        message = connection.poll()
        if message is not None:
            return message
        time.sleep(0.01)
    raise AssertionError("timed out waiting for a message")


def test_connection_receives_a_message_sent_on_the_raw_socket():
    local, remote = socket.socketpair()
    connection = Connection(local)

    remote.sendall(b'{"type": "hello", "name": "Alice"}\n')

    assert _poll_until_message(connection) == {"type": "hello", "name": "Alice"}


def test_connection_send_is_framed_as_one_json_line():
    local, remote = socket.socketpair()
    connection = Connection(local)

    connection.send({"type": "shot", "x": 3, "y": 4})

    raw = remote.recv(4096)
    assert raw.endswith(b"\n")
    assert json.loads(raw) == {"type": "shot", "x": 3, "y": 4}


def test_connection_splits_two_messages_sent_in_a_single_chunk():
    local, remote = socket.socketpair()
    connection = Connection(local)

    remote.sendall(b'{"type": "a"}\n{"type": "b"}\n')

    assert _poll_until_message(connection) == {"type": "a"}
    assert _poll_until_message(connection) == {"type": "b"}


def test_connection_poll_returns_none_when_nothing_has_arrived():
    local, _remote = socket.socketpair()
    connection = Connection(local)

    assert connection.poll() is None


def test_connection_poll_raises_once_peer_disconnects():
    local, remote = socket.socketpair()
    connection = Connection(local)
    remote.close()

    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        try:
            message = connection.poll()
        except ConnectionError:
            return
        assert message is None
        time.sleep(0.01)
    raise AssertionError("expected a ConnectionError after the peer disconnected")


def _poll_listener_until_connection(listener, timeout=2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        connection = listener.poll()
        if connection is not None:
            return connection
        time.sleep(0.01)
    raise AssertionError("timed out waiting for the host to accept a peer")


def test_host_listener_accepts_multiple_peers():
    # Port 0 lets the OS pick a free port so parallel test runs don't collide.
    listener = HostListener(0)
    port = listener._socket.getsockname()[1]
    try:
        first_client = socket.create_connection(("127.0.0.1", port))
        first = _poll_listener_until_connection(listener)
        second_client = socket.create_connection(("127.0.0.1", port))
        second = _poll_listener_until_connection(listener)

        first_client.sendall(b'{"who": 1}\n')
        second_client.sendall(b'{"who": 2}\n')
        assert _poll_until_message(first) == {"who": 1}
        assert _poll_until_message(second) == {"who": 2}
    finally:
        listener.close()


def test_loopback_pair_round_trips_in_both_directions():
    host_end, player_end = loopback_pair()

    player_end.send({"type": "fire", "x": 2, "y": 3})
    host_end.send({"type": "state", "turn": 0})

    assert host_end.poll() == {"type": "fire", "x": 2, "y": 3}
    assert player_end.poll() == {"type": "state", "turn": 0}
    assert host_end.poll() is None  # nothing left queued


def test_network_port_is_a_valid_tcp_port():
    assert 1 <= NETWORK_PORT <= 65535
