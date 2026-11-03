"""I114–I126: plan, sürüm ve olay dışı bildirim korunumu."""
from copy import deepcopy
from .saat import an

TANIMLAR = {
    'I114': 'Tam plan aralığında başlangıç bitişten küçüktür.',
    'I115': 'Çakışma simetrik, tekil ve pozitif kesişimdir; uç uca değme sayılmaz.',
    'I116': 'Bitmiş/iptal işler ve görevler çakışma kümesine girmez.',
    'I117': 'Geçerli sürüm en büyük numaralı ONAYLI sürümdür.',
    'I118': 'Sürüm numaraları ardışık, adları tekil, dosya listesi doludur.',
    'I119': 'Taslak listesi nesneyi gören ekleyen, sorumlu, sorumlunun üstleri ve onaylayabilecek kişilere açıktır.',
    'I120': 'Sürümü ekleyen kendi sürümünü onaylayamaz veya geri çekemez.',
    'I121': 'Modül anahtarları tekildir; olaylarda ve olay_nesneleri içinde yoktur.',
    'I122': 'Modül tablosu yeniden kurmada aynen korunur; Motor kaynağı değildir.',
    'I123': 'Modül bildirimi güncel erişimi ve istihdamı olmayan alıcıya görünmez.',
    'I124': 'Görülme alıcının insan olayına bağlıdır ve doğumdan önce olamaz.',
    'I125': 'R43 yalnız geçerli sürüm değişiminden doğar; yazana gitmez.',
    'I126': 'Her modülün servis kimliği diğer modüllerden ayrıdır.',
}


def denetle(d, derin=False):
    from .gorunum_v10_1 import plan_cakismalari, gecerli_surum, surumler
    from .kurallar_v10_1 import surum_satirlari, onaylayabilir
    from .modul_bildirimi import kimlik, alici_gorebilir, kutu
    from .kurallar_v9 import olaylar
    from .gorunum_v9 import gorebilir_mi
    from .yetki_v6 import ustler
    s=dict.fromkeys(TANIMLAR,True); es=olaylar(d); ids={e['olay_kimligi'] for e in es}
    for x in list(d.isler.values())+list(d.gorevler.values()):
        a,b=x.get('planlanan_baslangic'),x.get('planlanan_bitis')
        if a and b: s['I114'] &= an(a)<an(b)
    if derin:
        from .gorunum_v10_1 import plan_araligi
        for tur, tabla in [('KISI',d.kisiler),('TEZGAH',d.tezgahlar)]:
            for k in tabla:
                aday=[]
                for cins, xs in [('IS',d.isler),('GOREV',d.gorevler)]:
                    for key,x in xs.items():
                        ait=(key in d.listeler.get(k,[]) if cins=='IS' else x.get('kisi')==k) if tur=='KISI' else cins=='IS' and x.get('tezgah')==k
                        a,b=plan_araligi(d,cins,x)
                        if ait and a and b and x['durum'] not in ('BITTI','IPTAL'): aday.append((cins,key,a,b))
                if not aday: continue
                bas=min(x[2] for x in aday); bit=max(x[3] for x in aday)
                bek=set()
                for x in aday:
                    for y in aday:
                        if x[:2]>=y[:2]: continue
                        if x[2]<y[3] and y[2]<x[3]: bek.add((x[:2],y[:2],max(x[2],y[2]),min(x[3],y[3])))
                bulunan=plan_cakismalari(d,dict(tur=tur,kimlik=k),bas,bit)
                gercek=set()
                for c in bulunan:
                    hs=tuple((h['tur'],h['kimlik']) for h in c['hedefler'])
                    gercek.add((*hs,c['baslangic'],c['bitis']))
                    s['I116'] &= all((d.isler if h['tur']=='IS' else d.gorevler)[h['kimlik']]['durum'] not in ('BITTI','IPTAL') for h in c['hedefler'])
                s['I115'] &= bek==gercek and len(gercek)==len(bulunan)
    for n,x in d.nesneler.items():
        ss=surum_satirlari(d,n); onay=[x['surum_no'] for x in ss if x['durum']=='ONAYLI']
        v=gecerli_surum(d,n)
        s['I117'] &= (v['surum_no'] if v else None)==max(onay,default=None)
        s['I118'] &= [x['surum_no'] for x in ss]==list(range(1,len(ss)+1)) and len({x['surum_adi'] for x in ss})==len(ss)
        for v in ss:
            s['I118'] &= bool(v['dosyalar']) and v['doguran_olay'] in ids
            s['I120'] &= v['ekleyen']!=v.get('onaylayan') and v['ekleyen']!=v.get('geri_ceken')
            if v['durum']=='TASLAK' and derin:
                for k in d.kisiler:
                    bek = gorebilir_mi(d,k,'NESNE',n) and (k in (v['ekleyen'],x['sorumlu'])
                        or k in ustler(d,x['sorumlu']) or onaylayabilir(d,k,x,v))
                    s['I119'] &= (v in surumler(d,n,cagiran=k)) == bek
    for key,x in d.modul_bildirimleri.items():
        s['I121'] &= key==kimlik(x['kaynak'],x['kural'],x['kayit'],x['alici']) and key not in ids and key not in d.olay_nesneleri
        if x.get('gorulme_ani'):
            s['I124'] &= x['birakma_ani']<=x['gorulme_ani'] and any(e['kim']==x['alici'] and key in e['bildirimler'] and e['an']==x['gorulme_ani'] for e in d.bildirim_gorulmeleri.values())
        if not alici_gorebilir(d,x['alici'],x['kayit']): s['I123'] &= not any(z.get('kimlik')==key for z in kutu(d,x['alici']))
    s['I121'] &= all(not e['eylem_kodu'].startswith('MODUL.BILDIRIM') for e in es)
    s['I126'] &= len({x['servis_kimligi'] for x in d.moduller.values()})==len(d.moduller)
    # Geçerli sürüm değişimlerinin bağımsız küçük durum hesabı.
    ss={}; degisen=set()
    for e in sorted(es,key=lambda e:(an(e['oldugu_an']),e['olay_kimligi'])):
        kod,g=e['eylem_kodu'],e['girdiler']
        if not kod.startswith('NESNE.SURUM_'): continue
        vs=ss.setdefault(g['hedef'],{}); eski=max((n for n,durum in vs.items() if durum=='ONAYLI'),default=None)
        if kod.endswith('EKLEDIM'): vs[e.get('nesne_surum_no',len(vs)+1)]='TASLAK'
        else: vs[g['surum_no']]='ONAYLI' if kod.endswith('ONAYLADIM') else 'GERI_CEKILDI'
        yeni=max((n for n,durum in vs.items() if durum=='ONAYLI'),default=None)
        if eski!=yeni: degisen.add(e['olay_kimligi'])
    for x in d.bildirimler.values():
        if x['kural']!='R43' or not x['gecerli']: continue
        e=next((e for e in es if e['olay_kimligi']==x['doguran_olay']),{})
        s['I125'] &= x['doguran_olay'] in degisen and x['alici']!=e.get('kim')
    if derin and d.modul_bildirimleri:
        from .depo import Depo
        from .saat import Saat
        z=Depo(Saat(d.saat.simdi()),'tam'); z._kayitlar=deepcopy(d._kayitlar)
        z.modul_bildirimleri=deepcopy(d.modul_bildirimleri); z.yeniden_kur()
        s['I122'] &= z.modul_bildirimleri==d.modul_bildirimleri and not hasattr(z.gorunum,'modul_bildirimleri')
    return {k:bool(v) for k,v in s.items()}
