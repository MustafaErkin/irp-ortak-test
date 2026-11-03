"""Iptal edilen yaprak is ve gorevlerin ayri proje hesabi."""
from .is_ import emek
from .saat import gun

def iptal_edilenler(d, proje, bas=None, bit=None):
    from .gorunumler import para, ay_sinirlari
    from .maliyet_izi_v6 import maliyet_izleri
    from .saat import an
    es = d.olaylar.values() if hasattr(d.olaylar, 'values') else d.olaylar
    bas = gun(bas) if bas else min((an(e['oldugu_an']).date() for e in es), default=d.saat.simdi().date()).replace(day=1)
    bit = gun(bit) if bit else d.saat.simdi().date()
    isler = [i for i in d.isler.values() if i.get('proje') == proje and i['durum'] == 'IPTAL' and i.get('kisi_sayisi', 1) == 1]
    gorevler = [g for g in d.gorevler.values() if g.get('proje') == proje and g['durum'] == 'IPTAL' and g['tur'] != 'ONAY']
    tum_iptal = {('IS', k) for k, i in d.isler.items() if i['durum']=='IPTAL' and i.get('kisi_sayisi',1)==1}
    tum_iptal |= {('GOREV',k) for k,g in d.gorevler.items() if g['durum']=='IPTAL' and g['tur']!='ONAY'}
    secilen = {('IS',i['kimlik']) for i in isler} | {('GOREV',g['kimlik']) for g in gorevler}
    maliyet = {'iscilik': 0.0, 'tezgah': 0.0, 'maas': 0.0}; saat = 0.0
    ay = bas.replace(day=1)
    while ay <= bit:
        a, b = ay_sinirlari(ay)
        izler = d.ay_kapanislari.get(str(a) + ':MALIYET_IZLERI')
        if izler is None: izler = maliyet_izleri(d, a, b)
        for iz in izler:
            hedef = (iz['tur'], iz['kimlik'])
            if iz['proje'] != proje or hedef not in tum_iptal or not bas <= gun(iz['gun']) <= bit: continue
            secilen.add(hedef); saat += iz['emek_saat']
            for alan in maliyet: maliyet[alan] += iz[alan]
        from datetime import timedelta
        ay = b + timedelta(days=1)
    return {'sayi': len(secilen), 'isler': sorted(k for t,k in secilen if t=='IS'), 'gorevler': sorted(k for t,k in secilen if t=='GOREV'), 'emek_saat': saat, 'maliyet': {k:para(v) for k,v in maliyet.items()}}
