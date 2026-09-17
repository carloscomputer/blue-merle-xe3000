#!/usr/bin/env python3
"""Minimal standalone AT command sender for blue-merle (GL-XE3000).

Deliberately independent of quectel-5g-tools: talks directly to
/dev/ttyUSB2 via pyserial. Retries on a locked port, since other
tools (e.g. quectel-5g-tools' watchdog, if installed) may hold the
same port briefly.
"""
import sys
import time
import argparse
import serial

TTY = '/dev/ttyUSB2'
BAUDRATE = 9600
TIMEOUT = 3

ap = argparse.ArgumentParser()
ap.add_argument("command", help="AT command to send, e.g. 'AT+GSN'")
ap.add_argument("--retries", type=int, default=1)
ap.add_argument("--retry-delay", type=float, default=1.0)
args = ap.parse_args()

last_err = None
for attempt in range(1, args.retries + 1):
    try:
        with serial.Serial(TTY, BAUDRATE, timeout=TIMEOUT, exclusive=True) as ser:
            ser.write((args.command + '\r').encode())
            output = ser.read(256)
        print(output.decode(errors='replace'), end='')
        sys.exit(0)
    except serial.SerialException as e:
        last_err = e
        if attempt < args.retries:
            time.sleep(args.retry_delay)

print(f"AT send failed after {args.retries} attempt(s): {last_err}", file=sys.stderr)
sys.exit(1)
