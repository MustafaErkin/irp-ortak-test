"""Takvim ve en erken teslim (SPEC › 8.6). Saf. Hafta tam sayıdır; hafta 0 sipariş haftasıdır (Ek D.2)."""
from decimal import ROUND_HALF_UP, Decimal

SATIN_ALMA = 'SATIN_ALMA'
KESIN_KABUL = 'KESIN_KABUL'


def yarim_yukari(x):
    return int(Decimal(str(x)).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def sablondan(sablon, toplam_hafta):
    """Şablonun aktif her satırından takvim satırı: başlangıç = yy(bas_orani × N), bitiş = yy(bit_orani × N),
    süre = en az 1, bitiş − başlangıç."""
    n = Decimal(toplam_hafta)
    satirlar = []
    for s in sorted((s for s in sablon if s.get('aktif', True)), key=lambda s: s['sira']):
        bas = yarim_yukari(Decimal(str(s['bas_orani'])) * n)
        bit = yarim_yukari(Decimal(str(s['bit_orani'])) * n)
        satirlar.append({'etap_kodu': s['kod'], 'ad': s['ad'], 'sira': s['sira'], 'paralel_grup': s.get('paralel_grup'),
                         'baslangic_hafta': bas, 'sure_hafta': max(1, bit - bas)})
    return satirlar


def bitis(satir):
    return satir['baslangic_hafta'] + satir['sure_hafta']


def takvim_hesabi(satirlar, kalemler):
    """Takvim teslimi, kayma ve en erken teslim.

    - Takvim teslimi: KESIN_KABUL dışındaki satırların en geç bitişi.
    - Kayma: SATIN_ALMA satırı varsa en(0, başlangıcı + en uzun temin − bitişi); yoksa en(0, en uzun temin − takvim teslimi).
    - En erken teslim = takvim teslimi + kayma.
    """
    takvim_teslim = max((bitis(s) for s in satirlar if s.get('etap_kodu') != KESIN_KABUL), default=0)
    teminli = [k for k in kalemler if k.get('temin_hafta') is not None]
    en_uzun = max(teminli, key=lambda k: k['temin_hafta'], default=None)
    kayma, aciklama = 0, None
    if en_uzun is not None:
        n = en_uzun['temin_hafta']
        sa = next((s for s in satirlar if s.get('etap_kodu') == SATIN_ALMA), None)
        if sa is not None:
            kayma = max(0, sa['baslangic_hafta'] + n - bitis(sa))
            yer = 'satın almanın bitişini'
        else:
            kayma = max(0, n - takvim_teslim)
            yer = 'takvim teslimini'
        if kayma > 0:
            aciklama = (f'En uzun temin süreli kalem ({en_uzun.get("aciklama") or "adsız kalem"}, {n} hafta) '
                        f'{yer} {kayma} hafta geçiyor; en erken teslim {kayma} hafta kayar.')
    return {'takvim_teslim_hafta': takvim_teslim, 'kayma_hafta': kayma, 'en_erken_teslim_hafta': takvim_teslim + kayma,
            'en_uzun_temin_hafta': None if en_uzun is None else en_uzun['temin_hafta'], 'kayma_aciklamasi': aciklama}
