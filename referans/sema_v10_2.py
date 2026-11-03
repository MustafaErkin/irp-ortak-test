"""T11'in isteğe bağlı alanları ve yeni olayın alan sözleşmesi."""
from copy import deepcopy


def genislet(s):
    metin={'type':'string','minLength':1}; kod={'type':['string','null'],'minLength':1}
    s['NESNE.ACTIM']['girdi_semasi']['properties']['proje']=deepcopy(kod)
    s['KISI.YETKINLIK_TANIMLADIM']['girdi_semasi']['properties']={
        'kisi':metin,'yetkinlikler':{'type':'array','uniqueItems':True,'items':metin},
        'gecerli_baslangic':{'type':'string','format':'date'}}
    s['IS.TANIMLADIM']['girdi_semasi']['properties']['isler']['items']['properties']['yetkinlik']=deepcopy(kod)
    s['IS.PLANSIZ_TANIMLADIM']['girdi_semasi']['properties']['yetkinlik']=deepcopy(kod)
    s['IS.DEGISTIRDIM']['girdi_semasi']['properties']['degisenler'].setdefault('properties',{})['yetkinlik']=deepcopy(kod)
    s['MODUL.TANIMLADIM']['girdi_semasi']['properties']['cihaz_harfi']={'type':'string','pattern':'^[A-Z]$'}
    s['NOT.YAZDIM']['izinli_hedef_turleri']=['PARCA','GOREV','PROJE','NESNE']
    s['KOD.TANIMLADIM']['girdi_semasi']['properties']['liste']['enum'].append('YETKINLIK')


def kapi_semasi():
    from sema_v10_1 import kapi_semasi as eski
    s=eski(); s['surum']='10.2'
    s['birak_cevabi']={'type':'object','required':['sonuc','alicilar','yeni','guncellenen','alici_kalmadi','suzulenler'],
        'properties':{'sonuc':{'const':'BASARILI'},'alicilar':{'type':'array','items':{'type':'string'}},
                      'yeni':{'type':'integer','minimum':0},'guncellenen':{'type':'integer','minimum':0},'alici_kalmadi':{'type':'boolean'},
                      'suzulenler':{'type':'array','items':{'type':'object','required':['kisi','neden'],
                          'properties':{'kisi':{'type':'string'},'neden':{'enum':['PROJEYI_GOREMEZ','AYRILDI','ISTIHDAM_DISI']}}}}}}
    return s
