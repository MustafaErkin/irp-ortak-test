"""A12–A16: saat, kapasite, maaş, ilerleme ve performans görünümleri."""
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from math import fsum
from .saat import gun, an, gun_ani
from .gorev import son_teslim_ani
from .is_ import emek


def is_gunleri(depo, bas, bit, kisi=None):
    bas, bit = gun(bas), gun(bit)
    return [bas + timedelta(days=n) for n in range(max(0, (bit - bas).days + 1)) if depo.is_gunu(bas + timedelta(days=n),kisi)]


def kapasite(depo, kisi, bas, bit):
    from .gorunum_v7 import kapasite as v7
    return v7(depo,kisi,bas,bit)
    from .yetki_v6 import istihdamda
    return sum(gunluk_saat(depo, g) for g in is_gunleri(depo, bas, bit) if istihdamda(depo, kisi, g))


def gunluk_saat(depo, tarih, kisi=None):
    if not depo.is_gunu(tarih,kisi): return 0.0
    t = depo.takvim(tarih,kisi)
    mesai = (gun_ani(tarih, t['mesai_bitis']) - gun_ani(tarih, t['mesai_baslangic'])).total_seconds() / 3600
    molalar = sum((gun_ani(tarih, x['bit']) - gun_ani(tarih, x['bas'])).total_seconds() / 3600 for x in t['sabit_molalar'])
    return max(0, mesai - molalar)


def gorev_payi(depo, g, bas, bit, yuk=False, kisi=None):
    bas, bit = gun(bas), gun(bit)
    if g['tur'] == 'NOT' or (g['durum'] == 'IPTAL' and (yuk or g['tur']=='ONAY')): return 0.0
    if g['tur'] == 'ONAY':
        if kisi and g['kisi'] != kisi: return 0.0
        t = g['atama_ani'] if yuk else g['onay_ani']
        return float(g['zaman_degeri']) if t and bas <= gun(an(t)) <= bit else 0.0
    return fsum(s['saat'] for s in gorev_gunluk_paylar(depo, g, yuk)
               if bas <= gun(s['gun']) <= bit and (not kisi or s['kisi'] == kisi))


def gorev_gunluk_paylar(depo, g, yuk=False):
    """Karar 50: kapanis kaynagindaki pay sabit, kalan acik gunlere bolunur.

    Kapanis satirlari gorev/gun/kisi duzeyindedir. Yalniz proje toplami
    saklamak, birden cok gorevin kalan payini yeniden kurmaya yetmez.
    """
    # V4 A10/B30: kabulden sonra yuk de ilk kabulden bolunur.
    # Henuz kabul edilmemis atama, A12 uyarinca atama gununden planlanir.
    t = g.get('ilk_kabul_ani') or g['kabul_ani'] or (g['atama_ani'] if yuk else None)
    alan = 'yuk' if yuk else 'maas'
    kapanislar = getattr(depo, 'ay_kapanislari', {})
    kapali = {k[:10] for k in kapanislar if k.endswith(':GOREV_PAYLARI')}
    donmus = [dict(s) for ay in sorted(kapali)
              for s in kapanislar[ay + ':GOREV_PAYLARI'].get(g['kimlik'], {}).get(alan, [])]
    if not t or not g.get('teslim_tarihi'): return donmus
    from .takvim_v7 import gunler as tarihler
    gunler = [d for d in tarihler(an(t), g['teslim_tarihi']) if depo.is_gunu(d,gorevin_kisisi(g,d))
              if str(d.replace(day=1)) not in kapali]
    kalan = max(0.0, g['zaman_degeri'] - sum(s['saat'] for s in donmus))
    if not gunler: return donmus
    from .takvim_v7 import kisi_normal, saatler
    agirlik = {d:saatler(kisi_normal(depo,gorevin_kisisi(g,d),d)) for d in gunler}
    toplam = sum(agirlik.values())
    if not toplam: return donmus
    return donmus + [{'gun': str(d), 'kisi': gorevin_kisisi(g, d), 'saat': kalan * agirlik[d] / toplam}
                     for d in gunler
                     if agirlik[d] and (not g.get('iptal_ani') or d <= gun(an(g['iptal_ani'])))]


def gorevin_kisisi(g,tarih):
    uygun=[x for x in g.get('kisi_gecmisi',[]) if gun(an(x['baslangic']))<=gun(tarih)]
    return max(uygun,key=lambda x:x['baslangic'])['kisi'] if uygun else g['kisi']


def yuk(depo, kisi, bas, bit):
    toplam = sum(gorev_payi(depo, g, bas, bit, True) for g in depo.gorevler.values() if g['kisi'] == kisi and g['durum'] not in ('BITTI', 'IPTAL'))
    bugun = depo.saat.simdi().date()
    gun_no, kullanilan = 0, 0.0
    from .takvim_v7 import gunler as takvim_gunleri
    gunler = [g for g in takvim_gunleri(bugun,max(gun(bit),bugun)+timedelta(days=365)) if kapasite(depo,kisi,g,g)>0]
    for kimlik in depo.listeler.get(kisi, []):
        i = depo.isler[kimlik]
        kalan = max(0, i.get('tahmini_sure_dk', 0) - emek(depo, kimlik)) / 60
        if i.get('teslim_tarihi'):
            plan = [(g,kapasite(depo,kisi,g,g)) for g in takvim_gunleri(bugun,max(gun(i['teslim_tarihi']),bugun))]
            agirlik=sum(v for g,v in plan)
            if agirlik: toplam += kalan * sum(v for g,v in plan if gun(bas)<=g<=gun(bit))/agirlik
        else:
            while kalan > 1e-9 and gun_no < len(gunler):
                d = gunler[gun_no]
                kapasite_saat = kapasite(depo, kisi, d, d)
                parca = min(kalan, max(0, kapasite_saat - kullanilan))
                if gun(bas) <= d <= gun(bit): toplam += parca
                kalan -= parca; kullanilan += parca
                if kullanilan >= kapasite_saat - 1e-9: gun_no += 1; kullanilan = 0.0
    return toplam


def etap_kapasitesi(depo, birim, bas, bit):
    kisiler = {k: {'kapasite': kapasite(depo, k, bas, bit), 'planli': yuk(depo, k, bas, bit)} for k, v in depo.kisiler.items() if v['birim'] == birim}
    for v in kisiler.values(): v['bos'] = v['kapasite'] - v['planli']
    return {'kisiler': kisiler, 'toplam': {x: sum(v[x] for v in kisiler.values()) for x in ('kapasite', 'planli', 'bos')}}


def ay_sinirlari(ay):
    bas = gun(ay).replace(day=1)
    sonraki = (bas.replace(day=28) + timedelta(days=4)).replace(day=1)
    return bas, sonraki - timedelta(days=1)


def para(x):
    return Decimal(str(x)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def tutar_bul(depo, kimlik, tur, tarih, varsayilan=0):
    uygun = [x for x in depo.hassas_ekler if x['nesne_kimlik'] == kimlik and x['tur'] == tur and gun(x['gecerli_baslangic']) <= gun(tarih)]
    return max(uygun, key=lambda x: x['gecerli_baslangic'])['tutar'] if uygun else varsayilan


def maas_dagilimi(depo, kisi, ay, canli=False):
    from .gorunum_v7 import maas_dagilimi as v7
    return v7(depo,kisi,ay,canli)
    bas, bit = ay_sinirlari(ay)
    anahtar = str(bas) + ':' + kisi
    if not canli and anahtar in depo.ay_kapanislari: return depo.ay_kapanislari[anahtar]['maas']
    paylar = defaultdict(float)
    for g in depo.gorevler.values():
        if g['kisi'] == kisi or any(x['kisi']==kisi for x in g.get('kisi_gecmisi',[])):
            kalem = g.get('proje') or g.get('kategori') or 'BELIRSIZ'
            if g['durum'] == 'IPTAL': kalem = 'iptal:' + kalem
            elif g['tur'] == 'REVIZYON': kalem = 'revizyon:' + kalem
            paylar[kalem] += gorev_payi(depo, g, bas, bit, kisi=kisi)
    paylar = {k: v for k, v in paylar.items() if v}
    from .yetki_v6 import istihdamda
    gunler = is_gunleri(depo, bas, bit)
    calisilan = [g for g in gunler if istihdamda(depo, kisi, g)]
    oran = len(calisilan) / len(gunler) if gunler else 0
    toplam = sum(paylar.values()); payda = max(depo.ayar('maas_paydasi_saat', gun_ani(bas), 180) * oran, toplam)
    maas = sum(tutar_bul(depo, kisi, 'MAAS_AYLIK', d) for d in calisilan)/len(gunler) if gunler else 0
    tutarlar = {k: para(maas * v / payda) for k, v in paylar.items()}
    return {'paylar': paylar, 'toplam_saat': toplam, 'payda': payda, 'tutarlar': tutarlar, 'dagitilamayan': para(maas * (payda - toplam) / payda) if payda else para(maas), 'maas': para(maas)}


def kisinin_gunu(depo, kisi, tarih):
    araliklar = [a for a in depo.araliklar if a['kisi'] == kisi and a['gun'] == gun(tarih)]
    kovalar = defaultdict(float)
    for a in araliklar: kovalar[a['kova']] += ((a['bitis'] or depo.saat.simdi()) - a['baslangic']).total_seconds() / 60
    return {'araliklar': araliklar, 'kovalar': dict(kovalar)}


def iscilik_maliyeti(depo, proje, bas, bit, canli=False, iptal=False):
    from .gorunum_v7 import iscilik_maliyeti as v7
    return v7(depo,proje,bas,bit,canli,iptal)
    ay_bas, ay_bit = ay_sinirlari(bas)
    donmus = depo.ay_kapanislari.get(str(ay_bas) + (':IPTAL_MALIYET' if iptal else ':MALIYET'))
    if not canli and donmus is not None and (gun(bas) != ay_bas or gun(bit) != ay_bit):
        raise ValueError('Karar 49: kapanmis ay yalniz tam ay sorgulanir')
    if not canli and gun(bas) == ay_bas and gun(bit) == ay_bit and donmus is not None:
        return dict(donmus.get(proje, {'iscilik': para(0), 'tezgah': para(0)}))
    toplam = {'iscilik': 0.0, 'tezgah': 0.0}
    for a in depo.araliklar:
        if (depo.isler.get(a['is'], {}).get('durum') == 'IPTAL') != iptal: continue
        if a['proje'] != proje or a['kova'] not in ('CALISMA', 'YENIDEN_ISLEME', 'BEKLEME_ARIZA', 'BEKLEME_ON_IS', 'BEKLEME_ONAY', 'TEZGAH'): continue
        x, y = max(a['baslangic'], gun_ani(bas)), min(a['bitis'] or depo.saat.simdi(), gun_ani(gun(bit) + timedelta(days=1)))
        if x >= y: continue
        kimlik = a['tezgah'] if a['kova'] == 'TEZGAH' else a['kisi']
        saat = (y - x).total_seconds() / 3600
        toplam['tezgah' if a['kova'] == 'TEZGAH' else 'iscilik'] += saat * tutar_bul(depo, kimlik, 'SAAT_UCRETI', x)
    return {k: para(v) for k, v in toplam.items()}


def etap_gostergesi(depo, etap, t=None):
    t = an(t) if t else depo.saat.simdi()
    e = depo.etaplar[etap]
    gs = [g for g in depo.gorevler.values() if g.get('etap') == etap and g['tur'] in ('NORMAL','DEGISIKLIK') and g['durum'] != 'IPTAL']
    isler = [i for i in depo.isler.values() if i.get('etap') == etap and i.get('kisi_sayisi',1)==1 and i['durum'] != 'IPTAL']
    tamamlanan = sum(g['zaman_degeri'] for g in gs if g['durum'] == 'BITTI') + sum(i['tahmini_sure_dk'] / 60 for i in isler if i['durum'] == 'BITTI')
    kategoriler = dict.fromkeys(('tamamlandi', 'onay_bekliyor', 'revizyonda', 'geride'), 0.0)
    for g in gs + isler:
        if g['durum'] == 'IPTAL': continue
        teslim = son_teslim_ani(g, depo)
        if not teslim or teslim > t: continue
        k = 'tamamlandi' if g['durum'] == 'BITTI' else 'onay_bekliyor' if g['durum'] == 'ONAY_BEKLIYOR' else 'revizyonda' if g['durum'] in ('REDDEDILDI', 'REVIZYONDA') else 'geride'
        kategoriler[k] += g['zaman_degeri'] if 'zaman_degeri' in g else g['tahmini_sure_dk'] / 60
    gorev_saati = sum(gorev_payi(depo, g, e['baslangic'], t.date()) for g in depo.gorevler.values() if g.get('etap') == etap and g['durum'] != 'IPTAL')
    atolye_saati = sum(emek(depo, i['kimlik']) / 60 for i in isler)
    rev = sum(gorev_payi(depo, g, e['baslangic'], t.date()) for g in depo.gorevler.values() if g.get('etap') == etap and g['tur'] == 'REVIZYON' and g['durum'] != 'IPTAL')
    rev += sum(((a['bitis'] or t) - a['baslangic']).total_seconds() / 3600 for a in depo.araliklar if a['kova'] == 'YENIDEN_ISLEME' and a['is'] in [i['kimlik'] for i in isler])
    hedef = e['hedef_saat']
    return {'planli_toplam': sum(g['zaman_degeri'] for g in gs) + sum(i['tahmini_sure_dk'] / 60 for i in isler), 'tamamlanan': tamamlanan, 'hedef': hedef, 'yuzde': tamamlanan / hedef * 100 if hedef else 'Hesaplanamaz', 'dort_kategori': kategoriler, 'harcanan_emek': gorev_saati + atolye_saati, 'butce_tuketimi': (gorev_saati + atolye_saati) / hedef * 100 if hedef else 'Hesaplanamaz', 'revizyon_maliyeti_saat': rev}


def proje_gostergesi(depo, proje, cagiran=None):
    etaplar = {k: etap_gostergesi(depo, k) for k, v in depo.etaplar.items() if v['proje'] == proje}
    tamamlanan = sum(v['tamamlanan'] for v in etaplar.values()); hedef = sum(v['hedef'] for v in etaplar.values())
    from .gorunum_v6 import iptal_edilenler
    from .gorunum_v9 import proje_ekleri
    return {**proje_ekleri(depo,proje,cagiran), 'iptal_edilenler': iptal_edilenler(depo, proje), 'etaplar': etaplar, 'tamamlanan': tamamlanan, 'hedef': hedef, 'yuzde': tamamlanan / hedef * 100 if hedef else 'Hesaplanamaz'}


def adil_performans(depo, kisi, bas, bit, cagiran=None):
    from .gorunum_v7 import gorebilir_mi, sorumluluk_performansi
    from .gorunum_v9 import zaman_katkisi
    if cagiran and not gorebilir_mi(depo,cagiran,'PERFORMANS',kisi): raise PermissionError('Gorunurluk')
    def donemde(t): return t and gun(bas) <= gun(an(t)) <= gun(bit)
    gs = [g for g in depo.gorevler.values() if g['kisi'] == kisi]
    teslimler = [g for g in gs if g['tur'] in ('NORMAL','DEGISIKLIK') and donemde(g['ilk_teslim_ani'])]
    zamaninda = sum(an(g['ilk_teslim_ani']) <= son_teslim_ani(g, depo) for g in teslimler)
    retler = [r for r in depo.retler if r.get('sebep_olan') == kisi and donemde(r['an'])]
    gecikme = 0
    for r in [r for r in depo.retler if r.get('sebep_olan')==kisi]:
        g = depo.gorevler[r['gorev']]
        if g['durum'] == 'BITTI' and donemde(g['bitis_ani']) and an(g['bitis_ani']) > son_teslim_ani(g, depo):
            gecikme += r['zaman_degeri'] if r['revizyon_ver'] else g['zaman_degeri']
    cozum = [(an(g['teslim_ani']) - an(g['atama_ani'])).total_seconds() / 3600 for g in gs if g.get('sorun_kaynakli') and donemde(g['teslim_ani'])]
    cozum += [(an(g['onay_ani']) - an(g['atama_ani'])).total_seconds() / 3600 for g in gs if g['tur'] == 'ONAY' and donemde(g['onay_ani'])]
    sorumluluk = sorumluluk_performansi(depo,kisi,bas,bit)
    from .kurallar_v10 import kesinlesme
    return {**kesinlesme(depo,teslimler), 'zamaninda': zamaninda, 'teslim': len(teslimler), 'zaman_orani': sum(zaman_katkisi(depo,g) for g in teslimler) / len(teslimler) if teslimler else None, 'kalite_ret': sorumluluk['kalite_ret'], 'cozum_saatleri': cozum, 'katki_saat': sum(g['zaman_degeri'] for g in gs if g.get('nereye') == 'PROJE_DISI' and donemde(g['bitis_ani'])), 'sebep_olunan_gecikme': sorumluluk['sebep_olunan_gecikme'], 'bekletme':sum(x['geciktiren']==kisi and donemde(x['an']) for x in depo.bekletmeler.values())}


def kim_nerede(depo, bas, bit, cagiran=None):
    sonuc = defaultdict(lambda: defaultdict(float))
    for a in depo.araliklar:
        if a['kisi'] and gun(bas) <= a['gun'] <= gun(bit) and a['kova'] in ('CALISMA', 'YENIDEN_ISLEME'):
            sonuc[a['kisi'] + ':' + str(a['gun'])][a['proje'] or a['kategori'] or 'BELIRSIZ'] += ((a['bitis'] or depo.saat.simdi()) - a['baslangic']).total_seconds() / 3600
    for g in depo.gorevler.values():
        from .takvim_v7 import gunler
        for d in gunler(bas, bit):
            pay = gorev_payi(depo, g, d, d)
            if pay: sonuc[gorevin_kisisi(g,d) + ':' + str(d)][g.get('proje') or g.get('kategori') or 'BELIRSIZ'] += pay
    if cagiran:
        from .gorunum_v9 import gorebilir_mi,pano_projeleri
        return {k:pano_projeleri(depo,v,cagiran) for k,v in sonuc.items() if gorebilir_mi(depo,cagiran,'GUN',k.split(':')[0])}
    return {k: dict(v) for k, v in sonuc.items()}


def birim_dolulugu(depo, bas, bit):
    return {b: etap_kapasitesi(depo, b, bas, bit)['toplam'] for b in depo.birimler}


def saat_nereye_gitti(depo, bas, bit, cagiran=None):
    sonuc = defaultdict(lambda: defaultdict(float))
    for kisi_gun, paylar in kim_nerede(depo, bas, bit).items():
        birim = depo.kisiler[kisi_gun.split(':')[0]]['birim']
        for kalem, pay in paylar.items(): sonuc[birim][kalem] += pay
    for b in depo.birimler:
        kap = sum(kapasite(depo, k, bas, bit) for k, v in depo.kisiler.items() if v['birim'] == b)
        sonuc[b]['KAYDEDILMEYEN'] = kap - sum(sonuc[b].values())
    if cagiran:
        from .gorunum_v9 import gorebilir_mi,pano_projeleri
        if not gorebilir_mi(depo,cagiran,'UYGUNLUK'): raise PermissionError('Gorunurluk')
        return {k:pano_projeleri(depo,v,cagiran) for k,v in sonuc.items()}
    return {k: dict(v) for k, v in sonuc.items()}


def elle_sureler(depo, birim, bas, bit):
    return [a for a in depo.araliklar if a['elle'] and gun(bas) <= a['gun'] <= gun(bit) and depo.kisiler[a['kisi']]['birim'] == birim]


def onay_listesi(depo, kisi):
    from .yetki_v6 import yetkili_mi
    sonuc = []
    for tur, tablo in [('IS', depo.isler), ('GOREV', depo.gorevler)]:
        for k, x in tablo.items():
            e = dict(kim=kisi, eylem_kodu=tur + '.ONAYLADIM', girdiler={}, giris_sekli='LISTE', neyin_ustunde=[dict(tur=tur, kimlik=k)])
            if x['durum'] == 'ONAY_BEKLIYOR' and x.get('kisi_sayisi', 1) == 1 and yetkili_mi(depo, e): sonuc.append(x)
    return sonuc


def gorev_isaretleri(depo, gorev, ay=None):
    """R19: zaman işaretleri olaya veya son hal tablosuna yazılmaz."""
    g = depo.gorevler[gorev] if isinstance(gorev, str) else gorev
    isaretler = set()
    teslim = son_teslim_ani(g, depo)
    if teslim and g['ilk_teslim_ani'] and an(g['ilk_teslim_ani']) > teslim:
        isaretler.add('GEC_TESLIM')
    if teslim and not g['ilk_teslim_ani'] and g['durum'] not in ('BITTI', 'IPTAL') and depo.saat.simdi() > teslim:
        isaretler.add('GECIKTI')
    if ay:
        _, bit = ay_sinirlari(ay)
        sinir = gun_ani(bit, depo.takvim(bit,gorevin_kisisi(g,bit))['mesai_bitis'])
        if g['kabul_ani'] and an(g['kabul_ani']) <= sinir and (not g['bitis_ani'] or an(g['bitis_ani']) > sinir) and g['durum'] != 'IPTAL':
            isaretler.add('SUREN')
    return isaretler
