"""Bütçe ölçümü: dolum ile ilerleme (SPEC › 8.6). Saf fonksiyon; okumaları çağıran kullanıcının gözüyle yapar.

Para çekirdekten okunmaz. Tahmini işçilik = çekirdeğin saatleri × tekliften donmuş saat ücreti (karar 104)."""
from decimal import ROUND_HALF_UP, Decimal

from .butce import KALEMLER, cevir, para

ONDALIK = Decimal('0.1')
KAYNAKLAR = {'ISCILIK': 'SAAT_X_UCRET', 'MALZEME': 'BILGI_YOK_M3', 'FASON': 'BILGI_YOK_M3',
             'GENEL_GIDER': 'FORMUL_YOK'}


def bir_ondalik(x: Decimal) -> Decimal:
    return Decimal(x).quantize(ONDALIK, rounding=ROUND_HALF_UP)


def _saat(x) -> Decimal:
    return Decimal(str(x or 0))


def _yuzde(pay: Decimal, payda: Decimal) -> Decimal:
    return bir_ondalik(Decimal(100) * pay / payda)


def _sayi(x: Decimal | None) -> float | None:
    return None if x is None else float(x)


def ucret_birlestir(proje: list[dict], yedek: list[dict]) -> dict[str, dict]:
    """Projenin donmuş ücreti; yoksa ayarlardaki yedek ücret."""
    u = {r['birim']: r for r in yedek}
    u.update({r['birim']: r for r in proje})
    return u


def renk(sapma: Decimal | None, esik: Decimal) -> str:
    if sapma is None:
        return 'GRI'
    return 'KIRMIZI' if sapma > esik else 'YESIL'


def olcum(butce: dict, etaplar: list[dict], proje_durum: dict, ucretler: dict[str, dict], kurlar: list[dict],
          parcalar: list[dict], esik) -> dict:
    """butce: {'para_birimi', 'guncel': {kalem: Decimal}}; etaplar: ETAPLAR; proje_durum: PROJE_DURUM;
    ucretler: {birim: {'ucret', 'para_birimi'}}; parcalar: NESNELER; esik: puan."""
    pb, esik = butce['para_birimi'], Decimal(str(esik))
    birimler = {e['kimlik']: e.get('birim') for e in etaplar or []}
    pd_etaplar = (proje_durum or {}).get('etaplar') or {}
    if isinstance(pd_etaplar, list):
        pd_etaplar = {e['kimlik']: e for e in pd_etaplar}

    satirlar, bilinmeyen, gerceklesen, etap_toplami = [], Decimal(0), Decimal(0), Decimal(0)
    for kimlik, e in pd_etaplar.items():
        saat = _saat(e.get('harcanan_emek'))
        etap_toplami += saat
        if saat <= 0:
            continue
        birim = birimler.get(kimlik)
        u = ucretler.get(birim) if birim else None
        tutar = cevir(saat * u['ucret'], u['para_birimi'], pb, kurlar) if u else None
        if tutar is None:
            bilinmeyen += saat
        else:
            gerceklesen += tutar
        satirlar.append({'etap': kimlik, 'birim': birim, 'saat': bir_ondalik(saat),
                         'ucret': u['ucret'] if u else None, 'para_birimi': u['para_birimi'] if u else None,
                         'tutar': tutar})
    etapsiz = bir_ondalik(max(Decimal(0), _saat((proje_durum or {}).get('harcanan_emek')) - etap_toplami))
    if etapsiz > 0:
        bilinmeyen += etapsiz
        satirlar.append({'etap': None, 'birim': None, 'saat': etapsiz, 'ucret': None, 'para_birimi': None,
                         'tutar': None})

    iscilik_butcesi = Decimal(butce['guncel'].get('ISCILIK') or 0)
    kapsam = ['ISCILIK'] if iscilik_butcesi > 0 else []
    dolum = _yuzde(gerceklesen, iscilik_butcesi) if kapsam and bilinmeyen==0 else None

    core_progress=(proje_durum or {}).get('yuzde')
    ilerleme=bir_ondalik(Decimal(str(core_progress))) if isinstance(core_progress,(int,float,Decimal)) else None
    sapma = bir_ondalik(dolum - ilerleme) if dolum is not None and ilerleme is not None else None

    return {
        'dolum_yuzde': _sayi(dolum), 'ilerleme_yuzde': _sayi(ilerleme), 'sapma_puan': _sayi(sapma),
        'esik_puan': float(bir_ondalik(esik)), 'renk': renk(sapma, esik), 'kapsam': kapsam,
        'bilinmeyen_saat': bir_ondalik(bilinmeyen),
        'gerceklesen': {k: (para(gerceklesen) if k == 'ISCILIK' and bilinmeyen==0 else None) for k in KALEMLER},
        'kaynaklar': dict(KAYNAKLAR),
        'iscilik_satirlari': satirlar,
        'ilerleme': {'kaynak':'CEKIRDEK','tamamlanan':(proje_durum or {}).get('tamamlanan'),
                     'hedef':(proje_durum or {}).get('hedef')},
    }


def ozet(o: dict) -> tuple:
    """Saklanan değerler: yalnızca yüzdeler, kapsam, eşik, uyarı, bilinmeyen saat (SPEC › 8.6 Saklama)."""
    return (o['dolum_yuzde'], o['ilerleme_yuzde'], o['sapma_puan'], tuple(o['kapsam']), o['esik_puan'],
            o['renk'] == 'KIRMIZI', float(o['bilinmeyen_saat']))
