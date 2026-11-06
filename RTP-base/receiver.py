"""RTP-base receiver: buffer out-of-order UDP DATA and send cumulative ACKs."""

import argparse
import socket
import struct
import sys

from utils import compute_checksum

START, END, DATA, ACK = 0, 1, 2, 3
HEADER = struct.Struct("!IIII")
MAX_PACKET = 1472


def decode_packet(raw):
    """Reject malformed/corrupt packets rather than acknowledging them."""
    if not HEADER.size <= len(raw) <= MAX_PACKET:
        return None
    kind, sequence, length, checksum = HEADER.unpack_from(raw)
    if kind not in (START, END, DATA):
        return None
    if length != len(raw) - HEADER.size or (kind != DATA and length != 0):
        return None
    clean_header = HEADER.pack(kind, sequence, length, 0)
    if compute_checksum(clean_header + raw[HEADER.size:]) != checksum:
        return None
    return kind, sequence, raw[HEADER.size:]


def ack_packet(seq):
    initial = HEADER.pack(ACK, seq, 0, 0)
    return HEADER.pack(ACK, seq, 0, compute_checksum(initial))


def receiver(receiver_ip, receiver_port, window_size):
    if window_size < 1:
        raise ValueError("window_size must be at least 1")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((receiver_ip, receiver_port))
        peer = None
        expected = 1  # START (seq=0) occupies the first sequence number
        buffered = {}
        output = sys.stdout.buffer

        while True:
            raw, address = sock.recvfrom(2048)
            parsed = decode_packet(raw)
            if parsed is None:
                continue
            kind, seq, payload = parsed

            if peer is None:
                if kind == START and seq == 0:
                    peer = address
                    sock.sendto(ack_packet(expected), peer)
                continue

            if address != peer:
                continue  # one active sender per connection
            if kind == START:
                continue  # ignore START during an existing connection

            if kind == DATA:
                if expected <= seq < expected + window_size:
                    buffered.setdefault(seq, payload)
                    # Release contiguous data only, preserving byte order.
                    while expected in buffered:
                        output.write(buffered.pop(expected))
                        expected += 1
                    output.flush()
                # Duplicate, missing or out-of-window packet: reply with
                # the next expected sequence number (cumulative ACK).
                sock.sendto(ack_packet(expected), peer)

            elif kind == END:
                if seq == expected:
                    sock.sendto(ack_packet(expected + 1), peer)
                    output.flush()
                    return
                # Out-of-order END: do not terminate before missing DATA.
                sock.sendto(ack_packet(expected), peer)


def main():
    parser = argparse.ArgumentParser(description="Reliable UDP receiver (RTP-base)")
    parser.add_argument("receiver_ip")
    parser.add_argument("receiver_port", type=int)
    parser.add_argument("window_size", type=int)
    args = parser.parse_args()
    receiver(args.receiver_ip, args.receiver_port, args.window_size)


if __name__ == "__main__":
    main()
