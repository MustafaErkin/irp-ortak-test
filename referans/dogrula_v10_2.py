"""10.2 günlük doğrulaması: testler, çekirdek/M3 cevapları ve beş kısa akış."""
import argparse
import subprocess
import sys
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--buyuk-dahil',action='store_true');a=p.parse_args()
    root=Path(__file__).resolve().parent;package=root/'cevap_anahtari'
    subprocess.run([sys.executable,'-B',str(root/'calistir_testler.py')],check=True)
    command=[sys.executable,'-I','-B',str(package/'yurut.py')]
    subprocess.run(command+['--tum','--tam-kontrol'],check=True)
    for name in ['farkli_firma','ilk_ay','ilk_ay_t9','ilk_ay_t10_1','ilk_ay_t10_2']+(['buyuk'] if a.buyuk_dahil else []):
        subprocess.run(command+[str(package/'simulasyon'/(name+'.girdi.json')),'--dogrula','--tam-kontrol','--degismez-kontrol'],check=True)


if __name__=='__main__':main()
