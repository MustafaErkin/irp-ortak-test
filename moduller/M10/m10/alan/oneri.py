"""İşçilik önerisi (SPEC › 8.5). Saf.

Öneri iki ayaktan gelir: başlangıç tablosu (8a) ve elle girilen geçmiş proje formu (8b). Kapanan projenin
gerçek saatleri öneriyi kendiliğinden beslemez (Faz 1'de yok; istekler M10-03, M10-04).
"""
from decimal import ROUND_HALF_UP, Decimal


def iscilik_onerisi(makine_turu, birim, tablo, gecmis):
    """tablo: {(makine_turu, birim): tipik_saat}; gecmis: [{makine_turu, birim, gercek_saat}] (proje başına bir satır).
    → {tablo, gecmis_ortalama, gecmis_sayi}; geçmiş ortalaması bir haneye yarım yukarı."""
    saatler = [Decimal(g['gercek_saat']) for g in gecmis if g['makine_turu'] == makine_turu and g['birim'] == birim]
    ortalama = None
    if saatler:
        ortalama = (sum(saatler) / len(saatler)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
    t = tablo.get((makine_turu, birim))
    return {'tablo': None if t is None else Decimal(t), 'gecmis_ortalama': ortalama, 'gecmis_sayi': len(saatler)}


def onerileri_doldur(satirlar, makine_turu, tablo, gecmis):
    """Makine türünün başlangıç tablosundaki her birim için satır yoksa açar. Saati boşsa tablo değeriyle,
    tablo yoksa geçmiş ortalamasıyla doldurur. Dolu saate dokunmaz. Yeni satırların ücreti çağıranındır."""
    sonuc = [dict(s) for s in satirlar]
    var = {s['birim'] for s in sonuc}
    for (mt, birim) in sorted(tablo):
        if mt == makine_turu and birim not in var:
            sonuc.append({'birim': birim, 'saat': None, 'yeni': True})
            var.add(birim)
    for s in sonuc:
        if s.get('saat') is None:
            o = iscilik_onerisi(makine_turu, s['birim'], tablo, gecmis)
            s['saat'] = o['tablo'] if o['tablo'] is not None else o['gecmis_ortalama']
    return sonuc
