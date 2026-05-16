# i-Buddy Protocol

## Hardware

- Chip: Tenx Technology USB controller (VID 0x1130)
- Device: PID 0x0005 (old software references 0x0001 or 0x0002 — wrong)
- Class: HID (Human Interface Device)
- Endpoints: only **1 Interrupt IN** (0x82), **no Interrupt OUT**
- Communication: exclusively via **control endpoint 0**

Because there's no Interrupt OUT endpoint, `WriteFile` / `send_output_report` cannot reach the device.
Commands must go through the control endpoint via `SET_REPORT`.

---

## Control transfer

Each command is two consecutive control transfers (`bmRequestType=0x21, bRequest=0x09`):

| Parameter     | Value   | Meaning                          |
| ------------- | ------- | -------------------------------- |
| bmRequestType | 0x21    | Host-to-Device, Class, Interface |
| bRequest      | 0x09    | SET_REPORT                       |
| wValue        | 0x02    | (as old pyusb had it)            |
| wIndex        | 0x01    | Interface 1                      |
| Data          | 8 bytes | see below                        |

### 1. SETUP (8 bytes, sent first)

```
0x22 0x09 0x00 0x02 0x01 0x00 0x00 0x00
```

Purpose unknown — possibly initializes the device state machine before accepting
a command. Must precede every command, even repeated identical ones.

### 2. MESS + command (8 bytes)

```
0x55 0x53 0x42 0x43  0x00  0x40  0x02  0xNN
 U    S    B    C     \x00  \x40  \x02   CMD
```

- `USBC` is an ASCII prefix, the vendor protocol identifier for Tenx Technology.
- Byte 5–7 (`\x00\x40\x02`) are fixed header fields, meaning unknown.
- `0xNN` is the command byte (see below).

---

## Command byte layout (inverted bit logic)

**Inverted:** `0` = feature ON, `1` = feature OFF.

A command of `0xFF` (all bits set) disables everything: lights off, wings closed,
body centered.

```
Bit  position:  7    6    5    4    3    2    1    0
               +----+----+----+----+----+----+----+----+
               | HRT|  B |  G |  R | WU | WD | SR | SL |
               +----+----+----+----+----+----+----+----+
ON (0 = active):  0    0    0    0    0    0    0    0
OFF (1 = idle):   1    1    1    1    1    1    1    1
```

| Bit(s) | Feature       | Notes                   |
| ------ | ------------- | ----------------------- |
| 0      | Swivel left   | `0` = turn left         |
| 1      | Swivel right  | `0` = turn right        |
| 0+1=00 | Swivel center | both 1 = centered       |
| 2      | Wings down    | `0` = wings down        |
| 3      | Wings up      | `0` = wings up          |
| 2+3=11 | Wings neutral | both 1 = closed/neutral |
| 4      | Red LED       | `0` = on                |
| 5      | Green LED     | `0` = on                |
| 6      | Blue LED      | `0` = on                |
| 7      | Heart LED     | `0` = on                |

### Examples

| Command | Binary      | Effect                 |
| ------- | ----------- | ---------------------- |
| `0xFF`  | `1111 1111` | Reset (everything off) |
| `0xEF`  | `1110 1111` | Red ON                 |
| `0xDF`  | `1101 1111` | Green ON               |
| `0xBF`  | `1011 1111` | Blue ON                |
| `0x8F`  | `1000 1111` | White (R+G+B) ON       |
| `0x7F`  | `0111 1111` | Heart ON               |
| `0xF7`  | `1111 0111` | Wings UP               |
| `0xFB`  | `1111 1011` | Wings DOWN             |
| `0xFE`  | `1111 1110` | Swivel LEFT            |
| `0xFD`  | `1111 1101` | Swivel RIGHT           |

### Computing the command byte

```python
def make_cmd(red, green, blue, heart, wing_up, wing_down, swivel_left, swivel_right):
    """Each param: True = ON, False = OFF"""
    cmd = 0xFF
    if red:          cmd &= ~(1 << 4)
    if green:        cmd &= ~(1 << 5)
    if blue:         cmd &= ~(1 << 6)
    if heart:        cmd &= ~(1 << 7)
    if wing_up:      cmd &= ~(1 << 3)
    if wing_down:    cmd &= ~(1 << 2)
    if swivel_left:  cmd &= ~(1 << 0)
    if swivel_right: cmd &= ~(1 << 1)
    return cmd
```

---

## Full send sequence (Python/pyusb)

```python
import usb.core

dev = usb.core.find(idVendor=0x1130, idProduct=0x0005)
dev.set_configuration()

SETUP = bytes([0x22, 0x09, 0x00, 0x02, 0x01, 0x00, 0x00, 0x00])
MESS  = [0x55, 0x53, 0x42, 0x43, 0x00, 0x40, 0x02]

def send(cmd_byte):
    dev.ctrl_transfer(0x21, 0x09, 0x02, 0x01, SETUP)
    sleep(0.02)
    dev.ctrl_transfer(0x21, 0x09, 0x02, 0x01, bytes(MESS + [cmd_byte]))
```

---

## Windows quirks

1. **Driver**: The HID driver must be replaced with WinUSB via **Zadig**.
   - Select `i-Buddy` (VID 1130, PID 0005), install WinUSB on both interfaces.
2. **libusb DLL**: `pyusb` needs `libusb-1.0.dll` or `libusb0.dll` on PATH.
3. **PATH workaround**: On Python 3.8+, DLL search path changed. The library
   prepends common install directories to `os.environ['PATH']` at import.
4. **pywinusb / HID API**: `HidD_SetOutputReport` returns success but the
   device does not respond — the HID driver transforms/filters the report.
   Only raw libusb control transfers work reliably.

---

## USB Descriptor (summary)

```
VID:         0x1130
PID:         0x0005
bNumConfig:  1
Interface 1: HID class
  Endpoint:  0x82 (Interrupt IN, 8 bytes)
  No OUT endpoint
```
