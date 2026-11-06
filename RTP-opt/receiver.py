"""RTP-opt receiver: individually ACK valid DATA, buffer for in-order output."""

import argparse
import socket
import struct
import sys

from utils import compute_checksum

START, END, DATA, ACK = 0, 1, 2, 3
HEADER = struct.Struct("!IIII")
MAX_PACKET = 1472


def decode_packet(raw):
    if not HEADER.size <= len(raw) <= MAX_PACKET:
        return None
    kind, sequence, length, checksum = HEADER.unpack_from(raw)
    if kind not in (START, END, DATA):
        return None
    if length != len(raw) - HEADER.size or (kind != DATA and length != 0):
        return None
    checked = HEADER.pack(kind, sequence, length, 0) + raw[HEADER.size:]
    if compute_checksum(checked) != checksum:
        return None
    return kind, sequence, raw[HEADER.size:]


def ack_packet(sequence):
    clean = HEADER.pack(ACK, sequence, 0, 0)
    return HEADER.pack(ACK, sequence, 0, compute_checksum(clean))


def receiver(receiver_ip, receiver_port, window_size):
    if window_size < 1:
        raise ValueError("window_size must be at least 1")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((receiver_ip, receiver_port))
        peer = None
        expected = 1
        buffered = {}
        output = sys.stdout.buffer

        while True:
            raw, address = sock.recvfrom(2048)
            decoded = decode_packet(raw)
            if decoded is None:
                continue
            kind, seq, payload = decoded

            if peer is None:
                if kind == START and seq == 0:
                    peer = address
                    sock.sendto(ack_packet(1), peer)
                continue
            if address != peer or kind == START:
                continue

            if kind == DATA:
                if seq < expected:
                    # A duplicate of a packet already written to stdout.
                    sock.sendto(ack_packet(seq), peer)
                elif seq < expected + window_size:
                    buffered.setdefault(seq, payload)
                    # Optimization: ACK this DATA's own sequence number.
                    sock.sendto(ack_packet(seq), peer)
                    while expected in buffered:
                        output.write(buffered.pop(expected))
                        expected += 1
                    output.flush()
                # Packets beyond the receive window must be dropped.

            elif kind == END:
                if seq == expected:
                    sock.sendto(ack_packet(expected + 1), peer)
                    output.flush()
                    return
                # END is not safe to process before all DATA is present.


def main():
    parser = argparse.ArgumentParser(description="Reliable UDP receiver (RTP-opt)")
    parser.add_argument("receiver_ip")
    parser.add_argument("receiver_port", type=int)
    parser.add_argument("window_size", type=int)
    args = parser.parse_args()
    receiver(args.receiver_ip, args.receiver_port, args.window_size)


if __name__ == "__main__":
    main()
