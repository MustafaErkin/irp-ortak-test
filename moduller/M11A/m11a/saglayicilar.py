"""M1.0'a giden tek kapı (SPEC › Ek D.4). Çekirdek modüller arası okumayı yönlendirince yalnızca bu dosya değişir
(istek M11A-02). Kullanıcının erişim anahtarı olduğu gibi iletilir; servis anahtarı kullanılmaz."""
from copy import deepcopy
from typing import Protocol

import httpx

ZAMAN_ASIMI_SN = 5.0
DENEME = 2      # zaman aşımında bir kez yeniden denenir


class SaglayiciHatasi(Exception):
    """kod: OTURUM, YETKI, BULUNAMADI, TANIMSIZ_VERI, KAPI, DOGRULAMA, SAGLAYICI_YOK."""

    def __init__(self, kod: str, mesaj: str = '', http: int | None = None, govde: dict | None = None):
        super().__init__(f'{kod}: {mesaj}')
        self.kod, self.mesaj, self.http, self.govde = kod, mesaj, http, govde or {}

    @property
    def neden(self):
        return self.govde.get('neden')


class M10Saglayici(Protocol):
    def kazanan_surum(self, anahtar: str, surum: int) -> dict: ...


def _govde(r: httpx.Response) -> dict:
    try:
        g = r.json()
        return g if isinstance(g, dict) else {}
    except ValueError:
        return {}


class HttpM10Saglayici:
    """GET <taban>/saglanan/<AD>?<parametre>=<değer>, Authorization: Bearer <kullanıcının anahtarı>."""

    def __init__(self, taban: str | None, transport: httpx.BaseTransport | None = None,
                 zaman_asimi: float = ZAMAN_ASIMI_SN):
        self.taban = (taban or '').strip().rstrip('/') or None
        self.transport, self.zaman_asimi = transport, zaman_asimi

    def oku(self, anahtar: str, ad: str, **parametre) -> dict:
        if not self.taban:
            raise SaglayiciHatasi('SAGLAYICI_YOK', 'M1.0 adresi verilmedi')
        r = None
        with httpx.Client(transport=self.transport, timeout=self.zaman_asimi) as istemci:
            for deneme in range(DENEME):
                try:
                    r = istemci.get(f'{self.taban}/saglanan/{ad}', params=parametre,
                                    headers={'Authorization': f'Bearer {anahtar}'})
                except httpx.TransportError as h:
                    if deneme + 1 == DENEME:
                        raise SaglayiciHatasi('SAGLAYICI_YOK', f'{type(h).__name__}') from h
                    continue
                if r.status_code < 500 or deneme + 1 == DENEME:
                    break
        g = _govde(r)
        if r.status_code == 200:
            return g
        if r.status_code >= 500:
            raise SaglayiciHatasi('SAGLAYICI_YOK', f'HTTP {r.status_code}', r.status_code, g)
        if r.status_code == 401:
            raise SaglayiciHatasi('OTURUM', 'Oturum düşmüş', 401, g)
        kod = {403: 'YETKI', 409: 'KAPI', 422: 'DOGRULAMA'}.get(r.status_code)
        if r.status_code == 404:
            kod = g.get('kod') if g.get('kod') in ('BULUNAMADI', 'TANIMSIZ_VERI') else 'BULUNAMADI'
        raise SaglayiciHatasi(kod or 'SAGLAYICI_YOK', g.get('mesaj', f'HTTP {r.status_code}'), r.status_code, g)

    def kazanan_surum(self, anahtar: str, surum: int) -> dict:
        return self.oku(anahtar, 'M10.KAZANAN_SURUM', surum=surum)


class SahteM10Saglayici:
    """Sınama ve M1.0'sız geliştirme: M1.0'ın yerine verilen sürümleri döndürür; M1.0'ın kapısını uygular (D.5)."""

    def __init__(self, surumler=(), kapi: bool = True):
        self.surumler = {int(s['surum']): deepcopy(s) for s in surumler}
        self.kapi = kapi
        self.cagrilar: list[tuple[str, int]] = []
        self.hata: SaglayiciHatasi | None = None

    def ekle(self, s: dict) -> None:
        self.surumler[int(s['surum'])] = deepcopy(s)

    def kazanan_surum(self, anahtar: str, surum: int) -> dict:
        self.cagrilar.append((anahtar, surum))
        if self.hata:
            raise self.hata
        s = self.surumler.get(int(surum))
        if s is None:
            raise SaglayiciHatasi('BULUNAMADI', 'Sürüm yok', 404, {'kod': 'BULUNAMADI'})
        if self.kapi and s.get('durum') != 'GONDERILDI':
            raise SaglayiciHatasi('KAPI', 'Sürüm gönderilmemiş', 409, {'kod': 'KAPI', 'neden': 'GONDERILMEDI'})
        if self.kapi and s.get('talep_durumu') != 'KAZANILDI':
            raise SaglayiciHatasi('KAPI', 'Talep kazanılmamış', 409, {'kod': 'KAPI', 'neden': 'KAZANILMADI'})
        return deepcopy(s)


class SdkM10Saglayici:
    """Üretimde adres seçmez; iki künye ve aynı kullanıcının ortak SDK oturumu esastır."""
    def __init__(self, cekirdek):
        self.cekirdek = cekirdek

    def oku(self, anahtar, ad, **parametre):
        from irp_sozlesme.baglanti import CekirdekHatasi
        try:
            return self.cekirdek.oturum(anahtar).oku(ad, **parametre).deger
        except CekirdekHatasi as error:
            kind = {'BILGI_YOK': 'BULUNAMADI', 'BICIM': 'DOGRULAMA', 'BAGLANTI': 'SAGLAYICI_YOK'}.get(error.tur, error.tur)
            raise SaglayiciHatasi(kind, 'Sağlayıcı bilgisi alınamadı.') from error

    def kazanan_surum(self, anahtar, surum):
        return self.oku(anahtar, 'M10.KAZANAN_SURUM', surum=surum)


def saglayici_ac(cekirdek):
    return SdkM10Saglayici(cekirdek)
