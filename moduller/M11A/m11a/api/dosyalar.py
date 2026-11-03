from ..alan import yetki
from .hatalar import ModulHatasi

def izin(i,target,write):
    if target.get('tur') not in ('PROJE','TEKNIK_GIRDI'):
        raise ModulHatasi(403,'YETKI','Dosya nesnesi uygun değil.')
    if not i.proje(str(target.get('kimlik',''))):
        raise ModulHatasi(403,'YETKI','Bu projenin dosyasını göremiyorsunuz.')
    if write or target['tur']=='PROJE':i.rol_gerek(yetki.SIPARIS_VE_TICARI)
