"""Gerçek unittest yürütücüsü; pytest bulunmadığında aynı testleri çalıştırır."""
import json
import sys
import unittest
from pathlib import Path


class Sonuc(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kayitlar = []

    def kaydet(self, test, durum, hata=None):
        self.kayitlar.append({'test': test.id(), 'sonuc': durum, 'aciklama': test.shortDescription(), 'hata': self._exc_info_to_string(hata, test) if hata else None, 'hata_turu': hata[0].__name__ if hata else None})

    def addSuccess(self, test):
        super().addSuccess(test); self.kaydet(test, 'GECTI')

    def addFailure(self, test, err):
        super().addFailure(test, err); self.kaydet(test, 'KALDI', err)

    def addError(self, test, err):
        super().addError(test, err); self.kaydet(test, 'HATA', err)

    def addExpectedFailure(self, test, err):
        if not issubclass(err[0], AssertionError):
            self.addError(test, err)
            return
        super().addExpectedFailure(test, err); self.kaydet(test, 'XFAIL', err)

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test); self.kaydet(test, 'XPASS')

    def addSkip(self, test, reason):
        super().addSkip(test, reason); self.kaydet(test, 'ATLANDI')


def calistir():
    kok = Path(__file__).resolve().parent
    paket = unittest.defaultTestLoader.discover(str(kok / 'testler'), top_level_dir=str(kok))
    sonuc = unittest.TextTestRunner(verbosity=1, resultclass=Sonuc).run(paket)
    gecen = sum(x['sonuc'] == 'GECTI' for x in sonuc.kayitlar)
    veri = {'toplam': sonuc.testsRun, 'gecen': gecen, 'kalan': sonuc.testsRun-gecen, 'beklenmeyen_hata': len(sonuc.errors) + len(sonuc.failures), 'atlanan': len(sonuc.skipped), 'xpass': len(sonuc.unexpectedSuccesses), 'testler': sonuc.kayitlar}
    (kok / 'test_sonuclari.json').write_text(json.dumps(veri, ensure_ascii=False, indent=2), encoding='utf-8')
    return sonuc.wasSuccessful() and veri['kalan'] == 0


if __name__ == '__main__': sys.exit(0 if calistir() else 1)
