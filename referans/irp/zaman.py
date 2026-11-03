"""A17: zaman olay üretmez. Kapanışlar yeniden kurmada korunur."""
from copy import deepcopy
from .gorunumler import maas_dagilimi, iscilik_maliyeti, ay_sinirlari, gorev_gunluk_paylar


def takvim_siniri_isi(depo, t):
    depo.ilerlet(t)


def ay_kapanisi(depo, ay):
    bas, bit = ay_sinirlari(ay)
    if depo.saat.simdi().date() <= bit:
        raise ValueError('Ay henuz bitmedi')
    pay_anahtari = str(bas) + ':GOREV_PAYLARI'
    if pay_anahtari in depo.ay_kapanislari: return deepcopy(depo.ay_kapanislari)
    # Hesaplarin tamami basarili olmadan kaynaga kismi kapanis yazma.
    yeni = {}
    paylar = {}
    for k, g in depo.gorevler.items():
        if g['tur'] not in ('NORMAL', 'REVIZYON', 'DEGISIKLIK'): continue
        paylar[k] = {alan: [s for s in gorev_gunluk_paylar(depo, g, yuk)
                           if str(bas) <= s['gun'] <= str(bit)]
                     for alan, yuk in (('maas', False), ('yuk', True))}
    for kisi in depo.kisiler:
        anahtar = str(bas) + ':' + kisi
        if anahtar not in depo.ay_kapanislari:
            yeni[anahtar] = {'maas': deepcopy(maas_dagilimi(depo, kisi, bas, True)), 'kapanis_ani': depo.saat.simdi()}
    anahtar = str(bas) + ':MALIYET'
    if anahtar not in depo.ay_kapanislari:
        yeni[anahtar] = {p: deepcopy(iscilik_maliyeti(depo, p, bas, bit, True)) for p in depo.projeler}
    yeni[str(bas) + ':IPTAL_MALIYET'] = {p: deepcopy(iscilik_maliyeti(depo, p, bas, bit, True, True)) for p in depo.projeler}
    from .maliyet_izi_v6 import maliyet_izleri
    yeni[str(bas) + ':MALIYET_IZLERI'] = maliyet_izleri(depo, bas, bit)
    yeni[pay_anahtari] = paylar
    from .gorunum_v7 import kapanis_ekleri
    yeni.update(kapanis_ekleri(depo,bas,bit))
    depo.ay_kapanislari.update(yeni)
    return deepcopy(depo.ay_kapanislari)
