"""Modülün sözleşme senaryolarını çekirdeğin simülatöründe baştan oynatır (sozlesme/05_sinama.md).

    python3 irp_sozlesme/arac/senaryo_dogrula.py senaryolar/*.girdi.json

Her `<ad>.girdi.json` için:
- simülatör senaryoyu baştan, tek başına oynatır (modülün kodu çalışmaz; yalnızca çekirdeğe giden adımlar);
- çıktısını `<ad>.beklenen.json` olarak yanına yazar; bu dosya senaryonun "doğru cevabı"dır;
- modülün adımlarında çekirdeğin verdiği cevapları sayar: kabul, ret (koduyla), okuma hatası.
Teslimde girdi ve beklenen dosyaları birlikte gelir; biz aynı girdiyi ürüne oynatıp beklenenle karşılaştırırız.
"""
from collections import Counter
import importlib.util
import json
from pathlib import Path
import sys

PAKET = Path(__file__).resolve().parents[1]
SIM = PAKET / 'simulator'
ZEMIN_ADIM = len(json.loads((SIM / 'ornek_firma.girdi.json').read_text('utf-8'))['depolar'][0]['adimlar'])


def yurutucu():
    for yol in (str(PAKET.parent), str(SIM), str(SIM / 'model')):
        if yol not in sys.path:
            sys.path.insert(0, yol)
    spec = importlib.util.spec_from_file_location('_irp_senaryo_yurut', SIM / 'yurut.py')
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    # Sürüm 1.1 uyarlaması yalnız bu paket yürütücüsüne eklenir; donmuş dosya değişmez.
    m.SORGULAR=set(m.SORGULAR)|{'irp_sozlesme.baglanti.okuma_uyarlamasi'}
    return m


def dogrula(yol, y=None):
    y = y or yurutucu()
    yol = Path(yol)
    girdi = json.loads(yol.read_text('utf-8'))
    sonuc = y.yurut(json.loads(json.dumps(girdi)))
    beklenen = yol.with_name(yol.name.replace('.girdi.json', '.beklenen.json'))
    beklenen.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1, sort_keys=True) + '\n', 'utf-8')
    sayim = Counter()
    adimlar = girdi['depolar'][0]['adimlar']
    for adim, cevap in list(zip(adimlar, sonuc['depolar'][0]['cevaplar']))[ZEMIN_ADIM:]:
        if 'hata_turu' in cevap:
            sayim[f'{adim["tur"]}: hata {cevap["hata_turu"]}'] += 1
        elif adim['tur'] == 'olay':
            d = cevap.get('deger', {})
            sayim[f'olay: {d.get("sonuc")}' + (f' {d.get("kod")}' if d.get('kod') else '')] += 1
        else:
            sayim[f'{adim["tur"]}: tamam'] += 1
    return beklenen, sayim


def main(yollar):
    if not yollar:
        print(__doc__)
        return 2
    y = yurutucu()
    for yol in yollar:
        beklenen, sayim = dogrula(yol, y)
        print(f'{Path(yol).name} → {beklenen.name}')
        for k, v in sorted(sayim.items()):
            print(f'  {v:4d}  {k}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
