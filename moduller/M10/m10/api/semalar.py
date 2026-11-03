"""İstek gövdeleri (Pydantic v2). Tutarlar Decimal; JSON'da ondalık metin olarak gelir ("56000.00")."""
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Metin = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Kod = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r'^[A-Z][A-Z0-9_]{1,39}$')]
ParaKodu = Annotated[str, StringConstraints(pattern=r'^[A-Z]{3}$')]
Tutar = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]
Saat = Annotated[Decimal, Field(ge=0, max_digits=8, decimal_places=1)]
ButceKalemi = Literal['MALZEME', 'ISCILIK', 'FASON', 'GENEL_GIDER']


class Govde(BaseModel):
    model_config = ConfigDict(extra='forbid')


# ---- ayarlar

class Unsur(Govde):
    kod: Kod
    ad: Metin
    butce_kalemi: ButceKalemi
    sik: bool = False
    aktif: bool = True
    sira: int = 100


class YeniUnsur(Govde):
    ad: Metin
    butce_kalemi: ButceKalemi
    sik: bool = False


class KatalogKalemi(Govde):
    kimlik: int | None = None
    kod: Metin
    ad: Metin
    unsur: Kod
    olcu_birimi: Metin = 'adet'
    birim_fiyat: Tutar | None = None
    para_birimi: ParaKodu | None = None
    fiyat_tarihi: date | None = None
    fiyat_kaynagi: str | None = None
    tipik_temin_hafta: Annotated[int, Field(ge=0)] | None = None
    kritik: bool = False
    aktif: bool = True


class MakineTuru(Govde):
    kod: Kod
    ad: Metin
    tipik_toplam_hafta: Annotated[int, Field(gt=0)] | None = None
    aktif: bool = True


class BaslangicSatiri(Govde):
    makine_turu: Kod
    birim: Metin
    tipik_saat: Saat
    tipik_sure_hafta: Annotated[int, Field(ge=0)] | None = None


class SaatUcreti(Govde):
    birim: Metin
    ucret: Tutar
    para_birimi: ParaKodu


class SablonSatiri(Govde):
    kod: Kod
    birim: str | None = None
    aktif: bool = True


class Firma(Govde):
    unvan: Metin
    adres: str = ''
    telefon: str = ''
    eposta: str = ''
    web: str = ''


class VarsayilanMetinler(Govde):
    odeme_kosullari: str = ''
    teslim_kosullari: str = ''
    notlar: str = ''


class ParaBirimiAktifligi(Govde):
    kod: ParaKodu
    aktif: bool


class GenelAyarlar(Govde):
    firma: Firma
    varsayilan_metinler: VarsayilanMetinler
    varsayilan_gecerlilik_gun: Annotated[int, Field(gt=0)]
    varsayilan_para_birimi: ParaKodu
    cevap_uyari_gun: Annotated[int, Field(ge=0)]
    yonetim_birimleri: list[Metin]
    para_birimleri: list[ParaBirimiAktifligi] = []


class GecmisSaat(Govde):
    birim: Metin
    gercek_saat: Saat


class GecmisProje(Govde):
    proje_kodu: Metin
    ad: Metin
    makine_turu: Kod
    kapanis_tarihi: date | None = None
    aciklama: str | None = None
    saatler: list[GecmisSaat] = []


# ---- müşteriler

class MusteriKisisi(Govde):
    kimlik: int | None = None
    ad: Metin
    unvan: str | None = None
    telefon: str | None = None
    eposta: str | None = None
    aktif: bool = True


class Musteri(Govde):
    ad: Metin
    kisa_ad: str | None = None
    adres: str | None = None
    ulke: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=2)] = 'TR'
    vergi_dairesi: str | None = None
    vergi_no: str | None = None
    strateji_notu: str | None = None
    aktif: bool = True
    kisiler: list[MusteriKisisi] = []
    yine_de: bool = False          # aynı adlı müşteri varken yine de kaydet


# ---- talep

class Gereksinim(Govde):
    metin: Metin
    belirsiz: bool = False
    soru: str | None = None
    cevap: str | None = None


class Kapsam(Govde):
    dahil: list[Metin] = []
    haric: list[Metin] = []


class Talep(Govde):
    musteri: int
    kaynak: Literal['YENI_IS', 'EK_IS', 'SERVIS']
    bagli_proje: Annotated[str, StringConstraints(strip_whitespace=True)] | None = None
    tur: Literal['KURUMSAL_SARTNAME', 'SAHA_NOTU', 'ARGE']
    makine_turu: Kod | None = None
    konu: Metin
    aciklama: str | None = None
    gelis_tarihi: date | None = None
    cevap_tarihi: date | None = None
    gereksinimler: list[Gereksinim] = []
    kapsam: Kapsam = Kapsam()


class TalepGuncelleme(Talep):
    surum: int                     # eşzamanlılık sayacı (8.3)


class Dosya(Govde):
    tur: Literal['SARTNAME', 'FOTOGRAF', 'VIDEO', 'SAHA_NOTU', 'TEDARIKCI_TEKLIFI', 'CIZIM', 'DIGER']
    ad: Metin
    konum: Metin
    aciklama: str | None = None
    parmak_izi: Annotated[str, StringConstraints(pattern=r'^[0-9a-f]{64}$')] | None = None


class Gerekce(Govde):
    gerekce: Metin


# ---- sürüm

Hafta = Annotated[int, Field(ge=0)]


class YeniSurum(Govde):
    kaynak: Literal['BOS', 'SURUM'] = 'BOS'
    kaynak_surum: int | None = None
    revize: bool = False           # müşteri revize istedi (8.12): durum değişmez, geçmişe not düşer


class KatalogaKaydet(Govde):
    kod: Metin


class MaliyetKalemi(Govde):
    unsur: Kod
    katalog_kalemi: int | None = None
    aciklama: Metin
    adet: Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=3)] = Decimal(1)
    olcu_birimi: Metin = 'adet'
    birim_fiyat: Tutar | None = None
    para_birimi: ParaKodu | None = None
    kaynak_etiketi: Literal['TEDARIKCI_TEKLIFI', 'GECMIS_PROJE', 'TAHMIN'] = 'TAHMIN'
    kaynak_notu: str | None = None
    kaynak_tarihi: date | None = None
    kaynak_dosyasi: int | None = None
    temin_hafta: Hafta | None = None
    kritik: bool = False
    katalog_kaydet: KatalogaKaydet | None = None     # "Kataloğa da kaydet"


class IscilikSatiri(Govde):
    """Saat ücreti gönderilmez: satır eklenirken ayardan gelir ve satırda donar (8.5)."""
    birim: Metin
    saat: Saat
    aciklama: str | None = None


class TakvimSatiri(Govde):
    etap_kodu: Kod | None = None
    ad: Metin
    paralel_grup: str | None = None
    baslangic_hafta: Hafta
    sure_hafta: Annotated[int, Field(ge=1)]


class Kur(Govde):
    para_birimi: ParaKodu
    kur_try: Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=6)]
    kur_tarihi: date


class SurumFormu(Govde):
    surum: int                     # eşzamanlılık sayacı
    para_birimi: ParaKodu
    fiyat_girisi: Literal['KAR', 'FIYAT'] = 'KAR'
    kar_orani: Annotated[Decimal, Field(max_digits=7, decimal_places=2)] | None = None
    fiyat: Tutar | None = None
    toplam_hafta: Annotated[int, Field(gt=0)] | None = None
    teslim_suresi_hafta: Annotated[int, Field(gt=0)] | None = None
    gecerlilik_gun: Annotated[int, Field(gt=0)] | None = None
    teknik_cozum: str | None = None
    odeme_kosullari: str | None = None
    teslim_kosullari: str | None = None
    notlar: str | None = None
    kalemler: list[MaliyetKalemi] = []
    iscilik: list[IscilikSatiri] = []
    takvim: list[TakvimSatiri] = []
    kurlar: list[Kur] = []


class SablondanTakvim(Govde):
    toplam_hafta: Annotated[int, Field(gt=0, le=520)]


# ---- onay, gönderim, sonuç

class Gecis(Govde):
    surum: int | None = None       # verilirse eşzamanlılık denetlenir


class GerekceliGecis(Gecis):
    gerekce: Metin


class Gonderim(Gecis):
    gonderim_sekli: Literal['E_POSTA', 'ELDEN', 'PORTAL', 'DIGER']
    not_: str | None = Field(default=None, alias='not')


class Sonuc(Govde):
    sonuc: Literal['KAZANILDI', 'KAYBEDILDI', 'BEKLEMEDE', 'BEKLENIYOR']
    kazanan_surum: int | None = None
    kayip_nedeni: Literal['FIYAT', 'TEKNIK_COZUM', 'TESLIM_SURESI'] | None = None
    aciklama: str | None = None
