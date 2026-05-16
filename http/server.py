#!/usr/bin/env python
"""HTTP server for i-Buddy remote control. Zero external dependencies."""

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from time import sleep
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pybuddylib import iBuddyDevice, NoBuddyException

HOST = os.environ.get('IBUDDY_HOST', '0.0.0.0')
PORT = int(os.environ.get('IBUDDY_PORT', '8888'))

buddy = None


def get_buddy():
    global buddy
    if buddy is None:
        buddy = iBuddyDevice()
    return buddy


COLORS = {
    'red':    (1, 0, 0),
    'green':  (0, 1, 0),
    'blue':   (0, 0, 1),
    'yellow': (1, 1, 0),
    'purple': (1, 0, 1),
    'cyan':   (0, 1, 1),
    'white':  (1, 1, 1),
    'ltblue': (0, 1, 1),
    'orange': (1, 1, 0),
    'pink':   (1, 0, 1),
}


HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>i-Buddy Control</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #111; color: #eee; max-width: 600px; margin: 20px auto; padding: 0 16px; }
  h1 { text-align: center; margin: 20px 0; }
  h1 img { vertical-align: middle; }
  section { background: #1a1a2e; border-radius: 12px; padding: 16px; margin-bottom: 16px; }
  h2 { font-size: 1rem; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; }
  .grid { display: flex; flex-wrap: wrap; gap: 8px; }
  button { flex: 1; min-width: 60px; padding: 10px; border: none; border-radius: 8px; font-size: 0.85rem; cursor: pointer; transition: 0.15s; background: #333; color: #eee; }
  button:hover { filter: brightness(1.3); transform: scale(1.05); }
  button:active { transform: scale(0.95); }
  .color-1 { background: #e74c3c; } .color-2 { background: #2ecc71; } .color-3 { background: #3498db; }
  .color-4 { background: #f1c40f; color: #111; } .color-5 { background: #9b59b6; } .color-6 { background: #1abc9c; }
  .color-7 { background: #ecf0f1; color: #111; }
  .action { background: #2c3e50; } .danger { background: #c0392b; }
  #status { text-align: center; margin: 10px 0; color: #888; font-size: 0.9rem; }
  pre { background: #0003; padding: 8px; border-radius: 6px; overflow-x: auto; }
</style>
</head>
<body>
<h1>&#x1F47C; i-Buddy</h1>
<div id="status">Conectado</div>

<section>
<h2>Colores</h2>
<div class="grid">
  <button class="color-1" onclick="api('/api/color','red')">Rojo</button>
  <button class="color-2" onclick="api('/api/color','green')">Verde</button>
  <button class="color-3" onclick="api('/api/color','blue')">Azul</button>
  <button class="color-4" onclick="api('/api/color','yellow')">Amarillo</button>
  <button class="color-5" onclick="api('/api/color','purple')">Purpura</button>
  <button class="color-6" onclick="api('/api/color','cyan')">Cyan</button>
  <button class="color-7" onclick="api('/api/color','white')">Blanco</button>
</div>
</section>

<section>
<h2>Movimientos</h2>
<div class="grid">
  <button class="action" onclick="api('/api/flap')">Aletear</button>
  <button class="action" onclick="api('/api/wiggle')">Girar</button>
  <button class="action" onclick="api('/api/heartbeat')">Latido</button>
  <button class="action" onclick="api('/api/party')">Fiesta</button>
</div>
</section>

<section>
<h2>Partes</h2>
<div class="grid">
  <button class="action" onclick="api('/api/heart','on')">Corazon ON</button>
  <button class="action" onclick="api('/api/heart','off')">Corazon OFF</button>
  <button class="action" onclick="api('/api/wing','up')">Alas arriba</button>
  <button class="action" onclick="api('/api/wing','down')">Alas abajo</button>
  <button class="action" onclick="api('/api/swivel','left')">Giro izq</button>
  <button class="action" onclick="api('/api/swivel','right')">Giro der</button>
</div>
</section>

<section>
<h2>Extras</h2>
<div class="grid">
  <button class="action" onclick="api('/api/demo')">Demo completa</button>
  <button class="danger" onclick="api('/api/reset')">RESET</button>
</div>
</section>

<script>
async function api(path, param) {
  const url = param ? path + '/' + param : path;
  document.getElementById('status').textContent = 'Enviando...';
  try {
    const r = await fetch(url);
    const j = await r.json();
    document.getElementById('status').textContent = j.status || 'OK';
  } catch(e) {
    document.getElementById('status').textContent = 'Error: ' + e.message;
  }
}
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):

    def _json(self, data, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _html(self, content, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(content.encode())

    def _error(self, msg, code=400):
        self._json({'status': 'error', 'message': msg}, code)

    def _ok(self, msg='ok'):
        self._json({'status': msg})

    def log_message(self, fmt, *args):
        pass  # quiet

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')
        parts = path.split('/')[1:]

        if path == '' or path == '/':
            return self._html(HTML)

        try:
            b = get_buddy()
        except NoBuddyException:
            return self._error('i-Buddy no encontrado. Conectalo e instala WinUSB via Zadig.', 503)

        try:
            # --- /api/color/<name> ---
            if len(parts) >= 3 and parts[:2] == ['api', 'color']:
                name = parts[2].lower()
                rgb = COLORS.get(name)
                if not rgb:
                    return self._error('Color no valido. Usa: ' + ','.join(COLORS.keys()))
                b.doColorName(rgb, 0.1)
                return self._ok('color ' + name)

            # --- /api/heart/<on|off> ---
            if len(parts) >= 3 and parts[:2] == ['api', 'heart']:
                state = parts[2] == 'on'
                b.setHeart(state)
                b.doCmd(0.1)
                return self._ok('heart ' + ('on' if state else 'off'))

            # --- /api/wing/<up|down> ---
            if len(parts) >= 3 and parts[:2] == ['api', 'wing']:
                dir = iBuddyDevice.UP if parts[2] == 'up' else iBuddyDevice.DOWN
                b.setWing(dir)
                b.doCmd(0.1)
                return self._ok('wing ' + parts[2])

            # --- /api/swivel/<left|right> ---
            if len(parts) >= 3 and parts[:2] == ['api', 'swivel']:
                dir = iBuddyDevice.LEFT if parts[2] == 'left' else iBuddyDevice.RIGHT
                b.setSwivel(dir)
                b.doCmd(0.1)
                return self._ok('swivel ' + parts[2])

            # --- /api/flap ---
            if parts == ['api', 'flap']:
                qs = parse_qs(parsed.query)
                times = int(qs.get('times', [3])[0])
                speed = float(qs.get('speed', [0.2])[0])
                b.doFlap(times, speed)
                return self._ok('flap')

            # --- /api/wiggle ---
            if parts == ['api', 'wiggle']:
                qs = parse_qs(parsed.query)
                times = int(qs.get('times', [3])[0])
                speed = float(qs.get('speed', [0.2])[0])
                b.doWiggle(times, speed)
                return self._ok('wiggle')

            # --- /api/heartbeat ---
            if parts == ['api', 'heartbeat']:
                qs = parse_qs(parsed.query)
                times = int(qs.get('times', [3])[0])
                speed = float(qs.get('speed', [0.3])[0])
                b.doHeartbeat(times, speed)
                return self._ok('heartbeat')

            # --- /api/party ---
            if parts == ['api', 'party']:
                for name, rgb in [('red',(1,0,0)),('green',(0,1,0)),('blue',(0,0,1)),
                                   ('yellow',(1,1,0)),('purple',(1,0,1)),('cyan',(0,1,1)),('white',(1,1,1))]:
                    b.doColorName(rgb, 0.2)
                    sleep(0.1)
                b.doFlap(2, 0.15)
                sleep(0.2)
                b.doWiggle(2, 0.15)
                sleep(0.2)
                b.doHeartbeat(3, 0.2)
                return self._ok('party!')

            # --- /api/demo ---
            if parts == ['api', 'demo']:
                b.doColorName(iBuddyDevice.PURPLE, 0.5)
                b.doColorName(iBuddyDevice.BLUE, 0.5)
                b.doColorName(iBuddyDevice.LTBLUE, 0.5)
                b.doColorName(iBuddyDevice.YELLOW, 0.5)
                b.doColorName(iBuddyDevice.GREEN, 0.5)
                b.doColorName(iBuddyDevice.RED, 0.5)
                b.doColorName(iBuddyDevice.WHITE, 0.5)
                b.doFlap()
                sleep(1)
                b.doWiggle()
                sleep(1)
                b.doHeartbeat()
                sleep(1)
                b.doReset()
                return self._ok('demo completo')

            # --- /api/reset ---
            if parts == ['api', 'reset']:
                b.doReset()
                return self._ok('reset')

            # --- /api/status ---
            if parts == ['api', 'status']:
                return self._json({
                    'status': 'ok',
                    'colors': list(COLORS.keys()),
                })

            return self._error('Ruta no valida: ' + self.path, 404)

        except Exception as e:
            return self._error(str(e), 500)

    do_POST = do_GET


def main():
    print(f'i-Buddy HTTP server on http://{HOST}:{PORT}')
    print('Open the URL in a browser to control the device.')
    server = HTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nShutting down.')
        server.server_close()


if __name__ == '__main__':
    main()
