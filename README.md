# Reliable Transport Protocol (RTP) over UDP

Implementation for **Project 4: Reliable Transport**. The two variants use the
same 16-byte RTP header (`type`, `seq_num`, `length`, CRC32 `checksum`) and the
packet format from the provided starter files.

## Project layout

- `RTP-base/sender.py`, `RTP-base/receiver.py`: sliding-window delivery with
  cumulative acknowledgments and Go-Back-N-style timeout retransmissions.
- `RTP-opt/sender.py`, `RTP-opt/receiver.py`: selective per-packet acknowledgments
  and selective timeout retransmissions.
- `RTP-base/utils.py` and `RTP-opt/utils.py`: **unchanged** supplied utilities.
- `test_scripts/`: **unchanged** supplied `proxy.py`, `test.sh`, `compare.sh`, and test message.
- `HUONG_DAN_GITHUB.md`: Vietnamese setup, test, and Git/GitHub walkthrough.

## Technical design

1. The sender transmits `START(seq=0)` and awaits `ACK(seq=1)`.
2. Each `DATA` datagram contains up to **1456 bytes** (1472 UDP payload bytes
   less a 16-byte RTP header). The sender reads binary input from `stdin`.
3. The receiver verifies length and CRC32, buffers valid out-of-order data
   within its receive window, and emits contiguous bytes to binary `stdout`.
4. In `RTP-base`, `ACK(seq=N)` cumulatively confirms all DATA packets below N.
   When the one 500-ms window timer expires, all still-outstanding packets
   are retransmitted.
5. In `RTP-opt`, DATA packets are individually ACKed with their *own* sequence
   numbers. The 500-ms timer retransmits only unacknowledged packets, while
   acknowledged out-of-order packets stay recorded until the window advances.
6. Once all data is confirmed, the sender sends `END`, waiting for its ACK or
   at most 500 ms before returning.

Only UDP sockets (`socket.SOCK_DGRAM`) are used; no TCP sockets.

## Setup on Ubuntu

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git lsof
python3 -m venv .venv
source .venv/bin/activate
python -m pip install scapy
chmod +x test_scripts/test.sh test_scripts/compare.sh
```

The original assignment recommends `scapy==2.4.0` on the course VM. On a modern
Python release, use a compatible Scapy version if 2.4.0 cannot be installed.

## Testing

```bash
./test_scripts/test.sh RTP-base
./test_scripts/test.sh RTP-opt
```

**Note about the supplied test script:** it references `SENDER_ID` during cleanup
but previously sets `SENDER_PID`. It also has a fixed 10-second timeout and may
leave processes running; do not change the instructor's file. If it is unreliable,
follow the **manual three-terminal test** in `HUONG_DAN_GITHUB.md` instead.

See [HUONG_DAN_GITHUB.md](HUONG_DAN_GITHUB.md) for an explanation of each Git
command and submission instructions.
