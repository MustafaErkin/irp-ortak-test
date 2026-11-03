"""Paket değişmiş mi? BUTUNLUK.json'daki özetlerle karşılaştırır.

    python3 irp_sozlesme/arac/paket_denetle.py

Paket salt okunurdur (BASLA.md › Kural 1). Değişen dosya bağlanmayı bozar; bir şey eksikse ya da yanlışsa
paketi değiştirmek yerine çekirdeğe istek yazılır (sozlesme/06_teslim.md › 3).
"""
import hashlib
import json
from pathlib import Path
import sys

PAKET = Path(__file__).resolve().parents[1]


def denetle(paket=PAKET):
    kayit = json.loads((paket / 'BUTUNLUK.json').read_text('utf-8'))
    beklenen = kayit['dosyalar']
    degisen, eksik = [], []
    for yol, ozet in beklenen.items():
        p = paket / yol
        if not p.exists():
            eksik.append(yol)
        elif hashlib.sha256(p.read_bytes()).hexdigest() != ozet:
            degisen.append(yol)
    fazla = sorted(p.relative_to(paket).as_posix() for p in paket.rglob('*')
                   if p.is_file() and p.name != 'BUTUNLUK.json' and '__pycache__' not in p.parts
                   and p.relative_to(paket).as_posix() not in beklenen)
    return kayit, degisen, eksik, fazla


def main():
    kayit, degisen, eksik, fazla = denetle()
    print(f'Paket {kayit["paket"]} · çekirdek {kayit["cekirdek"]} · {len(kayit["dosyalar"])} dosya')
    for ad, liste in (('DEĞİŞMİŞ', degisen), ('EKSİK', eksik), ('FAZLA', fazla)):
        for yol in liste:
            print(f'  {ad}: {yol}')
    if degisen or eksik:
        print('Paket bozulmuş. Paketi bize geldiği haliyle geri koyun (zip dosyasından).')
        return 1
    print('Paket sağlam.' + (' Fazla dosyalar pakete ait değil; modülün klasörüne taşıyın.' if fazla else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
