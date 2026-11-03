"""Proje kodu ve sipariş adı (SPEC › 8.1, 8.9). Saf fonksiyonlar: veritabanına ve çekirdeğe dokunmaz."""
from datetime import date
import re

DEGISKENLER = frozenset({'YY', 'YYYY', 'AA', 'SIRA3', 'YILLIK_SIRA3', 'PROJE_KODU', 'MUSTERI', 'PROJE_ADI', 'PO'})
KAPSAMLAR = ('YIL', 'AY')
ELLE_KOD = re.compile(r'^[0-9A-Za-z-]{2,20}$')
_DEGISKEN = re.compile(r'\{([^{}]*)\}')
PO_YOK = 'PO-BEKLENIYOR'


def kalip_degiskenleri(desen: str) -> set[str]:
    return set(_DEGISKEN.findall(desen))


def bilinmeyen_degiskenler(desen: str) -> list[str]:
    return sorted(kalip_degiskenleri(desen) - DEGISKENLER)


def _doldur(desen: str, degerler: dict[str, str]) -> str:
    return _DEGISKEN.sub(lambda m: degerler.get(m.group(1), m.group(0)), desen)


def sira_donemi(siparis_tarihi: date, kapsam: str = 'YIL') -> str:
    """Proje kodu sayacının dönemi: YIL → '2026', AY → '2026-11'."""
    if kapsam not in KAPSAMLAR:
        raise ValueError(f'Bilinmeyen sıra kapsamı: {kapsam}')
    return f'{siparis_tarihi.year}' if kapsam == 'YIL' else f'{siparis_tarihi.year}-{siparis_tarihi.month:02d}'


def _tarih_degerleri(t: date) -> dict[str, str]:
    return {'YY': f'{t.year % 100:02d}', 'YYYY': f'{t.year}', 'AA': f'{t.month:02d}'}


def proje_kodu(desen: str, siparis_tarihi: date, sira: int) -> str:
    """Varsayılan desen {YY}{AA}{SIRA3}: 02.11.2026'daki ilk sipariş 2611001."""
    return _doldur(desen, {**_tarih_degerleri(siparis_tarihi), 'SIRA3': f'{sira:03d}'})


def elle_kod_gecerli(kod: str) -> bool:
    return bool(ELLE_KOD.match(kod or ''))


def siparis_adi(desen: str, siparis_tarihi: date, yillik_sira: int, proje_kodu: str, musteri: str,
                proje_adi: str, po: str | None) -> str:
    """Yalnızca gösterim; saklanmaz, alanlarından kurulur. PO yoksa PO-BEKLENIYOR."""
    return _doldur(desen, {**_tarih_degerleri(siparis_tarihi), 'YILLIK_SIRA3': f'{yillik_sira:03d}',
                           'PROJE_KODU': proje_kodu, 'MUSTERI': musteri, 'PROJE_ADI': proje_adi,
                           'PO': (po or '').strip() or PO_YOK})
