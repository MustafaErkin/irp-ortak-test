"""I67-I75: sayisal tutarlilik ve kabul anindaki kaynaktan yetki denetimi."""
from copy import deepcopy
from .saat import an, gun, Saat, gun_ani
from .olay import hedefler

TANIMLAR = {
    'I67': 'Iptal yaprak is/gorevler etkin proje emegine ve tamamlananina girmez.',
    'I68': 'Iptal, iptal anindan onceki kisisel emegi azaltmaz.',
    'I69': 'Kapasite istihdam icinde normal takvim ve ek mesai toplamindan onayli izin cikarilarak bulunur (T8 genisletmesi).',
    'I70': 'Kurulmus firmanin kabul tarihcesinde en az bir istihdamli YETKILI vardir.',
    'I71': 'Kabul edilmis onay/retlerde yapan, isi tamamlayan veya gorevin kisisi degildir.',
    'I72': 'Her kabul edilmis yonetim karari o kabul aninin kaynaklariyla yeniden yetkilendirilir.',
    'I73': 'Kapanmis ayin isciligi baglanti duzeltmesinden sonra kapanis kaynagi ile aynidir.',
    'I74': 'Istihdam donemleri siralidir, ayriliktan sonraki yeniden giris cakismaya yol acmaz.',
    'I75': 'Ustun kapattigi onay gorevinin maas payi ve puani sifirdir.'}


def yetki_tarihcesi(d):
    from .motor import Motor
    from .kabul import TANIKLIK
    from .yetki_v6 import yetkili_mi, istihdamda
    once, hatalar, kendi, yetkilisiz = [], [], [], []
    for e in d.olaylar.values():
        if e['giris_sekli'] != 'AKTARIM' and e['eylem_kodu'] not in TANIKLIK:
            t = an(e['bulut_ulasma_ani'])
            m = Motor(Saat(t)); m.yurut(once)
            if not yetkili_mi(m, e): hatalar.append(e['olay_kimligi'])
            kod = e['eylem_kodu']
            if kod in ('IS.ONAYLADIM', 'IS.REDDETTIM'):
                if any(m.isler.get(k, {}).get('tamamlayan') == e['kim'] for k in hedefler(e, 'IS')): kendi.append(e['olay_kimligi'])
            if kod in ('GOREV.ONAYLADIM', 'GOREV.REDDETTIM'):
                if any(m.gorevler.get(k, {}).get('kisi') == e['kim'] for k in hedefler(e, 'GOREV')): kendi.append(e['olay_kimligi'])
            if not any('YETKILI' in p.get('roller', []) and istihdamda(m, k, t) for k, p in m.kisiler.items()): yetkilisiz.append(e['olay_kimligi'])
        once.append(e)
    return {'yetkisiz_kararlar': hatalar, 'kendi_onaylari': kendi, 'yetkilisiz_anlar': yetkilisiz}


def denetle(d, tarihce=False):
    from .gorunumler import (etap_gostergesi, gorev_payi, kapasite, is_gunleri,
                            gunluk_saat, iscilik_maliyeti)
    from .yetki_v6 import istihdamda
    from .motor import Motor
    sonuc = dict.fromkeys(TANIMLAR, True)
    for et, e in d.etaplar.items():
        gorevler = [g for g in d.gorevler.values() if g.get('etap') == et and g['durum'] != 'IPTAL']
        isler = [i for i in d.isler.values() if i.get('etap') == et and i.get('kisi_sayisi', 1) == 1 and i['durum'] != 'IPTAL']
        ids = {i['kimlik'] for i in isler}
        emek = sum(((a['bitis'] or d.saat.simdi()) - a['baslangic']).total_seconds()/3600 for a in d.araliklar if a['is'] in ids and a['kova'] in ('CALISMA', 'YENIDEN_ISLEME'))
        emek += sum(gorev_payi(d, g, e['baslangic'], d.saat.simdi().date()) for g in gorevler)
        biten = sum(i.get('tahmini_sure_dk', 0)/60 for i in isler if i['durum'] == 'BITTI') + sum(g['zaman_degeri'] for g in gorevler if g['durum'] == 'BITTI' and g['tur'] in ('NORMAL','DEGISIKLIK'))
        v = etap_gostergesi(d, et)
        sonuc['I67'] &= abs(emek - v['harcanan_emek']) < 1e-7 and abs(biten - v['tamamlanan']) < 1e-7
    for k, p in d.kisiler.items():
        donemler = p.get('istihdam_donemleri', [])
        for n, x in enumerate(donemler):
            sonuc['I74'] &= not x['ayrilis'] or gun(x['giris']) <= gun(x['ayrilis'])
            if n: sonuc['I74'] &= bool(donemler[n-1]['ayrilis']) and gun(donemler[n-1]['ayrilis']) < gun(x['giris'])
        bas, bit = '2026-10-01', '2026-11-30'
        from .takvim_v7 import gunler,kisi_normal,ekler,izinler,cikar,saatler
        bek = sum(saatler(cikar(kisi_normal(d,k,g)+ekler(d,k,g),izinler(d,k))) for g in gunler(bas,bit) if any(gun(x['giris'])<=g and (not x['ayrilis'] or g<=gun(x['ayrilis'])) for x in donemler))
        sonuc['I69'] &= abs(kapasite(d,k,bas,bit)-bek)<1e-9
    sonuc['I70'] = not d.kisiler or any('YETKILI' in p.get('roller', []) and istihdamda(d, k, d.saat.simdi()) for k, p in d.kisiler.items())
    for g in d.gorevler.values():
        if g['tur'] == 'ONAY' and g['durum'] == 'IPTAL':
            sonuc['I75'] &= g['is_puani'] is None and gorev_payi(d, g, '2026-01-01', '2026-12-31') == 0
    for k, kapanis in d.ay_kapanislari.items():
        if not k.endswith(':MALIYET'): continue
        from .gorunumler import ay_sinirlari
        a, b = ay_sinirlari(k[:10])
        for p, maliyet in kapanis.items(): sonuc['I73'] &= iscilik_maliyeti(d, p, a, b) == maliyet
    if tarihce:
        denetim = yetki_tarihcesi(d)
        sonuc['I70'] &= not denetim['yetkilisiz_anlar']
        sonuc['I71'] = not denetim['kendi_onaylari']; sonuc['I72'] = not denetim['yetkisiz_kararlar']
        # Kapanis gorunumunu kendi kaynagiyla karsilastirmakla yetinme:
        # kapanis aninda ulasmis olaylardan isciligi bagimsiz yeniden uret.
        from .depo import Depo
        for ay in sorted({k[:10] for k in d.ay_kapanislari if k.endswith(':MALIYET')}):
            kapanis_ani = next(v['kapanis_ani'] for k, v in d.ay_kapanislari.items() if k.startswith(ay + ':') and isinstance(v, dict) and 'kapanis_ani' in v)
            z = Depo(Saat(kapanis_ani), 'tam')
            z._kayitlar = {k:deepcopy(e) for k,e in d.olaylar.items() if an(e['bulut_ulasma_ani']) <= an(kapanis_ani)}
            z.hassas_ekler = [deepcopy(x) for x in d.hassas_ekler if x['olay'] in z._kayitlar]
            z.yeniden_kur()
            a, b = ay_sinirlari(ay)
            for p, v in d.ay_kapanislari[ay + ':MALIYET'].items(): sonuc['I73'] &= iscilik_maliyeti(z, p, a, b, True) == v
        es = list(d.olaylar.values())
        for e in es:
            if e['eylem_kodu'] != 'IS.IPTAL_ETTIM': continue
            t = an(e['oldugu_an']); ids = set(hedefler(e, 'IS'))
            m = Motor(Saat(t)); m.yurut([x for x in es if x['olay_kimligi'] != e['olay_kimligi'] and (an(x['oldugu_an']), x['olay_kimligi']) < (t, e['olay_kimligi'])])
            ids.update(i['kimlik'] for i in m.isler.values() if i.get('ana_is') in ids)
            def dakika(araliklar):
                return sum(max(0, (min(a['bitis'] or t, t)-a['baslangic']).total_seconds()) for a in araliklar if a['is'] in ids and a['kova'] in ('CALISMA', 'YENIDEN_ISLEME'))
            sonuc['I68'] &= abs(dakika(d.araliklar) - dakika(m.araliklar)) < 1e-6
    return sonuc
