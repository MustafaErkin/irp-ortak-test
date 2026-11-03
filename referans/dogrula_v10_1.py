"""Sürüm 10.1: test, donmuş cevaplar ve kısa simülasyonlar; beklenen yazmaz."""
import argparse
import subprocess
import sys
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--buyuk-dahil',action='store_true')
    a=p.parse_args(); r=Path(__file__).resolve().parent; paket=r/'cevap_anahtari'
    subprocess.run([sys.executable,'-B',str(r/'calistir_testler.py')],check=True)
    taban=[sys.executable,'-I','-B',str(paket/'yurut.py')]
    subprocess.run(taban+['--tum','--tam-kontrol'],check=True)
    for ad in ['farkli_firma','ilk_ay','ilk_ay_t9','ilk_ay_t10_1']+(['buyuk'] if a.buyuk_dahil else []):
        subprocess.run(taban+[str(paket/'simulasyon'/(ad+'.girdi.json')),'--dogrula','--tam-kontrol','--degismez-kontrol'],check=True)


if __name__=='__main__': main()
