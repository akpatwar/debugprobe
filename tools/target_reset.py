#!/usr/bin/env python3
"""Pulses the target's reset through a Debug Probe running the single-wire firmware (PROBE_UART_SINGLE_WIRE).

    python3 tools/target_reset.py --port /dev/cu.usbmodemXXXX [--ms 10]

The firmware pulls the UART connector's TX pin (P1, GPIO4) low, open-drain, while the host holds a serial break, and releases it
otherwise. Wired straight to the target's NRST (which needs its own pull-up), a break of N ms holds the target in reset for N ms.
Keep the probe powered while P1 is wired: an unpowered RP2040 can load NRST through its pin protection.

The port is opened without exclusive access, so this can run next to a tool that already has the port open (an update tool waiting
in its listen-window mode, for example): the break reaches the probe either way. Exit code 0 when the break was sent.
"""

import argparse
import fcntl
import os
import sys
import time

BREAK_IOCTLS = {
    "darwin": (0x2000747B, 0x2000747A),
    "linux": (0x5427, 0x5428),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--port", required=True, help="the probe's serial port, for example /dev/cu.usbmodem1102")
    parser.add_argument("--ms", type=int, default=10, help="how long to hold the target in reset, in ms (default 10)")
    args = parser.parse_args()
    if not 1 <= args.ms <= 10000:
        parser.error("--ms must be 1 to 10000")

    ioctls = BREAK_IOCTLS.get(sys.platform if sys.platform != "linux2" else "linux")
    if ioctls is None:
        parser.error("unsupported platform %s (macOS and Linux only)" % sys.platform)
    set_break, clear_break = ioctls

    descriptor = os.open(args.port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    try:
        fcntl.ioctl(descriptor, set_break)
        try:
            time.sleep(args.ms / 1000.0)
        finally:
            fcntl.ioctl(descriptor, clear_break)
    finally:
        os.close(descriptor)
    print("reset pulse of %d ms sent on %s" % (args.ms, args.port))
    return 0


if __name__ == "__main__":
    sys.exit(main())
