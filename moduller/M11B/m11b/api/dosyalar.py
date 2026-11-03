from ..alan import yetki
from ..alan.hatalar import ModulHatasi
from ..depo import devir

def izin(b,target,write):
    if target.get('tur')!='PROJE':raise ModulHatasi(403,'YETKI','Dosya nesnesi uygun değil.')
    p=b.proje(str(target.get('kimlik','')))
    if write and not yetki.sorumlu_ya_da_yetkili(b,p):
        with b.vt.islem() as c:
            folders=devir.klasorler(c,p['kimlik'])
        if not any(yetki.dosya_ekleyebilir(b,p,k) for k in folders):
            raise ModulHatasi(403,'YETKI','Bu projeye dosya ekleyemezsiniz.')
