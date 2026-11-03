"""Projeye ait uçlar. {proje} taşıyan her uç önce PROJE'yi kullanıcının gözüyle okur (SPEC › 6, 9)."""
from fastapi import APIRouter, Depends

from ..alan import acilis, devir, dosya, gantt, gorevler, kapi, klasor, projeler, sorumlu, sunum, yetki
from ..alan.zaman import kayit
from ..depo import devir as depo_devir
from .bagimlilik import baglam
from .semalar import DosyaKaydi, Gecis, GorevAtama, SorumluDegisikligi, Sunum

yonlendirici = APIRouter(tags=['projeler'])


def _devir(d):
    return kayit(d)


@yonlendirici.get('/projeler')
def projeler_listesi(b=Depends(baglam)):
    return b.yanit({'projeler': projeler.projeler_listesi(b)})


@yonlendirici.post('/projeler/{proje}/devir')
def devri_baslat(proje: str, b=Depends(baglam)):
    d, yeni = devir.devri_baslat(b, proje)
    from ..alan import siparis
    return b.yanit({'devir': _devir(d), 'yeni': yeni, 'siparis_kaynagi':siparis.al(b,proje)})


@yonlendirici.get('/projeler/{proje}/siparis-kaynagi')
def siparis_kaynagi(proje: str, b=Depends(baglam)):
    from ..alan import siparis
    return b.yanit(siparis.gorunum(b,proje))


@yonlendirici.post('/projeler/{proje}/siparis-kaynagi')
def siparis_aktar(proje: str, b=Depends(baglam)):
    from ..alan import siparis
    return b.yanit(siparis.al(b,proje))


@yonlendirici.get('/projeler/{proje}')
def proje_ozeti(proje: str, b=Depends(baglam)):
    p = b.proje(proje)
    with b.vt.islem() as c:
        d = depo_devir.devir(c, proje)
        klasorler = depo_devir.klasorler(c, proje) if d else []
    return b.yanit({
        'proje': {k: p.get(k) for k in ('kimlik', 'kod', 'ad', 'musteri', 'sorumlu', 'aktif', 'baslangic_tarihi',
                                        'teslim_tarihi', 'kesin_kabul_tarihi', 'surum')},
        'sorumlu_adi': b.kisi_adi(p.get('sorumlu')),
        'devir': _devir(d),
        'acilis': acilis.acilis(b, proje) if d else None,
        'izinler': yetki.izinler(b, p, klasorler),
    })


@yonlendirici.get('/projeler/{proje}/klasorler')
def klasorler(proje: str, b=Depends(baglam)):
    return b.yanit(klasor.klasorler(b, proje))


@yonlendirici.get('/projeler/{proje}/gantt')
def gantt_(proje: str, b=Depends(baglam)):
    return b.yanit(gantt.gantt(b, proje))


@yonlendirici.post('/projeler/{proje}/dosyalar')
def dosya_ekle(proje: str, govde: DosyaKaydi, b=Depends(baglam)):
    kayit_ = dosya.dosya_ekle(b, proje, govde.model_dump())
    acilis.degerlendir(b, proje)
    return b.yanit({'dosya': klasor.dosya_metni(kayit_)})


@yonlendirici.get('/projeler/{proje}/kapi')
def kapi_durumu(proje: str, b=Depends(baglam)):
    return b.yanit(kapi.kapi(b, proje))


@yonlendirici.post('/projeler/{proje}/kapi/gecis')
def kapi_gecis(proje: str, govde: Gecis, b=Depends(baglam)):
    return b.yanit(kapi.gecis(b, proje, govde.gerekce))


@yonlendirici.get('/projeler/{proje}/gorevler')
def gorev_satirlari(proje: str, b=Depends(baglam)):
    return b.yanit(gorevler.gorev_satirlari(b, proje))


@yonlendirici.post('/projeler/{proje}/gorevler')
def gorev_ata(proje: str, govde: GorevAtama, b=Depends(baglam)):
    sonuc = gorevler.gorev_ata(b, proje, govde.sozluk())
    acilis.degerlendir(b, proje)
    return b.yanit(sonuc)


@yonlendirici.post('/projeler/{proje}/sunum')
def sunum_kaydet(proje: str, govde: Sunum, b=Depends(baglam)):
    d = sunum.sunum_kaydet(b, proje, govde.sozluk())
    return b.yanit({'devir': d, 'acilis': acilis.degerlendir(b, proje)})


@yonlendirici.put('/projeler/{proje}/sorumlu')
def sorumlu_degistir(proje: str, govde: SorumluDegisikligi, b=Depends(baglam)):
    return b.yanit(sorumlu.sorumlu_degistir(b, proje, govde.sorumlu, govde.proje_surum))
