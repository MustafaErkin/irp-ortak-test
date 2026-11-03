"""T11 dış okuma kapısının listeleri, takvimleri ve görünür kaynak yükü."""
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
from .saat import an, gun, gun_ani
from .gorunum_v10_1 import pencere, plan_araligi

YENI_VERILER = {'KISILER','BIRIMLER','TEZGAHLAR','TAKVIM','ETAPLAR','NESNELER',
               'TOP_KIMDE','KAPASITE','TEZGAH_UYGUNLUK','TEZGAH_GOSTERGESI',
               'TEZGAH_UCRETI','ISCILIK_MALIYETI','LISTE','KAYNAK_YUKU'}
ESKI_VERILER = {'GANTT','PLAN_CAKISMALARI','SURUMLER','GECERLI_SURUM','BILDIRIMLER',
               'PROJE','ETAP','NOT','DOSYA','PLAN','KIM_NEREDE','SAAT_NEREYE_GITTI',
               'PERFORMANS','GUN','MAAS','SAAT_MALIYETI','IZIN','IZIN_DETAY','HAM_OLAY',
               'FAZLA_MESAI','NESNE','UYGUNLUK','BIRIM_PERFORMANS','PROJE_DURUM',
               'ETAP_DURUM','GOREV','IS'}


def tezgah_ucreti(d, key, tarih):
    from .gorunumler import tutar_bul
    v = tutar_bul(d, key, 'SAAT_UCRETI', tarih, None)
    return 'VERI_EKSIK' if v is None else Decimal(str(v))


def kaynak_satirlari(d, tur, key, bas, bit=None):
    a, b = pencere(bas, bit)
    if tur not in ('KISI', 'TEZGAH') or key not in (d.kisiler if tur == 'KISI' else d.tezgahlar):
        raise ValueError('Kaynak turu veya kimligi')
    for cins, tablo in [('IS', d.isler), ('GOREV', d.gorevler)]:
        for k, x in sorted(tablo.items()):
            if x['durum'] in ('BITTI', 'IPTAL'): continue
            ait = (k in d.listeler.get(key, []) if cins == 'IS' else x.get('kisi') == key) if tur == 'KISI' else cins == 'IS' and x.get('tezgah') == key
            p, q = plan_araligi(d, cins, x)
            if ait and p and q and max(a, p) < min(b, q): yield cins, k, x, p, q


def kaynak_yuku(d, kim, tur, key, bas, bit=None, kapasite_dahil=False):
    from .gorunum_v9 import proje_gorebilir_mi
    from .gorunum_v7 import temel_gorebilir_mi
    sonuc = []
    for cins, k, x, p, q in kaynak_satirlari(d, tur, key, bas, bit):
        if tur == 'KISI' and not temel_gorebilir_mi(d, kim, 'IS', key):
            sonuc.append(dict(durum='MESGUL', bas=p, bit=q))
        elif x.get('proje') and not proje_gorebilir_mi(d, kim, x['proje']):
            sonuc.append(dict(proje='ERISIM_DISI', planlanan_baslangic=p, planlanan_bitis=q))
        else:
            sonuc.append(dict(tur=cins, kimlik=k, ad=x.get('ad', x.get('islem')), proje=x.get('proje'),
                              planlanan_baslangic=p, planlanan_bitis=q, durum=x['durum']))
    if kapasite_dahil:
        from .gorunum_v7 import tezgah_planli_araliklar
        from .takvim_v7 import saatler
        if tur != 'TEZGAH': raise ValueError('Kapasite ozeti TEZGAH icindir')
        a,b=pencere(bas,bit)
        return dict(satirlar=sonuc,planli_kullanilabilir=saatler(tezgah_planli_araliklar(d,key,a,b)))
    return sonuc


def kapasite_araligi(d, kisi, bas, bit, birim=None):
    """A12 kapasitesi, [bas, bit) anlarına kırpılmış saat."""
    from .takvim_v7 import gunler, normal, kisi_normal, ekler, izinler, cikar, saatler
    from .yetki_v6 import istihdamda
    a,b=an(bas),an(bit)
    if a>=b: return 0
    xs=[]
    for tarih in gunler(a,b-timedelta(microseconds=1)):
        if kisi:
            if not istihdamda(d,kisi,tarih): continue
            araliklar=kisi_normal(d,kisi,tarih)+ekler(d,kisi,tarih)
        else: araliklar=normal(d,tarih,birim=birim)
        xs.extend((max(a,p),min(b,q)) for p,q in araliklar if max(a,p)<min(b,q))
    return saatler(cikar(xs,izinler(d,kisi)) if kisi else xs)


def gecikme_olculeri(d, tur, x):
    """Karar 113; performans ve saklanan durum değişmeden iki gecikme ölçüsü."""
    from .gorev import son_teslim_ani
    son=son_teslim_ani(x,d) if tur=='GOREV' else None
    son=son or x.get('planlanan_bitis')
    if not son or x['durum']=='IPTAL':
        return dict(gecikme_takvim_dk=None,gecikme_mesai_dk=None)
    a=an(son); b=an(x['bitis_ani']) if x['durum']=='BITTI' and x.get('bitis_ani') else d.saat.simdi()
    return dict(gecikme_takvim_dk=max(0,(b-a).total_seconds()/60),
                gecikme_mesai_dk=60*kapasite_araligi(d,x.get('kisi'),a,b,birim=x.get('birim')))


def takvim(d, kim, tur, key, bas, bit=None):
    from .takvim_v7 import gunler, normal, ekler, cikar, birlesim, birim_kapsamda
    from .gorunum_v7 import tezgah_calisma_pencereleri, tezgah_engelleri, gorebilir_mi
    from .yetki_v6 import istihdamda
    tablolar = {'KISI': d.kisiler, 'BIRIM': d.birimler, 'TEZGAH': d.tezgahlar}
    if tur not in tablolar or key not in tablolar[tur]: raise ValueError('Takvim turu veya kimligi')
    a, b = pencere(bas, bit); calisma = []; kapali = []
    def kapat(p, q, neden):
        p, q = max(a, an(p)), min(b, an(q))
        if p < q: kapali.append(dict(bas=p, bit=q, neden=neden))
    for tarih in gunler(a, b - timedelta(microseconds=1)):
        u, v = max(a, gun_ani(tarih)), min(b, gun_ani(tarih + timedelta(days=1)))
        if tur == 'TEZGAH': araliklar = tezgah_calisma_pencereleri(d, key, tarih)
        elif tur == 'BIRIM': araliklar = normal(d, tarih, birim=key)
        else: araliklar = normal(d, tarih, kisi=key) + ekler(d, key, tarih) if istihdamda(d, key, tarih) else []
        araliklar = [(max(u,p), min(v,q)) for p,q in araliklar if max(u,p) < min(v,q)]
        calisma.extend(araliklar)
        neden = 'TATIL' if str(tarih) in d.tatiller else 'VARDIYA_DISI' if tur == 'TEZGAH' else 'MESAI_DISI'
        for p,q in cikar([(u,v)], araliklar): kapat(p,q,neden)
    if tur == 'KISI':
        for x in d.izinler.values():
            if x['kisi'] == key and x['durum'] == 'ONAYLI':
                kapat(x['baslangic'], x['bitis'], 'IZIN' if gorebilir_mi(d,kim,'IZIN_DETAY',key) else 'MUSAIT_DEGIL')
    if tur == 'TEZGAH':
        for x in d.bakimlar.values():
            if x['tezgah'] == key and not x['iptal']: kapat(x['baslangic'],x['bitis'],'BAKIM')
        for p,q,_ in tezgah_engelleri(d,key): kapat(p,q,'DURUS')
    else:
        birim = key if tur == 'BIRIM' else d.kisiler[key]['birim']
        for x in d.duruslar.values():
            if birim_kapsamda(d,birim,x['kapsam']): kapat(x['baslangic'],x['bitis'] or d.saat.simdi(),'DURUS')
    calisma = cikar(birlesim(calisma), [(x['bas'],x['bit']) for x in kapali])
    # Aynı nedenli bitişik parçaları birleştir; farklı nedenlerin kesişimi korunur.
    birlesmis = []
    for neden in sorted({x['neden'] for x in kapali}):
        birlesmis.extend(dict(bas=p,bit=q,neden=neden) for p,q in birlesim([(x['bas'],x['bit']) for x in kapali if x['neden']==neden]))
    return dict(calisma=[dict(bas=p,bit=q) for p,q in calisma], kapali=sorted(birlesmis,key=lambda x:(x['bas'],x['bit'],x['neden'])))


def oku(d, kim, veri, hedef=None, **g):
    from .gorunum_v7 import gorebilir_mi, top_kimde, tezgah_uygun_mu, tezgah_gostergesi, iscilik_maliyeti
    from .gorunum_v9 import proje_gorebilir_mi
    from .yetki_v6 import istihdamda, yoneticiler
    if not istihdamda(d,kim,d.saat.simdi()): raise PermissionError('Gorunurluk')
    if veri == 'KISILER':
        return [dict(kimlik=k,ad=x['ad'],birim=x['birim'],yaka=x['yaka'],roller=deepcopy(x['roller']),
                     aktif=istihdamda(d,k,d.saat.simdi()) and x.get('aktif',True),yetkinlikler=deepcopy(x.get('yetkinlikler',[])))
                for k,x in sorted(d.kisiler.items()) if not g.get('birim',hedef) or x['birim']==g.get('birim',hedef)]
    if veri == 'BIRIMLER':
        return [dict(kimlik=k,ad=x['ad'],ust=x.get('ust_birim'),basi=x.get('basi'),yoneticileri=sorted(yoneticiler(d,k)),
                     takvim=deepcopy(d.takvim(d.saat.simdi(),birim=k))) for k,x in sorted(d.birimler.items())]
    if veri == 'TEZGAHLAR':
        sonuc=[]
        for k,x in sorted(d.tezgahlar.items()):
            if g.get('birim',hedef) and x['birim']!=g.get('birim',hedef): continue
            ts=[s for s in d.tezgah_takvimleri.values() if s['tezgah']==k and gun(s['gecerli_baslangic'])<=d.saat.simdi().date()]
            vs=deepcopy(max(ts,key=lambda s:(s['gecerli_baslangic'],s['kimlik']))['vardiyalar']) if ts else []
            sonuc.append(dict(kod=k,ad=x['ad'],birim=x['birim'],aktif=x.get('aktif',True),vardiyalar=vs))
        return sonuc
    if veri == 'TAKVIM': return takvim(d,kim,g['tur'],g.get('kimlik',hedef),g['bas'],g.get('bit'))
    if veri == 'KAYNAK_YUKU': return kaynak_yuku(d,kim,g['tur'],g.get('kimlik',hedef),g['bas'],g.get('bit'),g.get('kapasite_dahil',False))
    if veri == 'ETAPLAR':
        p=g.get('proje',hedef)
        if not proje_gorebilir_mi(d,kim,p): raise PermissionError('Proje gorunurlugu')
        return [deepcopy(x) for _,x in sorted(d.etaplar.items()) if x['proje']==p]
    if veri == 'NESNELER':
        return [deepcopy(x) for k,x in sorted(d.nesneler.items()) if
                (not g.get('proje',hedef) or x.get('proje')==g.get('proje',hedef)) and
                (not g.get('tur') or x['tur']==g['tur']) and (not g.get('kod') or x.get('kod')==g['kod']) and gorebilir_mi(d,kim,'NESNE',k)]
    if veri == 'TOP_KIMDE':
        n=g.get('nesne',hedef)
        if not gorebilir_mi(d,kim,'NESNE',n): raise PermissionError('Gorunurluk')
        return top_kimde(d,n)
    if veri == 'KAPASITE':
        k=g.get('kisi',hedef); a,b=pencere(g['bas'],g.get('bit'))
        if k not in d.kisiler: raise ValueError('Kisi')
        return kapasite_araligi(d,k,a,b)
    if veri in ('TEZGAH_UYGUNLUK','TEZGAH_GOSTERGESI'):
        k=g.get('tezgah',hedef); a,b=pencere(g['bas'],g.get('bit'))
        if veri=='TEZGAH_UYGUNLUK': return tezgah_uygun_mu(d,k,a,b)
        return tezgah_gostergesi(d,k,g['bas'],g.get('bit',g['bas']))
    if veri == 'TEZGAH_UCRETI':
        if not {'YETKILI','MALIYET'}.intersection(d.kisiler[kim]['roller']): raise PermissionError('Gorunurluk')
        return tezgah_ucreti(d,g.get('tezgah',hedef),g['gun'])
    if veri == 'ISCILIK_MALIYETI':
        p=g.get('proje',hedef)
        if not gorebilir_mi(d,kim,'TUTAR') or not proje_gorebilir_mi(d,kim,p): raise PermissionError('Gorunurluk')
        return iscilik_maliyeti(d,p,g['bas'],g['bit'])
    if veri == 'LISTE':
        k=g.get('kisi',hedef)
        if not gorebilir_mi(d,kim,'IS',k): raise PermissionError('Gorunurluk')
        from .surum import liste_surumu
        return dict(isler=[deepcopy(d.isler[x]) for x in d.listeler.get(k,[]) if gorebilir_mi(d,kim,'IS',x)],surum=liste_surumu(d,k))
    raise ValueError('TANIMSIZ_VERI')
