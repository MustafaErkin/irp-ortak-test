"""Canlı verisini ürüne yükler (T19 › 3): test programının ürün sürücüsüyle, modelin beklenen dosyasıyla karşılaştırarak.

Önce veritabanı boşaltılır (test.sifirla). Olaylar kendi anlarında, test saatiyle yazılır. Bulutta yükleme
bitince saat gerçek saate bırakılır ve saat işi bir kez koşar; hesap eşlemeleri yeniden yazılmalıdır
(test.sifirla onları da siler): urun/hesaplar.py.

Yerel:  IRP_TEST_DB=... python urun/veri/canli_yukle.py
Bulut:  python urun/veri/canli_yukle.py --hedef supabase-test --onay <proje kimliği>   (IRP_SB_TEST_DB)
"""
import argparse
import json
import os
from pathlib import Path
import sys
from time import perf_counter

KOK = Path(__file__).resolve().parents[2]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))
BURASI = Path(__file__).resolve().parent


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--hedef', choices=('yerel', 'supabase-test'), default='yerel')
    p.add_argument('--onay', help='bulutta: proje kimliği (adresteki ile aynı olmalı)')
    p.add_argument('--girdi', type=Path, default=BURASI / 'canli.girdi.json')
    p.add_argument('--saat-birak', action='store_true', help='yerelde de saati gerçek saate bırak (bulutta her zaman)')
    a = p.parse_args(argv)
    if a.hedef == 'supabase-test':
        from urun.kur import supabase_projesi
        dsn = os.environ.get('IRP_SB_TEST_DB')
        if not dsn:
            p.error('IRP_SB_TEST_DB tanımlı değil')
        try:
            supabase_projesi(dsn, a.onay or '')
        except ValueError as h:
            p.error(str(h))
        os.environ['IRP_TEST_DB'] = dsn  # yalnız bu süreç için; ürün sürücüsü buradan okur
    elif not os.environ.get('IRP_TEST_DB'):
        p.error('IRP_TEST_DB tanımlı değil')
    birak = a.saat_birak or a.hedef == 'supabase-test'

    from test.oynatici.akis import yurut
    from test.oynatici.hakem import karsilastirici
    from test.oynatici.karsilastirma import degerlendir
    from test.oynatici.urun_surucu import UrunSurucu
    k = karsilastirici()
    girdi = k.oku(a.girdi)
    beklenen = k.oku(a.girdi.with_name(a.girdi.name.replace('.girdi.json', '.beklenen.json')))
    surucu = UrunSurucu()
    surucu._baglan()  # ilk kapı TEST denetimi; değilse hiçbir şey yazılmaz
    bas = perf_counter()
    yurutum = yurut(girdi, surucu)
    sonuc = degerlendir(beklenen, yurutum, girdi, 'tam')
    cevaplar = yurutum.cikti['depolar'][0]['cevaplar'] if yurutum.cikti['depolar'] else []
    kabul = sum(1 for c in cevaplar if isinstance(c.get('deger'), dict) and c['deger'].get('sonuc') == 'BASARILI')
    olaylar = [s for s in girdi['depolar'][0]['adimlar'] if s['tur'] in ('olay', 'kurulum')]
    ozet = {'hedef': a.hedef, 'sonuc': sonuc['sonuc'], 'adim': len(cevaplar), 'olay': len(olaylar),
            'kabul_edilen': kabul, 'saniye': round(perf_counter() - bas, 1)}
    if sonuc['sonuc'] != 'GECTI':
        ozet['ilk_farklar'] = json.loads(json.dumps(sonuc.get('farklar', sonuc.get('fark', []))[:5], default=str))[:5] \
            if isinstance(sonuc.get('farklar', sonuc.get('fark')), list) else str(sonuc)[:1500]
    if birak:
        surucu._cagir('SELECT test.saat_birak()', kontrol=True)
        surucu._cagir('SELECT motor.saat_isi()', kontrol=True)
        ozet['saat'] = 'gerçek saate bırakıldı'
    print(json.dumps(ozet, ensure_ascii=False, indent=1, default=str))
    raise SystemExit(0 if sonuc['sonuc'] == 'GECTI' else 1)


if __name__ == '__main__':
    main()
