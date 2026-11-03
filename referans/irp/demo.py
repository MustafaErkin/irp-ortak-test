"""A18: olay dosyası üretimi ve sınırları sırayla geçen demo oynatıcı."""
from copy import deepcopy
from datetime import timedelta
from .saat import an, gun_ani
from .zaman import ay_kapanisi


def uret(senaryolar, tohum=42):
    # Tohum üretecin girdisidir; hazır olayları dönüştürürken rastgelelik gerekmez.
    sonuc = {}
    for olaylar in senaryolar:
        for e in olaylar:
            e = deepcopy(e); e['giris_sekli'] = 'AKTARIM'
            sonuc[e['olay_kimligi']] = e
    return sorted(sonuc.values(), key=lambda e: (e['oldugu_an'], e['olay_kimligi']))


class Demo:
    def __init__(self, depo, olaylar, baslangic):
        if not depo.saat.demo: raise PermissionError('Demo surumu gerekli')
        self.depo, self.olaylar, self.baslangic = depo, uret([olaylar]), an(baslangic)

    def oynat(self, hedef):
        hedef = an(hedef)
        if hedef < self.depo.saat.simdi(): self.demo_sifirla()
        noktalar = [(an(e['oldugu_an']), 0, e) for e in self.olaylar if e['olay_kimligi'] not in self.depo.olaylar and an(e['oldugu_an']) <= hedef]
        d = self.depo.saat.simdi().date()
        while d <= hedef.date():
            if d.day == 1:
                t = gun_ani(d, '00:30')
                if self.depo.saat.simdi() < t <= hedef: noktalar.append((t, 1, d - timedelta(days=1)))
            d += timedelta(days=1)
        for t, tur, veri in sorted(noktalar, key=lambda x: (x[0], x[1], x[2].get('olay_kimligi', '') if isinstance(x[2], dict) else '')):
            self.depo.ilerlet(max(t, self.depo.saat.simdi()))
            if tur == 0: self.depo.olay_ekle(veri, oturum='SERVIS', servis=True)
            else: ay_kapanisi(self.depo, veri)
        self.depo.ilerlet(hedef)

    def demo_sifirla(self):
        self.depo.demo_sifirla(self.baslangic)
