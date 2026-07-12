import json
import socket
import time

from battleship.network.connection import Connection


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
