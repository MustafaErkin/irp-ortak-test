"""Arka yüz: uvicorn m11a.api.uygulama:app --port 8011 (SPEC › 9, 15)."""
from contextlib import asynccontextmanager
import logging
import threading

from fastapi import APIRouter, FastAPI

from .. import vt
from ..ayarlar import ortam
from ..baglanti import cekirdek_ac
from ..saglayicilar import saglayici_ac
from . import ayarlar, donustur, genel, hatalar, projeler, saglanan
from .baglam import Uygulama

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
gunluk = logging.getLogger('m11a')


def _kural_dongusu(durum: Uygulama, dakika: int, dur: threading.Event) -> None:
    """Kural işi arka yüz içinde M11A_KURAL_ARALIGI_DK dakikada bir (SPEC › 8.7)."""
    from ..alan import kurallar
    while not dur.wait(dakika * 60):
        try:
            with vt.baglan(durum.vt_url, autocommit=True) as b:
                gunluk.info('Kural işi: %s', kurallar.calistir(durum.cekirdek, b))
        except Exception:  # noqa: BLE001 — iş bir sonraki turda yeniden dener
            gunluk.exception('Kural işi yarıda kaldı')


def uygulama_kur(cekirdek=None, vt_url: str | None = None, saglayici=None, gelistirme: bool | None = None,
                 kural_araligi_dk: int | None = None) -> FastAPI:
    o = ortam()
    durum = Uygulama(cekirdek, vt_url or o.veritabani, saglayici,
                     o.gelistirme if gelistirme is None else gelistirme)
    aralik = o.kural_araligi_dk if kural_araligi_dk is None else kural_araligi_dk

    @asynccontextmanager
    async def omur(_app):
        if durum.cekirdek is None:
            durum.cekirdek = cekirdek_ac(o.kunye, durum.vt_url)
        if durum.saglayici is None:
            durum.saglayici = saglayici_ac(durum.cekirdek)
        dur = threading.Event()
        if aralik > 0:
            threading.Thread(target=_kural_dongusu, args=(durum, aralik, dur), daemon=True, name='m11a-kurallar').start()
        yield
        dur.set()

    app = FastAPI(title='M1.1A Sipariş alma ve muhasebeye devir', lifespan=omur)
    app.state.m11a = durum
    hatalar.kur(app)
    api = APIRouter(prefix='/api')
    for r in (genel, donustur, projeler, saglanan, ayarlar):
        api.include_router(r.yol)
    app.include_router(api)
    from modul_platformu.dosya_api import kur
    from .baglam import istek
    from .dosyalar import izin
    kur(app,istek,izin)
    return app


app = uygulama_kur()
