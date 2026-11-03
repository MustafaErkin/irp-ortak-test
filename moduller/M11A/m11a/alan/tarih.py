"""Teklif takviminin tarihlenmesi (SPEC › 8.1, Ek D.2). Saf fonksiyonlar."""
from datetime import date, timedelta


def hafta_baslangici(siparis: date, baslangic_hafta: int) -> date:
    return siparis + timedelta(days=7 * baslangic_hafta)


def hafta_bitisi(siparis: date, baslangic_hafta: int, sure_hafta: int) -> date:
    """Bitiş dahildir: sipariş + 7 × (başlangıç + süre) − 1 gün."""
    return siparis + timedelta(days=7 * (baslangic_hafta + sure_hafta) - 1)


def kayma(teslim_suresi_hafta: int | None, takvim_teslim_hafta: int | None) -> int:
    if teslim_suresi_hafta is None or takvim_teslim_hafta is None:
        return 0
    return max(0, teslim_suresi_hafta - takvim_teslim_hafta)


def teslim_tarihi(siparis: date, teslim_suresi_hafta: int | None) -> date | None:
    if teslim_suresi_hafta is None:
        return None
    return siparis + timedelta(days=7 * teslim_suresi_hafta - 1)


def kesin_kabul_tarihi(siparis: date, takvim: list[dict], teslim_suresi_hafta: int | None,
                       takvim_teslim_hafta: int | None) -> date | None:
    """Takvimde KESIN_KABUL varsa onun bitişi + kayma; yoksa boş."""
    kk = next((s for s in takvim if s.get('etap_kodu') == 'KESIN_KABUL'), None)
    if not kk:
        return None
    return hafta_bitisi(siparis, kk['baslangic_hafta'] + kayma(teslim_suresi_hafta, takvim_teslim_hafta),
                        kk['sure_hafta'])


def baslangic_plani(siparis: date, takvim: list[dict]) -> list[dict]:
    """Plan teklifteki gibidir; kayma satırlara eklenmez (M1.1B B0'da düzenler)."""
    return [{'sira': s['sira'], 'etap_kodu': s.get('etap_kodu'), 'ad': s['ad'], 'paralel_grup': s.get('paralel_grup'),
             'baslangic_hafta': s['baslangic_hafta'], 'sure_hafta': s['sure_hafta'],
             'baslangic': hafta_baslangici(siparis, s['baslangic_hafta']),
             'bitis': hafta_bitisi(siparis, s['baslangic_hafta'], s['sure_hafta'])}
            for s in sorted(takvim, key=lambda s: s['sira'])]


def oneriler(siparis: date, kazanan: dict) -> dict:
    """Önizlemede önerilen tarihler: teslim, kesin kabul, kayma, tarihlenmiş takvim."""
    takvim = kazanan.get('takvim') or []
    ts, tt = kazanan.get('teslim_suresi_hafta'), kazanan.get('takvim_teslim_hafta')
    return {'teslim_tarihi': teslim_tarihi(siparis, ts if ts is not None else tt),
            'kesin_kabul_tarihi': kesin_kabul_tarihi(siparis, takvim, ts, tt),
            'kayma_hafta': kayma(ts, tt),
            'baslangic_plani': baslangic_plani(siparis, takvim)}
