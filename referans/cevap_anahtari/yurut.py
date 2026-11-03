"""Donmus JSON girdisini standart kutuphane modeliyle yurutur."""
import argparse
import importlib
import json
import sys
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

KOK=Path(__file__).resolve().parent
sys.path.insert(0,str(KOK))
sys.path.insert(0,str(KOK/'model'))
from irp import Depo, Saat, an
from irp.cihaz import Cihaz
from irp.zaman import ay_kapanisi
from karsilastir import kanonik, farklar, oku

TABLOLAR=('isler','gorevler','kisiler','birimler','projeler','tezgahlar','etaplar',
          'notlar','listeler','kisi_durumu','araliklar','bildirimler','supheliler',
          'sonuclar','bekletmeler','dosyalar','kisi_gecmisi','kod_listesi','yetki_kurallari')
from irp.kurallar_v7 import TABLOLAR as V7_TABLOLAR
TABLOLAR += V7_TABLOLAR
from irp.kurallar_v9 import TABLOLAR as V9_TABLOLAR
TABLOLAR += V9_TABLOLAR
from irp.kurallar_v10_1 import TABLOLAR as T10_TABLOLAR
TABLOLAR += T10_TABLOLAR + ('modul_bildirimleri',)
SORGULAR={'irp.gorunumler','irp.gorunum_v6','irp.gorunum_v7','irp.gorunum_v9','irp.kurallar_v10','irp.is_','irp.gorev','irp.kisi_gunu','irp.hesap_yetkisi','irp.surum'}
SORGULAR.add('irp.gorunum_v10_1')
SORGULAR.add('irp.gorunum_v10_2')


def kodla_arg(x):
    if isinstance(x,datetime): return {'$an':x.isoformat()}
    if isinstance(x,date): return {'$gun':x.isoformat()}
    if isinstance(x,Decimal): return {'$ondalik':str(x)}
    if isinstance(x,set): return {'$kume':sorted(x)}
    if isinstance(x,(list,tuple)): return [kodla_arg(v) for v in x]
    if isinstance(x,dict): return {k:kodla_arg(v) for k,v in x.items()}
    return x


def coz(x):
    if isinstance(x,dict):
        if set(x)=={'$an'}: return an(x['$an'])
        if set(x)=={'$gun'}: return date.fromisoformat(x['$gun'])
        if set(x)=={'$ondalik'}: return Decimal(x['$ondalik'])
        if set(x)=={'$kume'}: return set(x['$kume'])
        return {k:coz(v) for k,v in x.items()}
    if isinstance(x,list): return [coz(v) for v in x]
    return x


def saat_bilgisi(s):
    return {'simdi':s.simdi().isoformat(),'gercek':s.gercek().isoformat(),'demo':s.demo}


def saat_kur(veri): return Saat(veri['simdi'],gercek=veri['gercek'],demo=veri['demo'])


def son_hal(d):
    veri={ad:deepcopy(getattr(d,ad)) for ad in TABLOLAR}
    veri['bildirimler']={k:v for k,v in veri['bildirimler'].items() if v['gecerli']}
    veri['ay_kapanislari']=deepcopy(d.ay_kapanislari)
    veri['cihaz_esitlemeleri']=deepcopy(d.cihaz_esitlemeleri)
    if d.cihaz_harfleri: veri['cihaz_harfleri']=deepcopy(d.cihaz_harfleri)
    veri['olay_kimlikleri']=sorted(d.olaylar)
    veri['isleme_hatalari']=[{k:v for k,v in x.items() if k!='an'} for x in d.isleme_hatalari]
    if d.kurulum_tamamlandi:
        veri['kurulum']={'tamamlandi':True,'kod_listeleri':deepcopy(d.kod_listeleri)}
    return kanonik(veri)


def dene(f,*args,**kwargs):
    try: return {'deger':kanonik(f(*args,**kwargs))}
    except (ValueError,PermissionError,ConnectionError,OverflowError) as h:
        return {'hata_turu':type(h).__name__,'neden':str(h)}


def sorgu_fonksiyonu(modul,ad):
    if modul not in SORGULAR or ad.startswith('_'): raise ValueError('Bilinmeyen sorgu')
    return getattr(importlib.import_module(modul),ad)


def tam_deneti(d):
    """Kabul yolunu atlamadan olusan kaynagi bos bir motorda tekrar kur."""
    yeni=Depo(saat_kur(saat_bilgisi(d.saat)),yontem='tam')
    yeni._kayitlar=deepcopy(d._kayitlar)
    yeni.hassas_ekler=deepcopy(d.hassas_ekler)
    yeni.ay_kapanislari=deepcopy(d.ay_kapanislari)
    yeni.cihaz_esitlemeleri=deepcopy(d.cihaz_esitlemeleri)
    yeni.cihaz_harfleri=deepcopy(d.cihaz_harfleri)
    yeni.isleme_hatalari=deepcopy(d.isleme_hatalari)
    yeni.kurulum_tamamlandi=d.kurulum_tamamlandi
    yeni.kod_listeleri=deepcopy(d.kod_listeleri)
    yeni.modul_bildirimleri=deepcopy(d.modul_bildirimleri)
    yeni.yeniden_kur()
    fark=farklar(son_hal(d),son_hal(yeni),sinir=3)
    if fark: raise AssertionError(('Kapsam/tam farki',fark))


def yurut(girdi,tam_kontrol=False,denetim_depolari=None,ilerleme=None,surum_koprusu=True):
    from contextlib import nullcontext
    from uyum_v8 import Kopru
    eski=girdi.get('bicim_surumu',1)<3 or girdi.get('surum_uyumu') in ('v8','v9')
    with Kopru() if eski and surum_koprusu else nullcontext():
        return _yurut(girdi,tam_kontrol,denetim_depolari,ilerleme)


def _yurut(girdi,tam_kontrol=False,denetim_depolari=None,ilerleme=None):
    depolar=[]; sonuc={'depolar':[], 'cihaz_denemeleri':[], 'saf_sorgular':[]}
    for kayit in girdi.get('depolar',[]):
        d=Depo(saat_kur(kayit['baslangic']),yontem=kayit.get('yontem','kapsamli'))
        depolar.append(d); cevaplar=[]; ara_haller=[]; denetim_bekliyor=False
        for adim in kayit['adimlar']:
            d.saat=saat_kur(adim['saat']); d.gorunum.saat=d.saat
            d.yontem=adim.get('yontem',d.yontem)
            tur=adim['tur']; args=coz(adim.get('args',[])); kwargs=coz(adim.get('kwargs',{}))
            if tur=='olay': cevap=dene(d.olay_ekle,*args,**kwargs)
            elif tur=='kurulum': cevap=dene(d.kurulum,*args,**kwargs)
            elif tur=='kapanis': cevap=dene(ay_kapanisi,d,*args,**kwargs)
            elif tur=='sorgu': cevap=dene(sorgu_fonksiyonu(adim['modul'],adim['ad']),d,*args,**kwargs)
            elif tur=='modul_bildirimi':
                if adim.get('ad') not in ('birak','kaldir'): raise ValueError('Modul bildirim islemi')
                cevap=dene(getattr(d,'modul_bildirimi_'+adim['ad']),*args,**kwargs)
            elif tur in ('ilerlet','yeniden_kur','demo_sifirla','olay_koru','cihaz_esitle','cihaz_kaydol'):
                cevap=dene(getattr(d,tur),*args,**kwargs)
            else: raise ValueError('Bilinmeyen adim: '+tur)
            # Kapanis zaten son halin parcasidir; ayni buyuk kaynagi iki kez yazma.
            if tur=='kapanis' and 'deger' in cevap: cevap={'deger':'KAPANDI'}
            cevaplar.append(cevap)
            if ilerleme and len(cevaplar)%500==0: ilerleme(len(cevaplar),len(kayit['adimlar']))
            if adim.get('kontrol'): ara_haller.append({'adim':len(cevaplar)-1,'son_hal':son_hal(d)})
            if tam_kontrol and (len(cevaplar)%100==0 or tur=='kapanis'): denetim_bekliyor=True
            hesap_yapildi = tur in ('ilerlet','yeniden_kur','demo_sifirla','kapanis') or (
                tur=='olay' and cevap.get('deger',{}).get('sonuc')=='BASARILI'
                and not cevap['deger'].get('tekrar'))
            # Red/tekrar motoru calistirmaz. Yeni saate ait tam hesap ile
            # onceki anda hesaplanmis gorunumu karsilastirmak hatali olur.
            if denetim_bekliyor and hesap_yapildi:
                tam_deneti(d); denetim_bekliyor=False
        d.saat=saat_kur(kayit['son_saat']); d.gorunum.saat=d.saat
        if tam_kontrol: tam_deneti(d)
        sonuc['depolar'].append({'cevaplar':cevaplar,'ara_haller':ara_haller,'son_hal':son_hal(d)})
    for kayit in girdi.get('cihaz_denemeleri',[]):
        c=Cihaz(kayit['kisi'],kayit['harf'],saat_kur(kayit['saat']))
        c.veri=coz(kayit['veri']); args=coz(kayit.get('args',[])); kwargs=coz(kayit.get('kwargs',{}))
        if kayit['ad']=='sayaci_esitle':
            from types import SimpleNamespace
            args=[SimpleNamespace(olaylar={k:{} for k in kayit['bulut_kimlikleri']})]
        if kayit['ad'] not in ('olay_kimligi_uret','sayaci_esitle','depo_kayboldu','yeniden_kaydol','ekran_hali','tazelik'):
            raise ValueError('Bilinmeyen cihaz islemi')
        cevap=dene(getattr(c,kayit['ad']),*args,**kwargs)
        sonuc['cihaz_denemeleri'].append({'cevap':cevap,'veri':kanonik(c.veri),'harf':c.harf})
    for s in girdi.get('saf_sorgular',[]):
        sonuc['saf_sorgular'].append(dene(sorgu_fonksiyonu(s['modul'],s['ad']),*coz(s['args']),**coz(s['kwargs'])))
    if denetim_depolari is not None: denetim_depolari.extend(depolar)
    return kanonik(sonuc)


def yaz(yol,veri):
    Path(yol).write_text(json.dumps(veri,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('girdi',nargs='?',type=Path); p.add_argument('--cikti',type=Path)
    p.add_argument('--dogrula',action='store_true'); p.add_argument('--tum',action='store_true')
    p.add_argument('--simulasyon',action='store_true')
    p.add_argument('--modul',choices=['M3'])
    p.add_argument('--degismez-kontrol',action='store_true',help='Akis sonunda I59-I131 denetimi; I1-I58 test takiminda')
    p.add_argument('--tam-kontrol',action='store_true',help='Her 100 adimda, kapanista ve sonda kaynaklardan tam hesapla karsilastir')
    a=p.parse_args()
    yollar=sorted((KOK/'senaryolar').glob('*.girdi.json')) if a.tum else ([a.girdi] if a.girdi else [])
    if a.tum or a.modul=='M3': yollar+=sorted((KOK/'modul_sozlesmeleri/modul3').glob('*.girdi.json'))
    if a.simulasyon: yollar+=sorted((KOK/'simulasyon').glob('*.girdi.json'))
    if not yollar: p.error('Girdi dosyasi, --tum veya --simulasyon gerekli')
    kalan=0
    for yol in yollar:
        denetim_depolari=[]
        sonuc=yurut(json.loads(yol.read_text('utf-8')),tam_kontrol=a.tam_kontrol,denetim_depolari=denetim_depolari,
            ilerleme=lambda n,s: print(yol.name+': '+str(n)+'/'+str(s)+' adim',flush=True))
        if a.degismez_kontrol:
            from irp.degismezler_v5 import denetle as d5
            from irp.degismezler_v6 import denetle as d6
            from irp.degismezler_v7 import denetle as d7
            from irp.degismezler_v9 import denetle as d9
            from irp.degismezler_v10 import denetle as d10
            from irp.degismezler_v10_1 import denetle as d101
            from irp.degismezler_v10_2 import denetle as d102
            for d in denetim_depolari:
                ss=dict(d5(d),**d6(d,True),**d7(d,True),**d9(d,True),**d10(d,True),**d101(d,True),**d102(d,True))
                assert all(ss.values()),(yol.name,ss)
            print(yol.name+': I59-I131 GECTI',flush=True)
        if a.cikti:
            if len(yollar)!=1: p.error('--cikti tek girdide kullanilir')
            yaz(a.cikti,sonuc)
        if a.dogrula or a.tum or a.simulasyon or a.modul:
            bek=oku(yol.with_name(yol.name.replace('.girdi.json','.beklenen.json')))
            fark=farklar(bek,sonuc,sinir=5); kalan+=bool(fark)
            print(yol.name+(': GECTI' if not fark else ': KALDI '+json.dumps(fark,ensure_ascii=True)),flush=True)
        elif not a.cikti: print(json.dumps(sonuc,ensure_ascii=False,indent=2))
    if a.dogrula or a.tum or a.simulasyon or a.modul: print(f'Toplam {len(yollar)}; gecen {len(yollar)-kalan}; kalan {kalan}')
    return 1 if kalan else 0


if __name__=='__main__': raise SystemExit(main())
