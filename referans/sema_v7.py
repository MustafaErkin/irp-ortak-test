"""T8 JSON Schema alanlari; anlamsal iliski ve takvim kapilari modeldedir."""
from copy import deepcopy
from irp.kurallar_v7 import SEMALAR


def genislet(semalar,alan):
    metin={'type':'string'}; sayi={'type':'number','minimum':0,'maximum':100}
    dizi=lambda x: {'type':'array','items':x}
    bag={'type':'object','required':['tur','kimlik'],'properties':{'tur':metin,'kimlik':metin}}
    sorumlu=deepcopy(bag); sorumlu['required']+=['yuzde']; sorumlu['properties']['tur']={'enum':['KISI','BIRIM']}; sorumlu['properties']['yuzde']=sayi
    ek={k:deepcopy(metin) for k in ('anahtar','gun','ozet_surumu','yeni_asama','baslangic_asamasi','sorumlu','karar','tanimsiz_aciklama')}
    ek.update(asamalar=dizi({'oneOf':[metin,{'type':'object','required':['kod'],'properties':{'kod':metin}}]}),
        gecisler=dizi({'type':'object','required':['den','e','kimler'],'properties':{'den':metin,'e':metin,'kimler':dizi(metin)}}),
        acabilenler={'oneOf':[dizi(metin),{'type':'object','required':['kimler'],'properties':{'kimler':dizi(metin),'kapsam':{'enum':['BIRIM','FIRMA']}}}]},baglanabilir_turler=dizi(metin),son_asamalar=dizi(metin),baglar=dizi(bag),
        yuzde=sayi,sorumlular=dizi(sorumlu),
        vardiyalar=dizi({'type':'object','required':['gunler','bas','bit'],'properties':{'gunler':dizi({'type':'integer','minimum':1,'maximum':7}),'bas':metin,'bit':metin}}))
    for kod in SEMALAR:
        g=semalar[kod]['girdi_semasi']
        for k in list(g['properties']):
            if k in ek: g['properties'][k]=deepcopy(ek[k])
        if kod=='AYAR.DEGISTIRDIM':
            g['properties']['deger']={}; g['properties']['gecerli_baslangic']=alan['gecerli_baslangic']
            g['properties']['anahtar']={'enum':['standart_gunluk_saat','fazla_mesai_katsayilari','gun_sonu_raporu_zorunlu','gun_sonu_hatirlatma','izin_ik_onayi']}
        if kod=='DURUS.BASLADI': g['properties']['kapsam']={'oneOf':[{'const':'FIRMA'},{'type':'array','minItems':1,'uniqueItems':True,'items':metin}]}
        if kod=='GUN.TANIMLADIM':
            g['properties']['tur']={'enum':['TATIL','YARIM_GUN','OZEL_MESAI']}
            for k in ('mesai_baslangic','mesai_bitis','sabit_molalar'): g['properties'][k]=deepcopy(alan[k])
            g['allOf']=[{'if':{'properties':{'tur':{'enum':['YARIM_GUN','OZEL_MESAI']}}},'then':{'required':['mesai_baslangic','mesai_bitis','sabit_molalar']}}]
        if kod=='NESNE.ACTIM': g['properties']['baglar']=ek['baglar']
        if kod=='NESNE_TURU.TANIMLADIM': g['properties']['son_asamalar']=ek['son_asamalar']
        if kod.startswith('SORUMLULUK.'):
            g['properties']['yuzde']=sayi
            if kod.endswith('DOGRULADIM'): g['properties']['karar']={'enum':['ONAY','DEGISTIR','KALDIR']}
            if kod.endswith('ITIRAZI_DEGERLENDIRDIM'): g['properties']['karar']={'enum':['KABUL','RET']}
        semalar[kod]['yazabilen']='T8 14 + sabit iliski + birim zinciri; kabul aninda model/irp/kurallar_v7.py denetler.'
    for kod in ('IS.REDDETTIM','GOREV.REDDETTIM'): semalar[kod]['girdi_semasi']['properties']['sorumlular']=ek['sorumlular']
    for kod in ('IS.ATADIM','GOREV.ATADIM'):
        semalar[kod]['girdi_semasi']['properties']['ek_mesai']={'type':'object','required':['tarih','baslangic','bitis'],'properties':{k:metin for k in ('tarih','baslangic','bitis','aciklama')}}
    semalar['KOD.TANIMLADIM']['girdi_semasi']['properties']['liste']={'enum':['ARIZA','MOLA','PD','ROL','IZIN','DURUS']}
    semalar['IS.BAGLANTI_DUZELTTIM']['girdi_semasi']['properties']['degisenler']['properties']['nesne']= {'type':['string','null']}
