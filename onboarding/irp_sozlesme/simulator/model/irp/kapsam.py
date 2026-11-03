"""Bağımlı nesne ve kişi-gün kapsamı; tam yol karşılaştırma içindir.

İşin emek geçmişi ve gün başı bağlamı gerektiğinden ilişkili kişinin günleri
temkinli biçimde birlikte kirletilir. Bağımsız kişiler/görevler yürütülmez.
"""
from collections import defaultdict
from copy import deepcopy, copy
from .saat import an,gun_ani
from .kisi_gunu import CALISAN
from .motor import Motor

def ana_veri(e): return e['eylem_kodu']=='IS.TANIMLADIM' or not e['eylem_kodu'].startswith(('IS.','MESAI.','GOREV.','NOT.','KAYIT.'))

def dugumler(e):
    kod,g,k=e['eylem_kodu'],e['girdiler'],e['olay_kimligi']; s={('OLAY',k)}
    for x in e['neyin_ustunde']:
        if x['tur'] in ('IS','GOREV','NOT'): s.add((x['tur'],x['kimlik']))
    if kod.startswith(('IS.','MESAI.')):
        for alan in ('kisi','kimden','kime'):
            if g.get(alan): s.add(('GUNLER',g[alan]))
        for kisi in g.get('kisiler',[]): s.add(('GUNLER',kisi))
        if kod in CALISAN: s.add(('GUNLER',e.get('adina') or e['kim']))
        if e.get('adina'): s.add(('GUNLER',e['adina']))
    if kod in ('IS.TANIMLADIM','GOREV.ATADIM'):
        tur='IS' if kod.startswith('IS.') else 'GOREV'; satirlar=g['isler' if tur=='IS' else 'gorevler']
        for n,x in enumerate(satirlar,1):
            kimlik=k+'/'+str(n) if tur=='GOREV' or len(satirlar)>1 else k
            s.add((tur,kimlik))
            if x.get('kisi_sayisi',1)>1:
                for alt in range(1,x['kisi_sayisi']+1): s.add(('IS',kimlik+'/k'+str(alt)))
            for on in x.get('on_isler',x.get('on_kosul',[])): s.add((tur,k+'/'+str(on['satir']) if isinstance(on,dict) else on))
    if kod=='IS.ATADIM' and g.get('kisiler'):
        for x in e['neyin_ustunde']:
            if x['tur']=='IS':
                for n in range(1,len(g['kisiler'])+1): s.add(('IS',x['kimlik']+'/k'+str(n)))
    if kod=='IS.DEGISTIRDIM':
        for on in g.get('degisenler', {}).get('on_isler', []): s.add(('IS', on))
    if kod=='IS.PLANSIZ_TANIMLADIM': s.add(('IS',k))
    if kod=='GOREV.TAMAMLADIM': s.add(('GOREV',k))
    if kod=='GOREV.REDDETTIM': s.add(('GOREV',k+'/1'))
    if kod=='GOREV.DEGISTIRDIM':
        s.add(('GOREV',k+'/1'))
        for on in g.get('degisenler', {}).get('on_kosul', []): s.add(('GOREV', on))
    if kod=='NOT.YAZDIM': s.add(('NOT',k))
    for tur,kimlik in list(s):
        if tur=='GOREV' and '/' in kimlik: s.add(('OLAY',kimlik.rsplit('/',1)[0]))
    if kod=='KAYIT.GECERSIZ_SAYDIM': s.add(('OLAY',g['hedef']))
    return s

def hesapla(depo,e):
    kayitlar=list(depo._kayitlar.values())
    rol_siniri = any(x['eylem_kodu'] == 'KISI.DEGISTIRDIM' and getattr(depo.gorunum, 'hesap_ani', depo.saat.simdi()) < an(x['girdiler']['gecerli_baslangic']) <= depo.saat.simdi() for x in kayitlar)
    from .kurallar_v7 import SEMALAR
    v7_bagli = any(x['eylem_kodu'] in SEMALAR or 'ek_mesai' in str(x['girdiler']) for x in kayitlar)
    from .kurallar_v9 import SEMALAR as SEMALAR_V9
    from .kurallar_v10_1 import SEMALAR as SEMALAR_T10
    v10_bagli = any(x['eylem_kodu'] in SEMALAR_T10 for x in kayitlar)
    v9_bagli = any(x['eylem_kodu'] in SEMALAR_V9 or any(k in x['girdiler'] for k in ('takvim','makine_bitis_ani','degisiklik')) or any('degisiklik' in s for s in x['girdiler'].get('gorevler',x['girdiler'].get('isler',[]))) for x in kayitlar)
    if ana_veri(e) or depo.gorunum is None or rol_siniri or v7_bagli or v9_bagli or v10_bagli:
        m=Motor(depo.saat); m.yurut(kayitlar)
        return m,{'olay':len(kayitlar),'tum':True,'kisi_gun':len({(a['kisi'],a['gun']) for a in m.araliklar})}
    indeks=defaultdict(set); kumeler={}
    for x in kayitlar:
        if ana_veri(x): continue
        k=x['olay_kimligi']; kumeler[k]=dugumler(x)
        for n in kumeler[k]: indeks[n].add(k)
    # Çok satırlı iş tanımı okuma girdisidir; kardeş işler birbirinin bağımlısı değildir.
    for x in kayitlar:
        if x['eylem_kodu']!='IS.TANIMLADIM': continue
        kok=x['olay_kimligi']; satirlar=x['girdiler']['isler']
        for n,satir in enumerate(satirlar,1):
            i=kok+'/'+str(n) if len(satirlar)>1 else kok
            bag={('IS',i)}
            for on in satir.get('on_isler',[]): bag.add(('IS',kok+'/'+str(on['satir']) if isinstance(on,dict) else on))
            for a in range(1,satir.get('kisi_sayisi',1)+1):
                if satir.get('kisi_sayisi',1)>1: bag.add(('IS',i+'/k'+str(a)))
            for dugum in bag:
                for k in list(indeks[dugum]): kumeler[k] |= bag
    secilen=set(); kirli=set(); kuyruk=list(dugumler(e))
    simdi=depo.saat.simdi()
    for kisi,h in depo.kisi_durumu.items():
        once=h.get('son_hesap_ani',simdi)
        if h['durum']=='MESAI_DISI': continue
        tak=depo.takvim(simdi)
        sinirlar=[gun_ani(simdi.date(),x[a]) for x in tak['sabit_molalar'] for a in ('bas','bit')]+[gun_ani(simdi.date(),tak['mesai_bitis'])]
        if once.date()!=simdi.date() or any(once<s<=simdi for s in sinirlar): kuyruk.append(('GUNLER',kisi))
    while kuyruk:
        n=kuyruk.pop()
        if n in kirli: continue
        kirli.add(n)
        for k in indeks[n]-secilen: secilen.add(k); kuyruk.extend(kumeler[k]-kirli)
    secili=[x for x in kayitlar if ana_veri(x) or x['olay_kimligi'] in secilen]
    yeni=Motor(depo.saat); yeni.yurut(secili)
    m=copy(depo.gorunum); m.saat=depo.saat
    kisiler={k for tur,k in kirli if tur=='GUNLER'}; isler={k for tur,k in kirli if tur=='IS'}; gorevler={k for tur,k in kirli if tur=='GOREV'}
    for ad in ('isler','gorevler','notlar','listeler','kisi_durumu','supheliler','sonuclar','olay_nesneleri','dosyalar','bekletmeler'):
        eski=dict(getattr(m,ad)); setattr(m,ad,eski); gelen=getattr(yeni,ad)
        def etkili(k,v):
            if ad in ('listeler','kisi_durumu'): return k in kisiler
            if ad=='isler': return k in isler
            if ad=='gorevler': return k in gorevler or v.get('doguran_olay') in secilen
            if ad=='bekletmeler': return v.get('on_kosul') in gorevler or v.get('bekleyen') in gorevler
            if ad=='olay_nesneleri': return k in secilen
            return k in secilen or v.get('olay') in secilen or v.get('doguran_olay') in secilen
        for k in [k for k,v in eski.items() if etkili(k,v)]: del eski[k]
        for k,v in gelen.items():
            if etkili(k,v): eski[k]=v
    m.bildirimler={k:v for k,v in m.bildirimler.items() if v['doguran_olay'] not in secilen}; m.bildirimler.update(yeni.bildirimler)
    m.araliklar=[a for a in m.araliklar if a['kisi'] not in kisiler and a['is'] not in isler]+yeni.araliklar
    # Önceki yayında uzunluğu sıfır olduğu için yazılmayan açık aralık artık ölçülebilir.
    acik_kisiler={a['kisi'] for a in m.araliklar if a['bitis'] is None}
    for kisi,h in m.kisi_durumu.items():
        if kisi not in acik_kisiler and h.get('kova') and h.get('baslangic'): m.aralik_ekle(kisi,h,None)
    m.araliklar.sort(key=lambda a:(a['kisi'] or '',a['baslangic'],a['kova']))
    m.retler=[r for r in m.retler if r['olay'] not in secilen]+yeni.retler
    m.sorumluluklar={k:v for k,v in m.sorumluluklar.items() if v['ret'] not in secilen}
    m.sorumluluklar.update(yeni.sorumluluklar)
    m.mesai_sonrasi_isaretleri={k:v for k,v in m.mesai_sonrasi_isaretleri.items() if k not in secilen}
    m.mesai_sonrasi_isaretleri.update(yeni.mesai_sonrasi_isaretleri)
    m.elle_olaylar=[x for x in m.elle_olaylar if x['olay_kimligi'] not in secilen]+yeni.elle_olaylar
    m.olaylar=[x for x in kayitlar if an(x['oldugu_an'])<=depo.saat.simdi()]
    m.yakinsama_turlari=yeni.yakinsama_turlari; m.motor_hatalari=yeni.motor_hatalari; m.islenemedi=yeni.islenemedi
    m.kisi_durumu={k:dict(h,son_hesap_ani=simdi) for k,h in m.kisi_durumu.items()}
    m.hesap_ani = simdi
    from .kurallar_v6 import baglantilari_yansit
    baglantilari_yansit(m)
    from .kurallar_v7 import tamamla
    tamamla(m)
    from .kurallar_v9 import tamamla as tamamla_v9
    tamamla_v9(m)
    return m,{'olay':len(secili),'tum':False,'nesne':len(kirli),'kisi_gun':len({(a['kisi'],a['gun']) for a in yeni.araliklar})}
