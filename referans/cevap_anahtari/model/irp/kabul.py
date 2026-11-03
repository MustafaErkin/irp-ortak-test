"""T3 §4 ve T4 A5: kimlik, eylem yetkisi ve yönetim kapısı ayrı."""
from .saat import an, gun_ani
from .olay import hedefler
from .kisi_gunu import CALISAN

from .kurallar_v7 import TANIKLIK as TANIKLIK_V7
TANIKLIK = TANIKLIK_V7 | CALISAN | {'GOREV.KABUL_ETTIM', 'GOREV.TAMAMLADIM', 'NOT.YAZDIM', 'BILDIRIM.GORDUM'}
LIDER = {'IS.ATADIM','IS.SIRALADIM','IS.DEVRETTIM','IS.PLANSIZ_TANIMLADIM','IS.ONAYLADIM','IS.REDDETTIM','IS.DEVAM_ONAYLADIM','IS.SURE_EKLEDIM'}
MATRIS = [
    ('is_duzenle', ['IS.DEGISTIRDIM','IS.IPTAL_ETTIM'], 'havuz/ust birim basi veya yetkili veya is birimi ekip lideri'),
    ('yasam_ana', ['PROJE.DEGISTIRDIM','PROJE.KAPATTIM','AYAR.MAAS_PAYDASI','AYAR.PARCA_KODU_DESENI'], 'YETKILI'),
    ('etap_duzenle', ['ETAP.DEGISTIRDIM'], 'YONETICI/YETKILI'),
    ('saat', sorted(CALISAN), 'kendisi/adina is birimi lideri'),
    ('havuz', ['IS.TANIMLADIM'], 'havuz birimi basi/ust birim basi/yetkili'),
    ('lider', sorted(LIDER), 'is birimi ekip lideri; onay/ret icin atayan da'),
    ('isaret', ['KAYIT.GECERSIZ_SAYDIM'], 'hedef kim/lider'),
    ('gorev_ata', ['GOREV.ATADIM'], 'YONETICI/EKIP_LIDERI/YETKILI'),
    ('gorev_kisi', ['GOREV.KABUL_ETTIM','GOREV.TAMAMLADIM'], 'gorevin olay anindaki kisisi'),
    ('gorev_onay', ['GOREV.ONAYLADIM','GOREV.REDDETTIM'], 'onaylayan'),
    ('gorev_duzenle', ['GOREV.DEGISTIRDIM','GOREV.IPTAL_ETTIM'], 'veren/yetkili'),
    ('not', ['NOT.YAZDIM'], 'her oturum'),
    ('yonlendirme', ['AYAR.YONLENDIRDIM'], 'birim basi'),
    ('etap', ['ETAP.TANIMLADIM'], 'YONETICI/YETKILI'),
    ('ana', ['AYAR.ONAY_ORANI','AYAR.SAAT_KAYDIRDIM','KISI.EKLEDIM','KISI.DEGISTIRDIM','KISI.AYRILDI','MAAS.GUNCELLEDIM','PROJE.ACTIM','BIRIM.TANIMLADIM','TEZGAH.TANIMLADIM','TAKVIM.TANIMLADIM','TATIL.EKLEDIM'], 'YETKILI'),
    ('aktarim', ['AKTARIM'], 'servis'),
]

def nesne(d, tur, kimlik):
    if tur == 'LISTE':
        from .surum import liste_surumu
        return {'surum':liste_surumu(d,kimlik)} if kimlik in d.kisiler else {}
    if tur == 'NESNE': return d.nesneler.get(kimlik,{})
    tablo={'IS':'isler','GOREV':'gorevler','KISI':'kisiler','BIRIM':'birimler','ETAP':'etaplar','PROJE':'projeler','NOT':'notlar','TEZGAH':'tezgahlar'}
    return getattr(d,tablo.get(tur,''),{}).get(kimlik,{})

def lider(d, kim, birim):
    k=d.kisiler.get(kim,{})
    return k.get('birim')==birim and 'EKIP_LIDERI' in k.get('roller',[])

def yetki(d,e,servis=False):
    from .yetki_v6 import yetkili_mi
    return yetkili_mi(d, e, servis)
    # Servis AKTARIM tarihsel veri taşır: henüz doğmamış nesnenin yetkisi kurulamaz (B26).
    if servis and e['giris_sekli']=='AKTARIM': return True
    kim,kod,g=e['kim'],e['eylem_kodu'],e['girdiler']
    kisi=d.kisiler.get(kim,{})
    if not kisi: return False
    if kisi.get('ayrilis_tarihi') and an(e['oldugu_an']).date() > an(kisi['ayrilis_tarihi']).date(): return False
    if e.get('adina'):
        adina = d.kisiler.get(e['adina'], {})
        if not adina or (adina.get('ayrilis_tarihi') and an(e['oldugu_an']).date() > an(adina['ayrilis_tarihi']).date()): return False
    roller=set(kisi.get('roller',[])); yetkili='YETKILI' in roller
    isler=[d.isler.get(x,{}) for x in hedefler(e,'IS')]
    gorevler=[d.gorevler.get(x,{}) for x in hedefler(e,'GOREV')]
    if kod in CALISAN:
        if not e.get('adina'): return bool(kisi)
        birimler={i.get('birim') for i in isler} or {d.kisiler.get(e['adina'],{}).get('birim')}
        return all(lider(d,kim,b) for b in birimler)
    if kod=='IS.TANIMLADIM':
        def havuz(b):
            birim=d.birimler.get(b,{})
            return kim in (birim.get('basi'),d.birimler.get(birim.get('ust_birim'),{}).get('basi'))
        return yetkili or all(havuz(i.get('birim')) for i in g['isler'])
    if kod in ('IS.DEGISTIRDIM', 'IS.IPTAL_ETTIM'):
        def izin(i):
            b = d.birimler.get(i.get('birim'), {})
            return yetkili or lider(d, kim, i.get('birim')) or kim in (b.get('basi'), d.birimler.get(b.get('ust_birim'), {}).get('basi'))
        return bool(isler) and all(izin(i) for i in isler)
    if kod in ('IS.ONAYLADIM','IS.REDDETTIM'):
        return bool(isler) and all(i.get('atayan')==kim or lider(d,kim,i.get('birim')) for i in isler)
    if kod in LIDER:
        birimler={i.get('birim') for i in isler} or {g.get('birim') or kisi.get('birim')}
        return all(lider(d,kim,b) for b in birimler)
    if kod=='KAYIT.GECERSIZ_SAYDIM':
        hedef=d.olaylar.get(g['hedef'],{})
        return bool(hedef) and (kim==hedef.get('kim') or lider(d,kim,d.kisiler.get(hedef.get('adina') or hedef.get('kim'),{}).get('birim')))
    if kod=='GOREV.ATADIM': return bool(roller & {'YONETICI','EKIP_LIDERI','YETKILI'})
    if kod in ('GOREV.KABUL_ETTIM','GOREV.TAMAMLADIM'): return bool(kisi) and bool(gorevler) and all(not x or x.get('kisi')==kim for x in gorevler)
    if kod in ('GOREV.ONAYLADIM','GOREV.REDDETTIM'): return bool(gorevler) and all(x.get('onaylayan')==kim for x in gorevler)
    if kod in ('GOREV.DEGISTIRDIM','GOREV.IPTAL_ETTIM'): return bool(gorevler) and all(yetkili or x.get('veren')==kim for x in gorevler)
    if kod=='NOT.YAZDIM': return bool(kisi)
    if kod=='AYAR.YONLENDIRDIM': return d.birimler.get(g['birim'],{}).get('basi')==kim
    if kod in ('ETAP.TANIMLADIM', 'ETAP.DEGISTIRDIM'): return bool(roller & {'YONETICI','YETKILI'})
    return yetkili

def durum(d,e):
    from .kurallar_v10_2 import durum as durum_v10_2
    karar = durum_v10_2(d,e)
    if karar is not None: return karar
    from .kurallar_v10_1 import durum as durum_v10_1
    karar = durum_v10_1(d,e)
    if karar is not None: return karar
    from .kurallar_v9 import durum as durum_v9
    karar = durum_v9(d,e)
    if karar is not None: return karar
    from .kurallar_v7 import durum as durum_v7
    karar = durum_v7(d,e)
    if karar is not None: return karar
    from .kapilar_v3 import ek_kapilar
    from .kapilar_v5 import kapilar
    if not ek_kapilar(d,e) or not kapilar(d,e): return False
    kod,g=e['eylem_kodu'],e['girdiler']; t=an(e['oldugu_an'])
    ids=hedefler(e,'IS'); i=d.isler.get(ids[0],{}) if ids else {}
    if kod=='IS.ATADIM':
        n=g.get('kisi_sayisi',i.get('kisi_sayisi',1))
        return i.get('durum') in ('HAVUZDA', 'REDDEDILDI') and not any(ids[0] in l for l in d.listeler.values()) and (n==1 or len(g.get('kisiler',[]))==n)
    if kod=='IS.SIRALADIM':
        l=d.listeler.get(g['kisi'],[])
        if not l or ids[0] not in l or i.get('durum')=='BITTI': return False
        if d.isler[l[0]]['durum']=='ONAY_BEKLIYOR' and d.isler[l[0]].get('onay_beklet') and ((ids[0]==l[0] and g['yeni_sira']!=1) or (ids[0]!=l[0] and g['yeni_sira']==1)): return False
    if kod=='IS.DEVRETTIM': return ids[0] in d.listeler.get(g['kimden'],[]) and g['kimden']!=g['kime'] and i.get('durum')!='ONAY_BEKLIYOR'
    if kod in ('IS.ONAYLADIM','IS.REDDETTIM'): return i.get('durum')=='ONAY_BEKLIYOR'
    if kod=='IS.DEVAM_ONAYLADIM':
        h=d.kisi_durumu.get(i.get('kisi'),{})
        if h.get('durum')=='SABIT_MOLADA': h=h.get('mola_onceki') or {}
        return h.get('durum')=='ARIZADA' and h.get('acik_is')==i.get('kimlik')
    if kod=='IS.SURE_EKLEDIM':
        a,b=an(g['baslangic']),an(g['bitis']); kisi=e['adina']
        tak=d.takvim(a.date(),kisi)
        return (a.date()==b.date() and a.isocalendar()[:2]==t.isocalendar()[:2] and b<=t and b<=d.saat.simdi() and d.is_gunu(a,kisi) and gun_ani(a.date(),tak['mesai_baslangic'])<=a<b<=gun_ani(a.date(),tak['mesai_bitis']) and (i.get('kisi')==kisi or any(x['kisi']==kisi and x['is']==i.get('kimlik') for x in d.araliklar)))
    if kod=='KAYIT.GECERSIZ_SAYDIM':
        h=d.olaylar.get(g['hedef']); pasif={x['girdiler']['hedef'] for x in d.olaylar.values() if x['eylem_kodu']==kod}
        return bool(h) and h['eylem_kodu'] in CALISAN and an(h['oldugu_an']).isocalendar()[:2]==t.isocalendar()[:2] and g['hedef'] not in pasif
    if kod=='GOREV.ATADIM': return all(x['kisi']!=e['kim'] for x in g['gorevler'])
    if kod.startswith('GOREV.'):
        from .gorev import kapi
        return all(x in d.gorevler and kapi(d,d.gorevler[x],e) for x in hedefler(e,'GOREV'))
    return True
