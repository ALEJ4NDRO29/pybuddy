#!/usr/bin/env python
"""HTTP server for i-Buddy remote control. Zero external dependencies."""

import json
import os
import sys
import time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from time import sleep
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pybuddylib import iBuddyDevice, NoBuddyException

HOST = os.environ.get('IBUDDY_HOST', '0.0.0.0')
PORT = int(os.environ.get('IBUDDY_PORT', '8888'))
STATIC_DIR = Path(__file__).resolve().parent

COLORS = {
    'red':    (1, 0, 0),
    'green':  (0, 1, 0),
    'blue':   (0, 0, 1),
    'yellow': (1, 1, 0),
    'purple': (1, 0, 1),
    'cyan':   (0, 1, 1),
    'white':  (1, 1, 1),
}

buddy = None
buddy_ok = False


def get_buddy():
    global buddy, buddy_ok
    if buddy_ok:
        return buddy
    t = time.time()
    try:
        print("Trying to connect to i-Buddy...")
        buddy = iBuddyDevice()
        buddy_ok = True
        print(f'device connected in {(time.time() - t) * 1000:.0f}ms')
        return buddy
    except NoBuddyException:
        raise
    except Exception as e:
        print(f'connection failed: {e}')
        raise


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def _send_json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, content, code=200):
        body = content.encode()
        self.send_response(code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _ok(self, msg):
        self._send_json({'status': msg})

    def _error(self, msg, code=400):
        self._send_json({'error': msg}, code)

    def log_message(self, fmt, *args):
        pass

    def _log_action(self, action, detail=''):
        msg = action + ('  ' + detail if detail else '')
        print(f'>>> {msg}')

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/') or '/'
        parts = path.split('/')[1:]

        # --- serve static files ---
        if path == '/':
            index = STATIC_DIR / 'index.html'
            if index.exists():
                return self._send_html(index.read_text(encoding='utf-8'))
            return self._error('index.html not found', 404)

        # --- API ---
        if not parts or parts[0] != 'api':
            return self._error('not found', 404)

        try:
            ibuddy = get_buddy()
        except NoBuddyException:
            return self._error(
                'i-Buddy not found. Connect the device and install WinUSB via Zadig.', 503)
        except Exception as e:
            return self._error(f'device error: {e}', 503)

        try:
            match parts[1:]:
                case ['color', name]:
                    rgb = COLORS.get(name.lower())
                    if not rgb:
                        return self._error(f'unknown color "{name}"')
                    ibuddy.doColorName(rgb, 0.1)
                    self._log_action('color', name)
                    return self._ok(f'color {name}')

                case ['heart', state] if state in ('on', 'off'):
                    ibuddy.setHeart(state == 'on')
                    ibuddy.doCmd(0.1)
                    self._log_action('heart', state)
                    return self._ok(f'heart {state}')

                case ['wing', direction] if direction in ('up', 'down', 'center'):
                    if direction == 'center':
                        ibuddy.setReverseBitValue(3, 0)
                        ibuddy.setReverseBitValue(2, 0)
                    else:
                        ibuddy.setWing(iBuddyDevice.UP if direction == 'up' else iBuddyDevice.DOWN)
                    ibuddy.doCmd(0.1)
                    self._log_action('wing', direction)
                    return self._ok(f'wing {direction}')

                case ['swivel', direction] if direction in ('left', 'right', 'center'):
                    if direction == 'center':
                        ibuddy.setReverseBitValue(1, 0)
                        ibuddy.setReverseBitValue(0, 0)
                    else:
                        ibuddy.setSwivel(iBuddyDevice.LEFT if direction == 'left' else iBuddyDevice.RIGHT)
                    ibuddy.doCmd(0.1)
                    self._log_action('swivel', direction)
                    return self._ok(f'swivel {direction}')

                case ['flap']:
                    ibuddy.doFlap()
                    self._log_action('flap')
                    return self._ok('flap')

                case ['flap', times_str]:
                    ibuddy.doFlap(int(times_str))
                    self._log_action('flap', times_str)
                    return self._ok('flap')

                case ['flap', times_str, speed_str]:
                    ibuddy.doFlap(int(times_str), float(speed_str))
                    self._log_action('flap', f'{times_str}x {speed_str}s')
                    return self._ok('flap')

                case ['wiggle']:
                    ibuddy.doWiggle()
                    self._log_action('wiggle')
                    return self._ok('wiggle')

                case ['wiggle', times_str]:
                    ibuddy.doWiggle(int(times_str))
                    self._log_action('wiggle', times_str)
                    return self._ok('wiggle')

                case ['wiggle', times_str, speed_str]:
                    ibuddy.doWiggle(int(times_str), float(speed_str))
                    self._log_action('wiggle', f'{times_str}x {speed_str}s')
                    return self._ok('wiggle')

                case ['heartbeat']:
                    ibuddy.doHeartbeat()
                    self._log_action('heartbeat')
                    return self._ok('heartbeat')

                case ['heartbeat', times_str]:
                    ibuddy.doHeartbeat(int(times_str))
                    self._log_action('heartbeat', times_str)
                    return self._ok('heartbeat')

                case ['heartbeat', times_str, speed_str]:
                    ibuddy.doHeartbeat(int(times_str), float(speed_str))
                    self._log_action('heartbeat', f'{times_str}x {speed_str}s')
                    return self._ok('heartbeat')

                case ['party']:
                    self._log_action('party')
                    for rgb in [(1,0,0), (0,1,0), (0,0,1), (1,1,0), (1,0,1), (0,1,1), (1,1,1)]:
                        ibuddy.doColorName(rgb, 0.15)
                    ibuddy.doFlap(2, 0.15)
                    sleep(0.2)
                    ibuddy.doWiggle(2, 0.15)
                    sleep(0.2)
                    ibuddy.doHeartbeat(3, 0.15)
                    return self._ok('party!')

                case ['demo']:
                    self._log_action('demo')
                    for c in [iBuddyDevice.PURPLE, iBuddyDevice.BLUE, iBuddyDevice.LTBLUE,
                              iBuddyDevice.YELLOW, iBuddyDevice.GREEN, iBuddyDevice.RED,
                              iBuddyDevice.WHITE]:
                        ibuddy.doColorName(c, 0.5)
                    ibuddy.doFlap()
                    sleep(1)
                    ibuddy.doWiggle()
                    sleep(1)
                    ibuddy.doHeartbeat()
                    sleep(1)
                    ibuddy.doReset()
                    return self._ok('demo complete')

                case ['reset']:
                    self._log_action('reset')
                    ibuddy.doReset()
                    return self._ok('reset')

                case ['status']:
                    return self._send_json({
                        'device': 'i-Buddy',
                        'connected': True,
                        'colors': list(COLORS.keys()),
                    })

                case _:
                    return self._error(f'unknown endpoint: /api/{" ".join(parts[1:])}', 404)

        except Exception as e:
            print(f'error: {e}')
            return self._error(str(e), 500)

    do_POST = do_GET


def main():
    print(f'  i-Buddy HTTP server starting on http://{HOST}:{PORT}')
    print(f'  Open http://localhost:{PORT} in your browser')
    print()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.timeout = 0.5
    get_buddy()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
        print('shutting down')
        server.server_close()


if __name__ == '__main__':
    main()
