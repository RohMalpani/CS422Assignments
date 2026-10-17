# Implement the iperf3 control exchange and timed TCP data transfer using Python sockets.
#
# iperf3 protocol summary (TCP test, client sends, 1 stream):
#   1. Client opens the control connection and sends a 37-byte cookie (36 random chars + NUL).
#   2. Server sends state PARAM_EXCHANGE; client replies with JSON test parameters
#      (4-byte big-endian length, then JSON).
#   3. Server sends CREATE_STREAMS; client opens the data connection and sends the same cookie on it.
#   4. Server sends TEST_START then TEST_RUNNING; client sends data for `duration` seconds.
#   5. Client sends TEST_END; server sends EXCHANGE_RESULTS; client sends its results JSON,
#      reads the server's results JSON; server sends DISPLAY_RESULTS; client sends IPERF_DONE.
# Control messages are single signed bytes ("states"); only the JSON blobs are length-prefixed.
import json
import random
import select
import socket
import string
import struct
import time

# iperf3 state codes (iperf_api.h)
TEST_START = 1
TEST_RUNNING = 2
TEST_END = 4
PARAM_EXCHANGE = 9
CREATE_STREAMS = 10
SERVER_TERMINATE = 11
EXCHANGE_RESULTS = 13
DISPLAY_RESULTS = 14
IPERF_DONE = 16
ACCESS_DENIED = -1
SERVER_ERROR = -2

COOKIE_SIZE = 37
BLOCK_SIZE = 128 * 1024  # iperf3's default TCP write size


class Iperf3Error(Exception):
    """Any failure talking to the server (timeout, reset, protocol surprise)."""


class ServerRejected(Iperf3Error):
    """Server refused the test (busy / access denied / error state)."""


def _recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise Iperf3Error("connection closed by server")
        buf += chunk
    return buf


def _recv_state(sock):
    (state,) = struct.unpack("b", _recv_exact(sock, 1))
    if state == ACCESS_DENIED:
        raise ServerRejected("server sent ACCESS_DENIED (busy or not allowed)")
    if state == SERVER_ERROR:
        raise ServerRejected("server sent SERVER_ERROR")
    if state == SERVER_TERMINATE:
        raise Iperf3Error("server terminated the test early")
    return state


def _send_state(sock, state):
    sock.sendall(struct.pack("b", state))


def _send_json(sock, obj):
    data = json.dumps(obj).encode()
    sock.sendall(struct.pack(">I", len(data)) + data)


def _recv_json(sock):
    (length,) = struct.unpack(">I", _recv_exact(sock, 4))
    return json.loads(_recv_exact(sock, length))


def _expect(sock, wanted):
    state = _recv_state(sock)
    if state != wanted:
        raise Iperf3Error(f"protocol error: expected state {wanted}, got {state}")


def make_cookie():
    chars = string.ascii_lowercase + string.digits
    return ("".join(random.choices(chars, k=COOKIE_SIZE - 1)) + "\0").encode()


def run_test(host, port, duration=10, congestion=None, sample_interval=1.0,
             on_sample=None, connect_timeout=5.0, io_timeout=10.0):
    """Run one iperf3 TCP upload test.

    on_sample(data_sock, elapsed_s) is called about every `sample_interval` seconds while sending,
    so goodput.py can read TCP stats from the data socket. Returns a dict with total bytes sent and
    the server's JSON results. Raises Iperf3Error / ServerRejected on failure.
    """
    cookie = make_cookie()
    ctrl = data = None
    try:
        try:
            ctrl = socket.create_connection((host, port), timeout=connect_timeout)
        except OSError as e:
            raise Iperf3Error(f"control connect failed: {e}") from e
        ctrl.settimeout(io_timeout)
        ctrl.sendall(cookie)

        _expect(ctrl, PARAM_EXCHANGE)
        _send_json(ctrl, {
            "tcp": True, "omit": 0, "time": duration, "num": 0, "blockcount": 0,
            "parallel": 1, "len": BLOCK_SIZE, "pacing_timer": 1000, "client_version": "3.9",
        })

        _expect(ctrl, CREATE_STREAMS)
        data = socket.socket(socket.AF_INET6 if ":" in ctrl.getpeername()[0] else socket.AF_INET,
                             socket.SOCK_STREAM)
        if congestion:
            # Must be set before connect() so the algorithm is in use from the first packet.
            data.setsockopt(socket.IPPROTO_TCP, socket.TCP_CONGESTION, congestion.encode())
        data.settimeout(connect_timeout)
        try:
            data.connect(ctrl.getpeername()[:2])
        except OSError as e:
            raise Iperf3Error(f"data connect failed: {e}") from e
        data.sendall(cookie)
        # Ask the kernel what it is really using (the OS default if we didn't set one).
        actual_cc = data.getsockopt(socket.IPPROTO_TCP, socket.TCP_CONGESTION, 16).split(b"\0")[0].decode()

        _expect(ctrl, TEST_START)
        _expect(ctrl, TEST_RUNNING)

        total = _send_data(ctrl, data, duration, sample_interval, on_sample, io_timeout)

        _send_state(ctrl, TEST_END)
        data.close()
        data = None

        _expect(ctrl, EXCHANGE_RESULTS)
        _send_json(ctrl, {
            "cpu_util_total": 0, "cpu_util_user": 0, "cpu_util_system": 0,
            "sender_has_retransmits": -1,
            "streams": [{"id": 1, "bytes": total, "retransmits": -1,
                         "jitter": 0, "errors": 0, "packets": 0}],
        })
        server_results = _recv_json(ctrl)
        _expect(ctrl, DISPLAY_RESULTS)
        _send_state(ctrl, IPERF_DONE)
        return {"bytes_sent": total, "server_results": server_results, "congestion": actual_cc}
    except socket.timeout as e:
        raise Iperf3Error(f"timed out: {e}") from e
    except (ConnectionError, OSError) as e:
        if isinstance(e, Iperf3Error):
            raise
        raise Iperf3Error(f"socket error: {e}") from e
    finally:
        for s in (data, ctrl):
            if s is not None:
                s.close()


def _send_data(ctrl, data, duration, sample_interval, on_sample, io_timeout):
    """Blast zero-filled blocks for `duration` seconds; watch the control socket for early termination."""
    block = bytes(BLOCK_SIZE)
    data.settimeout(io_timeout)
    total = 0
    start = time.monotonic()
    next_sample = start + sample_interval
    while True:
        now = time.monotonic()
        if now - start >= duration:
            return total
        total += data.send(block)
        now = time.monotonic()
        if now >= next_sample:
            next_sample += sample_interval
            if on_sample:
                on_sample(data, now - start)
            # A readable control socket mid-test means the server is telling us something (e.g. terminate).
            if select.select([ctrl], [], [], 0)[0]:
                _recv_state(ctrl)
