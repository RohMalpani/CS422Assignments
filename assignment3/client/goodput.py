# Sample acknowledged bytes from the data socket and calculate interval goodput.
#
# Linux only: reads struct tcp_info through getsockopt(TCP_INFO). Field order/types follow
# include/uapi/linux/tcp.h. Older kernels return a shorter struct, so we decode only the fields
# that fit in whatever length the kernel gives us.
import socket
import struct
import time

# (name, struct format char). "pad" = the 8 leading u8 fields we don't use individually.
# Native-size '=' packing is correct here: every field in the real struct is naturally aligned,
# so the C compiler inserts no padding (checked against offsetof() in WSL, see DECISIONS.md).
_TCP_INFO_FIELDS = (
    [("state", "B"), ("ca_state", "B"), ("retransmits", "B"), ("probes", "B"),
     ("backoff", "B"), ("options", "B"), ("wscale", "B"), ("flags", "B")]
    + [(n, "I") for n in (
        "rto", "ato", "snd_mss", "rcv_mss", "unacked", "sacked", "lost", "retrans", "fackets",
        "last_data_sent", "last_ack_sent", "last_data_recv", "last_ack_recv", "pmtu",
        "rcv_ssthresh", "rtt", "rttvar", "snd_ssthresh", "snd_cwnd", "advmss", "reordering",
        "rcv_rtt", "rcv_space", "total_retrans")]
    + [(n, "Q") for n in ("pacing_rate", "max_pacing_rate", "bytes_acked", "bytes_received")]
    + [(n, "I") for n in ("segs_out", "segs_in", "notsent_bytes", "min_rtt",
                          "data_segs_in", "data_segs_out")]
    + [(n, "Q") for n in ("delivery_rate", "busy_time", "rwnd_limited", "sndbuf_limited")]
    + [(n, "I") for n in ("delivered", "delivered_ce")]
    + [(n, "Q") for n in ("bytes_sent", "bytes_retrans")]
    + [(n, "I") for n in ("dsack_dups", "reord_seen")]
)
_TCP_INFO_BUFLEN = 256  # larger than today's struct (224 B) so newer kernels don't truncate us


def read_tcp_info(sock):
    """Return a dict of tcp_info fields for `sock` (units: rtt/rttvar in microseconds, cwnd in
    segments, rates in bytes/s, byte counters in bytes)."""
    raw = sock.getsockopt(socket.IPPROTO_TCP, socket.TCP_INFO, _TCP_INFO_BUFLEN)
    info = {}
    offset = 0
    for name, fmt in _TCP_INFO_FIELDS:
        size = struct.calcsize(fmt)
        if offset + size > len(raw):
            break  # older kernel: remaining fields not provided
        (info[name],) = struct.unpack_from("=" + fmt, raw, offset)
        offset += size
    return info


class GoodputSampler:
    """Callable for iperf3_client.run_test(on_sample=...). Appends one row to self.rows per call.

    goodput = (delta bytes_acked) / (delta actual elapsed time) * 8, using the real time between
    samples (not the nominal interval), as the handout specifies.
    """

    def __init__(self):
        self.rows = []
        self._prev_acked = 0
        self._prev_elapsed = 0.0
        self._prev_retrans = 0

    def __call__(self, sock, elapsed):
        info = read_tcp_info(sock)
        dt = elapsed - self._prev_elapsed
        acked = info.get("bytes_acked", 0)
        retrans = info.get("total_retrans", 0)
        self.rows.append({
            "timestamp": time.time(),
            "elapsed_s": round(elapsed, 4),
            "interval_s": round(dt, 4),
            "bytes_acked": acked,
            "goodput_bps": (acked - self._prev_acked) * 8 / dt if dt > 0 else 0.0,
            "snd_cwnd": info.get("snd_cwnd"),
            "rtt_us": info.get("rtt"),
            "rttvar_us": info.get("rttvar"),
            "total_retrans": retrans,
            "retrans_interval": retrans - self._prev_retrans,  # loss proxy: new retransmits this interval
            "lost": info.get("lost"),
            "pacing_rate_Bps": info.get("pacing_rate"),
            "delivery_rate_Bps": info.get("delivery_rate"),
        })
        self._prev_acked = acked
        self._prev_elapsed = elapsed
        self._prev_retrans = retrans
