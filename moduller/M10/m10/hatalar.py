"""Modülün hataları ve SPEC › 10'daki anlamları. Alan katmanı da bunları kullanır; HTTP'ye eşleme api/hatalar.py'de."""


class ModulHatasi(Exception):
    def __init__(self, http, kod, mesaj=None, **ek):
        super().__init__(f'{http} {kod}: {mesaj}')
        self.http, self.kod, self.mesaj, self.ek = http, kod, mesaj, ek

    def govde(self):
        return {'kod': self.kod, 'mesaj': self.mesaj, **self.ek}


def oturum_yok():
    return ModulHatasi(401, 'OTURUM', 'Oturum yok ya da süresi doldu; yeniden giriş yapın.')


def yetki(mesaj='Bu işi satış yöneticisi ya da yetkili yapar.'):
    return ModulHatasi(403, 'YETKI', mesaj)


def bulunamadi(mesaj='Kayıt bulunamadı.'):
    return ModulHatasi(404, 'BULUNAMADI', mesaj)


def durum(mesaj='Bu kayıt bu durumda değiştirilemez.'):
    return ModulHatasi(409, 'DURUM', mesaj)


def kapi(mesaj='Onaylanmamış teklif müşteriye gönderilemez.', **ek):
    return ModulHatasi(409, 'KAPI', mesaj, **ek)


def degisti(guncel):
    return ModulHatasi(409, 'DEGISTI', 'Kayıt siz bakarken değişti.', guncel=guncel)


def dogrulama(hatalar, **ek):
    """hatalar: [{alan, sira, mesaj}]"""
    return ModulHatasi(422, 'DOGRULAMA', 'Girilen bilgilerde eksik ya da yanlış var.', hatalar=hatalar, **ek)


def hata(alan, mesaj, sira=None):
    return {'alan': alan, 'sira': sira, 'mesaj': mesaj}
