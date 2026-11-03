"""Yerel sahte bulut: çekirdeğin simülatörünü Supabase'in biçimiyle HTTP'den sunar.

Python dışında bir dille yazılan modül de geliştirirken buna bağlanır; gerçek buluta geçerken yalnızca
taban adres ve anahtarlar değişir (sozlesme/01_baglanti.md › 3).

    python3 irp_sozlesme/simulator/sunucu.py --kunye kunye.json --port 8787

Uç noktalar (gerçek bulutla aynı):
    POST /auth/v1/token?grant_type=password   {"email": "k006@calisan.irp", "password": "..."}
    POST /rest/v1/rpc/simdi                   {}
    POST /rest/v1/rpc/olay_ekle               {"olay": {...}, "hassas_ek": null}        (kullanıcının anahtarı)
    POST /rest/v1/rpc/oku                     {"veri": "...", "hedef": ..., "g": {...}} (kullanıcının anahtarı)
    POST /rest/v1/rpc/servis_oku              {"veri": "...", "hedef": ..., "g": {...}} (servis anahtarı)
    POST /rest/v1/rpc/modul_bildirimi_birak   {"g": {...}}                              (servis anahtarı)
    POST /rest/v1/rpc/modul_bildirimi_kaldir  {"g": {...}}                              (servis anahtarı)
Yalnızca sahte bulutta:
    POST /sahte/saat                          {"an": "2026-10-28T10:00:00+03:00"}
    POST /sahte/senaryo                       {"ad": "KAL01"}  → kaydedilen sözleşme senaryosu
Hata: HTTP 400 {"code": "P0001", "message": "IRP|<TUR>|<neden>"}; anahtarsız ya da yanlış anahtar: 401.
"""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import socketserver
import threading
import secrets
from urllib.parse import parse_qs, urlsplit

PAKET = Path(__file__).resolve().parents[1]
if str(PAKET) not in sys.path:
    sys.path.insert(0, str(PAKET))

from baglanti.cekirdek import CekirdekHatasi, jwt_icerigi  # noqa: E402
from baglanti.surucu_simulator import SimulatorSurucu, anahtar_uret  # noqa: E402

ANON = 'sahte-anon'


class SahteBulut:
    def __init__(self, kunye, zemin=None):
        kunyeler=kunye if isinstance(kunye,list) else [kunye]
        self.moduller={}
        for k in kunyeler:
            if k['kod'] in self.moduller:raise ValueError('Modül kodu tekrarlanamaz')
            self.moduller[k['kod']]=SimulatorSurucu(k,zemin,ortak=next(iter(self.moduller.values()),None))
        self.s = next(iter(self.moduller.values()))
        self._yetkili=secrets.token_urlsafe(32)
        self.kilit = threading.Lock()      # tek gişe: istekler sırayla işlenir

    def servis_anahtari(self,kod=None):
        return (self.moduller[kod] if kod else self.s).servis_anahtari()

    def yetkili_anahtari(self):
        """Yalnız bu yerel test sürecine ait işletim anahtarı; canlı API'de karşılığı yoktur."""
        return self._yetkili

    def isle(self, yol, sorgu, govde, anahtar):
        with self.kilit:
            s=self.s
            if yol.startswith('/modul/'):
                _,_,kod,kalan=yol.split('/',3)
                if kod not in self.moduller:raise CekirdekHatasi('KUNYE','Modül bulunamadı')
                s=self.moduller[kod];yol='/'+kalan
            if yol=='/sahte/yetkili':
                if not anahtar or not secrets.compare_digest(anahtar,self._yetkili):
                    raise PermissionError('Yerel test işletimi anahtarı gerekli')
                return s.yetkili_olay(govde['eylem_kodu'],govde['girdiler'],
                    neyin_ustunde=govde.get('neyin_ustunde',[]))
            if yol == '/auth/v1/token':
                if sorgu.get('grant_type') != ['password']:
                    raise CekirdekHatasi('BICIM', 'grant_type=password')
                eposta = govde.get('email', '')
                if not eposta.endswith('@calisan.irp'):
                    raise CekirdekHatasi('YETKI', 'Giris')
                tok = s.giris(eposta.split('@')[0].upper(), govde.get('password'))
                return {'access_token': tok, 'token_type': 'bearer', 'user': {'email': eposta}}
            if yol == '/sahte/saat':
                s.saat(govde['an'])
                return {'an': s.simdi()}
            if yol == '/sahte/senaryo':
                return s.senaryo(govde.get('ad', 'sahte_bulut'))
            if not yol.startswith('/rest/v1/rpc/'):
                raise CekirdekHatasi('BICIM', 'Bilinmeyen yol')
            ad = yol.rsplit('/', 1)[1]
            if ad == 'simdi':
                return s.simdi()
            icerik = jwt_icerigi(anahtar) if anahtar and anahtar != ANON else {}
            if ad in ('olay_ekle', 'oku'):
                if icerik.get('role') != 'authenticated':
                    raise PermissionError('Kullanıcı oturumu gerekli')
                if ad == 'olay_ekle':
                    return s.olay_ekle(anahtar, govde['olay'], govde.get('hassas_ek'))
                return s.oku(anahtar, govde['veri'], govde.get('hedef'), govde.get('g') or {})
            if ad in ('servis_oku', 'modul_bildirimi_birak', 'modul_bildirimi_kaldir'):
                if icerik.get('role') != 'service_role':
                    raise PermissionError('Servis anahtarı gerekli')
                servis = icerik.get('servis_kimligi')
                if ad == 'servis_oku':
                    return s.servis_oku(servis, govde['veri'], govde.get('hedef'), govde.get('g') or {})
                return s.bildirim(servis, ad.rsplit('_', 1)[1], govde['g'])
            raise CekirdekHatasi('BICIM', f'Bilinmeyen kapı: {ad}')


def isleyici(bulut):
    class Isleyici(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _yaz(self, kod, govde):
            veri = json.dumps(govde, ensure_ascii=False).encode('utf-8')
            self.send_response(kod)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(veri)))
            self.end_headers()
            self.wfile.write(veri)

        def do_POST(self):  # noqa: N802
            parca = urlsplit(self.path)
            if self.headers.get('apikey') != ANON:
                return self._yaz(401, {'message': 'IRP|YETKI|apikey'})
            uzunluk = int(self.headers.get('Content-Length') or 0)
            try:
                govde = json.loads(self.rfile.read(uzunluk) or b'{}')
            except ValueError:
                return self._yaz(400, {'code': 'P0001', 'message': 'IRP|BICIM|JSON'})
            yetki = self.headers.get('Authorization', '')
            anahtar = yetki[7:] if yetki.startswith('Bearer ') else None
            try:
                self._yaz(200, bulut.isle(parca.path, parse_qs(parca.query), govde, anahtar))
            except CekirdekHatasi as e:
                self._yaz(400, {'code': 'P0001', 'message': f'IRP|{e.tur}|{e.neden}'})
            except PermissionError as e:
                self._yaz(401, {'message': f'IRP|YETKI|{e}'})
            except (KeyError, TypeError) as e:
                self._yaz(400, {'code': 'P0001', 'message': f'IRP|BICIM|Eksik alan {e}'})
    return Isleyici


class _Sunucu(ThreadingHTTPServer):
    def server_bind(self):
        # HTTPServer bilgisayarın adını ters DNS ile arar (getfqdn); ağı kısıtlı makinede yarım dakika sürer.
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]


def baslat(kunye, port=8787, zemin=None):
    """Arka planda başlatır; (sunucu, bulut) döner. Testler için."""
    bulut = SahteBulut(kunye, zemin)
    sunucu = _Sunucu(('127.0.0.1', port), isleyici(bulut))
    threading.Thread(target=sunucu.serve_forever, daemon=True).start()
    return sunucu, bulut


def main():
    a = argparse.ArgumentParser(description='Yerel sahte bulut (çekirdek simülatörü, Supabase biçiminde)')
    a.add_argument('--kunye', action='append', help='Birden çok modül için tekrarlanabilir')
    a.add_argument('--port', type=int, default=8787)
    a.add_argument('--zemin', help='Örnek firma yerine başka bir girdi dosyası')
    x = a.parse_args()
    kunye = [json.loads(Path(p).read_text('utf-8')) for p in (x.kunye or ['kunye.json'])]
    sunucu, bulut = baslat(kunye, x.port, x.zemin)
    print(f'Sahte bulut hazır: http://127.0.0.1:{x.port}')
    print(f'  IRP_CEKIRDEK=http  IRP_TABAN=http://127.0.0.1:{x.port}  IRP_ANON={ANON}')
    print(f'  IRP_SERVIS={bulut.servis_anahtari()}')
    print('  Kişiler: simulator/ornek_firma.md (simülatörde şifre denetlenmez)')
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        sunucu.shutdown()


if __name__ == '__main__':
    main()


__all__ = ['ANON', 'SahteBulut', 'anahtar_uret', 'baslat']
