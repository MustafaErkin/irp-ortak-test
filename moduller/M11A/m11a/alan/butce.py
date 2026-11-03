"""Bütçe dönüşümü, kur ve tutar biçimi (SPEC › 8.1, Ek D.2). Saf fonksiyonlar; para Decimal."""
from decimal import ROUND_HALF_UP, Decimal

KALEMLER = ('MALZEME', 'ISCILIK', 'FASON', 'GENEL_GIDER')
KURUS = Decimal('0.01')


def para(x) -> Decimal:
    return Decimal(str(x)).quantize(KURUS, rounding=ROUND_HALF_UP)


def metin(x: Decimal | None) -> str | None:
    """Tutar her zaman iki haneli ondalık metindir: "56000.00"."""
    return None if x is None else f'{para(x):.2f}'


def kur_try(kurlar: list[dict], para_birimi: str) -> Decimal | None:
    """1 birim kaç TL. TRY'nin kuru 1'dir; listede olmayan birim bilinmez."""
    if para_birimi == 'TRY':
        return Decimal(1)
    k = next((k for k in kurlar or [] if k.get('para_birimi') == para_birimi), None)
    return Decimal(str(k['kur_try'])) if k and k.get('kur_try') not in (None, '') else None


def cevir(tutar: Decimal, kaynak: str, hedef: str, kurlar: list[dict]) -> Decimal | None:
    """Kur kuralıyla çevirip yarım yukarı yuvarlar; kur eksikse None (bilinmeyen sıfır sayılmaz)."""
    if kaynak == hedef:
        return para(tutar)
    a, b = kur_try(kurlar, kaynak), kur_try(kurlar, hedef)
    if a is None or b is None or b == 0:
        return None
    return para(Decimal(tutar) * a / b)


def baslangic_butcesi(kazanan: dict) -> dict[str, Decimal]:
    """Teklifin donmuş özetinden dört kalem (toplamlar.kalemler); eksik kalem 0,00."""
    k = (kazanan.get('toplamlar') or {}).get('kalemler') or {}
    return {kalem: para(k.get(kalem, '0')) for kalem in KALEMLER}


def saat_ucretleri(kazanan: dict) -> list[dict]:
    """İşçilik satırlarından birim saat ücretleri: MEK_TASARIM 1.760 TL, IMALAT 1.408 TL."""
    ucretler = {}
    for s in kazanan.get('iscilik') or []:
        if s.get('birim') and s.get('saat_ucreti') not in (None, ''):
            ucretler.setdefault(s['birim'], {'birim': s['birim'], 'ucret': para(s['saat_ucreti']),
                                             'para_birimi': s['para_birimi']})
    return list(ucretler.values())


def odeme_toplami(satirlar: list[dict], para_birimi: str, kurlar: list[dict]) -> Decimal | None:
    """Ödeme satırlarının sözleşme para birimindeki toplamı; kuru bilinmeyen satır varsa None."""
    toplam = Decimal(0)
    for s in satirlar:
        t = cevir(Decimal(str(s['tutar'])), s['para_birimi'], para_birimi, kurlar)
        if t is None:
            return None
        toplam += t
    return para(toplam)
