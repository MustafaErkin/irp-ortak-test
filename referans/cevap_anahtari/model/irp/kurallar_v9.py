"""T9: olay kapilari ve kaynak olaylardan uretilen ek kayitlar.

Acik tasarim yorumlari codex/sonuclar/tur12_yorumlar.md'dedir.
"""
from copy import deepcopy
from decimal import Decimal
from datetime import timedelta
from .saat import an, gun, gun_ani

SEMALAR = {
    'PROJE.KOD_DEGISTIRDIM': ('kod', 'gerekce'),
    'PROJE.ERISIM_VERDIM': ('proje', 'kisi', 'gerekce'),
    'PROJE.ERISIM_KALDIRDIM': ('proje', 'kisi', 'gerekce'),
    'GECIKME.DEGERLENDIRDIM': ('hedef', 'neden', 'sorumlular', 'gerekce'),
    'GUN_ONAYI.AYARLADIM': ('birim', 'gerekli', 'gecerli_baslangic'),
    'BILDIRIM.GORDUM': ('bildirimler',),
}
TABLOLAR = ('gecikme_degerlendirmeleri', 'proje_erisimleri', 'gun_onay_ayarlari',
            'bildirim_gorulmeleri')
DURUS_NEDENLERI = {
    'CALISAN': ('KENDI', 'DIGER'),
    'MALZEME': ('EKSIK', 'HATALI', 'GECIKTI', 'DIGER'),
    'MAKINE': ('CNC', 'TORNA', 'KAYNAK', 'DIGER'),
    'BEKLEME': ('BIRIM', 'MUSTERI', 'BILGI', 'DIGER'),
    'TEKNIK': ('RESIM', 'OLCU', 'LISTE', 'TASARIM', 'DIGER'),
    'HATA': ('KIRILMA', 'BOZULMA', 'DIGER'),
    'ISLETME': ('ELEKTRIK', 'TOPLANTI', 'EGITIM', 'YONLENDIRME', 'DIGER'),
}


def varsayilan_yetkiler():
    return [dict(eylem_kodu=k, kimler=r, kapsam='FIRMA') for k, r in (
        ('PROJE.KOD_DEGISTIRDIM', ['YETKILI']),
        ('PROJE.HEPSINI_GORUR', ['YONETICI', 'YETKILI']),
        ('PROJE.ERISIM_VERDIM', ['YONETICI', 'YETKILI']),
        ('PROJE.ERISIM_KALDIRDIM', ['YONETICI', 'YETKILI']),
        ('IZIN.IK_ONAYLADIM', ['IK', 'YETKILI']),
        ('IZIN.REDDETTIM', ['IK', 'YETKILI']),
        ('GUN_ONAYI.AYARLADIM', ['YETKILI']))]


def olaylar(d):
    # Depo ham gunlugu da saklar; T9 okumalar etkin motor kaynagini kullanir.
    kaynak = (getattr(d,'gorunum',None) or d).olaylar
    es=list(kaynak.values()) if hasattr(kaynak,'values') else list(kaynak)
    pasif={x['girdiler']['hedef'] for x in es if x['eylem_kodu']=='KAYIT.GECERSIZ_SAYDIM'}
    return [x for x in es if x['olay_kimligi'] not in pasif]


def hedef_proje(e):
    from .olay import hedefler
    return e['girdiler'].get('proje') or next(iter(hedefler(e, 'PROJE')), None)


def onay_satirlari(g):
    return g.get('gunler', [g])


def sorumluluk_satiri(d, g):
    h = g.get('hedef')
    if h in d.itirazlar: h = d.itirazlar[h]['sorumluluk']
    if 'satir' in g: h = h + '/' + str(g['satir'])
    return d.sorumluluklar.get(h, {})


def neden_satiri(d, kod):
    if not isinstance(kod, str): return {}
    ad = kod.removeprefix('DURUS_NEDENI.')
    return d.kod_listesi.get('DURUS_NEDENI:' + ad, {})


def neden_bicimi(d, kod, aciklama='', eski=False):
    # Tarihsel ARIZA tanikligi V8'de liste/pasiflik kapisindan gecmiyordu.
    if eski and isinstance(kod,str) and kod.startswith('ARIZA.'): return
    s = neden_satiri(d, kod)
    if not s.get('aktif') or not s.get('ust'):
        raise ValueError('DURUS_NEDENI aktif alt nedeni gerekli')
    if str(kod).endswith('_DIGER') and not str(aciklama or '').strip():
        raise ValueError('Diger nedeninde aciklama gerekli')


def pay_bicimi(ss, tam=False, dis=False):
    if not isinstance(ss, list) or any(not isinstance(s, dict) for s in ss):
        raise ValueError('Sorumlular dizi olmali')
    toplam = Decimal(0)
    anahtarlar = set()
    for s in ss:
        if s.get('tur') not in (('KISI', 'BIRIM', 'DIS') if dis else ('KISI', 'BIRIM')):
            raise ValueError('Sorumlu turu')
        if not isinstance(s.get('kimlik'), str) or not s['kimlik']:
            raise ValueError('Sorumlu kimligi')
        if type(s.get('yuzde')) not in (int, float) or not 0 <= s['yuzde'] <= 100:
            raise ValueError('Sorumlu yuzdesi')
        if s['tur'] == 'DIS' and s['kimlik'] not in ('MUSTERI', 'TEDARIKCI', 'ISLETME'):
            raise ValueError('Dis sorumlu kimligi')
        key = (s['tur'], s['kimlik'])
        if key in anahtarlar: raise ValueError('Tekil sorumlular')
        anahtarlar.add(key)
        toplam += Decimal(str(s['yuzde']))
    if (tam and toplam != 100) or toplam > 100:
        raise ValueError('Sorumluluk toplami tam 100' if tam else 'Sorumluluk toplami en cok 100')


def bicim(d, e):
    kod, g = e['eylem_kodu'], e['girdiler']
    if kod in ('SORUMLULUK.DOGRULADIM','SORUMLULUK.ITIRAZI_DEGERLENDIRDIM'):
        x=sorumluluk_satiri(d,g)
        if x.get('kaynak_turu') != 'GECIKME' and not str(g.get('gerekce') or '').strip():
            raise ValueError('Hata sorumlulugunda gerekce gerekli')
    if kod == 'PROJE.KOD_DEGISTIRDIM' and not hedef_proje(e):
        raise ValueError('Proje hedefi gerekli')
    if kod in ('PROJE.ACTIM', 'PROJE.KOD_DEGISTIRDIM'):
        if not isinstance(g.get('kod'), str) or not g['kod'].strip(): raise ValueError('Proje kodu')
        if g.get('ek') is not None and not isinstance(g['ek'], str): raise ValueError('Proje eki metin')
        if 'kimlik' in g and (not isinstance(g['kimlik'], str) or not g['kimlik']): raise ValueError('Proje kimligi')
    if kod == 'AYAR.DEGISTIRDIM':
        if g['anahtar'] == 'sessiz_kabul_is_gunu' and (type(g['deger']) is not int or g['deger'] < 0): raise ValueError('Sessiz kabul negatif olmayan tam is gunu')
        if g['anahtar'] == 'proje_gorunurlugu' and g['deger'] not in ('HERKES', 'UYELER'): raise ValueError('Proje gorunurlugu')
        if g['anahtar'] == 'izin_ik_onayi' and (not isinstance(g['deger'], dict) or any(type(v) is not bool for v in g['deger'].values()) or set(g['deger']) - {'YILLIK','SAATLIK','MAZERET','UCRETLI','UCRETSIZ','SAGLIK','SERBEST_ZAMAN'}): raise ValueError('Izin IK ayari')
    if kod == 'IS.ARIZA_BILDIRDIM':
        if g.get('neden'): neden_bicimi(d, g['neden'], g.get('not'), eski=True)
        elif not isinstance(g.get('not'), str) or not g['not'].strip(): raise ValueError('Duruş nedeni veya not gerekli')
    if kod in ('ETAP.TANIMLADIM', 'ETAP.DEGISTIRDIM'):
        s = g.get('degisenler', g)
        if s.get('sorumlu') is not None and not isinstance(s['sorumlu'], str): raise ValueError('Etap sorumlusu kisi kimligi')
    if kod == 'GOREV.TAMAMLADIM' and g.get('gecikme_nedeni'):
        neden_bicimi(d, g['gecikme_nedeni'], g.get('gecikme_aciklamasi'))
    if kod == 'GECIKME.DEGERLENDIRDIM':
        neden_bicimi(d, g['neden'], g['gerekce'])
        pay_bicimi(g['sorumlular'], tam=True, dis=True)
    if kod == 'GUN_ONAYI.AYARLADIM':
        if type(g['gerekli']) is not bool: raise ValueError('Gerekli bool')
        gun(g['gecerli_baslangic'])
    if kod == 'GUN_SONU.ONAYLADIM':
        ss = onay_satirlari(g)
        if not isinstance(ss, list) or not ss or any(not isinstance(s, dict) or not {'kisi','gun','ozet_surumu'} <= set(s) for s in ss): raise ValueError('Gun onay satirlari')
        if len({(s['kisi'],s['gun']) for s in ss}) != len(ss): raise ValueError('Gun onayi tekil')
        for s in ss: gun(s['gun'])
    if kod == 'BILDIRIM.GORDUM':
        if not isinstance(g['bildirimler'], list) or not g['bildirimler'] or any(not isinstance(x, str) for x in g['bildirimler']): raise ValueError('Bildirim kimlikleri')
    if kod == 'BIRIM.TANIMLADIM' and 'takvim' in g:
        from .takvim_v7 import saat_ani, kesisim
        t = g['takvim']; gun(g['takvim_gecerli'])
        if not isinstance(t, dict) or not set(t.get('gunler', [])) <= set(range(1,8)) or not t.get('gunler'): raise ValueError('Birim takvim gunleri')
        a, b = (saat_ani('2026-01-01', t[x]) for x in ('mesai_baslangic','mesai_bitis'))
        if a >= b: raise ValueError('Takvim araligi')
        molalar = []
        for x in t['sabit_molalar']:
            p,q = saat_ani('2026-01-01', x['bas']), saat_ani('2026-01-01', x['bit'])
            if not a <= p < q <= b or any(kesisim(p,q,u,v) for u,v in molalar): raise ValueError('Takvim molasi')
            molalar.append((p,q))
        if sum((q-p).total_seconds() for p,q in molalar) >= (b-a).total_seconds(): raise ValueError('Takvim net saati pozitif')
    if kod == 'IS.TAMAMLADIM' and g.get('makine_bitis_ani'):
        from .olay import hedefler
        i = d.isler.get(next(iter(hedefler(e,'IS')), None), {})
        bas = makine_baslangici(d, i)
        if i.get('tezgah_rolu') != 'AL' or not bas or not bas <= an(g['makine_bitis_ani']) <= an(e['oldugu_an']): raise ValueError('Makine bitis araligi')
    ss = g.get('gorevler', g.get('isler', [g.get('degisenler', g)]))
    for s in ss:
        if 'oncelik' in s and s['oncelik'] not in ('NORMAL','YUKSEK','ACIL'): raise ValueError('Gorev onceligi')
        for alan in ('baslangic_tarihi','kesin_kabul_tarihi'):
            if s.get(alan): gun(s[alan])
        deg = s.get('degisiklik')
        if deg is not None:
            if not isinstance(deg, dict) or not isinstance(deg.get('kaynak'), str) or deg.get('neden') not in ('MUSTERI','HATA','IYILESTIRME'): raise ValueError('Degisiklik bicimi')
            if deg['neden'] != 'HATA' and deg.get('sorumlular'): raise ValueError('Yalniz hatada sorumlular')
            pay_bicimi(deg.get('sorumlular', []))


def tablo_izni(d, kim, kod):
    from .kurallar_v7 import rol_izni
    return any(r['eylem_kodu'] == kod and not r.get('gecerli_bitis') and rol_izni(d,kim,r) for r in d.yetki_kurallari)


def bildirim_bul(d, kimlik):
    if kimlik in getattr(d, 'modul_bildirimleri', {}): return d.modul_bildirimleri[kimlik]
    for key, s in d.bildirimler.items():
        if key == kimlik or bildirim_kimligi(s) == kimlik: return s
    return {}


def bildirim_kimligi(s):
    if s.get('kaynak', 'CEKIRDEK') != 'CEKIRDEK': return s['kimlik']
    return '/'.join((s['doguran_olay'], s['kural'], s['alici']))


def gecikme_hedefi(d, hedef):
    from .gorev import son_teslim_ani
    if hedef in d.gorevler:
        g = d.gorevler[hedef]
        son = son_teslim_ani(g, d)
        if g['tur'] in ('NORMAL','DEGISIKLIK') and g.get('ilk_teslim_ani') and son and an(g['ilk_teslim_ani']) > son:
            return dict(tur='GOREV', kisi=g['kisi'], birim=d.kisiler[g['kisi']]['birim'], proje=g.get('proje'), an=g['ilk_teslim_ani'], zaman_degeri=g['zaman_degeri'])
    e = next((x for x in olaylar(d) if x['olay_kimligi'] == hedef and x['eylem_kodu'] == 'IS.ARIZA_BILDIRDIM'), None)
    if e and hedef not in d.supheliler:
        from .olay import hedefler
        i = d.isler.get(next(iter(hedefler(e, 'IS')), None), {})
        return dict(tur='DURUS', kisi=e.get('adina') or e['kim'], birim=i.get('birim'), proje=i.get('proje'), an=e['oldugu_an'], zaman_degeri=0)
    return {}


def yetki(d, e):
    from .yetki_v6 import istihdamda, simdi, ustler, yoneticiler, birim_ustleri
    kod,g,kim = e['eylem_kodu'], e['girdiler'], e['kim']
    ilgili = kod in SEMALAR or kod == 'GUN_SONU.ONAYLADIM' or (kod.startswith('SORUMLULUK.') and ('satir' in g or g.get('hedef') in d.gecikme_degerlendirmeleri)) or kod == 'IZIN.IK_ONAYLADIM' or (kod == 'IZIN.REDDETTIM' and d.izinler.get(g.get('hedef'),{}).get('durum') == 'IK_BEKLIYOR')
    if not ilgili: return None
    if not istihdamda(d, kim, simdi(d)): return False
    if kod == 'BILDIRIM.GORDUM':
        return not e.get('adina') and all(not bildirim_bul(d,h) or bildirim_bul(d,h)['alici'] == kim for h in g['bildirimler'])
    if kod == 'PROJE.KOD_DEGISTIRDIM': return tablo_izni(d,kim,kod)
    if kod.startswith('PROJE.ERISIM_'): return kim == d.projeler.get(g['proje'],{}).get('sorumlu') or tablo_izni(d,kim,kod)
    if kod == 'GUN_ONAYI.AYARLADIM': return kim in birim_ustleri(d,g['birim']) or tablo_izni(d,kim,kod)
    if kod == 'GUN_SONU.ONAYLADIM': return all(kim != s['kisi'] and kim in ustler(d,s['kisi']) for s in onay_satirlari(g))
    if kod == 'GECIKME.DEGERLENDIRDIM':
        h = gecikme_hedefi(d,g['hedef'])
        if not h: return True  # Yetkili olmayan hedef DURUM kapisinda reddedilir.
        return kim != h['kisi'] and kim in (ustler(d,h['kisi']) if h['tur']=='GOREV' else yoneticiler(d,h['birim']) | birim_ustleri(d,h['birim']))
    if kod.startswith('IZIN.'):
        x = d.izinler.get(g['hedef'], {})
        return kim != x.get('kisi') and tablo_izni(d,kim,kod)
    x = sorumluluk_satiri(d,g)
    if not x or x['tur']=='DIS': return False
    if kod.endswith('ITIRAZ_ETTIM'): return kim == x['kimlik'] if x['tur']=='KISI' else kim in yoneticiler(d,x['kimlik'])
    from .kurallar_v7 import satir_ustleri
    return kim != x['kimlik'] and kim in satir_ustleri(d,x)


def ik_kalir(d, e):
    """Tum ileri rol/ayrilis/ayar sinirlarinda IK guvencesi."""
    es = [x for x in olaylar(d) if x['olay_kimligi'] != e['olay_kimligi']] + [e]
    if not any(x['eylem_kodu']=='AYAR.DEGISTIRDIM' and x['girdiler']['anahtar']=='izin_ik_onayi' and any(x['girdiler']['deger'].values()) for x in es): return True
    sinirlar = {an(e['oldugu_an'])}
    for x in es:
        g=x['girdiler']; kod=x['eylem_kodu']
        if kod=='KISI.DEGISTIRDIM': sinirlar.add(an(g['gecerli_baslangic']))
        if kod=='KISI.AYRILDI' and not g.get('iptal'): sinirlar.add(gun_ani(gun(g['ayrilis_tarihi'])+timedelta(days=1)))
        if kod=='AYAR.DEGISTIRDIM' and g['anahtar']=='izin_ik_onayi': sinirlar.add(an(g.get('gecerli_baslangic',x['oldugu_an'])))
    for t in sorted(sinirlar):
        if t < an(e['oldugu_an']): continue
        ayarlar=[x for x in es if x['eylem_kodu']=='AYAR.DEGISTIRDIM' and x['girdiler']['anahtar']=='izin_ik_onayi' and an(x['girdiler'].get('gecerli_baslangic',x['oldugu_an'])) <= t]
        acik = max(ayarlar, key=lambda x:(an(x['girdiler'].get('gecerli_baslangic',x['oldugu_an'])),x['olay_kimligi']))['girdiler']['deger'] if ayarlar else {}
        if not any(acik.values()): continue
        kisiler={}
        for x in sorted(es, key=lambda x:(an(x['girdiler'].get('gecerli_baslangic',x['oldugu_an'])),x['olay_kimligi'])):
            g=x['girdiler']; kod=x['eylem_kodu']
            if an(g.get('gecerli_baslangic',x['oldugu_an'])) > t: continue
            if kod=='KISI.EKLEDIM': kisiler[g['kod']]=dict(g)
            elif kod=='KISI.DEGISTIRDIM' and g['kisi'] in kisiler: kisiler[g['kisi']].update(g['degisenler'])
            elif kod=='KISI.AYRILDI' and g['kisi'] in kisiler: kisiler[g['kisi']]['ayrilis_tarihi']=None if g.get('iptal') else g['ayrilis_tarihi']
        if not any('IK' in p.get('roller',[]) and gun(p['giris_tarihi'])<=t.date() and (not p.get('ayrilis_tarihi') or t.date()<=gun(p['ayrilis_tarihi'])) for p in kisiler.values()): return False
    return True


def durum(d, e):
    from .yetki_v6 import istihdamda
    from .kapilar_v5 import aktif_kisi
    kod,g,t = e['eylem_kodu'], e['girdiler'], an(e['oldugu_an'])
    if kod in ('ETAP.TANIMLADIM', 'ETAP.DEGISTIRDIM'):
        s = g.get('degisenler', g)
        if s.get('sorumlu') and not aktif_kisi(d, s['sorumlu']): return False
    if kod in ('KISI.DEGISTIRDIM','KISI.AYRILDI') or (kod=='AYAR.DEGISTIRDIM' and g['anahtar']=='izin_ik_onayi'):
        if not ik_kalir(d,e): return False
    if kod=='KOD.TANIMLADIM' and g['liste']=='ROL' and g['kod']=='IK' and not g['aktif']:
        if any(d.ayar('izin_ik_onayi',t,{}).values()): return False
    if kod=='KOD.TANIMLADIM' and g['liste']=='DURUS_NEDENI':
        ust = g.get('ust')
        if ust:
            p = d.kod_listesi.get('DURUS_NEDENI:'+ust,{})
            return bool(p.get('aktif')) and not p.get('ust') and ust != g['kod'] and not any(x.get('liste')=='DURUS_NEDENI' and x.get('ust')==g['kod'] for x in d.kod_listesi.values())
        return not any(x.get('ust')==g['kod'] for x in d.kod_listesi.values()) or g['aktif']
    if kod in ('PROJE.ACTIM','PROJE.KOD_DEGISTIRDIM'):
        cift=(g['kod'],g.get('ek') or '')
        if any((h['kod'],h.get('ek') or '') == cift for p in d.projeler.values() for h in p['kod_gecmisi']): return False
        if kod.endswith('ACTIM'):
            if g.get('kimlik',g['kod']) in d.projeler: return False
            ana=g.get('ana_proje')
            if ana and (ana not in d.projeler or d.projeler[ana].get('ana_proje')): return False
            return not g.get('sorumlu') or aktif_kisi(d,g['sorumlu'])
        return hedef_proje(e) in d.projeler
    if kod=='PROJE.DEGISTIRDIM':
        s=g['degisenler']
        return d.projeler.get(hedef_proje(e),{}).get('aktif',False) and set(s)<={'ad','musteri','teslim_tarihi','baslangic_tarihi','kesin_kabul_tarihi','sorumlu'} and (not s.get('sorumlu') or aktif_kisi(d,s['sorumlu']))
    if kod.startswith('PROJE.ERISIM_'):
        if g['proje'] not in d.projeler or not aktif_kisi(d,g['kisi']): return False
        if kod.endswith('KALDIRDIM'):
            ss=[x for x in d.proje_erisimleri.values() if x['proje']==g['proje'] and x['kisi']==g['kisi']]
            return bool(ss) and max(ss,key=lambda x:(x['an'],x['kimlik']))['acik']
        return True
    if kod=='GUN_ONAYI.AYARLADIM': return g['birim'] in d.birimler and gun(g['gecerli_baslangic']) >= t.date()
    if kod=='GUN_SONU.ONAYLADIM':
        from .gorunum_v7 import gun_sonu_raporu
        for s in onay_satirlari(g):
            if gun(s['gun'])>t.date() or not istihdamda(d,s['kisi'],s['gun']): return False
            r=gun_sonu_raporu(d,s['kisi'],s['gun'])
            izin=('TASLAK','GONDERILDI','DEGISTI') if d.kisiler[s['kisi']]['yaka']=='MAVI' else ('GONDERILDI','DEGISTI')
            if r['durum'] not in izin or r['ozet_surumu'] != s['ozet_surumu']: return False
        return True
    if kod=='GUN_SONU.IADE_ETTIM' and d.kisiler.get(g['kisi'],{}).get('yaka')=='MAVI': return False
    if kod=='BILDIRIM.GORDUM': return all(bildirim_bul(d,x) for x in g['bildirimler'])
    if kod=='GECIKME.DEGERLENDIRDIM':
        return bool(gecikme_hedefi(d,g['hedef'])) and sorumlular_var(d,g['sorumlular'])
    if kod.startswith('SORUMLULUK.') and ('satir' in g or g.get('hedef') in d.gecikme_degerlendirmeleri):
        x=sorumluluk_satiri(d,g)
        if not x: return False
        from .kurallar_v7 import durum as eski
        k=deepcopy(e); k['girdiler']['hedef']=x['satir']; k['girdiler'].pop('satir',None)
        return eski(d,k)
    if kod=='BIRIM.TANIMLADIM' and 'takvim' in g and gun(g['takvim_gecerli']) <= t.date(): return False
    if kod in ('NESNE.ACTIM','NESNE.GUNCELLEDIM'):
        x=g if kod.endswith('ACTIM') else dict(d.nesneler.get(g['hedef'],{}), **g['degisenler'])
        yeni=g if kod.endswith('ACTIM') else g['degisenler']
        if 'kod' in yeni and x.get('kod'):
            if any(n['tur']==x.get('tur') and any(h['kod']==x['kod'] for h in n.get('kod_gecmisi',[])) for n in d.nesneler.values()): return False
        if kod.endswith('GUNCELLEDIM') and 'kod' in yeni:
            from .kurallar_v7 import durum as eski
            k=deepcopy(e); k['girdiler']['degisenler'].pop('kod')
            return eski(d,k)
    for s in g.get('gorevler',g.get('isler',[g] if kod=='IS.PLANSIZ_TANIMLADIM' else [])):
        deg=s.get('degisiklik')
        if deg:
            x=(d.gorevler if kod.startswith('GOREV') else d.isler).get(deg['kaynak'],{})
            if not x or x['durum']=='IPTAL' or (kod.startswith('GOREV') and x['tur'] not in ('NORMAL','REVIZYON','DEGISIKLIK')): return False
            if s.get('proje')!=x.get('proje') or not sorumlular_var(d,deg.get('sorumlular',[])): return False
    return None


def sorumlular_var(d, ss):
    return all(s['tur']=='DIS' or s['kimlik'] in (d.kisiler if s['tur']=='KISI' else d.birimler) for s in ss)


def makine_baslangici(d, i):
    baslar=[d.isler.get(x,{}) for x in i.get('on_isler',[])]
    return next((x.get('bitis_ani') or x.get('tamamlanma_ani') for x in baslar if x.get('tezgah_rolu')=='BASLAT' and x.get('tezgah')==i.get('tezgah') and x.get('parca_kodu')==i.get('parca_kodu')), None)


def sorumluluk_dogur(m, e, ss, hedef, kaynak_turu, onek=None):
    from .kurallar_v7 import satir_ustleri, bildirim
    for n,s in enumerate(ss,1):
        key=(onek or e['olay_kimligi'])+'/'+str(n)
        ustler=set() if s['tur']=='DIS' else satir_ustleri(m,s)
        m.sorumluluklar[key]=dict(deepcopy(s),satir=key,ret=onek or e['olay_kimligi'],an=e['oldugu_an'],dogrulandi=s['tur']=='DIS' or e['kim'] in ustler,itirazda=False,kanit=deepcopy(e['kanit']),hedef=deepcopy(hedef),kaynak_turu=kaynak_turu)
        if not m.sorumluluklar[key]['dogrulandi']: bildirim(m,e,'R38',ustler)


def isle(m,e):
    kod,g,oid,t=e['eylem_kodu'],e['girdiler'],e['olay_kimligi'],an(e['oldugu_an'])
    if kod=='PROJE.ACTIM':
        p=g.get('kimlik',g['kod'])
        m.projeler[p]=dict(deepcopy(g),kimlik=p,ek=g.get('ek') or '',aktif=True,
            kod_gecmisi=[dict(kod=g['kod'],ek=g.get('ek') or '',baslangic=t,bitis=None)])
        for a in ('ana_proje','sorumlu','baslangic_tarihi','kesin_kabul_tarihi'): m.projeler[p].setdefault(a,None)
    elif kod=='PROJE.KOD_DEGISTIRDIM':
        p=m.projeler[hedef_proje(e)]; p['kod_gecmisi'][-1]['bitis']=t
        p.update(kod=g['kod'],ek=g.get('ek') or '')
        p['kod_gecmisi'].append(dict(kod=p['kod'],ek=p['ek'],baslangic=t,bitis=None))
    elif kod.startswith('PROJE.ERISIM_'):
        m.proje_erisimleri[oid]=dict(deepcopy(g),kimlik=oid,an=t,yazan=e['kim'],acik=kod.endswith('VERDIM'))
        m.bildir(e,'R42',g['kisi'],t,g['proje'])
    elif kod=='GUN_ONAYI.AYARLADIM': m.gun_onay_ayarlari[oid]=dict(deepcopy(g),kimlik=oid,an=t)
    elif kod=='GECIKME.DEGERLENDIRDIM':
        h=gecikme_hedefi(m,g['hedef'])
        if not h: m.supheli(e,'Gecikme hedefi etkin degil'); return True
        m.gecikme_degerlendirmeleri[oid]=dict(deepcopy(g),kimlik=oid,an=t,yazan=e['kim'],kaynak=h)
        sorumluluk_dogur(m,e,g['sorumlular'],[dict(tur=h['tur'],kimlik=g['hedef'])],'GECIKME')
    elif kod=='BILDIRIM.GORDUM': m.bildirim_gorulmeleri[oid]=dict(deepcopy(g),kim=e['kim'],an=t)
    elif kod=='GUN_SONU.ONAYLADIM':
        from .kurallar_v7 import isle as eski
        for s in onay_satirlari(g):
            k=deepcopy(e); k['girdiler']=deepcopy(s)
            if 'not' in g: k['girdiler']['not']=g['not']
            eski(m,k)
    elif kod=='GUN_SONU.GONDERDIM':
        from .kurallar_v7 import isle as eski
        k=deepcopy(e); k['girdiler'].setdefault('aciklama',''); k['girdiler'].setdefault('tanimsiz_aciklama','')
        kisi=g.get('kisi') or e.get('adina') or e['kim']
        once=m.gun_sonu_raporlari.get(kisi+':'+g['gun'],{}).get('durum','TASLAK')
        eski(m,k)
        if m.kisiler.get(kisi,{}).get('yaka')=='MAVI': m.gun_sonu_raporlari[kisi+':'+g['gun']]['durum']=once
    elif kod.startswith('SORUMLULUK.') and ('satir' in g or g.get('hedef') in m.gecikme_degerlendirmeleri):
        from .kurallar_v7 import isle as eski
        x=sorumluluk_satiri(m,g)
        if not x: m.supheli(e,'Sorumluluk yok'); return True
        k=deepcopy(e); k['girdiler']['hedef']=x['satir']; k['girdiler'].pop('satir',None)
        if kod.endswith('ITIRAZI_DEGERLENDIRDIM'):
            itiraz=next((key for key,v in reversed(list(m.itirazlar.items())) if v['sorumluluk']==x['satir'] and v['karar'] is None),None)
            if not itiraz: m.supheli(e,'Acik itiraz yok'); return True
            k['girdiler']['hedef']=itiraz
        eski(m,k)
        if x.get('kaynak_turu')=='GECIKME' and kod.endswith('ITIRAZI_DEGERLENDIRDIM'):
            # Kararı veren sorumlunun üstüdür; ret kalan payı doğrular.
            x['dogrulandi']=True
    else: return False
    return True


def sonra(m,e):
    from .olay import hedefler
    from .gorev import son_teslim_ani
    from .yetki_v6 import yoneticiler
    kod,g,oid=e['eylem_kodu'],e['girdiler'],e['olay_kimligi']
    if kod=='GOREV.TAMAMLADIM':
        for key in hedefler(e,'GOREV'):
            x=m.gorevler.get(key,{})
            if x.get('tur') in ('NORMAL','DEGISIKLIK') and x.get('ilk_teslim_ani')==e['oldugu_an'] and an(x['ilk_teslim_ani'])>son_teslim_ani(x,m):
                x['gecikme_nedeni']=g.get('gecikme_nedeni') or ('BELIRTILMEDI' if str(g.get('gecikme_aciklamasi') or '').strip() else 'GIRILMEDI')
                if g.get('gecikme_aciklamasi'): x['gecikme_aciklamasi']=g['gecikme_aciklamasi']
                for k in yoneticiler(m,m.kisiler[x['kisi']]['birim'])-{x['kisi']}: m.bildir(e,'R40',k,an(e['oldugu_an']),key)
    if kod in ('GOREV.ATADIM','IS.TANIMLADIM','IS.PLANSIZ_TANIMLADIM'):
        tablo=m.gorevler if kod.startswith('GOREV') else m.isler
        for key,x in tablo.items():
            if x.get('doguran_olay')!=oid or not x.get('degisiklik'): continue
            deg=x['degisiklik']; x['degisiklik_kaynagi']=deg['kaynak']
            if kod.startswith('GOREV'): x['tur']='DEGISIKLIK'
            if deg['neden']=='HATA': sorumluluk_dogur(m,e,deg.get('sorumlular',[]),[dict(tur='GOREV' if kod.startswith('GOREV') else 'IS',kimlik=key)],'DEGISIKLIK',onek=key)
    if kod in ('NESNE.ACTIM','NESNE.GUNCELLEDIM'):
        x=m.nesneler.get(oid if kod.endswith('ACTIM') else g['hedef'])
        if x:
            x.setdefault('kod_gecmisi',[])
            s=g if kod.endswith('ACTIM') else g['degisenler']
            if 'kod' in s:
                if x['kod_gecmisi']: x['kod_gecmisi'][-1]['bitis']=an(e['oldugu_an'])
                if s['kod']: x['kod_gecmisi'].append(dict(kod=s['kod'],baslangic=an(e['oldugu_an']),bitis=None))
    if kod=='IZIN.ONAYLADIM':
        # hazirla() kapasite icin son durumu onceden kurar; bildirim olay anini kullanir.
        x=m.izinler.get(g['hedef'],{})
        if m.ayar('izin_ik_onayi',an(e['oldugu_an']),{}).get(x.get('tur'),False):
            for k,p in m.kisiler.items():
                from .yetki_v6 import istihdamda
                if 'IK' in p.get('roller',[]) and istihdamda(m,k,an(e['oldugu_an'])): m.bildir(e,'R41',k,an(e['oldugu_an']),x.get('kisi'))
            m.bildirimler.pop(oid+':R36:'+str(x.get('kisi')),None)
    if kod=='IS.TAMAMLADIM' and g.get('makine_bitis_ani'):
        for key in hedefler(e,'IS'):
            x=m.isler.get(key,{})
            if x.get('durum')=='BITTI': x['makine_bitis_ani']=an(g['makine_bitis_ani'])


def tamamla(m):
    from .gorev import puan
    for x in m.etaplar.values(): x.setdefault('sorumlu', None)
    for x in m.gorevler.values():
        x.setdefault('oncelik','NORMAL'); x.setdefault('degisiklik_kaynagi',None); x.setdefault('gecikme_nedeni',None)
        if x['tur']=='DEGISIKLIK':
            x['sorumlulugu_dogrulandi']=any(s['ret']==x['kimlik'] and s['tur']=='KISI' and s['kimlik']==x['kisi'] and s['dogrulandi'] and not s['itirazda'] and s['yuzde']>0 for s in m.sorumluluklar.values())
            x['is_puani']=puan(x)
    for s in m.kod_listesi.values(): s.setdefault('ust',None)
    for x in list(m.isler.values())+list(m.gorevler.values()):
        if not x.get('parca_kodu'): continue
        for n in m.nesneler.values():
            if n['tur']=='PARCA' and n.get('proje')==x.get('proje') and any(h['kod']==x['parca_kodu'] for h in n.get('kod_gecmisi',[])):
                x['nesne']=n['kimlik']; break
    gorulmeleri_yansit(m)


def gorulmeleri_yansit(m):
    for s in m.bildirimler.values(): s['gorulme_ani']=None
    for x in sorted(m.bildirim_gorulmeleri.values(),key=lambda x:x['an']):
        for h in x['bildirimler']:
            s=bildirim_bul(m,h)
            if s and s.get('gecerli') and s['alici']==x['kim'] and s['an']<=x['an'] and s.get('gorulme_ani') is None: s['gorulme_ani']=x['an']
