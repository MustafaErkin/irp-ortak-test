#!/usr/bin/env python3
"""IRP yerel web sunucusu. Hesap yönetiminde psycopg; iş motoru Supabase'tedir."""
import argparse
import base64
import getpass
import json
import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import re
import signal
import urllib.request
import urllib.error
from urllib.parse import urlparse,urlsplit

PROJECT=next((p for p in Path(__file__).resolve().parents if (p/'modul_platformu').is_dir()),None)
if PROJECT is not None:
    sys.path.insert(0,str(PROJECT))

WEB = Path(__file__).resolve().parent / 'web'


def ayar_dogrula(adres, anahtar):
    u = urlparse(adres)
    uygun = anahtar.startswith('sb_publishable_')
    if len(anahtar.split('.')) == 3:
        try:
            p = anahtar.split('.')[1]
            uygun = json.loads(base64.urlsafe_b64decode(p + '=' * (-len(p) % 4)))['role'] == 'anon'
        except (ValueError, KeyError, TypeError):
            uygun = False
    if u.scheme != 'https' or not u.hostname or not uygun or anahtar.startswith('sb_secret_'):
        raise ValueError('Proje adresi veya genel anon anahtarı geçersiz. Servis anahtarı kullanma.')


def ayar_yaz():
    if not sys.stdin.isatty():
        raise ValueError('Ayarı Terminal içinde ayar_yaz.command ile gir.')
    adres = input('Supabase proje adresi: ').strip()
    anahtar = getpass.getpass('Genel anon / publishable anahtarı (görünmez): ').strip()
    ayar_dogrula(adres, anahtar)
    if not WEB.is_dir():
        raise ValueError('web klasörü bulunamadı; dağıtım paketini bütünüyle indir.')
    gecici = WEB / '.ayar.json.tmp'
    # Geçici dosya da yalnız bu kullanıcıya açıktır. Anahtar hiçbir zaman yazdırılmaz.
    fd = os.open(gecici, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.chmod(gecici, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(dict(bulut='SUPABASE', supabase_url=adres, supabase_anon=anahtar), f)
            f.write('\n')
        os.replace(gecici, WEB / 'ayar.json')
    finally:
        if gecici.exists():
            gecici.unlink()
    print('Ayar web/ayar.json dosyasına yazıldı. Tarayıcı sayfasını yenile.')


class Isleyici(SimpleHTTPRequestHandler):
    extensions_map = dict(SimpleHTTPRequestHandler.extensions_map,
                          **{'.wasm': 'application/wasm', '.js': 'application/javascript',
                             '.json': 'application/json; charset=utf-8'})

    def do_GET(self):
        if self.modul_istegi():return
        if self.path == '/irp/durum':
            self.json_response({'surum': 'WEB-20', 'hesap_yonetimi': bool(os.environ.get('IRP_SB_TEST_SERVIS'))})
            return
        return super().do_GET()

    def do_POST(self):
        if self.modul_istegi():return
        if self.path != '/irp/hesap':
            self.send_error(404)
            return
        # Bu uç yalnız yerel sunucuda, açıkça kullanıcı jetonuyla çağrılır.
        if self.headers.get('Host') not in (f'localhost:{self.server.server_port}', f'127.0.0.1:{self.server.server_port}'):
            self.send_error(403)
            return
        origin = self.headers.get('Origin')
        if origin and origin not in (f'http://localhost:{self.server.server_port}', f'http://127.0.0.1:{self.server.server_port}'):
            self.send_error(403)
            return
        size = int(self.headers.get('Content-Length', '0'))
        if not 0 < size <= 2048:
            self.send_error(400)
            return
        try:
            body = json.loads(self.rfile.read(size))
            result = hesap_isle(self.headers.get('Authorization', ''), body)
            self.json_response(result)
        except PermissionError:
            self.json_response({'message': 'Bu işlem yalnız yetkiliye açıktır.'}, 403)
        except ValueError as error:
            self.json_response({'message': str(error)}, 400)
        except Exception:
            # Ağ/SQL hatası veya anahtar asla günlükte ya da cevapta görünmez.
            self.json_response({'message': 'Hesap işlemi tamamlanamadı. Bağlantıyı kontrol edin.'}, 503)

    def do_PUT(self):
        if not self.modul_istegi():self.send_error(404)

    def do_DELETE(self):
        if not self.modul_istegi():self.send_error(404)

    def modul_istegi(self):
        path=urlsplit(self.path).path
        if not (path.startswith('/irp/moduller') or path.startswith('/irp/cekirdek/') or path.startswith('/moduller/')):
            return False
        from modul_platformu.gecit import Hata
        platform=getattr(self.server,'platform',None)
        try:
            allowed=(f'localhost:{self.server.server_port}',f'127.0.0.1:{self.server.server_port}')
            if self.headers.get('Host') not in allowed:
                raise Hata(403,'İşlem ortak çalışma adresinden yapılmalıdır.')
            origin=self.headers.get('Origin')
            if origin and origin not in tuple('http://'+a for a in allowed):
                raise Hata(403,'İşlem ortak çalışma adresinden yapılmalıdır.')
            if platform is None:raise Hata(503,'Modül bağlantısı hazırlanıyor.')
            auth=self.headers.get('Authorization','')
            if path=='/irp/moduller' and self.command=='GET':
                self.json_response(platform.list(auth));return True
            static=re.fullmatch(r'/moduller/([A-Z][A-Z0-9_]+)/([A-Za-z0-9_/-]+\.(js|css|svg|png))',path)
            if static and self.command=='GET':
                row=platform.rows.get(static[1])
                if not row or static[1] not in platform.addresses:
                    raise Hata(404,'Çalışma alanı bulunamadı.')
                folder=(row['klasor']/'on_yuz').resolve()
                source=(folder/static[2]).resolve()
                if not folder.is_relative_to(row['klasor'].resolve()) or not source.is_relative_to(folder) or not source.is_file():
                    raise Hata(404,'Çalışma alanı dosyası bulunamadı.')
                data=source.read_bytes()
                mime={'js':'application/javascript; charset=utf-8','css':'text/css; charset=utf-8','svg':'image/svg+xml','png':'image/png'}[static[3]]
                self.send_response(200);self.send_header('Content-Type',mime)
                self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return True
            size=int(self.headers.get('Content-Length','0'))
            if not 0<=size<=2*1024*1024:raise Hata(413,'İşlem boyutu sınırı aşıldı.')
            body=self.rfile.read(size) if size else None
            rpc=re.fullmatch(r'/irp/cekirdek/([A-Z][A-Z0-9_]+)/rest/v1/rpc/([a-z_]+)',path)
            if rpc and self.command=='POST':
                value=json.loads(body or b'{}')
                if not isinstance(value,dict):raise Hata(400,'IRP|BICIM|Nesne govdesi gerekli')
                self.json_response(platform.rpc(rpc[1],rpc[2],value,auth));return True
            api=re.fullmatch(r'/irp/moduller/([A-Z][A-Z0-9_]+)(/api/.*)',path)
            if api:
                status,headers,data=platform.api(api[1],api[2]+('?' + urlsplit(self.path).query if urlsplit(self.path).query else ''),self.command,body,auth)
                if status>=500:raise Hata(503,'İşlem tamamlanamadı. Bağlantıyı kontrol edin.')
                mime=headers.get('Content-Type') or headers.get('content-type') or 'application/json; charset=utf-8'
                self.send_response(status);self.send_header('Content-Type',mime)
                self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return True
            raise Hata(404,'Çalışma alanı bulunamadı.')
        except (BrokenPipeError,ConnectionResetError):
            pass  # Profil değişiminde iptal edilmiş istek; yeniden cevap yazılmaz.
        except Hata as e:
            self.json_response({'message':e.message,'mesaj':e.message},e.status)
        except (ValueError,TypeError,KeyError):
            self.json_response({'message':'İşlem bilgileri uygun değil.','mesaj':'İşlem bilgileri uygun değil.'},400)
        except Exception:
            self.json_response({'message':'Modül bağlantısı şu an kullanılamıyor.','mesaj':'Modül bağlantısı şu an kullanılamıyor.'},503)
        return True

    def json_response(self, value, status=200):
        data = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        try:
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError,ConnectionResetError):
            pass

    def list_directory(self, path):
        self.send_error(404)
        return None

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        super().end_headers()

    def log_message(self, format, *args):
        # Anahtarlar ve adres sorguları terminal günlüğüne girmez.
        pass


def hesap_isle(authorization, body, env=None, remote=None, connector=None):
    """T3/T5 hesap açma/sıfırlama. Yetki aynı public.oku kapısıyla doğrulanır."""
    env = env or os.environ
    if not authorization.startswith('Bearer ') or len(authorization) < 12:
        raise PermissionError()
    person = body.get('kisi', '')
    password = body.get('sifre', '')
    action = body.get('islem')
    if not re.fullmatch(r'K[0-9]{3}', person) or not re.fullmatch(r'[0-9]{6}', password) or action not in ('ac', 'sifirla'):
        raise ValueError('Çalışan, işlem ve 6 rakamlı şifre gerekli.')
    url = env['IRP_SB_TEST_URL'].rstrip('/')
    def request(method, path, data=None, admin=False):
        key = env['IRP_SB_TEST_SERVIS' if admin else 'IRP_SB_TEST_ANON']
        headers = {'apikey': key, 'Content-Type': 'application/json'}
        if not admin:
            headers['Authorization'] = authorization
        elif not key.startswith('sb_secret_'):
            headers['Authorization'] = 'Bearer ' + key
        req = urllib.request.Request(url+path, method=method, headers=headers,
                                     data=None if data is None else json.dumps(data).encode())
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code in (401, 403):
                raise PermissionError() from None
            raise ValueError('Hesap işlemi kabul edilmedi. Hesabın durumunu kontrol edin.') from None
    api = remote or request
    # Servis yetkisi kullanılmadan önce gerçek kullanıcı jetonu RLS kapısından geçer.
    rows = api('POST', '/rest/v1/rpc/oku', {'veri': 'WEB_HESAPLAR', 'hedef': None, 'g': {}}, False)['deger']
    row = next((r for r in rows if r['kisi'] == person), None)
    if row is None:
        raise ValueError('Çalışan bulunamadı.')
    if action == 'ac' and row['hesap_var']:
        raise ValueError('Hesap zaten var; şifre sıfırlamayı kullanın.')
    import psycopg
    connector = connector or psycopg.connect
    with connector(env['IRP_SB_TEST_DB'], autocommit=True) as conn:
        auth_id = conn.execute('SELECT auth_kimligi FROM public.kisi_hesaplari WHERE kisi=%s', (person,)).fetchone()
        if action == 'sifirla':
            if not auth_id:
                raise ValueError('Önce giriş hesabını açın.')
            api('PUT', '/auth/v1/admin/users/'+str(auth_id[0]), {'password': password}, True)
        else:
            user = api('POST', '/auth/v1/admin/users', {'email': person.lower()+'@calisan.irp', 'password': password,
                      'email_confirm': True, 'user_metadata': {'kisi': person}}, True)
            conn.execute('INSERT INTO public.kisi_hesaplari(auth_kimligi,kisi) VALUES(%s,%s)', (user['id'], person))
    return {'ok': True}


class YerelSunucu(ThreadingHTTPServer):
    # Modül dosyaları ile çevrimdışı paket aynı anda istenirken bağlantılar bekleyebilir.
    request_queue_size = 64
    daemon_threads = True


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ayar-yaz', action='store_true')
    p.add_argument('--port', type=int, default=8080)
    args = p.parse_args()
    if sys.version_info < (3, 9):
        p.exit(1, 'Python 3.9 veya sonrası gerekli.\n')
    if args.ayar_yaz:
        try:
            ayar_yaz()
        except (ValueError, OSError, EOFError):
            p.exit(1, 'Ayar yazılamadı. Adresi, genel anahtarı ve klasör iznini kontrol et.\n')
        return
    if not (WEB / 'index.html').is_file():
        p.exit(1, 'web/index.html bulunamadı; dağıtım paketini bütünüyle indir.\n')
    try:
        sunucu = YerelSunucu(('127.0.0.1', args.port), partial(Isleyici, directory=str(WEB)))
    except OSError:
        p.exit(1, 'Sunucu açılamadı. Önceki IRP terminalini kapat veya 8080 portunu kontrol et.\n')
    platform=None
    if PROJECT is not None:
        from modul_platformu.gecit import Platform
        platform=Platform(PROJECT)
        sunucu.platform=platform
        try:platform.start(args.port)
        except Exception:
            platform.close()
            print('Modül çalışma alanı henüz hazır değil; çekirdek kullanılabilir.',flush=True)
    print('Bu terminal açık kalsın; durdurmak için Ctrl+C.', flush=True)
    print('Canlı:    http://localhost:{}/'.format(args.port), flush=True)
    print('Gösterim: http://localhost:{}/?kip=gosterim'.format(args.port), flush=True)
    def durdur(*_):
        raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM,durdur)
    try:
        sunucu.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if platform:platform.close()
        sunucu.server_close()


if __name__ == '__main__':
    main()
