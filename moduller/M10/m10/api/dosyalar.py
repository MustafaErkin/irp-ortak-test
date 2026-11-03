from .. import hatalar,vt
from ..depo import talepler

def izin(b,target,write):
    if target.get('tur')!='TALEP' or not b.kisi.erisim or write and not b.kisi.duzenleyici:
        raise hatalar.yetki('Bu dosya için yetkiniz yok.')
    try:identity=int(target['kimlik'])
    except (ValueError,TypeError,KeyError):raise hatalar.bulunamadi() from None
    with vt.islem() as c:
        if not talepler.bul(c,identity):raise hatalar.bulunamadi()
