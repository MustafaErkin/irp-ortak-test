"""T9 olay alanlari; iliskisel kapilar kurallar_v9.py ile denetlenir."""
from copy import deepcopy


def genislet(semalar,alan):
    metin={'type':'string'}; bos={'type':['string','null']}
    tarih={'type':'string','format':'date'}; an={'type':'string','format':'date-time'}
    dizi=lambda x: dict(type='array',items=x)
    sorumlu=dict(type='object',required=['tur','kimlik','yuzde'],properties=dict(
        tur=dict(enum=['KISI','BIRIM','DIS']),kimlik=metin,yuzde=dict(type='number',minimum=0,maximum=100)))
    deg=dict(type='object',required=['kaynak','neden'],properties=dict(kaynak=metin,
        neden=dict(enum=['MUSTERI','HATA','IYILESTIRME']),sorumlular=dizi(dict(sorumlu,properties=dict(sorumlu['properties'],tur=dict(enum=['KISI','BIRIM']))))))
    takvim=dict(type='object',required=['mesai_baslangic','mesai_bitis','gunler','sabit_molalar'],properties=dict(
        mesai_baslangic=metin,mesai_bitis=metin,gunler=dict(type='array',minItems=1,uniqueItems=True,items=dict(type='integer',minimum=1,maximum=7)),sabit_molalar=alan['sabit_molalar']))
    def ek(eylem,**alanlar): semalar[eylem]['girdi_semasi']['properties'].update(deepcopy(alanlar))
    for kod in ('PROJE.ACTIM','PROJE.KOD_DEGISTIRDIM'):
        ek(kod,kod=dict(type='string',minLength=1),ek=bos)
    semalar['PROJE.KOD_DEGISTIRDIM']['zorunlu_hedef_turu']='PROJE'
    ek('PROJE.ACTIM',kimlik=metin,ana_proje=bos,sorumlu=bos,baslangic_tarihi=tarih,kesin_kabul_tarihi=tarih)
    for k in ('PROJE.DEGISTIRDIM','GOREV.DEGISTIRDIM'):
        p=semalar[k]['girdi_semasi']['properties']['degisenler'].setdefault('properties',{})
        p.update(dict(sorumlu=bos,baslangic_tarihi=tarih,kesin_kabul_tarihi=tarih) if k.startswith('PROJE') else dict(oncelik=dict(enum=['NORMAL','YUKSEK','ACIL'])))
    for k,s in [('IS.TANIMLADIM','isler'),('GOREV.ATADIM','gorevler')]:
        p=semalar[k]['girdi_semasi']['properties'][s]['items']['properties']; p['degisiklik']=deepcopy(deg)
        if s=='gorevler': p['oncelik']=dict(enum=['NORMAL','YUKSEK','ACIL'])
    ek('IS.PLANSIZ_TANIMLADIM',degisiklik=deg)
    ek('GOREV.TAMAMLADIM',gecikme_nedeni=metin,gecikme_aciklamasi=metin)
    ek('IS.TAMAMLADIM',makine_bitis_ani=an)
    ek('BIRIM.TANIMLADIM',takvim=takvim,takvim_gecerli=tarih)
    semalar['BIRIM.TANIMLADIM']['girdi_semasi']['dependentRequired']={'takvim':['takvim_gecerli']}
    ek('KOD.TANIMLADIM',ust=bos,liste=dict(enum=['ARIZA','MOLA','PD','ROL','IZIN','DURUS','DURUS_NEDENI']))
    ek('NESNE.ACTIM',kod=bos)
    # Okuma satiri olay degildir; yalniz yetki tablosunun girdisinde gecerlidir.
    semalar['YETKI.TANIMLADIM']['girdi_semasi']['properties']['eylem_kodu']['enum'].append('PROJE.HEPSINI_GORUR')
    ek('GECIKME.DEGERLENDIRDIM',sorumlular=dict(type='array',minItems=1,items=sorumlu))
    ek('GUN_ONAYI.AYARLADIM',gerekli=dict(type='boolean'),gecerli_baslangic=tarih)
    ek('BILDIRIM.GORDUM',bildirimler=dict(type='array',minItems=1,items=metin))
    for kod in ('SORUMLULUK.DOGRULADIM','SORUMLULUK.ITIRAZ_ETTIM','SORUMLULUK.ITIRAZI_DEGERLENDIRDIM'):
        ek(kod,satir=dict(type='integer',minimum=1))
    for kod in ('GUN_SONU.GONDERDIM','GUN_SONU.ONAYLADIM'): ek(kod,kisi=metin,gun=tarih)
    ek('GUN_SONU.GONDERDIM',aciklama=metin,tanimsiz_aciklama=metin)
    gun=dict(type='object',required=['kisi','gun','ozet_surumu'],properties=dict(kisi=metin,gun=tarih,ozet_surumu=metin))
    ek('GUN_SONU.ONAYLADIM',ozet_surumu=metin,gunler=dict(type='array',minItems=1,items=gun),**{'not':metin})
    semalar['GUN_SONU.ONAYLADIM']['girdi_semasi']['oneOf']=[dict(required=['kisi','gun','ozet_surumu'],**{'not':dict(required=['gunler'])}),dict(required=['gunler'])]
    semalar['AYAR.DEGISTIRDIM']['girdi_semasi']['properties']['anahtar']['enum'].append('proje_gorunurlugu')
