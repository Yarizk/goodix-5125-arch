#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""goodix-5125-diagnose - READ-ONLY health check for the Goodix USB 27c6:5125 fingerprint reader.

Sends only read commands of the Goodix USB protocol:
  0xA8  firmware application identity
  0xE4  read key-slot descriptor, slots 0xbb010002 (host pairing record) and 0xbb020003 (validator)
It prints status / type / length / ACK status only - never key material, hashes or record contents,
so the output is safe to share in a bug report. Nothing is written to the reader.

Usage:  sudo systemctl stop fprintd;  sudo goodix-5125-diagnose
"""
import struct
import sys

try:
    import usb.core
    import usb.util
except ImportError:
    sys.exit("python-pyusb is required:  sudo pacman -S python-pyusb")

VID, PID = 0x27C6, 0x5125
SUPPORTED_APPS = ("GF_ST411SEC_APP_12509", "GF_ST411SEC_APP_12508")
QUALIFIED_ACK = (0x01, 0x07)


def pack(payload):
    head = struct.pack("<BH", 0xA0, len(payload))
    return head + bytes([sum(head) & 0xFF]) + payload


def proto(cmd, payload):
    body = struct.pack("<BH", cmd, len(payload) + 1) + payload
    return body + bytes([(0xAA - sum(body)) & 0xFF])


def unpack(raw):
    if len(raw) < 7 or raw[0] != 0xA0 or (sum(raw[0:3]) & 0xFF) != raw[3]:
        raise ValueError("unexpected frame")
    msg = raw[4:4 + struct.unpack("<H", raw[1:3])[0]]
    return msg[0], msg[3:2 + struct.unpack("<H", msg[1:3])[0]]


def request(dev, ep_in, ep_out, cmd, payload):
    dev.write(ep_out, pack(proto(cmd, payload)), timeout=2000)
    ack = None
    for _ in range(4):
        rcmd, msg = unpack(bytes(dev.read(ep_in, 0x10000, timeout=2000)))
        if rcmd == 0xB0:
            ack = msg
        elif rcmd == cmd:
            return ack, msg
    raise ValueError(f"no reply to {cmd:#04x}")


def main():
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        print("FAIL  reader 27c6:5125 not found on USB")
        return 1
    intf = usb.util.find_descriptor(dev.get_active_configuration(), bInterfaceClass=0x0A)
    ep_in = usb.util.find_descriptor(intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN).bEndpointAddress
    ep_out = usb.util.find_descriptor(intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT).bEndpointAddress
    try:
        usb.util.claim_interface(dev, intf.bInterfaceNumber)
    except usb.core.USBError as e:
        print(f"FAIL  cannot claim the reader ({e}). Stop fprintd first: sudo systemctl stop fprintd")
        return 1
    problems = 0
    try:
        try:
            while True:
                dev.read(ep_in, 0x10000, timeout=200)
        except usb.core.USBTimeoutError:
            pass

        ack, body = request(dev, ep_in, ep_out, 0xA8, b"\x00\x00")
        app = body.split(b"\x00")[0].decode(errors="replace")
        ok = app in SUPPORTED_APPS
        problems += not ok
        print(f"{'OK  ' if ok else 'FAIL'}  firmware application: {app}"
              + ("" if ok else "  (not a firmware the driver supports)"))
        status = ack[1] if ack and len(ack) == 2 else None
        ok = status in QUALIFIED_ACK
        problems += not ok
        print(f"{'OK  ' if ok else 'WARN'}  ACK status: {status:#04x}" if status is not None else "WARN  ACK status: none",
              "" if ok else " (driver accepts only 0x01/0x07 - see 'Recovery' in the README)")

        for slot, need_len, label in ((0xBB010002, 332, "host pairing record"), (0xBB020003, 32, "validator")):
            _, body = request(dev, ep_in, ep_out, 0xE4, struct.pack("<II", slot, 0))
            st = body[0] if body else None
            typ = struct.unpack("<I", body[1:5])[0] if len(body) >= 9 else None
            n = struct.unpack("<I", body[5:9])[0] if len(body) >= 9 else None
            ok = st == 0 and typ == slot and n == need_len
            problems += not ok
            detail = f"status {st:#04x}" + (f", type {typ:#010x}, length {n}" if typ is not None else ", no data")
            print(f"{'OK  ' if ok else 'FAIL'}  slot {slot:#010x} ({label}): {detail}"
                  + ("" if ok else f"  (driver needs status 0x00, length {need_len})"))
    finally:
        usb.util.release_interface(dev, intf.bInterfaceNumber)
        usb.util.dispose_resources(dev)
    print("\nResult:", "reader state looks compatible with the driver" if problems == 0 else
          f"{problems} problem(s) - see 'Troubleshooting' in the README")
    return 0 if problems == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
