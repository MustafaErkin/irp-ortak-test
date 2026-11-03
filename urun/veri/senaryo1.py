"""Karar 144–147: kullanıma hazır, iş verisi boş altı kişilik firma.

Yalnız ana veri olayları üretir. Proje/etap/iş/görev veya sahte teslim üretmez.
Mevcut kurulum ve kabul kuralları kullanılır; cevap anahtarı değiştirilmez.
"""
from datetime import date, timedelta
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from urun.veri.canli_veri import Uretici,yurutucu,kurulum_paketi,yetki_ve_kodlar,an

from urun.veri.cekirdek_onkosullari import eksikler

KISILER=(
    ('K001','CEO','YONETIM',['YETKILI'],'BEYAZ',135000,'web'),
    ('K004','Yönetici','PLANLAMA',['YONETICI'],'BEYAZ',117000,'web'),
    ('K009','Ekip Lideri','IMALAT',['EKIP_LIDERI'],'MAVI',70200,'ikisi'),
    ('K041','Ofis Çalışanı','MEK_TASARIM',['BEYAZ_YAKA'],'BEYAZ',93600,'web'),
    ('K017','Atölye Çalışanı','IMALAT',['CALISAN'],'MAVI',63000,'telefon'),
    ('K031','Saha Çalışanı','KURULUM',['CALISAN'],'MAVI',63000,'telefon'),
)


def uret(bugun=None):
    bugun=bugun or date.today()
    kurulus=bugun-timedelta(days=1)
    y=yurutucu()
    u=Uretici(y,an(kurulus,'06:59'))
    paket,kodlar=kurulum_paketi(kurulus)
    for event in paket:
        if event['eylem_kodu']=='KISI.EKLEDIM':
            event['girdiler']['ad']='CEO'
    u.kurulum(an(kurulus,'07:00'),paket,kodlar)
    u.sayac[('K001','M',kurulus.strftime('%y%m%d'))]=len(paket)
    for code,g in yetki_ve_kodlar():
        u.olay(an(kurulus,'07:01'),'K001',code,g)
    minute=2

    def emit(code,g,**kw):
        nonlocal minute
        t=an(kurulus,'07:00')+timedelta(minutes=minute)
        minute+=1
        return u.olay(t,'K001',code,g,**kw)

    for code,name,kind,parent in (
        ('PLANLAMA','Proje Yönetimi','MASA_BASI','YONETIM'),
        ('MEK_TASARIM','Ofis','MASA_BASI','PLANLAMA'),
        ('IMALAT','Atölye','ATOLYE','PLANLAMA'),
        ('KURULUM','Saha','ATOLYE','IMALAT'),
    ):
        emit('BIRIM.TANIMLADIM',{'kod':code,'ad':name,'tur':kind,'ust_birim':parent,'basi':None})
    for code,name,unit,roles,collar,salary,_ in KISILER:
        if code!='K001':
            emit('KISI.EKLEDIM',{'kod':code,'ad':name,'birim':unit,'roller':roles,'yaka':collar,'giris_tarihi':kurulus.isoformat()})
        emit('MAAS.GUNCELLEDIM',{'kisi':code,'gecerli_baslangic':kurulus.isoformat()},hassas={
            'nesne_tur':'KISI','nesne_kimlik':code,'tur':'MAAS_AYLIK','tutar':salary,'gecerli_baslangic':kurulus.isoformat()})
    for code,name,kind,parent,head in (
        ('PLANLAMA','Proje Yönetimi','MASA_BASI','YONETIM','K004'),
        ('MEK_TASARIM','Ofis','MASA_BASI','PLANLAMA','K004'),
        ('IMALAT','Atölye','ATOLYE','PLANLAMA','K009'),
        ('KURULUM','Saha','ATOLYE','IMALAT','K009'),
    ):
        emit('BIRIM.TANIMLADIM',{'kod':code,'ad':name,'tur':kind,'ust_birim':parent,'basi':head})
    # T9 §6.3 / karar 57: CEO, etap planını kendi proje sorumlusuna devreder.
    # Etap açma yetkisi CEO'da kalır; başka projede yönetici istisnası yoktur.
    emit('YETKI.TANIMLADIM',{'eylem_kodu':'ETAP.DEGISTIRDIM','kimler':['YETKILI','PROJE_SORUMLUSU'],'kapsam':'FIRMA'})
    for code,g in eksikler([],[]):
        emit(code,g)
    data=u.girdi(bugun)
    data.update(senaryo='senaryo1',kaynak='urun/veri/senaryo1.py')
    return y,u,data
