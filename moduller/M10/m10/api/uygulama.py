"""FastAPI uygulaması: uvicorn m10.api.uygulama:app

Katman kuralı: ekran → bu arka yüz → bağlantı katmanı. Ekran çekirdeği hiç çağırmaz.
"""
from fastapi import FastAPI
from contextlib import asynccontextmanager
import threading
from starlette.concurrency import run_in_threadpool

from . import ayarlar, ben, hatalar, liste, musteriler, onay, projeler, saglanan, surumler, talepler


def uygulama_kur():
    from ..bildirim import esitle
    @asynccontextmanager
    async def omur(app):
        stop=threading.Event()
        def loop():
            while not stop.wait(60):esitle()
        threading.Thread(target=loop,daemon=True,name='m10-bildirim').start()
        yield
        stop.set()
    app = FastAPI(title='M1.0 Teklif hazırlama', openapi_url='/api/openapi.json', docs_url='/api/belgeler',lifespan=omur)
    @app.middleware('http')
    async def kuyruk(request,call_next):
        response=await call_next(request)
        if request.method in ('POST','PUT'):await run_in_threadpool(esitle)
        return response
    hatalar.kur(app)
    # liste, /talepler/{kimlik}'ten önce: /talepler/sayac oraya düşmesin
    for modul in (ben, ayarlar, musteriler, projeler, liste, talepler, surumler, onay, saglanan):
        app.include_router(modul.yol, prefix='/api')
    from modul_platformu.dosya_api import kur
    from .baglam import baglam
    from .dosyalar import izin
    kur(app,baglam,izin)
    return app


app = uygulama_kur()
