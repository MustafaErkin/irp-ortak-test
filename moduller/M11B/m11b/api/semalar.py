"""İsteklerin gövdeleri (Pydantic v2)."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class PlanSatiri(BaseModel):
    sira: int = Field(ge=1)
    etap: str | None = None
    okunan_surum: str | None = None
    ad: str = ''
    birim: str | None = None
    baslangic: date | None = None
    bitis: date | None = None
    hedef_saat: int = 0
    sorumlu: str | None = None
    sablon_kodu: str | None = None
    paralel_grup: str | None = None
    tasarim_kapisi: bool | None = None


class Taslak(BaseModel):
    satirlar: list[PlanSatiri] = []
    neden: Literal['MUSTERI_OTELEMESI', 'KARSILIKLI_ANLASMA'] | None = None
    gerekce: str | None = None
    kanitlar: list[int] = []

    def sozluk(self):
        d = self.model_dump()
        for s in d['satirlar']:
            for k in ('baslangic', 'bitis'):
                s[k] = s[k].isoformat() if s[k] else None
        return d


class DosyaKaydi(BaseModel):
    tur: Literal['TASARIM_GIRDISI', 'RISK_ANALIZI', 'TGG', 'TUTANAK', 'PLAN_KANITI', 'DIGER']
    ad: str
    konum: str
    klasor: int | None = None
    aciklama: str | None = None
    parmak_izi: str | None = None


class Gecis(BaseModel):
    gerekce: str


class YeniDosya(BaseModel):
    ad: str
    konum: str
    aciklama: str | None = None
    parmak_izi: str | None = None


class GorevAtama(BaseModel):
    etap: str
    etap_surum: str | None = None
    kisiler: list[str] = Field(min_length=1)
    ad: str = Field(min_length=1)
    teslim_tarihi: date
    zaman_degeri: int = Field(ge=1)
    zorluk: int = Field(default=3, ge=1, le=5)
    oncelik: Literal['NORMAL', 'YUKSEK', 'ACIL'] = 'NORMAL'
    onay_gerekli: bool = False
    onaylayan: str | None = None
    dosya_gerekli: bool = False
    is_tanimi: str | None = None
    planlanan_baslangic: str | None = None
    planlanan_bitis: str | None = None
    tgg: bool = False
    tgg_dosyasi: int | None = None
    yeni_tgg: YeniDosya | None = None

    def sozluk(self):
        d = self.model_dump()
        d['teslim_tarihi'] = d['teslim_tarihi'].isoformat()
        return d


class BilgiNotu(BaseModel):
    kategori: str
    alici_birim: str
    metin: str
    etap: str | None = None
    bagli_gorev: str | None = None
    ekler: list[int] = []


class Sunum(BaseModel):
    tarih: date | None = None
    tutanak: int | None = None
    yeni_tutanak: YeniDosya | None = None

    def sozluk(self):
        d = self.model_dump()
        d['tarih'] = d['tarih'].isoformat() if d['tarih'] else None
        return d


class SorumluDegisikligi(BaseModel):
    sorumlu: str = Field(pattern=r'^K[0-9]{3}$')
    proje_surum: str | None = None


class EtapSablonuAyari(BaseModel):
    kod: str
    varsayilan_birim: str | None = None
    aktif: bool = True


class KlasorSablonuAyari(BaseModel):
    kod: str
    sorumlu_birim: str | None = None


class KategoriAyari(BaseModel):
    kod: str
    varsayilan_birim: str | None = None


class SablonAyarlari(BaseModel):
    etaplar: list[EtapSablonuAyari] = []
    klasorler: list[KlasorSablonuAyari] = []
    kategoriler: list[KategoriAyari] = []
