"""Sürüm 10: beklenen dosyaları değiştirmeyen tam doğrulama."""
import argparse
import subprocess
import sys
from pathlib import Path


def calistir():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--buyuk-dahil',action='store_true')
    a=p.parse_args(); kok=Path(__file__).resolve().parent; paket=kok/'cevap_anahtari'
    subprocess.run([sys.executable,'-B',str(kok/'calistir_testler.py')],cwd=kok,check=True)
    taban=[sys.executable,'-I','-B',str(paket/'yurut.py')]
    subprocess.run(taban+['--tum','--tam-kontrol'],cwd=paket,check=True)
    for ad in ['farkli_firma','ilk_ay','ilk_ay_t9']+(['buyuk'] if a.buyuk_dahil else []):
        subprocess.run(taban+[str(paket/'simulasyon'/(ad+'.girdi.json')),'--dogrula','--tam-kontrol','--degismez-kontrol'],cwd=paket,check=True)


if __name__=='__main__': calistir()
