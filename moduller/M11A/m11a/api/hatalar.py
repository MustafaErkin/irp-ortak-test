"""Hata eşleme (SPEC › 10). Gövde {"kod", "mesaj", ...}."""
import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from decimal import Decimal

from ..baglanti import CekirdekHatasi

gunluk = logging.getLogger('m11a')


class ModulHatasi(Exception):
    def __init__(self, http: int, kod: str, mesaj: str = '', **ek):
        super().__init__(f'{http} {kod}: {mesaj}')
        self.http, self.kod, self.mesaj, self.ek = http, kod, mesaj, ek

    def govde(self) -> dict:
        return {'kod': self.kod, 'mesaj': self.mesaj, **self.ek}


def yetki(mesaj: str) -> ModulHatasi:
    return ModulHatasi(403, 'YETKI', mesaj)


def proje_gorunmuyor() -> ModulHatasi:
    return ModulHatasi(403, 'YETKI', 'Bu projeyi göremiyorsunuz.')


def dogrulama(hatalar: list[dict]) -> ModulHatasi:
    return ModulHatasi(422, 'DOGRULAMA', 'Girilen bilgilerde hata var.', hatalar=hatalar)


CEKIRDEK_ESLEME = {
    'YETKI': (403, 'YETKI', 'Bu işe yetkiniz yok.'),
    'DURUM': (409, 'DURUM', 'İş bu durumda yapılamaz.'),
    'BAGLANTI': (503, 'BAGLANTI', 'Çekirdeğe ulaşılamıyor; biraz sonra yeniden deneyin.'),
    'BICIM': (400, 'BEKLENMEYEN', 'Beklenmeyen bir hata oldu.'),
    'KUNYE': (500, 'BEKLENMEYEN', 'Beklenmeyen bir hata oldu.'),
    'URUN': (502, 'URUN', 'Çekirdekte beklenmeyen bir hata oldu.'),
}


def cekirdek_hatasi(h: CekirdekHatasi) -> ModulHatasi:
    http, kod, mesaj = CEKIRDEK_ESLEME.get(h.tur, (502, 'URUN', 'Çekirdekte beklenmeyen bir hata oldu.'))
    return ModulHatasi(http, kod, mesaj)


def kur(app) -> None:
    @app.exception_handler(ModulHatasi)
    async def _modul(_: Request, h: ModulHatasi):
        return JSONResponse(jsonable_encoder(h.govde(),custom_encoder={Decimal:str}), status_code=h.http)

    @app.exception_handler(CekirdekHatasi)
    async def _cekirdek(istek: Request, h: CekirdekHatasi):
        if h.tur in ('BICIM', 'KUNYE', 'URUN'):
            gunluk.error('Çekirdek hatası %s %s: %s %s', istek.method, istek.url.path, h.tur, h.neden)
        m = cekirdek_hatasi(h)
        return JSONResponse(m.govde(), status_code=m.http)

    @app.exception_handler(RequestValidationError)
    async def _dogrulama(_: Request, h: RequestValidationError):
        hatalar = [{'alan': '.'.join(str(x) for x in e['loc'][1:]), 'sira': None, 'mesaj': e['msg']}
                   for e in h.errors()]
        return JSONResponse(dogrulama(hatalar).govde(), status_code=422)
