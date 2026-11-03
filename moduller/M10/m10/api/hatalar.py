"""Hata eşleme (SPEC › 10). Gövde M1.1B ile aynı: {"kod", "mesaj", ...}."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
import psycopg.errors
from starlette.exceptions import HTTPException as StarletteHTTPException

from irp_sozlesme.baglanti import CekirdekHatasi

from .. import hatalar
from ..hatalar import ModulHatasi, dogrulama, hata
from .yanit import yanit

gunluk = logging.getLogger('m10')


# Çekirdeğin hatası → HTTP. YETKI okumada 403; modülün hatası olan BICIM ve KUNYE ayrıntısıyla günlüğe.
CEKIRDEK = {
    'YETKI': (403, 'YETKI', 'Bu bilgiyi görme yetkiniz yok.'),
    'DURUM': (409, 'DURUM', 'Çekirdekteki kayıt bu durumda değil.'),
    'BICIM': (400, 'BEKLENMEYEN', 'Beklenmeyen bir hata oldu.'),
    'KUNYE': (500, 'BEKLENMEYEN', 'Beklenmeyen bir hata oldu.'),
    'BAGLANTI': (503, 'BAGLANTI', 'Çekirdeğe ulaşılamıyor, biraz sonra yeniden deneyin.'),
    'URUN': (502, 'URUN', 'Çekirdekte beklenmeyen hata.'),
}


def cekirdek_hatasi(e):
    http, kod, mesaj = CEKIRDEK.get(e.tur, CEKIRDEK['URUN'])
    if e.tur in ('BICIM', 'KUNYE', 'URUN'):
        gunluk.error('Çekirdek hatası %s: %s', e.tur, e.neden)
    return ModulHatasi(http, kod, mesaj)


def _dogrulama_hatalari(e):
    hatalar = []
    for h in e.errors():
        yer = [x for x in h.get('loc', ()) if x not in ('body', 'query', 'path')]
        sira = next((x for x in yer if isinstance(x, int)), None)
        alan = '.'.join(str(x) for x in yer if not isinstance(x, int)) or None
        hatalar.append(hata(alan, h.get('msg', 'Geçersiz değer'), sira))
    return hatalar


def kur(app: FastAPI):
    @app.exception_handler(ModulHatasi)
    async def _modul(_: Request, e: ModulHatasi):
        return yanit(e.govde(), e.http)

    @app.exception_handler(CekirdekHatasi)
    async def _cekirdek(_: Request, e: CekirdekHatasi):
        m = cekirdek_hatasi(e)
        return yanit(m.govde(), m.http)

    @app.exception_handler(RequestValidationError)
    async def _dogrulama(_: Request, e: RequestValidationError):
        return yanit(dogrulama(_dogrulama_hatalari(e)).govde(), 422)

    @app.exception_handler(psycopg.errors.RaiseException)
    async def _tetikleyici(_: Request, e):
        # Gönderilmiş sürüm değişmez (veritabanının tetikleyicisi); modülün kuralı bunu önce yakalamalıydı.
        gunluk.warning('Tetikleyici reddetti: %s', e)
        return yanit(hatalar.durum('Gönderilmiş teklif sürümü değiştirilemez.').govde(), 409)

    @app.exception_handler(psycopg.errors.IntegrityError)
    async def _butunluk(_: Request, e):
        kisit = getattr(e.diag, 'constraint_name', None)
        gunluk.warning('Kısıt reddetti: %s %s', kisit, e)
        return yanit(dogrulama([hata(kisit, 'Kayıt veritabanının kuralına uymuyor.')]).govde(), 422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, e: StarletteHTTPException):
        kod = {404: 'BULUNAMADI', 401: 'OTURUM', 403: 'YETKI', 405: 'BULUNAMADI'}.get(e.status_code, 'BEKLENMEYEN')
        return yanit({'kod': kod, 'mesaj': str(e.detail)}, e.status_code)
