"""JSON cevabı. Tutar ondalık metindir ("56000.00"), float olmaz (Ek D.2).

FastAPI'nin kendi kodlayıcısı Decimal'i float'a çevirdiği için her uç cevabını buradan döner.
"""
from datetime import date, datetime
from decimal import Decimal

from fastapi.responses import JSONResponse


def duz(x):
    if isinstance(x, Decimal):
        return str(x)
    if isinstance(x, (datetime, date)):
        return x.isoformat()
    if isinstance(x, dict):
        return {k: duz(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [duz(v) for v in x]
    if isinstance(x, (bytes, memoryview)):
        raise TypeError('İkili veri JSON cevabına konmaz')
    return x


def yanit(veri, durum=200, baglam=None):
    veri = duz(veri)
    if baglam is not None and baglam.hesaplaniyor and isinstance(veri, dict):
        veri['hesaplaniyor'] = True
    return JSONResponse(veri, status_code=durum)
