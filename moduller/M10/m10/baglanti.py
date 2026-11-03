"""Çekirdeğe giden tek yol: irp_sozlesme.baglanti.Cekirdek, uygulamada tek örnek.

Sürücüyü (simülatör ya da HTTP) bağlantı katmanı ortam değişkenlerinden seçer; modül bilmez.
M1.0 çekirdeğe olay yazmaz (künye: olay_yolu YOK); yalnızca kullanıcının gözüyle okur.
"""
from datetime import datetime
import threading

from irp_sozlesme.baglanti import Cekirdek, CekirdekHatasi  # noqa: F401  (hata türü buradan da alınır)

from . import ayarlar

_cekirdek = None
_kilit = threading.Lock()


def cekirdek():
    global _cekirdek
    with _kilit:
        if _cekirdek is None:
            _cekirdek = Cekirdek.ac(ayarlar.kunye_yolu())
        return _cekirdek


def kur(c):
    """Testler kendi çekirdeklerini açar ve buraya verir."""
    global _cekirdek
    with _kilit:
        _cekirdek = c


def oturum(anahtar):
    """Kullanıcının gözü: kullanıcının erişim anahtarıyla."""
    return cekirdek().oturum(anahtar)


def simdi():
    """Çekirdeğin saati (+03:00). Modülün kayıtlarındaki anlar buradan alınır (SPEC › 5)."""
    return datetime.fromisoformat(cekirdek().simdi())
