"""RTP-opt sender: sliding-window Selective Repeat with individual ACKs."""

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
    raw = HEADER.pack(packet_type, sequence, len(payload), 0) + payload
    return HEADER.pack(packet_type, sequence, len(payload), compute_checksum(raw)) + payload


def read_ack(raw):
    if len(raw) != HEADER.size:
        return None
    kind, seq, length, checksum = HEADER.unpack(raw)
    if kind != ACK or length != 0:
        return None
    if checksum != compute_checksum(HEADER.pack(kind, seq, length, 0)):
        return None
    return seq


def sender(receiver_ip, receiver_port, window_size):
    if window_size < 1:
        raise ValueError("window_size must be at least 1")
    # Normalize hostname: recvfrom() returns a numeric IPv4 address, not "localhost".
    destination = (socket.gethostbyname(receiver_ip), receiver_port)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(TIMEOUT)
        start_packet = make_packet(START, 0)
        sock.sendto(start_packet, destination)
        while True:
            try:
                raw, address = sock.recvfrom(2048)
            except socket.timeout:
                sock.sendto(start_packet, destination)
                continue
            if address == destination and read_ack(raw) == 1:
                break

        base = 1
        next_seq = 1
        # Keep all sent packets until the window's left edge passes them.
        # This distinguishes acknowledged packets from those needing a retry.
        pending = {}  # seq -> [encoded_packet, has_been_acknowledged]
        end_of_input = False
        deadline = time.monotonic() + TIMEOUT
        stream = sys.stdin.buffer

        while pending or not end_of_input:
            while not end_of_input and next_seq < base + window_size:
                data = stream.read(MAX_PAYLOAD)
                if not data:
                    end_of_input = True
                    break
                raw = make_packet(DATA, next_seq, data)
                pending[next_seq] = [raw, False]
                sock.sendto(raw, destination)
                if len(pending) == 1:
                    deadline = time.monotonic() + TIMEOUT
                next_seq += 1

            if not pending:
                continue

            sock.settimeout(max(0.001, deadline - time.monotonic()))
            try:
                raw, address = sock.recvfrom(2048)
            except socket.timeout:
                raw, address = b"", None

            ack = read_ack(raw) if address == destination else None
            if ack in pending:
                # Unlike cumulative ACK, this confirms only one DATA packet.
                pending[ack][1] = True
                old_base = base
                while base in pending and pending[base][1]:
                    del pending[base]
                    base += 1
                if base != old_base:
                    deadline = time.monotonic() + TIMEOUT

            if pending and time.monotonic() >= deadline:
                # Retry *only* data that has not been individually ACKed.
                for packet, acknowledged in pending.values():
                    if not acknowledged:
                        sock.sendto(packet, destination)
                deadline = time.monotonic() + TIMEOUT

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
    parser = argparse.ArgumentParser(description="Reliable UDP sender (RTP-opt)")
    parser.add_argument("receiver_ip")
    parser.add_argument("receiver_port", type=int)
    parser.add_argument("window_size", type=int)
    args = parser.parse_args()
    sender(args.receiver_ip, args.receiver_port, args.window_size)


if __name__ == "__main__":
    main()
