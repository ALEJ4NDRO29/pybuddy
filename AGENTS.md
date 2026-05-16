# pybuddy2

Python library + daemon to control an i-Buddy USB device (0x1130:0x0005).

## Entrypoints

- `pybuddylib.py` — library usable as `from pybuddylib import iBuddyDevice`
- `src/pybuddy-daemon.py` — UDP daemon (Unix-only, uses `fork()`/`pwd`, broken on Windows)
- Running `pybuddylib.py` directly runs a demo sequence

## Windows prerequisites (non-negotiable)

1. WinUSB driver installed via **Zadig** (replace HID driver) for the device
2. `libusb-1.0.dll` on PATH (e.g. from Steam dir or libusb releases)
3. Python 3.10+ with `pip install pyusb`

The library hacks PATH at import time to find the DLL; if that fails, `import usb` will see zero devices.

## Device PID

- Real i-Buddy is PID 0x0005
- Old code had 0x0001 (pybuddylib) or 0x0002 (daemon config) — **wrong**
- The config file `src/pybuddy.cfg` also has the stale `usbproduct: 0001`

## Protocol (control transfers)

Each command sends two 8-byte HID output reports via control endpoint 0
(`bmRequestType=0x21, bRequest=0x09, wValue=0x02, wIndex=0x01`):

1. SETUP = `[0x22, 0x09, 0x00, 0x02, 0x01, 0x00, 0x00, 0x00]`
2. MESS + cmd = `[0x55, 0x53, 0x42, 0x43, 0x00, 0x40, 0x02, CMD]`
   (prefix `USBC\x00\x40\x02`)

The command byte uses **inverted bit logic**: `0` = feature ON, `1` = OFF.
- Bit 4-6: head RGB (R=4, G=5, B=6)
- Bit 7: heart
- Bits 0-1: swivel (left=0, right=1)
- Bits 2-3: wings (up=3, down=2)
- 0xFF = everything off/centered

## No build / test infra

- No `pyproject.toml`, `setup.py`, or lockfiles
- No test runner, no CI, no linter/formatter config
- Validate by running `python pybuddylib.py` with the i-Buddy connected

## Outdated / broken files

- `contrib/usbenum.py` — Python 2 syntax (`print` statement), not fixed
- `src/pybuddy-daemon.py` — uses `ConfigParser` (py2 name),
  `os.fork()`, `pwd.getpwnam()`, `os.setsid()`. Will not run on Windows
