"""T30: eksik ana veriyi normal olaylarla tamamlamak için tekrar güvenli plan.

Mevcut türler/seçenekler değiştirilmez. İş firması sıfırlanmaz.
"""
from copy import deepcopy

from pathlib import Path
import json

TANIMLAR = json.loads((Path(__file__).resolve().parents[2] / 'istemci/web/cekirdek_onkosullari.json').read_text())
BELGE = TANIMLAR['belge']
IZINLER = [(x['kod'], x['ad']) for x in TANIMLAR['izinler']]


def eksikler(kodlar, nesne_turleri):
    """Normal okuma satırlarından yalnız eksik tanımları döndürür."""
    bulunan = {(x.get('liste'), x.get('kod')) for x in kodlar}
    olaylar = [('KOD.TANIMLADIM', {'liste': 'IZIN', 'kod': kod, 'ad': ad, 'aktif': True})
               for kod, ad in IZINLER if ('IZIN', kod) not in bulunan]
    if not any(x.get('kod', x.get('kimlik')) == 'BELGE' for x in nesne_turleri):
        olaylar.append(('NESNE_TURU.TANIMLADIM', deepcopy(BELGE)))
    return olaylar
