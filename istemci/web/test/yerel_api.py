"""Yalnız sınama: gerçek PostgreSQL kapılarına yerel HTTP/Auth taşıması.

Ürün arayüzünün taşımasını sınar. Canlı Supabase'e bağlanmaz. Kullanıcılar ve
şifreler yalnız test sunucusunda üretilir; bu dosya web derlemesine girmez.
"""
import base64
from datetime import date, timedelta
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from urllib.parse import urlsplit, unquote
import secrets
import struct
import sys
import threading
import time

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from urun.kur import kur
from test.oynatici.urun_surucu import UrunSurucu, json_yaz


class Database:
    def __init__(self,empty=False):
        self.empty=empty
        self.name = 'irp_web_t20_test_' + str(os.getpid())
        self.port = int(os.environ.get('IRP_WEB_TEST_PORT','5433'))
        assert 1024 <= self.port < 65536
        self.dsn = f'postgresql://postgres@localhost:{self.port}/' + self.name
        with psycopg.connect(f'postgresql://postgres@localhost:{self.port}/postgres', autocommit=True) as conn:
            conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(self.name)))
        try:
            kur(self.dsn, test=True)
        except Exception:
            self.close()
            raise
        from urun.veri.canli_veri import uret
        if empty:
            from urun.veri.senaryo1 import uret
        from test.oynatici.akis import yurut
        print('Yerel web sınaması: örnek firma hazırlanıyor.', flush=True)
        fixture_day=date.today()
        if not empty:
            while fixture_day.weekday()>4:
                fixture_day-=timedelta(days=1)
        _, producer, data = uret(fixture_day)
        if not empty:data = producer.girdi(fixture_day)
        driver = self.driver()
        result = yurut(data, driver)
        errors = [x for x in result.cikti['depolar'][0]['cevaplar'] if 'hata_turu' in x or isinstance(x.get('deger'), dict) and x['deger'].get('sonuc') not in (None, 'BASARILI')]
        assert not errors, 'Yerel örnek firma kabul edilemeyen adım içeriyor: ' + str(errors[:2])
        driver._cagir('SELECT test.saat_birak()', kontrol=True)
        driver._cagir('SELECT motor.saat_isi()', kontrol=True)
        driver._cagir("INSERT INTO irp.sozluk(ad,hal) VALUES('olay_akisi_acik','true') ON CONFLICT(ad) DO UPDATE SET hal='true'",kontrol=True)
        driver.kapat()
        self.calls = []
        self.events = []
        self.errors = []
        print('Yerel web sınaması: gerçek motor ve örnek firma hazır.', flush=True)
        for person in ['K001', 'K009', 'K041']:
            context = self.rpc(person, 'oku', {'veri': 'WEB_BAGLAM', 'hedef': None, 'g': {}})
            assert isinstance(context.get('deger'), dict), context
        try:
            self.rpc('K017', 'oku', {'veri': 'WEB_FIRMA', 'hedef': None, 'g': {}})
            raise AssertionError('Çalışan firma yetkilerini okuyabildi')
        except PermissionError:
            pass

    def driver(self):
        return UrunSurucu(baglanti_fabrikasi=lambda: psycopg.connect(self.dsn, autocommit=True))

    def rpc(self, person, name, params):
        queries = {
            'islem_sonucu': ('SELECT public.islem_sonucu(%s)', (params.get('olay_kimligi'),)),
            'modul_oturum': ('SELECT public.modul_oturum(%s)', (params.get('modul'),)),
            'oku': ('SELECT public.oku(%s,%s,%s::jsonb)', (params.get('veri'), params.get('hedef'), json_yaz(params.get('g', {})))),
            'simdi': ('SELECT public.simdi()', ()),
            'cihaz_kaydol': ('SELECT public.cihaz_kaydol(%s)', (params.get('cihaz'),)),
            'cihaz_esitle': ('SELECT public.cihaz_esitle(%s)', (params.get('cihaz'),)),
            'olay_ekle': ('SELECT public.olay_ekle(%s::jsonb,%s::jsonb)', (json_yaz(params.get('olay')), None if params.get('hassas_ek') is None else json_yaz(params['hassas_ek']))),
            'olay_akisi': ('SELECT public.olay_akisi(%s,%s)', (params.get('sonra', 0), params.get('adet', 200))),
        }
        if name not in queries:
            raise ValueError('Tanımsız test kapısı')
        driver = self.driver()
        try:
            query, args = queries[name]
            return driver._cagir(query, args, kisi=person)
        finally:
            driver.kapat()

    def tick(self):
        driver=self.driver()
        try:
            driver._cagir('SELECT motor.saat_isi()',kontrol=True)
        finally:
            driver.kapat()

    def close(self):
        with psycopg.connect(f'postgresql://postgres@localhost:{self.port}/postgres', autocommit=True) as conn:
            conn.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(self.name)))


ROLES = {'K001': 'Yetkili', 'K004': 'Planlama Yöneticisi', 'K006': 'Satın Alma Uzmanı',
         'K009': 'İmalat Ekip Lideri', 'K017': 'Atölye Çalışanı 1', 'K023': 'Atölye Çalışanı 2',
         'K031': 'Saha Çalışanı', 'K012': 'Tasarım Yöneticisi', 'K041': 'Tasarımcı'}


class ApiServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 64

    def __init__(self, database, directory, jwt=False):
        self.database = database
        self.directory = directory
        self.jwt = jwt
        if database.empty:
            from urun.veri.senaryo1 import KISILER
            self.roles={p[0]:p[1] for p in KISILER}
        else:self.roles=ROLES
        self.peers = []
        self.uploads = {}
        self.signed_files = {}
        super().__init__(('127.0.0.1', 0), ApiHandler)

    def signal(self):
        for peer in list(self.peers):
            try:
                for topic in list(peer.topics):
                    peer.send({'topic': topic, 'event': 'postgres_changes', 'payload': {'data': {'record': {}}}, 'ref': None})
            except OSError:
                pass


class ApiHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(args[2].directory), **kwargs)

    def log_message(self, *_):
        pass

    def end_headers(self):
        origin=self.headers.get('Origin','')
        if urlsplit(origin).hostname in ('localhost','127.0.0.1'):
            self.send_header('Access-Control-Allow-Origin',origin)
            self.send_header('Access-Control-Allow-Headers','authorization,apikey,content-type,x-client-info')
            self.send_header('Access-Control-Allow-Methods','GET,POST,PUT,OPTIONS')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204);self.end_headers()

    def respond(self, data, status=200):
        data = json_yaz(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(data)))
        try:
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        if self.path.startswith('/storage/v1/object/test-signed/'):
            path = self.server.signed_files.get(self.path)
            data = self.server.uploads.get(path)
            if data is None:
                return self.respond({'message': 'Dosya bulunamadı'}, 404)
            self.send_response(200)
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if self.path == '/irp/moduller':
            return self.respond({'moduller': []})
        if self.path.startswith('/ayar.json'):
            return self.respond({'bulut': 'SUPABASE', 'supabase_url': 'http://127.0.0.1:' + str(self.server.server_port),
                                 'supabase_anon': 'sb_publishable_local_test', 'gosteri_kisileri': [
                                     {'kod': k, 'etiket': v, 'sifre': 'local-test-only', 'yer': 'ikisi'} for k, v in self.server.roles.items() if not self.server.database.empty or k in ('K001','K004','K009','K041')], 'senaryo':'senaryo1-local' if self.server.database.empty else None})
        if self.path.startswith('/realtime/v1/websocket'):
            return self.socket_loop()
        return super().do_GET()

    def do_PUT(self):
        if self.path.startswith('/auth/v1/user'):
            return self.respond({'id': 'local-user'})
        return self.respond({'message': 'Tanımsız test yolu'}, 404)

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
        if self.path.startswith('/storage/v1/object/sign/kanitlar/'):
            # Depo yalnız yerel taşıma taklididir; görünürlüğü gerçek SQL sınar.
            path = self.path.replace('/object/sign/', '/object/', 1)
            suffix = unquote(path.split('/kanitlar/', 1)[1])
            event, filename = suffix.split('/', 1)
            identifier = 'F-' + event + '/' + filename.split('-', 1)[0]
            person = self.headers.get('Authorization', '').removeprefix('Bearer LOCAL.')
            try:
                visible = self.server.database.rpc(person, 'oku', {'veri':'DOSYA','hedef':identifier,'g':{}})['deger']
            except PermissionError:
                return self.respond({'message':'IRP|YETKI|Dosya'}, 403)
            if not visible:
                return self.respond({'message':'IRP|YETKI|Dosya'}, 403)
            if path not in self.server.uploads:
                return self.respond({'message':'Dosya aktarımı bekleniyor'}, 404)
            url = '/object/test-signed/' + secrets.token_urlsafe(24)
            self.server.signed_files['/storage/v1' + url] = path
            return self.respond({'signedURL':url})
        if self.path.startswith('/storage/v1/object/'):
            self.server.uploads[self.path] = body
            return self.respond({'Key': self.path})
        params = json.loads(body or b'{}')
        if self.path.startswith('/auth/v1/token'):
            person = (params.get('email', '').split('@')[0] or params.get('refresh_token', 'LOCAL.K001').split('.')[-1]).upper()
            if person not in self.server.roles:
                return self.respond({'message': 'Giriş yapılamadı'}, 401)
            token = 'LOCAL.' + person
            if self.server.jwt:
                # Yalnız yerel taşıma testi. Üründe imzayı Supabase doğrular.
                payload = base64.urlsafe_b64encode(json.dumps({'email': person.lower()+'@calisan.irp',
                    'role': 'authenticated', 'exp': int(time.time())+3600}).encode()).decode().rstrip('=')
                token = 'eyJhbGciOiJURVNUIiJ9.' + payload + '.local-test'
            return self.respond({'access_token': token, 'refresh_token': 'LOCAL.' + person, 'expires_in': 3600})
        if self.path.startswith('/rest/v1/rpc/'):
            name = self.path.rsplit('/', 1)[-1]
            authorization = self.headers.get('Authorization', '').removeprefix('Bearer ')
            person = authorization.split('.')[-1]
            if self.server.jwt and authorization.count('.') == 2:
                try:
                    payload = authorization.split('.')[1]
                    person = json.loads(base64.urlsafe_b64decode(payload+'='*(-len(payload)%4)))['email'].split('@')[0].upper()
                except (ValueError, KeyError):
                    person = ''
            if name == 'simdi':
                return self.respond(self.server.database.rpc('K001', name, params))
            if person not in self.server.roles:
                return self.respond({'message': 'Oturum'}, 401)
            self.server.database.calls.append((person, name, params.get('veri')))
            try:
                value = self.server.database.rpc(person, name, params)
                if name == 'olay_ekle':
                    self.server.database.events.append((person,params['olay']['eylem_kodu'],value))
                    print('Yerel olay:',person,params['olay']['eylem_kodu'],value,flush=True)
                    if value.get('sonuc') == 'BASARILI':
                        threading.Thread(target=self.server.database.tick,daemon=True).start()
                self.respond(value)
                if name == 'olay_ekle':
                    self.server.signal()
                return
            except Exception as error:
                message = str(error)
                if isinstance(error, PermissionError):
                    message = 'IRP|YETKI|' + message
                elif isinstance(error, ValueError):
                    message = 'IRP|BICIM|' + message
                self.server.database.errors.append((person, name, params.get('veri'), type(error).__name__, message))
                print('Yerel kapı:', person, name, params.get('veri', ''), type(error).__name__, message[:350], flush=True)
                return self.respond({'message': message}, 400)
        return self.respond({'message': 'Tanımsız test yolu'}, 404)

    def socket_loop(self):
        self.send_response(101)
        self.send_header('Upgrade', 'websocket')
        self.send_header('Connection', 'Upgrade')
        key = self.headers.get('Sec-WebSocket-Key', '')
        self.send_header('Sec-WebSocket-Accept', base64.b64encode(hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode())
        self.end_headers()
        peer = SocketPeer(self)
        self.server.peers.append(peer)
        try:
            peer.loop()
        except (OSError, ValueError, EOFError):
            pass
        finally:
            self.server.peers.remove(peer)


class SocketPeer:
    def __init__(self, handler):
        self.handler = handler
        self.topics = []
        self.lock = threading.Lock()

    def read(self, length):
        data = self.handler.rfile.read(length)
        if len(data) != length:
            raise EOFError()
        return data

    def send(self, data):
        data = json.dumps(data).encode()
        frame = b'\x81' + (bytes([len(data)]) if len(data) < 126 else b'\x7e' + struct.pack('!H', len(data))) + data
        with self.lock:
            self.handler.connection.sendall(frame)

    def loop(self):
        while True:
            first, second = self.read(2)
            if first & 15 == 8:
                return
            length = second & 127
            if length == 126:
                length = struct.unpack('!H', self.read(2))[0]
            elif length == 127:
                length = struct.unpack('!Q', self.read(8))[0]
            mask = self.read(4) if second & 128 else None
            data = self.read(length)
            if mask:
                data = bytes(x ^ mask[i % 4] for i, x in enumerate(data))
            message = json.loads(data)
            if message['event'] == 'phx_join':
                self.topics.append(message['topic'])
            self.send({'topic': message['topic'], 'event': 'phx_reply', 'payload': {'status': 'ok', 'response': {}}, 'ref': message.get('ref'), 'join_ref': message.get('join_ref')})
