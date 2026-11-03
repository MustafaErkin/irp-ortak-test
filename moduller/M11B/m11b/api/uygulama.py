"""FastAPI uygulaması: uvicorn m11b.api.uygulama:app

Katman kuralı: ekran → bu arka yüz → irp_sozlesme.baglanti. Ön yüz çekirdeği doğrudan çağırmaz.
"""
from contextlib import asynccontextmanager
from dataclasses import dataclass
import logging
import threading

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from irp_sozlesme.baglanti import CekirdekHatasi

from ..alan.hatalar import ModulHatasi, cekirdek_hatasi, gunluk
from ..ayarlar import Ayarlar
from . import yonlendiriciler


@dataclass
class Kaynaklar:
    ayarlar: Ayarlar
    cekirdek: object
    vt: object


def _kural_dongusu(k, dur):
    from ..alan.kurallar import kurallari_calistir
    while not dur.wait(k.ayarlar.kural_araligi_dk * 60):
        try:
            gunluk.info('kural işi: %s', kurallari_calistir(k.cekirdek, k.vt))
        except Exception:  # noqa: BLE001 - kural işi bir sonraki turda yeniden dener
            gunluk.exception('kural işi başarısız')


def uygulama_kur(ayarlar=None, cekirdek=None, havuz=None, kural_isi=True):
    """Testler çekirdeği ve havuzu verir; verilmezse uygulama açılırken ortamdan kurulur."""
    ayarlar = ayarlar or Ayarlar.ortamdan()

    @asynccontextmanager
    async def omur(app):
        from ..baglanti import cekirdek_ac
        from ..vt import Vt, havuz_ac
        h = havuz or havuz_ac(ayarlar.veritabani)
        k = Kaynaklar(ayarlar, cekirdek or cekirdek_ac(ayarlar, h), Vt(h))
        app.state.kaynaklar = k
        dur = threading.Event()
        if kural_isi and ayarlar.kural_araligi_dk > 0:
            threading.Thread(target=_kural_dongusu, args=(k, dur), daemon=True, name='m11b-kural').start()
        yield
        dur.set()
        if havuz is None:
            h.close()

    app = FastAPI(title='M1.1B Siparişin proje ekibine devri', lifespan=omur)

    @app.exception_handler(ModulHatasi)
    async def _modul(request: Request, e: ModulHatasi):
        return JSONResponse(jsonable_encoder(e.govde()), status_code=e.durum)

    @app.exception_handler(CekirdekHatasi)
    async def _cekirdek(request: Request, e: CekirdekHatasi):
        m = cekirdek_hatasi(e)
        return JSONResponse(m.govde(), status_code=m.durum)

    @app.exception_handler(RequestValidationError)
    async def _girdi(request: Request, e: RequestValidationError):
        return JSONResponse({'kod': 'GIRDI', 'mesaj': 'Formda eksik ya da hatalı alan var.',
                             'alanlar': [{'yer': list(x['loc']), 'mesaj': x['msg']} for x in e.errors()]},
                            status_code=422)

    for y in yonlendiriciler.hepsi(ayarlar):
        app.include_router(y, prefix='/api')
    from modul_platformu.dosya_api import kur
    from .bagimlilik import baglam
    from .dosyalar import izin
    kur(app,baglam,izin)
    return app


logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
app = uygulama_kur()
