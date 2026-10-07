"""Adaptador inicial Cloud API. Cola SQLite durable y un único worker."""
import hashlib
import hmac
import json
import os
import sqlite3
import time
import urllib.request
import urllib.error
from flask import Flask, request, abort
from bot import respond

DB = os.getenv('BOT_DB', 'bot.sqlite3')
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024

def connect():
    db = sqlite3.connect(DB, timeout=30)
    db.execute('CREATE TABLE IF NOT EXISTS inbox (id TEXT PRIMARY KEY, sender TEXT, body TEXT, status TEXT DEFAULT "pending", reply TEXT, next_state TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS sessions (sender TEXT PRIMARY KEY, state TEXT)')
    return db

@app.get('/webhook')
def verify():
    token = os.environ.get('VERIFY_TOKEN', '')
    if token and request.args.get('hub.mode') == 'subscribe' and hmac.compare_digest(request.args.get('hub.verify_token', ''), token):
        return request.args.get('hub.challenge', ''), 200
    abort(403)

@app.post('/webhook')
def receive():
    secret = os.environ.get('META_APP_SECRET', '')
    expected = 'sha256=' + hmac.new(secret.encode(), request.get_data(), hashlib.sha256).hexdigest()
    if not secret or not hmac.compare_digest(request.headers.get('X-Hub-Signature-256', ''), expected):
        abort(403)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        abort(400)
    with connect() as db:
        for entry in payload.get('entry', []):
            for change in entry.get('changes', []):
                value = change.get('value', {})
                if value.get('metadata', {}).get('phone_number_id') != os.environ.get('PHONE_NUMBER_ID'):
                    continue
                for msg in value.get('messages', []):
                    if msg.get('id') and msg.get('from'):
                        body = msg.get('text', {}).get('body', '') if msg.get('type') == 'text' else ''
                        db.execute('INSERT OR IGNORE INTO inbox(id,sender,body) VALUES(?,?,?)', (msg['id'], msg['from'], body[:1500]))
    return 'OK', 200

def send(to, body):
    version = os.environ['GRAPH_API_VERSION']
    phone = os.environ['PHONE_NUMBER_ID']
    # Ajuste limitado al número de prueba y destinatario verificado.
    if phone == '1399277469929282' and to == '5493782416860':
        to = '543782416860'
    payload = {'messaging_product': 'whatsapp', 'to': to, 'type': 'text', 'text': {'body': body}}
    req = urllib.request.Request(f'https://graph.facebook.com/{version}/{phone}/messages', data=json.dumps(payload).encode(), headers={'Authorization': 'Bearer ' + os.environ['WHATSAPP_ACCESS_TOKEN'], 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.status

def worker():
    # Ejecutar exactamente un worker. No registrar tokens ni cuerpos de mensajes.
    while True:
        with connect() as db:
            row = db.execute('SELECT id,sender,body,status,reply,next_state FROM inbox WHERE status IN ("pending","ready") ORDER BY rowid LIMIT 1').fetchone()
            if row:
                mid, sender, body, status, reply, next_state = row
                if status == 'pending':
                    old = db.execute('SELECT state FROM sessions WHERE sender=?', (sender,)).fetchone()
                    state, reply = respond(json.loads(old[0]) if old else {}, body)
                    next_state = json.dumps(state, ensure_ascii=False)
                    db.execute('UPDATE inbox SET status="ready",reply=?,next_state=? WHERE id=?', (reply, next_state, mid))
        if not row:
            time.sleep(1)
            continue
        try:
            if reply:
                send(sender, reply)
            with connect() as db:
                db.execute('INSERT OR REPLACE INTO sessions(sender,state) VALUES(?,?)', (sender, next_state))
                db.execute('UPDATE inbox SET status="done" WHERE id=?', (mid,))
        except urllib.error.HTTPError as exc:
            # Solo códigos numéricos: nunca registrar respuesta cruda ni credenciales.
            try:
                error = json.loads(exc.read(65536)).get('error', {})
            except (ValueError, AttributeError):
                error = {}
            code = error.get('code')
            subcode = error.get('error_subcode')
            code = code if isinstance(code, int) else 'desconocido'
            subcode = subcode if isinstance(subcode, int) else 'ninguno'
            print(f'Error Meta: HTTP={exc.code}, code={code}, subcode={subcode}; reintento pendiente.', flush=True)
            time.sleep(10)
        except KeyError as exc:
            allowed = {'GRAPH_API_VERSION', 'PHONE_NUMBER_ID', 'WHATSAPP_ACCESS_TOKEN'}
            key = exc.args[0] if exc.args and exc.args[0] in allowed else 'desconocida'
            print(f'Configuración incompleta: falta {key}; reintento pendiente.', flush=True)
            time.sleep(10)
        except Exception as exc:
            print(f'Error interno: {type(exc).__name__}; reintento pendiente.', flush=True)
            print('Error de envío: revisar conexión o configuración; reintento pendiente.', flush=True)
            time.sleep(10)

if __name__ == '__main__':
    import sys
    if '--worker' in sys.argv:
        worker()
    else:
        app.run(host='127.0.0.1', port=8000)
