"""V8 günlük doğrulaması; donmuş cevapları yeniden üretmez."""
import subprocess
import sys
from pathlib import Path


def calistir():
    kok = Path(__file__).resolve().parent
    for komut in ([sys.executable, '-B', str(kok/'calistir_testler.py')],
                  [sys.executable, '-I', '-B', str(kok/'cevap_anahtari/yurut.py'),
                   '--tum', '--simulasyon', '--tam-kontrol', '--degismez-kontrol']):
        subprocess.run(komut, cwd=kok, check=True)


if __name__ == '__main__':
    calistir()
