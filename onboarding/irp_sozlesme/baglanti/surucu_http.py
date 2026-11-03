"""HTTP sürücüsü: Supabase'in biçimiyle çekirdeğe bağlanır (giriş: /auth/v1/token, kapılar: /rest/v1/rpc/<ad>).

Aynı sürücü yerel sahte bulutla da çalışır (`simulator/sunucu.py`); modül geliştirirken gerçek buluta ihtiyaç yoktur.
Bağlanma bilgisini (taban adres, anon anahtarı, servis anahtarı) biz veririz.
"""
import json
import time
import urllib.error
import urllib.request

from .cekirdek import CekirdekHatasi


class HttpSurucu:
    def __init__(self, taban, anon, servis_anahtari=None, zaman_asimi=15, deneme=3):
        self.taban, self.anon, self.servis_anahtari = taban.rstrip('/'), anon, servis_anahtari
        self.zaman_asimi, self.deneme = zaman_asimi, deneme

    def _istek(self, yol, govde, anahtar=None):
        basliklar = {'apikey': self.anon, 'Content-Type': 'application/json',
                     'Authorization': f'Bearer {anahtar or self.anon}'}
        veri = json.dumps(govde).encode('utf-8')
        bekle = 2
        for i in range(self.deneme):
            try:
                istek = urllib.request.Request(self.taban + yol, data=veri, headers=basliklar, method='POST')
                with urllib.request.urlopen(istek, timeout=self.zaman_asimi) as cevap:
                    metin = cevap.read().decode('utf-8')
                    return json.loads(metin) if metin else None
            except urllib.error.HTTPError as e:
                govde = e.read().decode('utf-8', 'replace')
                raise self._hata(e.code, govde) from None
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                # Ağ hatası: aynı istek yeniden gider. Kapılar tekrar güvenlidir (aynı olay zarfı = tekrar).
                if i == self.deneme - 1:
                    raise CekirdekHatasi('BAGLANTI', str(e)) from None
                time.sleep(bekle)
                bekle *= 2

    @staticmethod
    def _hata(kod, govde):
        try:
            mesaj = json.loads(govde).get('message') or json.loads(govde).get('msg') or govde
        except ValueError:
            mesaj = govde
        if isinstance(mesaj, str) and mesaj.startswith('IRP|'):
            parca = mesaj.split('|', 2)
            return CekirdekHatasi(parca[1], parca[2] if len(parca) > 2 else '')
        if kod in (401, 403):
            return CekirdekHatasi('YETKI', mesaj)
        return CekirdekHatasi('URUN', f'HTTP {kod}: {mesaj}')

    def _rpc(self, ad, govde, anahtar):
        return self._istek(f'/rest/v1/rpc/{ad}', govde, anahtar)

    # ---- kimlik ve saat
    def giris(self, kisi, sifre):
        try:
            cevap = self._istek('/auth/v1/token?grant_type=password',
                                {'email': f'{kisi.lower()}@calisan.irp', 'password': sifre})
        except CekirdekHatasi as e:
            raise CekirdekHatasi('YETKI', f'Giriş: {e.neden}') if e.tur == 'URUN' else e from None
        return cevap['access_token']

    def simdi(self):
        return self._rpc('simdi', {}, None)

    # ---- kapılar
    def olay_ekle(self, anahtar, olay, hassas_ek=None):
        return self._rpc('olay_ekle', {'olay': olay, 'hassas_ek': hassas_ek}, anahtar)

    def oku(self, anahtar, veri, hedef, g):
        return self._rpc('oku', {'veri': veri, 'hedef': hedef, 'g': g or {}}, anahtar)

    def servis_oku(self, servis, veri, hedef, g):
        return self._rpc('servis_oku', {'veri': veri, 'hedef': hedef, 'g': g or {}}, self._servis())

    def bildirim(self, servis, ad, g):
        return self._rpc('modul_bildirimi_' + ad, {'g': g}, self._servis())

    def modul_dosya(self,anahtar,ad,g):
        return self._rpc('modul_dosya_'+ad,g,anahtar)

    def _servis(self):
        if not self.servis_anahtari:
            raise CekirdekHatasi('KUNYE', 'Servis anahtarı verilmedi (IRP_SERVIS)')
        return self.servis_anahtari
