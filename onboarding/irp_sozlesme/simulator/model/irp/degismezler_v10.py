"""I106–I113: karar 91–92; tarihi kaynaklar ve bağımsız pay hesabı."""
from datetime import timedelta
from decimal import Decimal
from .saat import an, gun, Saat

TANIMLAR={
    'I106':'UYELER yönetim kararında proje yetkisi veya karar 99un dar belge sorumlusu istisnası vardır.',
    'I107':'Yeni iş alanın departmanı veya ek erişimi olay anında uygundur; havuz birimi dahildir.',
    'I108':'Geç teslim kredisi 0–1 aralığında ve yalnız dış/etkin başka payların toplamıdır.',
    'I109':'Doğrulanmamış veya itirazdaki başka pay krediye ve sebep olunan gecikmeye girmez.',
    'I110':'Sessiz kabul yalnız gecikmede, ayar açıkken, iş günü süresi dolunca ve müdahale yokken olur.',
    'I111':'Kesinleşmedi ve bekleyen sayısı yalnız son değerlendirmedeki açık paylardan gelir.',
    'I112':'Kredi dışındaki pay teslim edende kalır; toplam 1 ve kaynak dağılımı en çok 100dür.',
    'I113':'Sessiz kabul kaynak olay üretmez; kaynak dağılımları olay kimliğine bağlı kalır.',
}


def denetle(d, derin=False):
    from .kurallar_v10 import etkin_pay, kredi, projede_yetkili, olay_projeleri, proje_yazma_kapisi
    from .gorunum_v9 import son_degerlendirme
    from .gorunumler import adil_performans
    from .gorev import son_teslim_ani
    from .kabul import TANIKLIK
    from .motor import Motor
    s=dict.fromkeys(TANIMLAR,True)
    olaylar=list(d.olaylar.values()) if hasattr(d.olaylar,'values') else list(d.olaylar)
    ids={e['olay_kimligi'] for e in olaylar}
    for x in d.sorumluluklar.values():
        if x.get('kaynak_turu')!='GECIKME': continue
        s['I113'] &= x['ret'] in ids and x['ret'] in d.gecikme_degerlendirmeleri
        if etkin_pay(d,x) and not x['dogrulandi'] and x['tur']!='DIS':
            a=an(x['an']); b=d.saat.simdi(); n=d.ayar('sessiz_kabul_is_gunu',a,0)
            sayi=0; t=a
            while t+timedelta(days=1)<=b:
                t+=timedelta(days=1)
                sayi+=bool(d.is_gunu(t,**({'kisi':x['kimlik']} if x['tur']=='KISI' else {'birim':x['kimlik']})))
            s['I110'] &= n>0 and sayi>=n and not x['itirazda'] and not x.get('gecmis') and x['yuzde']>0
    donemler=set()
    for g in d.gorevler.values():
        if g['tur'] not in ('NORMAL','DEGISIKLIK') or not g.get('ilk_teslim_ani'): continue
        tarih=gun(an(g['ilk_teslim_ani'])); donemler.add((g['kisi'],tarih.replace(day=1)))
        if an(g['ilk_teslim_ani'])<=son_teslim_ani(g,d): continue
        ev=son_degerlendirme(d,g['kimlik'])
        ss=[x for x in d.sorumluluklar.values() if ev and x['ret']==ev['kimlik']]
        bek=sum((Decimal(str(x['yuzde']))/100 for x in ss if etkin_pay(d,x) and (x['tur']!='KISI' or x['kimlik']!=g['kisi'])),Decimal(0))
        c=kredi(d,g); s['I108'] &= 0<=c<=1 and abs(c-float(bek))<1e-12
        s['I109'] &= all(not etkin_pay(d,x) for x in ss if x['itirazda'])
        s['I112'] &= 0<=sum(Decimal(str(x['yuzde'])) for x in ss)<=100 and abs(c+(1-c)-1)<1e-12
    for k,bas in donemler:
        bit=(bas.replace(day=28)+timedelta(days=4)).replace(day=1)-timedelta(days=1)
        gs=[g for g in d.gorevler.values() if g['kisi']==k and g['tur'] in ('NORMAL','DEGISIKLIK') and g.get('ilk_teslim_ani') and bas<=gun(an(g['ilk_teslim_ani']))<=bit]
        sonlar={ev['kimlik'] for g in gs if (ev:=son_degerlendirme(d,g['kimlik']))}
        bek=sum(x['yuzde']>0 and (x['itirazda'] or not etkin_pay(d,x)) for x in d.sorumluluklar.values() if x['ret'] in sonlar)
        p=adil_performans(d,k,bas,bit)
        s['I111'] &= (p['kesinlesmedi'],p['bekleyen_satir_sayisi'])==(bool(bek),bek)
    if derin:
        once=[]
        for e in olaylar:
            if e['giris_sekli']!='AKTARIM' and e['eylem_kodu'] not in TANIKLIK and d.ayar('proje_gorunurlugu',an(e['oldugu_an']),'HERKES')=='UYELER':
                m=Motor(Saat(e['oldugu_an']))
                sinir=(an(e['oldugu_an']),e['olay_kimligi'])
                m.yurut([x for x in once if (an(x['oldugu_an']),x['olay_kimligi'])<sinir])
                # Karar 99: belgeyi gören sorumlu, kendi belgesine taslak
                # ekleyebilir. Ek hedefteki başka projeye bu istisna taşınmaz.
                n=m.nesneler.get(e['girdiler'].get('hedef'),{})
                istisna=e['eylem_kodu'] in ('NESNE.SURUM_EKLEDIM','NESNE.ASAMA_GECIRDIM') and n.get('sorumlu')==e['kim']
                if istisna:
                    from .gorunum_v9 import proje_gorebilir_mi
                    uygun=all(proje_gorebilir_mi(m,e['kim'],p) if p==n.get('proje') else projede_yetkili(m,e['kim'],p)
                              for p in olay_projeleri(m,e))
                    s['I106'] &= uygun
                    s['I107'] &= uygun
                elif e['eylem_kodu'] != 'NOT.YAZDIM':
                    s['I106'] &= all(projede_yetkili(m,e['kim'],p) for p in olay_projeleri(m,e))
                    s['I107'] &= proje_yazma_kapisi(m,e)
                else: s['I107'] &= proje_yazma_kapisi(m,e)
            once.append(e)
    return {k:bool(v) for k,v in s.items()}
