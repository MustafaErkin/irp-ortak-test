"""Kapanista tutarin hangi is/gorev ve gunden geldigini de dondurur."""
from collections import defaultdict
from datetime import timedelta
from .saat import gun, gun_ani


def maliyet_izleri(d, bas, bit):
    from .gorunumler import tutar_bul, maas_dagilimi, gorev_payi, is_gunleri
    bas, bit = gun(bas), gun(bit)
    kovalar = {'CALISMA', 'YENIDEN_ISLEME', 'BEKLEME_ARIZA', 'BEKLEME_ON_IS', 'BEKLEME_ONAY', 'TEZGAH'}
    izler = defaultdict(lambda: dict(emek_saat=0.0, iscilik=0.0, tezgah=0.0, maas=0.0))
    for a in d.araliklar:
        if a['kova'] not in kovalar or not a['is']: continue
        x, son = max(a['baslangic'], gun_ani(bas)), min(a['bitis'] or d.saat.simdi(), gun_ani(bit + timedelta(days=1)))
        while x < son:
            y = min(son, gun_ani(x.date() + timedelta(days=1)))
            v = izler[('IS', a['is'], a.get('proje'), str(x.date()))]
            saat = (y - x).total_seconds()/3600
            if a['kova'] in ('CALISMA', 'YENIDEN_ISLEME'): v['emek_saat'] += saat
            makine = a['kova'] == 'TEZGAH'
            from .gorunum_v7 import saat_maliyeti
            oran = tutar_bul(d,a['tezgah'],'SAAT_UCRETI',x) if makine else saat_maliyeti(d,a['kisi'],x)
            alan='tezgah' if makine else 'iscilik'
            if oran == 'VERI_EKSIK' or v[alan] == 'VERI_EKSIK': v[alan]='VERI_EKSIK'
            else: v[alan] += saat * float(oran)
            x = y
    maaslar = {k: maas_dagilimi(d, k, bas) for k in d.kisiler}
    for g in d.gorevler.values():
        kisiler = {g['kisi']} | {x['kisi'] for x in g.get('kisi_gecmisi', [])}
        kalem = g.get('proje') or g.get('kategori') or 'BELIRSIZ'
        if g['durum'] == 'IPTAL': kalem = 'iptal:' + kalem
        elif g['tur'] == 'REVIZYON': kalem = 'revizyon:' + kalem
        from .takvim_v7 import gunler
        for tarih in gunler(bas, bit):
            for k in kisiler:
                pay = gorev_payi(d, g, tarih, tarih, kisi=k)
                if not pay: continue
                m = maaslar[k]; toplam = m['paylar'].get(kalem, 0)
                v = izler[('GOREV', g['kimlik'], g.get('proje'), str(tarih))]
                v['emek_saat'] += pay
                if m['tutarlar'].get(kalem) == 'VERI_EKSIK': v['maas']='VERI_EKSIK'
                elif toplam and v['maas'] != 'VERI_EKSIK': v['maas'] += float(m['tutarlar'].get(kalem, 0)) * pay / toplam
    return [dict(v, tur=t, kimlik=k, proje=p, gun=g) for (t,k,p,g),v in sorted(izler.items(), key=lambda x: tuple(str(v) for v in x[0]))]
