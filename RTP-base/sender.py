"""RTP-base sender: UDP + cumulative acknowledgments and sliding window.

Packet layout is four unsigned 32-bit network-order integers, followed by at
most 1456 bytes.  We use the CRC32 function supplied by the starter code.
"""

import argparse
import socket
import struct
import sys
import time

from utils import compute_checksum

START, END, DATA, ACK = 0, 1, 2, 3
HEADER = struct.Struct("!IIII")
MAX_PAYLOAD = 1472 - HEADER.size
TIMEOUT = 0.5


def make_packet(packet_type, sequence, payload=b""):
    """Encode a packet, calculating CRC with its checksum field set to zero."""
    initial = HEADER.pack(packet_type, sequence, len(payload), 0) + payload
    crc = compute_checksum(initial)
    return HEADER.pack(packet_type, sequence, len(payload), crc) + payload


def read_ack(raw):
    """Return a verified ACK number, or None for invalid datagrams."""
    if len(raw) != HEADER.size:
        return None
    packet_type, seq, length, checksum = HEADER.unpack(raw)
    if packet_type != ACK or length != 0:
        return None
    verified = HEADER.pack(packet_type, seq, length, 0)
    if compute_checksum(verified) != checksum:
        return None
    return seq


def sender(receiver_ip, receiver_port, window_size):
    if window_size < 1:
        raise ValueError("window_size must be at least 1")

    # Normalize hostname: recvfrom() returns a numeric IPv4 address, not "localhost".
    destination = (socket.gethostbyname(receiver_ip), receiver_port)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(TIMEOUT)

        # START uses seq=0, with a cumulative ACK of 1.
        start_packet = make_packet(START, 0)
        sock.sendto(start_packet, destination)
        while True:
            try:
                datagram, address = sock.recvfrom(2048)
            except socket.timeout:
                sock.sendto(start_packet, destination)
                continue
            if address == destination and read_ack(datagram) == 1:
                break

        # base is the first unacknowledged DATA sequence number.
        base = 1
        next_seq = 1
        outstanding = {}  # sequence -> exact packet to retransmit
        reached_eof = False
        last_progress = time.monotonic()
        stream = sys.stdin.buffer

        while outstanding or not reached_eof:
            # Never send more than 'window_size' unacknowledged packets.
            while not reached_eof and next_seq < base + window_size:
                chunk = stream.read(MAX_PAYLOAD)
                if not chunk:
                    reached_eof = True
                    break
                packet = make_packet(DATA, next_seq, chunk)
                outstanding[next_seq] = packet
                sock.sendto(packet, destination)
                next_seq += 1
                if len(outstanding) == 1:
                    last_progress = time.monotonic()

            if not outstanding:
                continue

            remaining = TIMEOUT - (time.monotonic() - last_progress)
            sock.settimeout(max(0.001, remaining))
            try:
                raw, address = sock.recvfrom(2048)
            except socket.timeout:
                raw, address = b"", None

            ack_num = read_ack(raw) if address == destination else None
            # A cumulative ACK denotes the NEXT expected packet.
            if ack_num is not None and base < ack_num <= next_seq:
                for sequence in range(base, ack_num):
                    outstanding.pop(sequence, None)
                base = ack_num
                last_progress = time.monotonic()
            elif time.monotonic() - last_progress >= TIMEOUT:
                # Go-Back-N retransmission; only the outstanding window.
                for packet in outstanding.values():
                    sock.sendto(packet, destination)
                last_progress = time.monotonic()

        # END has its own sequence number, after the last DATA packet.
        # The receiver may exit after acknowledging it, so wait at most 500ms.
        end_sequence = next_seq
        sock.sendto(make_packet(END, end_sequence), destination)
        deadline = time.monotonic() + TIMEOUT
        while time.monotonic() < deadline:
            sock.settimeout(max(0.001, deadline - time.monotonic()))
            try:
                raw, address = sock.recvfrom(2048)
            except socket.timeout:
                break
            if address == destination and read_ack(raw) == end_sequence + 1:
                break


def main():
    parser = argparse.ArgumentParser(description="Reliable UDP sender (RTP-base)")
    parser.add_argument("receiver_ip")
    parser.add_argument("receiver_port", type=int)
    parser.add_argument("window_size", type=int)
    args = parser.parse_args()
    sender(args.receiver_ip, args.receiver_port, args.window_size)


if __name__ == "__main__":
    main()
