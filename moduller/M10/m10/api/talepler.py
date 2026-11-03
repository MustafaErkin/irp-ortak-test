"""Talep (SPEC › 8.2): açma, numara, dosyalar, gereksinimler, kapsam, bağlı proje, "teklif vermiyoruz"."""
from fastapi import APIRouter, Depends

from .. import baglanti, hatalar, vt
from ..alan import durum
from ..depo import ayarlar as ayar_deposu
from ..depo import islem
from ..depo import katalog as kd
from ..depo import musteriler as md
from ..depo import surumler as sd
from ..depo import talepler as td
from .baglam import Baglam, duzenleyici, erisimli
from .projeler import proje_oku, proje_ozeti
from .semalar import Dosya, Gerekce, Sonuc, Talep, TalepGuncelleme
from .yanit import yanit

yol = APIRouter()


def talep_bul(b, kimlik, kilitle=False):
    t = td.bul(b, kimlik, kilitle)
    if t is None:
        raise hatalar.bulunamadi('Talep bulunamadı.')
    return t


def talep_karti(b, bg: Baglam, kimlik):
    t = talep_bul(b, kimlik)
    gereksinimler = td.gereksinimler(b, kimlik)
    musteri = md.bul(b, t['musteri'])
    return dict(
        t,
        musteri={k: musteri[k] for k in ('kimlik', 'ad', 'kisa_ad', 'adres', 'ulke', 'strateji_notu', 'aktif')},
        bagli_proje=proje_ozeti(bg, t['bagli_proje']),
        gereksinimler=gereksinimler,
        acik_gereksinim=sum(1 for g in gereksinimler if g['belirsiz'] and not g['cevap']),
        kapsam=td.kapsam(b, kimlik),
        dosyalar=td.dosyalar(b, kimlik),
        surumler=td.surum_ozetleri(b, kimlik),
        olusturan_adi=bg.kisi_adi(t['olusturan']))


def _denetle(b, bg, govde, eski=None):
    """Müşteri, makine türü ve bağlı proje. Bağlı proje kullanıcının gözüyle okunur; göremiyorsa 403."""
    m = md.bul(b, govde.musteri)
    if m is None or (not m['aktif'] and (eski is None or eski['musteri'] != govde.musteri)):
        raise hatalar.dogrulama([hatalar.hata('musteri', 'Aktif bir müşteri seçilmeli.')])
    if govde.makine_turu and not kd.makine_turu(b, govde.makine_turu):
        raise hatalar.dogrulama([hatalar.hata('makine_turu', f'{govde.makine_turu} tanımlı değil.')])
    if govde.kaynak == 'YENI_IS':
        return None
    if not govde.bagli_proje:
        raise hatalar.dogrulama([hatalar.hata('bagli_proje', 'Ek iş ve serviste bağlı proje zorunludur.')])
    if eski is not None and eski['bagli_proje'] == govde.bagli_proje:
        return govde.bagli_proje
    return proje_oku(bg, govde.bagli_proje)['kod']


def _alanlar(govde, bagli_proje, bugun):
    d = govde.model_dump()
    d['bagli_proje'] = bagli_proje
    d['gelis_tarihi'] = govde.gelis_tarihi or bugun
    return {a: d[a] for a in td.ALANLAR}


@yol.post('/talepler', status_code=201)
def ac(govde: Talep, bg: Baglam = Depends(duzenleyici)):
    an = baglanti.simdi()
    with vt.islem() as b:
        bagli_proje = _denetle(b, bg, govde)
        no = td.talep_no(b, ayar_deposu.oku(b, 'talep_no_deseni', 'T-{YYYY}-{SIRA4}'), an.year)
        kimlik = td.ekle(b, _alanlar(govde, bagli_proje, an.date()), no, bg.kisi.kimlik, an)
        td.gereksinimleri_yaz(b, kimlik, [g.model_dump() for g in govde.gereksinimler], an)
        td.kapsam_yaz(b, kimlik, govde.kapsam.model_dump())
        td.arama_yenile(b, kimlik)
        islem.yaz(b, kimlik, 'TALEP_ACILDI', bg.kisi.kimlik, an, {'talep_no': no})
        return yanit(talep_karti(b, bg, kimlik), 201, bg)


@yol.get('/talepler/{kimlik}')
def kart(kimlik: int, bg: Baglam = Depends(erisimli)):
    with vt.islem() as b:
        return yanit(talep_karti(b, bg, kimlik), baglam=bg)


@yol.put('/talepler/{kimlik}')
def guncelle(kimlik: int, govde: TalepGuncelleme, bg: Baglam = Depends(duzenleyici)):
    """Talep bütün olarak kaydedilir. `surum` uyuşmazsa 409 DEGISTI ve güncel hal (8.3)."""
    durum.talep_duzenlenebilir(bg.kisi)
    an = baglanti.simdi()
    with vt.islem() as b:
        eski = talep_bul(b, kimlik, kilitle=True)
        if eski['surum'] != govde.surum:
            raise hatalar.degisti(talep_karti(b, bg, kimlik))
        bagli_proje = _denetle(b, bg, govde, eski)
        yeni = _alanlar(govde, bagli_proje, eski['gelis_tarihi'])
        eski_liste = {'gereksinimler': td.gereksinimler(b, kimlik), 'kapsam': td.kapsam(b, kimlik)}
        degisiklikler = islem.farklar(eski, yeni, td.ALANLAR)
        yeni_gereksinimler = [g.model_dump() for g in govde.gereksinimler]
        if [(g['metin'], g['belirsiz'], g['soru'], g['cevap']) for g in eski_liste['gereksinimler']] != \
                [(g['metin'], g['belirsiz'], g['soru'], (g['cevap'] or '').strip() or None) for g in yeni_gereksinimler]:
            degisiklikler.append({'alan': 'gereksinimler', 'eski': len(eski_liste['gereksinimler']),
                                  'yeni': len(yeni_gereksinimler)})
        if eski_liste['kapsam'] != govde.kapsam.model_dump():
            degisiklikler.append({'alan': 'kapsam', 'eski': eski_liste['kapsam'], 'yeni': govde.kapsam.model_dump()})
        td.guncelle(b, kimlik, yeni)
        td.gereksinimleri_yaz(b, kimlik, yeni_gereksinimler, an)
        td.kapsam_yaz(b, kimlik, govde.kapsam.model_dump())
        td.arama_yenile(b, kimlik)
        if degisiklikler:
            islem.yaz(b, kimlik, 'TALEP_GUNCELLENDI', bg.kisi.kimlik, an, {'degisiklikler': degisiklikler})
        return yanit(talep_karti(b, bg, kimlik), baglam=bg)


@yol.post('/talepler/{kimlik}/dosyalar', status_code=201)
def dosya_ekle(kimlik: int, govde: Dosya, bg: Baglam = Depends(duzenleyici)):
    """Dosyanın kaydı: konum zorunlu, parmak izi isteğe bağlı. Kayıt silinmez (istek M10-05)."""
    durum.talep_duzenlenebilir(bg.kisi)
    an = baglanti.simdi()
    with vt.islem() as b:
        talep_bul(b, kimlik)
        d = govde.model_dump()
        dosya = td.dosya_ekle(b, kimlik, d, bg.kisi.kimlik, an)
        islem.yaz(b, kimlik, 'DOSYA_EKLENDI', bg.kisi.kimlik, an, {'dosya': dosya, 'tur': d['tur'], 'ad': d['ad']})
        return yanit({'dosyalar': td.dosyalar(b, kimlik)}, 201)


def durum_degistir(b, bg, t, yeni, an, ayrinti=None, **alanlar):
    td.guncelle(b, t['kimlik'], {'durum': yeni, **alanlar})
    islem.yaz(b, t['kimlik'], 'DURUM_DEGISTI', bg.kisi.kimlik, an, {'eski': t['durum'], 'yeni': yeni, **(ayrinti or {})})


@yol.post('/talepler/{kimlik}/kapat')
def kapat(kimlik: int, govde: Gerekce, bg: Baglam = Depends(duzenleyici)):
    """"Teklif vermiyoruz": gerekçe zorunlu; yalnızca ACIK ya da BEKLEMEDE talepte."""
    an = baglanti.simdi()
    with vt.islem() as b:
        t = talep_bul(b, kimlik, kilitle=True)
        yeni = durum.talep_gecisi(t['durum'], 'KAPAT', bg.kisi)
        durum_degistir(b, bg, t, yeni, an, {'gerekce': govde.gerekce}, kapatma_gerekcesi=govde.gerekce,
                       sonuc_ani=an, sonucu_yazan=bg.kisi.kimlik)
        return yanit(talep_karti(b, bg, kimlik), baglam=bg)


@yol.post('/talepler/{kimlik}/sonuc')
def sonuc(kimlik: int, govde: Sonuc, bg: Baglam = Depends(duzenleyici)):
    """Müşterinin cevabı talebe yazılır (8.12). KAZANILDI'da kazanan, gönderilmiş bir sürümdür; KAYBEDILDI'de neden
    zorunludur. KAZANILDI geri alınmaz: M1.1A siparişe dönüştürmüş olabilir."""
    an = baglanti.simdi()
    with vt.islem() as b:
        t = talep_bul(b, kimlik, kilitle=True)
        yeni = durum.talep_gecisi(t['durum'], govde.sonuc, bg.kisi)
        alanlar = {'sonuc_ani': an, 'sonucu_yazan': bg.kisi.kimlik}
        ayrinti = {'sonuc': govde.sonuc}
        if govde.sonuc == 'KAZANILDI':
            ks = sd.bul(b, govde.kazanan_surum) if govde.kazanan_surum else None
            if ks is None or ks['talep'] != kimlik or ks['durum'] != durum.GONDERILDI:
                raise hatalar.dogrulama([hatalar.hata('kazanan_surum', 'Kazanan, bu talebin gönderilmiş bir sürümü olmalı.')])
            alanlar['kazanan_surum'] = ks['kimlik']
            ayrinti.update(kazanan_surum=ks['kimlik'], etiket=f'{t["talep_no"]}/V{ks["no"]}')
        elif govde.sonuc == 'KAYBEDILDI':
            if not govde.kayip_nedeni:
                raise hatalar.dogrulama([hatalar.hata('kayip_nedeni', 'Kayıp nedeni seçilmeli.')])
            alanlar.update(kayip_nedeni=govde.kayip_nedeni, kayip_aciklamasi=govde.aciklama)
            ayrinti.update(kayip_nedeni=govde.kayip_nedeni, aciklama=govde.aciklama)
        durum_degistir(b, bg, t, yeni, an, ayrinti, **alanlar)
        return yanit(talep_karti(b, bg, kimlik), baglam=bg)


@yol.post('/talepler/{kimlik}/geri-ac')
def geri_ac(kimlik: int, govde: Gerekce, bg: Baglam = Depends(duzenleyici)):
    """KAYBEDILDI ya da KAPATILDI talep: yalnızca YETKILI, gerekçeyle. Gönderilmiş sürüm varsa TEKLIF_VERILDI."""
    an = baglanti.simdi()
    with vt.islem() as b:
        t = talep_bul(b, kimlik, kilitle=True)
        gonderilmis = any(x['durum'] == durum.GONDERILDI for x in td.surum_ozetleri(b, kimlik))
        yeni = durum.talep_gecisi(t['durum'], 'GERI_AC', bg.kisi, gonderilmis)
        durum_degistir(b, bg, t, yeni, an, {'gerekce': govde.gerekce, 'onceki_kayip_nedeni': t['kayip_nedeni'],
                                            'onceki_kapatma_gerekcesi': t['kapatma_gerekcesi']},
                       kayip_nedeni=None, kayip_aciklamasi=None, kapatma_gerekcesi=None, sonuc_ani=None,
                       sonucu_yazan=None)
        return yanit(talep_karti(b, bg, kimlik), baglam=bg)


@yol.get('/talepler/{kimlik}/gecmis')
def gecmis(kimlik: int, onayci: bool = False, bg: Baglam = Depends(erisimli)):
    """İşlem geçmişi; `onayci=true` ile yalnızca onaycı düzeltmeleri ("bilgi havuzu", 8.15)."""
    with vt.islem() as b:
        talep_bul(b, kimlik)
        kayitlar = islem.liste(b, kimlik, yalniz_onayci=onayci)
        for k in kayitlar:
            k['kim_adi'] = bg.kisi_adi(k['kim'])
        return yanit({'kayitlar': kayitlar}, baglam=bg)
