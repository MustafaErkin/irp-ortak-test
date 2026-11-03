"""T8 olay sozlesmesi, kabul kapilari ve olaydan tureyen nesneler."""
from copy import deepcopy
from datetime import timedelta
from .saat import an, gun, gun_ani
from .olay import hedefler
from .yetki_v6 import ustler, yoneticiler, birim_ustleri, istihdamda, simdi
from .takvim_v7 import pencere, kesisim, normal, gunler, kapsamda, birim_kapsamda

SEMALAR = {
    'AYAR.DEGISTIRDIM': ('anahtar', 'deger'),
    'GUN.TANIMLADIM': ('tarih', 'tur', 'ad'), 'GUN.KALDIRDIM': ('tarih',),
    'EK_MESAI.PLANLADIM': ('kisi','tarih','baslangic','bitis','aciklama'),
    'EK_MESAI.ONAYLADIM': ('kisi','tarih','baslangic','bitis'), 'EK_MESAI.IPTAL_ETTIM': ('hedef',),
    'IZIN.TALEP_ETTIM': ('kisi','tur','baslangic','bitis','gerekce'),
    'IZIN.ONAYLADIM': ('hedef',), 'IZIN.REDDETTIM': ('hedef','gerekce'),
    'IZIN.IK_ONAYLADIM': ('hedef',), 'IZIN.IPTAL_ETTIM': ('hedef',),
    'TEZGAH.TAKVIM_TANIMLADIM': ('tezgah','vardiyalar','gecerli_baslangic'),
    'TEZGAH.BAKIM_PLANLADIM': ('tezgah','baslangic','bitis','aciklama'), 'TEZGAH.BAKIM_IPTAL_ETTIM': ('hedef',),
    'TEZGAH.DURUS_BILDIRDIM': ('tezgah','neden'), 'TEZGAH.DURUS_BITTI': ('tezgah',),
    'DURUS.BASLADI': ('kapsam','neden'), 'DURUS.BITTI': ('hedef',),
    'GUN_SONU.GONDERDIM': ('gun','aciklama','tanimsiz_aciklama'),
    'GUN_SONU.ONAYLADIM': ('kisi','gun','ozet_surumu'), 'GUN_SONU.IADE_ETTIM': ('kisi','gun','gerekce'),
    'PLAN.ONAYLADIM': ('proje',),
    'SORUMLULUK.DOGRULADIM': ('hedef','karar','gerekce'),
    'SORUMLULUK.ITIRAZ_ETTIM': ('hedef','gerekce'),
    'SORUMLULUK.ITIRAZI_DEGERLENDIRDIM': ('hedef','karar','gerekce'),
    'NESNE_TURU.TANIMLADIM': ('kod','ad','asamalar','baslangic_asamasi','gecisler','baglanabilir_turler','acabilenler'),
    'NESNE.ACTIM': ('tur','ad','sorumlu'),
    'NESNE.ASAMA_GECIRDIM': ('hedef','yeni_asama','gerekce'), 'NESNE.GUNCELLEDIM': ('hedef','degisenler'),
}
TANIKLIK = {'DURUS.BASLADI','DURUS.BITTI','TEZGAH.DURUS_BILDIRDIM','TEZGAH.DURUS_BITTI','GUN_SONU.GONDERDIM'}
TABLOLAR = ('gun_tanimlari','ek_mesai_planlari','izinler','duruslar','tezgah_takvimleri','bakimlar','tezgah_duruslari',
            'gun_sonu_raporlari','plan_surumleri','sorumluluklar','itirazlar','nesne_turleri','nesneler','mesai_sonrasi_isaretleri')


def varsayilan_yetkiler():
    sonuc = []
    for kod in SEMALAR:
        roller, kapsam = ['YETKILI'], 'FIRMA'
        if kod.startswith('TEZGAH.'):
            roller, kapsam = (['BIRIM_UYESI'] if '.DURUS_' in kod else ['BIRIM_YONETICISI','YETKILI']), 'BIRIM'
        elif kod.startswith('DURUS.'): roller, kapsam = ['BIRIM_YONETICISI'], 'BIRIM'
        elif kod == 'PLAN.ONAYLADIM': roller = ['YONETICI','YETKILI']
        elif kod.startswith(('EK_MESAI.','IZIN.','GUN_SONU.','SORUMLULUK.','NESNE.')) and kod != 'IZIN.IK_ONAYLADIM': continue
        sonuc.append(dict(eylem_kodu=kod, kimler=roller, kapsam=kapsam))
    return sonuc


def hedef_satir(d, e):
    if e['eylem_kodu'].startswith('SORUMLULUK.') and 'satir' in e['girdiler']:
        from .kurallar_v9 import sorumluluk_satiri
        return sorumluluk_satiri(d,e['girdiler'])
    g, kod = e['girdiler'], e['eylem_kodu']
    if kod.startswith('IZIN.'): return d.izinler.get(g.get('hedef'), g)
    if kod.startswith('EK_MESAI.'): return d.ek_mesai_planlari.get(g.get('hedef'), g)
    if kod.startswith('DURUS.'): return d.duruslar.get(g.get('hedef'), g)
    if kod.startswith('TEZGAH.BAKIM_'): return d.bakimlar.get(g.get('hedef'), g)
    if kod.startswith('SORUMLULUK.'):
        hedef = d.itirazlar.get(g.get('hedef'), {}).get('sorumluluk', g.get('hedef'))
        return d.sorumluluklar.get(hedef, {})
    if kod.startswith('NESNE.'): return d.nesneler.get(g.get('hedef'), g)
    return g


def satir_ustleri(d, x):
    return ustler(d, x.get('kimlik')) if x.get('tur') == 'KISI' else birim_ustleri(d, x.get('kimlik'))


def rol_izni(d, kim, kural, birim=None):
    if isinstance(kural, list): kural = dict(kimler=kural, kapsam='FIRMA')
    kimler, kapsam = set(kural.get('kimler', [])), kural.get('kapsam','FIRMA')
    roller = set(d.kisiler.get(kim,{}).get('roller',[]))
    if not kimler: return False
    if 'YETKILI' in kimler and 'YETKILI' in roller: return True
    if kapsam == 'FIRMA':
        if roller & (kimler-{'YETKILI'}): return True
        return any(kim in ustler(d,k) and set(p.get('roller',[])) & (kimler-{'YETKILI'}) and istihdamda(d,k,simdi(d)) for k,p in d.kisiler.items())
    if d.kisiler.get(kim,{}).get('birim') == birim and ('BIRIM_UYESI' in kimler or roller & kimler): return True
    if 'BIRIM_YONETICISI' in kimler and kim in yoneticiler(d,birim): return True
    if 'BIRIM_BASI' in kimler and kim == d.birimler.get(birim,{}).get('basi'): return True
    return kim in birim_ustleri(d,birim)


def yetki(d, e):
    kod, g, kim = e['eylem_kodu'], e['girdiler'], e['kim']
    if kod not in SEMALAR:
        satirlar = g.get('gorevler', [g])
        for s in satirlar:
            if s.get('ek_mesai') and any(kim not in ustler(d,k) for k in s.get('kisiler',[s.get('kisi')])): return False
        return None
    if not istihdamda(d,kim,simdi(d)): return False
    x = hedef_satir(d,e); kisi = x.get('kisi', e.get('adina') or kim)
    if kod.startswith('EK_MESAI.'): return kim in ustler(d,kisi)
    if kod == 'IZIN.TALEP_ETTIM': return kim == kisi or kim in ustler(d,kisi)
    if kod.startswith('IZIN.') and kod != 'IZIN.IK_ONAYLADIM':
        return kim in ustler(d,kisi) or (kod == 'IZIN.IPTAL_ETTIM' and kim == kisi and x.get('durum') == 'TALEP')
    if kod.startswith('GUN_SONU.'):
        return kim in ustler(d,kisi) or (kod.endswith('GONDERDIM') and kim == kisi)
    if kod.startswith('SORUMLULUK.'):
        if not x: return False
        if kod.endswith('ITIRAZ_ETTIM'):
            return kim == x['kimlik'] if x['tur'] == 'KISI' else kim in yoneticiler(d,x['kimlik'])
        return kim != x['kimlik'] and kim in satir_ustleri(d,x)
    if kod.startswith('NESNE.'):
        b = d.kisiler.get(x.get('sorumlu'),{}).get('birim')
        tur = d.nesne_turleri.get(x.get('tur'),{})
        if kod == 'NESNE.ACTIM': return rol_izni(d,kim,tur.get('acabilenler',{}),b)
        iliski = kim == x.get('sorumlu') or kim in ustler(d,x.get('sorumlu'))
        if kod.endswith('GUNCELLEDIM'): return iliski or 'YETKILI' in d.kisiler[kim]['roller']
        gecis = next((s for s in tur.get('gecisler',[]) if s['den']==x.get('asama') and s['e']==g['yeni_asama']),None)
        # Gecissiz hedef DURUM tanisi alir; rol denetimi mevcut geciste yapilir.
        return gecis is None or iliski or rol_izni(d,kim,gecis,b)
    if kod.startswith('DURUS.') and x.get('kapsam') == 'FIRMA':
        return 'YETKILI' in d.kisiler[kim]['roller'] or any(not b.get('ust_birim') and kim in yoneticiler(d,k) for k,b in d.birimler.items())
    birimler = [d.tezgahlar.get(x.get('tezgah'),{}).get('birim')] if kod.startswith('TEZGAH.') else x.get('kapsam', [None]) if kod.startswith('DURUS.') else [None]
    kurallar = [r for r in d.yetki_kurallari if r['eylem_kodu']==kod and not r.get('gecerli_bitis')]
    return all(any(rol_izni(d,kim,r,b) for r in kurallar) for b in birimler)


def bicim(e):
    kod, g = e['eylem_kodu'], e['girdiler']
    def hata(kosul, mesaj):
        if not kosul: raise ValueError(mesaj)
    if kod in ('IS.REDDETTIM','GOREV.REDDETTIM'):
        ss = g.get('sorumlular',[])
        hata(isinstance(ss,list), 'Sorumlular dizi')
        hata(all(x.get('tur') in ('KISI','BIRIM') and isinstance(x.get('kimlik'),str) and type(x.get('yuzde')) in (int,float) and 0 <= x['yuzde'] <= 100 for x in ss),'Sorumluluk bicimi')
        hata(sum(x['yuzde'] for x in ss) <= 100, 'Sorumluluk toplami 100')
        hata(len({(x['tur'],x['kimlik']) for x in ss}) == len(ss),'Tekil sorumlular')
    if kod not in SEMALAR: return
    if kod == 'AYAR.DEGISTIRDIM':
        hata(g['anahtar'] in ('standart_gunluk_saat','fazla_mesai_katsayilari','gun_sonu_raporu_zorunlu','gun_sonu_hatirlatma','izin_ik_onayi','proje_gorunurlugu','sessiz_kabul_is_gunu'), 'T8 ayari')
        if g['anahtar']=='standart_gunluk_saat': hata(type(g['deger']) in (int,float) and 0 < g['deger'] <= 24,'Standart saat')
        if g['anahtar']=='fazla_mesai_katsayilari': hata(isinstance(g['deger'],dict) and set(g['deger'])=={'TATIL','PAZAR','CUMARTESI','HAFTA_ICI'} and all(type(x) in (int,float) and 1 <= x < float('inf') for x in g['deger'].values()),'Katsayi en az bir')
        if g['anahtar']=='gun_sonu_raporu_zorunlu': hata(type(g['deger']) is bool,'Zorunluluk bool')
    if kod == 'GUN.TANIMLADIM':
        hata(g['tur'] in ('TATIL','YARIM_GUN','OZEL_MESAI'),'Gun turu')
        if g['tur'] != 'TATIL':
            from .takvim_v7 import saat_ani
            a,b = saat_ani(g['tarih'],g['mesai_baslangic']),saat_ani(g['tarih'],g['mesai_bitis'])
            hata(a<b,'Gun mesaisi')
            araliklar=[]
            for x in g['sabit_molalar']:
                p,q=saat_ani(g['tarih'],x['bas']),saat_ani(g['tarih'],x['bit'])
                hata(a<=p<q<=b and not any(kesisim(p,q,c,d) for c,d in araliklar),'Mola araligi')
                araliklar.append((p,q))
    if kod in ('EK_MESAI.PLANLADIM','EK_MESAI.ONAYLADIM'):
        a,b=pencere(g); hata(a<b,'Ek mesai araligi'); hata(bool(hedefler(e,'IS')+hedefler(e,'GOREV')),'Ek mesai hedefi')
    if kod in ('IZIN.TALEP_ETTIM','TEZGAH.BAKIM_PLANLADIM'): hata(an(g['baslangic'])<an(g['bitis']),'Tarih araligi')
    if kod=='IZIN.TALEP_ETTIM': hata(g['tur'] in ('YILLIK','SAATLIK','MAZERET','UCRETLI','UCRETSIZ','SAGLIK','SERBEST_ZAMAN'),'Izin turu')
    if kod=='DURUS.BASLADI': hata(g['kapsam']=='FIRMA' or isinstance(g['kapsam'],list) and bool(g['kapsam']) and len(set(g['kapsam']))==len(g['kapsam']),'Durus kapsami')
    if kod=='TEZGAH.TAKVIM_TANIMLADIM':
        from .takvim_v7 import saat_ani
        hata(isinstance(g['vardiyalar'],list) and bool(g['vardiyalar']),'Vardiyalar')
        for x in g['vardiyalar']:
            hata(bool(x['gunler']) and set(x['gunler']) <= set(range(1,8)), 'Vardiya gunleri')
            hata(saat_ani('2026-01-01',x['bas'])<saat_ani('2026-01-01',x['bit']), 'Vardiya araligi')
    if kod.startswith('SORUMLULUK.'):
        if kod.endswith('DOGRULADIM'): hata(g['karar'] in ('ONAY','DEGISTIR','KALDIR'),'Dogrulama karari')
        if kod.endswith('ITIRAZI_DEGERLENDIRDIM'): hata(g['karar'] in ('KABUL','RET'),'Itiraz karari')
        if g.get('karar')=='DEGISTIR': hata('yuzde' in g,'Yeni yuzde gerekli')
        if 'yuzde' in g: hata(type(g['yuzde']) in (int,float) and 0 <= g['yuzde'] <= 100,'Yuzde')
    if kod=='NESNE_TURU.TANIMLADIM':
        asamalar=[s['kod'] if isinstance(s,dict) else s for s in g['asamalar']]
        hata(bool(asamalar) and len(set(asamalar))==len(asamalar) and g['baslangic_asamasi'] in asamalar,'Nesne asamalari')
        hata(all(x['den'] in asamalar and x['e'] in asamalar and x['den']!=x['e'] and 'kimler' in x for x in g['gecisler']),'Nesne gecisleri')


def ek_kapi(d,e,g,kisi):
    a,b=pencere(g); t=an(e['oldugu_an']); damga=e['eylem_kodu']=='EK_MESAI.ONAYLADIM'
    if damga:
        if b>t or a<t-timedelta(days=7): return False
    elif a<=t: return False
    if not all(istihdamda(d,kisi,x) for x in gunler(a,b-timedelta(microseconds=1))): return False
    if any(kesisim(a,b,p,q) for tarih in gunler(a,b) for p,q in normal(d,tarih,False,kisi)): return False
    from .takvim_v7 import izinler
    if any(kesisim(a,b,p,q) for p,q in izinler(d,kisi)): return False
    for x in d.ek_mesai_planlari.values():
        if x['kimlik']==e['olay_kimligi'] or x['kimlik'].startswith(e['olay_kimligi']+'/ek/'): continue
        if x['kisi']!=kisi or x.get('iptal'): continue
        p,q=pencere(x)
        if not kesisim(a,b,p,q): continue
        # Beyaz yaka gercekleseni ayni plan icinde damgalar. Plan + gercek iki mesai degildir.
        if damga and d.kisiler[kisi]['yaka']=='BEYAZ' and not x['damga'] and p<=a<b<=q: continue
        return False
    return True


def durum(d,e):
    kod,g,t=e['eylem_kodu'],e['girdiler'],an(e['oldugu_an'])
    for s in g.get('isler',g.get('gorevler',[g.get('degisenler',g)])):
        if s.get('nesne') and s['nesne'] not in d.nesneler: return False
    if kod in ('IS.ATADIM','GOREV.ATADIM') and getattr(d,'_an',None) is None:
        for s in g.get('gorevler',[g]):
            if s.get('ek_mesai') and not all(ek_kapi(d,e,s['ek_mesai'],k) for k in s.get('kisiler',[s.get('kisi')])): return False
    if kod in ('IS.REDDETTIM','GOREV.REDDETTIM'):
        if any(x['kimlik'] not in (d.kisiler if x['tur']=='KISI' else d.birimler) for x in g.get('sorumlular',[])): return False
    if kod not in SEMALAR: return None
    x=hedef_satir(d,e)
    if kod.startswith('GUN.'): return gun(g['tarih'])>t.date()
    if kod in ('EK_MESAI.PLANLADIM','EK_MESAI.ONAYLADIM'): return ek_kapi(d,e,g,g['kisi'])
    if kod=='EK_MESAI.IPTAL_ETTIM': return x is not g and not x['iptal'] and t<pencere(x)[0]
    if kod=='IZIN.TALEP_ETTIM':
        a,b=an(g['baslangic']),an(g['bitis'])
        return (a>=t or a.isocalendar()[:2]==t.isocalendar()[:2]) and all(istihdamda(d,g['kisi'],z) for z in gunler(a,b-timedelta(microseconds=1)))
    if kod.startswith('IZIN.'):
        if x is g: return False
        if kod in ('IZIN.ONAYLADIM','IZIN.IK_ONAYLADIM'):
            bek='TALEP' if kod=='IZIN.ONAYLADIM' else 'IK_BEKLIYOR'
            return x['durum']==bek and all(istihdamda(d,x['kisi'],z) for z in gunler(x['baslangic'],an(x['bitis'])-timedelta(microseconds=1))) and not any(y['kimlik']!=x['kimlik'] and y['kisi']==x['kisi'] and y['durum']=='ONAYLI' and kesisim(an(x['baslangic']),an(x['bitis']),an(y['baslangic']),an(y['bitis'])) for y in d.izinler.values())
        return x['durum'] not in ('IPTAL','REDDEDILDI','RET') and (kod!='IZIN.REDDETTIM' or x['durum'] in ('TALEP','IK_BEKLIYOR'))
    if kod=='TEZGAH.TAKVIM_TANIMLADIM': return g['tezgah'] in d.tezgahlar and gun(g['gecerli_baslangic'])>t.date()
    if kod=='TEZGAH.BAKIM_PLANLADIM': return g['tezgah'] in d.tezgahlar and an(g['baslangic'])>t
    if kod=='TEZGAH.BAKIM_IPTAL_ETTIM': return x is not g and not x['iptal'] and t<an(x['baslangic'])
    if kod=='PLAN.ONAYLADIM':
        return d.projeler.get(g['proje'],{}).get('aktif',False) and any(x['proje']==g['proje'] for x in d.etaplar.values()) and (not d.plan_surumleri.get(g['proje']) or bool(g.get('gerekce','').strip()))
    if kod.startswith('GUN_SONU.'):
        if gun(g['gun'])>t.date(): return False
        if kod=='GUN_SONU.GONDERDIM': return True
        from .gorunum_v7 import gun_sonu_raporu
        rapor=gun_sonu_raporu(d,g['kisi'],g['gun'])
        if kod.endswith('ONAYLADIM'): return rapor['durum'] in ('GONDERILDI','DEGISTI') and rapor['ozet_surumu']==g['ozet_surumu']
        return rapor['durum'] in ('GONDERILDI','DEGISTI')
    if kod.startswith('SORUMLULUK.'):
        if not x: return False
        if kod.endswith('ITIRAZ_ETTIM'): return not x.get('itirazda') and x['yuzde']>0
        if kod.endswith('ITIRAZI_DEGERLENDIRDIM') and not x.get('itirazda'): return False
        yeni=g.get('yuzde',x['yuzde'])
        return sum(y['yuzde'] for y in d.sorumluluklar.values() if y['ret']==x['ret'] and y['satir']!=x['satir'])+yeni <= 100
    if kod=='NESNE.ACTIM':
        from .kurallar_v10_2 import nesne_projesi
        g = dict(g, proje=nesne_projesi(g))
        tur=d.nesne_turleri.get(g['tur'],{})
        return bool(tur) and not any(x['tur']==g['tur'] and x['ad']==g['ad'] and x.get('proje')==g.get('proje') for x in d.nesneler.values()) and istihdamda(d,g['sorumlu'],t) and (not g.get('proje') or d.projeler.get(g['proje'],{}).get('aktif')) and baglar_gecerli(d,tur,g.get('baglar',[]))
    if kod=='NESNE_TURU.TANIMLADIM':
        asamalar={s['kod'] if isinstance(s,dict) else s for s in g['asamalar']}
        for x in d.nesneler.values():
            if x['tur']!=g['kod']: continue
            yol=[y['asama'] for y in x['asama_gecmisi']]+[x['asama']]
            if not set(yol)<=asamalar: return False
            if any(not any(z['den']==a and z['e']==b for z in g['gecisler']) for a,b in zip(yol,yol[1:])): return False
        return True
    if kod=='NESNE.ASAMA_GECIRDIM':
        if x is g: return False
        tur=d.nesne_turleri[x['tur']]
        son={s['kod'] for s in tur['asamalar'] if isinstance(s,dict) and s.get('son')}
        return x['asama'] not in son and any(s['den']==x['asama'] and s['e']==g['yeni_asama'] for s in tur['gecisler'])
    if kod=='NESNE.GUNCELLEDIM':
        s=g['degisenler']
        return x is not g and set(s)<={'ad','baglar','sorumlu','kod'} and (not s.get('sorumlu') or s['sorumlu'] in d.kisiler) and baglar_gecerli(d,d.nesne_turleri[x['tur']],s.get('baglar',[]))
    return True


def baglar_gecerli(d,tur,baglar):
    from .kabul import nesne
    return all(x['tur'] in tur['baglanabilir_turler'] and bool(nesne(d,x['tur'],x['kimlik'])) for x in baglar)


def bildirim(m,e,kod,alicilar,metin=''):
    for k in sorted(alicilar): m.bildir(e,kod,k,an(e['oldugu_an']),metin)


def isle(m,e):
    kod,g,oid,t=e['eylem_kodu'],e['girdiler'],e['olay_kimligi'],an(e['oldugu_an'])
    if kod not in SEMALAR: return False
    if kod.startswith('DURUS.'):
        if kod=='DURUS.BASLADI':
            if any(x['bitis'] is None and (x['kapsam']=='FIRMA' or g['kapsam']=='FIRMA' or any(birim_kapsamda(m,b,x['kapsam']) for b in g['kapsam']) or any(birim_kapsamda(m,b,g['kapsam']) for b in x['kapsam'])) for x in m.duruslar.values()):
                m.supheli(e,'Ayni kapsamda acik durus'); return True
            m.duruslar[oid]=dict(deepcopy(g),kimlik=oid,baslangic=t,bitis=None)
            x=m.duruslar[oid]
        else:
            x=m.duruslar.get(g['hedef'])
            if not x or x['bitis'] is not None: m.supheli(e,'Acik durus yok'); return True
            x['bitis']=t
        alicilar=set().union(*(yoneticiler(m,b)|birim_ustleri(m,b) for b in m.birimler if birim_kapsamda(m,b,x['kapsam'])))
        bildirim(m,e,'R34',alicilar)
        from .takvim_v7 import katman_guncelle
        katman_guncelle(m,t)
    elif kod=='TEZGAH.TAKVIM_TANIMLADIM': m.tezgah_takvimleri[oid]=dict(deepcopy(g),kimlik=oid)
    elif kod=='TEZGAH.BAKIM_PLANLADIM': m.bakimlar[oid]=dict(deepcopy(g),kimlik=oid,iptal=False)
    elif kod=='TEZGAH.BAKIM_IPTAL_ETTIM': m.bakimlar[g['hedef']]['iptal']=True
    elif kod.startswith('TEZGAH.DURUS_'):
        acik=next((x for x in m.tezgah_duruslari.values() if x['tezgah']==g['tezgah'] and not x['bitis']),None)
        if kod.endswith('BILDIRDIM'):
            if acik: m.supheli(e,'Tezgah durusu acik')
            else: m.tezgah_duruslari[oid]=dict(deepcopy(g),kimlik=oid,baslangic=t,bitis=None)
        elif not acik: m.supheli(e,'Acik tezgah durusu yok')
        else: acik['bitis']=t
    elif kod.startswith('IZIN.'):
        x=hedef_satir(m,e)
        bildirim(m,e,'R35' if kod.endswith('TALEP_ETTIM') else 'R36',ustler(m,x['kisi']) if kod.endswith('TALEP_ETTIM') else {x['kisi']})
    elif kod.startswith('GUN_SONU.'):
        k=g.get('kisi',e.get('adina') or e['kim']); anahtar=k+':'+g['gun']
        x=m.gun_sonu_raporlari.setdefault(anahtar,dict(kisi=k,gun=g['gun'],durum='TASLAK',gecmis=[]))
        x['gecmis'].append(deepcopy(e))
        if kod.endswith('GONDERDIM'): x.update(durum='GONDERILDI',aciklama=g['aciklama'],tanimsiz_aciklama=g['tanimsiz_aciklama'])
        elif kod.endswith('IADE_ETTIM'): x.update(durum='IADE',iade_gerekcesi=g['gerekce'])
        else: x.update(durum='ONAYLANDI',onaylanan_ozet_surumu=g['ozet_surumu'],onaylayan=e['kim'],onay_ani=t, onay_olayi=oid)
    elif kod=='PLAN.ONAYLADIM':
        ss=m.plan_surumleri.setdefault(g['proje'],[])
        kaynak=m
        kabul_ani=an(e.get('bulut_ulasma_ani',e['oldugu_an']))
        if any(x['eylem_kodu'].startswith('ETAP.') and an(x['oldugu_an'])<=t and an(x.get('bulut_ulasma_ani',x['oldugu_an']))>kabul_ani for x in m.olaylar):
            from .motor import Motor
            from .saat import Saat
            kaynak=Motor(Saat(t))
            kaynak.yurut([x for x in m.olaylar if not x['eylem_kodu'].startswith('PLAN.') and an(x.get('bulut_ulasma_ani',x['oldugu_an']))<=kabul_ani])
        etaplar={k:{a:v[a] for a in ('ad','birim','baslangic','bitis','hedef_saat')} for k,v in kaynak.etaplar.items() if v['proje']==g['proje']}
        ss.append(dict(no='B'+str(len(ss)),proje=g['proje'],onay_ani=t,onaylayan=e['kim'],gerekce=g.get('gerekce'),etaplar=deepcopy(etaplar)))
    elif kod.startswith('SORUMLULUK.'):
        x=hedef_satir(m,e)
        if not x: m.supheli(e,'Sorumluluk yok'); return True
        x.setdefault('gecmis',[]).append(deepcopy(e))
        if kod.endswith('DOGRULADIM'):
            x['dogrulandi']=True
            if g['karar']=='KALDIR': x['yuzde']=0
            if g['karar']=='DEGISTIR': x['yuzde']=g['yuzde']
        elif kod.endswith('ITIRAZ_ETTIM'):
            x['itirazda']=True; m.itirazlar[oid]=dict(sorumluluk=x['satir'],karar=None)
            bildirim(m,e,'R39',satir_ustleri(m,x))
        else:
            x['itirazda']=False; m.itirazlar[g['hedef']]['karar']=g['karar']
            if g['karar']=='KABUL': x['yuzde']=g.get('yuzde',0)
    elif kod=='NESNE_TURU.TANIMLADIM': m.nesne_turleri[g['kod']]=deepcopy(g)
    elif kod=='NESNE.ACTIM':
        from .kurallar_v10_2 import nesne_projesi
        if nesne_projesi(g): g = dict(g, proje=nesne_projesi(g))
        m.nesneler[oid]=dict(deepcopy(g),kimlik=oid,asama=m.nesne_turleri[g['tur']]['baslangic_asamasi'],asama_ani=t,olusma_ani=t,olusturan=e['kim'],asama_gecmisi=[],olaylar=[oid],dosyalar=deepcopy(e['kanit']))
    elif kod.startswith('NESNE.'):
        x=m.nesneler[g['hedef']]; x['olaylar'].append(oid); x['dosyalar'].extend(deepcopy(e['kanit']))
        if kod.endswith('GUNCELLEDIM'): x.update(deepcopy(g['degisenler']))
        else:
            x['asama_gecmisi'].append(dict(asama=x['asama'],baslangic=x['asama_ani'],bitis=t))
            x.update(asama=g['yeni_asama'],asama_ani=t)
    return True


def sonra(m,e):
    kod,g,oid=e['eylem_kodu'],e['girdiler'],e['olay_kimligi']
    if kod in ('IS.REDDETTIM','GOREV.REDDETTIM') and oid not in m.supheliler:
        ss=g.get('sorumlular',([dict(tur='KISI',kimlik=g['sebep_olan'],yuzde=100)] if g.get('sebep_olan') else []))
        for n,s in enumerate(ss,1):
            key=oid+'/'+str(n)
            x=dict(deepcopy(s),satir=key,ret=oid,an=e['oldugu_an'],dogrulandi=False,itirazda=False,kanit=deepcopy(e['kanit']),hedef=deepcopy(e['neyin_ustunde']))
            ustler = satir_ustleri(m,x)
            x['dogrulandi'] = e['kim'] != x['kimlik'] and e['kim'] in ustler
            m.sorumluluklar[key]=x
            if not x['dogrulandi']: bildirim(m,e,'R38',ustler)
    if kod in ('IS.ATADIM','IS.DEVRETTIM','GOREV.ATADIM'):
        kisiler=g.get('kisiler',[g.get('kime') or g.get('kisi')]) if not kod.startswith('GOREV') else [s['kisi'] for s in g['gorevler']]
        for kisi in kisiler:
            if kisi in m.kisiler and m.kisiler.get(kisi,{}).get('birim') != m.kisiler.get(e['kim'],{}).get('birim'):
                bildirim(m,e,'R30',yoneticiler(m,m.kisiler[kisi]['birim']),kisi)
    if kod in ('IS.TANIMLADIM','GOREV.ATADIM','IS.BAGLANTI_DUZELTTIM'):
        bag=next((h['kimlik'] for h in e['neyin_ustunde'] if h['tur']=='NESNE'),None)
        if bag:
            for x in list(m.isler.values())+list(m.gorevler.values()):
                if x.get('doguran_olay')==oid or x['kimlik'] in hedefler(e,'IS'): x['nesne']=bag
    if kod in ('IS.ATADIM','GOREV.ATADIM','IZIN.ONAYLADIM','IZIN.IK_ONAYLADIM'):
        for izin in m.izinler.values():
            if izin['durum']!='ONAYLI': continue
            kisi=izin['kisi']; a,b=an(izin['baslangic']),an(izin['bitis'])
            adaylar=[v for v in m.gorevler.values() if v.get('kisi')==kisi and v.get('teslim_tarihi') and a.date()<=gun(v['teslim_tarihi'])<=b.date() and v['durum'] not in ('BITTI','IPTAL')]
            adaylar += [m.isler[k] for k in m.listeler.get(kisi,[]) if m.isler[k]['durum'] in ('SIRADA','ON_IS_BEKLIYOR')]
            for x in adaylar: bildirim(m,e,'R37',{k for k in (izin.get('onaylayan'),x.get('veren') or x.get('atayan')) if k},kisi)


def tamamla(m):
    from .takvim_v7 import cikar, birim_kapsamda
    sonuc=[]
    for a in m.araliklar:
        if a['kova']!='TEZGAH': sonuc.append(a); continue
        b=m.tezgahlar.get(a['tezgah'],{}).get('birim')
        engeller=[(x['baslangic'],x['bitis'] or m.saat.simdi()) for x in m.duruslar.values() if birim_kapsamda(m,b,x['kapsam'])]
        engeller += [(x['baslangic'],x['bitis'] or m.saat.simdi()) for x in m.tezgah_duruslari.values() if x['tezgah']==a['tezgah']]
        for p,q in cikar([(a['baslangic'],a['bitis'] or m.saat.simdi())],engeller): sonuc.append(dict(a,baslangic=p,bitis=q))
    m.araliklar=sonuc
    for g in m.gorevler.values():
        if g['tur']=='REVIZYON':
            sorumlu=any(x['ret']==g['doguran_olay'] and x['tur']=='KISI' and x['kimlik']==g['kisi'] and x['yuzde']>0 and x['dogrulandi'] and not x['itirazda'] for x in m.sorumluluklar.values())
            g['sorumlulugu_dogrulandi']=sorumlu
            from .gorev import puan
            g['is_puani']=puan(g)
    for x in list(m.isler.values())+list(m.gorevler.values()):
        parca=x.get('parca_kodu')
        bag=next((n['kimlik'] for n in m.nesneler.values() if n['tur']=='PARCA' and n['ad']==parca and n.get('proje')==x.get('proje')),None)
        if bag: x['nesne']=bag
