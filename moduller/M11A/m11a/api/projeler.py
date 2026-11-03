"""Proje kartı, sipariş, ticari form, devir, eksikler, VEGA, dosyalar, gelen kutusu (SPEC › 8.2–8.4, 9)."""
from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field

from ..alan import devir, kapanis, proje as proje_kaydi, saglanan, serit, ticari, tutar
from .baglam import Istek, istek
from .donustur import DosyaGirdi

yol = APIRouter()
PARA_BIRIMI = r'^[A-Z]{3}$'


class SiparisGirdi(BaseModel):
    po_no: str | None = None
    po_dosyasi: DosyaGirdi | None = None
    sozlesme_dosyasi: DosyaGirdi | None = None


class OdemeGirdi(BaseModel):
    kosul: Literal['SIPARIS', 'SEVK', 'ON_KABUL', 'KESIN_KABUL', 'TARIH', 'DIGER']
    tarih: date | None = None
    tutar: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    para_birimi: str = Field(pattern=PARA_BIRIMI)
    aciklama: str | None = None


class TeminatGirdi(BaseModel):
    tur: Literal['AVANS', 'KESIN', 'DIGER']
    tutar: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    para_birimi: str = Field(pattern=PARA_BIRIMI)
    banka: str | None = None
    bitis_tarihi: date | None = None
    dosya: int | None = None
    aciklama: str | None = None


class TicariGirdi(BaseModel):
    surum: int
    faturalama_bicimi: Literal['PESIN', 'KADEMELI', 'SEVKTE', 'ON_KABULDE', 'KESIN_KABULDE', 'HAKEDIS'] | None = None
    faturalama_notu: str | None = None
    teslim_sekli: str | None = None
    ihracat: bool | None = None
    tesvik: Literal['VAR', 'YOK'] | None = None
    tesvik_belge_no: str | None = None
    teminat_gerekli: Literal['VAR', 'YOK'] | None = None
    notlar: str | None = None
    odeme_satirlari: list[OdemeGirdi] = []
    teminatlar: list[TeminatGirdi] = []


class DosyaKaydi(DosyaGirdi):
    tur: Literal['PO', 'SOZLESME', 'TEMINAT', 'TUTAR_DEGISIKLIGI', 'FATURA', 'DIGER']


class EksikGirdi(BaseModel):
    ne: str
    aciklama: str | None = None


class EksikDurumu(BaseModel):
    durum: Literal['EKSIK', 'ISTENDI', 'ALINDI']
    kimden: Literal['MUSTERI', 'SATIS', 'DIGER'] | None = None
    aciklama: str | None = None


class VegaGirdi(BaseModel):
    vega_cari_kodu: str | None = None
    vega_proje_kodu: str | None = None


@yol.get('/projeler')
def projeler_listesi(i: Istek = Depends(istek)):
    from ..depo import projeler as depo
    from ..alan import yetki
    i.rol_gerek(yetki.SIPARIS_VE_TICARI)
    rows=i.b.execute('SELECT proje,proje_adi,musteri_adi,durum,siparis_tarihi,teslim_tarihi,butce_durumu,acan '
                     'FROM mod_m11a.projeler ORDER BY acilis_ani DESC').fetchall()
    result=[]
    for row in rows:
        if row['durum']=='ACILIYOR' and row['acan']==i.kisi or i.proje_gorur_mu(row['proje']):
            result.append({k:v.isoformat() if hasattr(v,'isoformat') else v for k,v in row.items() if k!='acan'})
    return {'projeler':result}


@yol.get('/projeler/{p}/dosyalar')
def dosya_listesi(p: str,i: Istek = Depends(istek)):
    from ..depo import projeler as depo
    from ..alan import yetki
    i.rol_gerek(yetki.SIPARIS_VE_TICARI)
    proje_kaydi.kayit(i,p)
    return {'dosyalar':depo.dosyalar(i.b,p)}


@yol.get('/projeler/{p}')
def kart(p: str, i: Istek = Depends(istek)):
    return proje_kaydi.kart(i, p)


@yol.put('/projeler/{p}/siparis')
def siparis(p: str, g: SiparisGirdi, i: Istek = Depends(istek)):
    return ticari.siparis_yaz(i, p, g)


@yol.get('/projeler/{p}/ticari')
def ticari_form(p: str, i: Istek = Depends(istek)):
    return ticari.form(i, p)


@yol.put('/projeler/{p}/ticari')
def ticari_yaz(p: str, g: TicariGirdi, i: Istek = Depends(istek)):
    return ticari.form_yaz(i, p, g)


@yol.post('/projeler/{p}/dosyalar')
def dosya(p: str, g: DosyaKaydi, i: Istek = Depends(istek)):
    return ticari.dosya_ekle(i, p, g)


@yol.post('/projeler/{p}/devir')
def devret(p: str, i: Istek = Depends(istek)):
    return devir.devret(i, p)


@yol.post('/projeler/{p}/devir/aldim')
def devri_aldim(p: str, i: Istek = Depends(istek)):
    return devir.devri_aldim(i, p)


@yol.post('/projeler/{p}/devir/tamamla')
def devri_tamamla(p: str, i: Istek = Depends(istek)):
    return devir.devri_tamamla(i, p)


@yol.post('/projeler/{p}/eksikler')
def eksik_ekle(p: str, g: EksikGirdi, i: Istek = Depends(istek)):
    return devir.eksik_ekle(i, p, g.ne, g.aciklama)


@yol.put('/projeler/{p}/eksikler/{e}')
def eksik_guncelle(p: str, e: int, g: EksikDurumu, i: Istek = Depends(istek)):
    return devir.eksik_guncelle(i, p, e, g.durum, g.kimden, g.aciklama)


@yol.put('/projeler/{p}/vega')
def vega(p: str, g: VegaGirdi, i: Istek = Depends(istek)):
    return ticari.vega_yaz(i, p, g)


@yol.get('/gelen-kutusu')
def gelen_kutusu(i: Istek = Depends(istek)):
    return devir.gelen_kutusu(i)


@yol.get('/projeler/{p}/butce')
def butce(p: str, i: Istek = Depends(istek)):
    return serit.butce(i, p)


@yol.get('/butceler')
def butceler(i: Istek = Depends(istek)):
    return serit.butceler(i)


class TutarDegisikligi(BaseModel):
    yeni_tutar: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    butce: dict[Literal['MALZEME', 'ISCILIK', 'FASON', 'GENEL_GIDER'], Decimal]
    gerekce: str
    belge: int | None = None
    belge_dosyasi: DosyaGirdi | None = None


@yol.post('/projeler/{p}/tutar-degisikligi')
def tutar_degisikligi(p: str, g: TutarDegisikligi, i: Istek = Depends(istek)):
    return tutar.degistir(i, p, g)


class KapanisGirdi(BaseModel):
    kesin_kabul_tarihi: date | None = None


class DuzeltmeGirdi(BaseModel):
    kalem: Literal['MALZEME', 'ISCILIK', 'FASON', 'GENEL_GIDER']
    tutar: Decimal = Field(max_digits=14, decimal_places=2)
    gerekce: str
    belge: int | None = None
    belge_dosyasi: DosyaGirdi | None = None


@yol.post('/projeler/{p}/kapanis')
def kapanis_(p: str, g: KapanisGirdi, i: Istek = Depends(istek)):
    return kapanis.kapat(i, p, g.kesin_kabul_tarihi)


@yol.post('/projeler/{p}/kapanis-sonrasi')
def kapanis_sonrasi(p: str, g: DuzeltmeGirdi, i: Istek = Depends(istek)):
    return kapanis.duzelt(i, p, g)


@yol.get('/projeler/{p}/baslangic-plani')
def baslangic_plani(p: str, i: Istek = Depends(istek)):
    return saglanan.baslangic_plani(i, p)


@yol.get('/projeler/{p}/teklif-girdileri')
def teklif_girdileri(p: str, i: Istek = Depends(istek)):
    return saglanan.teklif_girdileri(i, p)


@yol.post('/projeler/{p}/teknik-girdileri-aktar')
def teknik_aktar(p: str,i: Istek = Depends(istek)):
    from ..alan import teknik
    return teknik.devret(i,proje_kaydi.kayit(i,p))


@yol.get('/projeler/{p}/teklif-pdf')
def teklif_pdf(p: str, i: Istek = Depends(istek)):
    pdf, ad = saglanan.teklif_pdf(i, p)
    return Response(pdf, media_type='application/pdf', headers={'Content-Disposition': f'inline; filename="{ad}"'})
