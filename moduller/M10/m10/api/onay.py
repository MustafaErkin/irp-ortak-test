"""Onay ve gönderim (SPEC › 8.10, 8.11).

TASLAK → onaya gönder → ONAY_BEKLIYOR → onayla → ONAYLANDI → gönderildi → GONDERILDI.
Onaylanmamış sürüm hiçbir rolle "gönderildi" yapılamaz (409 KAPI); geçiş yolu yok.
"""
from fastapi import APIRouter, Depends

from .. import baglanti, hatalar, vt
from ..alan import durum
from ..depo import islem
from ..depo import musteriler as md
from ..depo import surumler as sd
from ..depo import talepler as td
from .baglam import Baglam, erisimli
from .semalar import Gecis, GerekceliGecis, Gonderim
from .surumler import bolumler, form, hesaplar, onayli_pdf, surum_bul
from .yanit import yanit

yol = APIRouter()


def _ac(b, bg, kimlik, govde, eylem):
    """Sürümü kilitler, eşzamanlılığı ve geçişi denetler → (sürüm, yeni durum)."""
    s = surum_bul(b, kimlik, kilitle=True)
    yeni = durum.surum_gecisi(s['durum'], eylem, bg.kisi, s['hazirlayan'])
    if govde.surum is not None and govde.surum != s['surum']:
        raise hatalar.degisti(form(b, bg, kimlik))
    return s, yeni


def _gecmis(b, bg, s, yeni, an, **ayrinti):
    islem.yaz(b, s['talep'], 'DURUM_DEGISTI', bg.kisi.kimlik, an,
              {'kayit': 'SURUM', 'eski': s['durum'], 'yeni': yeni, **ayrinti}, surum=s['kimlik'])
    from ..bildirim import sirala
    sirala(b,s,yeni,an)


def _dogrula(b, s):
    _, _, d = hesaplar(b, s, bolumler(b, s['kimlik']))
    if d['hatalar']:
        raise hatalar.dogrulama(d['hatalar'], uyarilar=d['uyarilar'])
    return d


def donmus_ozet(b, s):
    """Onay anında dondurulan özet. Talep düzeyindeki bilgiler sonradan değişse de gönderilen sürüm bu haliyle kalır."""
    bol = bolumler(b, s['kimlik'])
    h, t, _ = hesaplar(b, s, bol)
    talep = td.bul(b, s['talep'])
    m = md.bul(b, talep['musteri'])
    return {
        'toplamlar': {'maliyet': str(h['maliyet']), 'kalemler': {k: str(v) for k, v in h['kirilim'].items()},
                      'marj_yuzde': None if h['marj_yuzde'] is None else str(h['marj_yuzde'])},
        'takvim_teslim_hafta': t['takvim_teslim_hafta'], 'en_erken_teslim_hafta': t['en_erken_teslim_hafta'],
        # unsurun bütçe kalemi sonradan değişebilir; gönderilen sürüm onaydaki kalemle kalır
        'kalemler': [{'sira': k['sira'], 'unsur': k['unsur'], 'unsur_adi': k['unsur_adi'],
                      'butce_kalemi': k['butce_kalemi'], 'katalog_kodu': k['katalog_kodu']} for k in bol['kalemler']],
        'musteri': {'kimlik': m['kimlik'], 'ad': m['ad'], 'adres': m['adres'], 'ulke': m['ulke'],
                    'vergi_dairesi': m['vergi_dairesi'], 'vergi_no': m['vergi_no'],
                    'kisiler': [{a: k[a] for a in ('ad', 'unvan', 'telefon', 'eposta')}
                                for k in md.kisiler(b, m['kimlik'], yalniz_aktif=True)]},
        'gereksinimler': [{'sira': g['sira'], 'metin': g['metin'], 'belirsiz': g['belirsiz'], 'cevap': g['cevap']}
                          for g in td.gereksinimler(b, s['talep'])],
        'kapsam': td.kapsam(b, s['talep']),
        'dosyalar': [{a: d[a] for a in ('tur', 'ad', 'konum', 'parmak_izi')} for d in td.dosyalar(b, s['talep'])],
    }


@yol.post('/surumler/{kimlik}/onaya-gonder')
def onaya_gonder(kimlik: int, govde: Gecis = Gecis(), bg: Baglam = Depends(erisimli)):
    """Doğrulama geçerse ONAY_BEKLIYOR. Hatalar 422 {alan, sira, mesaj}; uyarılar durdurmaz."""
    an = baglanti.simdi()
    with vt.islem() as b:
        s, yeni = _ac(b, bg, kimlik, govde, 'ONAYA_GONDER')
        d = _dogrula(b, s)
        sd.guncelle(b, kimlik, {'durum': yeni, 'onaya_gonderen': bg.kisi.kimlik, 'onaya_gonderim_ani': an})
        sd.onay_kaydi(b, kimlik, 'ONAYA_GONDERILDI', bg.kisi.kimlik, an)
        _gecmis(b, bg, s, yeni, an, uyarilar=[u['mesaj'] for u in d['uyarilar']])
        return yanit(form(b, bg, kimlik), baglam=bg)


@yol.post('/surumler/{kimlik}/onayla')
def onayla(kimlik: int, govde: Gecis = Gecis(), bg: Baglam = Depends(erisimli)):
    """Onaylı PDF ve donmuş özet yazılır. Hazırlayan ve onaylayan aynı kişi olabilir (S-8b); kayıtta görünür."""
    an = baglanti.simdi()
    with vt.islem() as b:
        s, yeni = _ac(b, bg, kimlik, govde, 'ONAYLA')
        _dogrula(b, s)
        pdf, iz = onayli_pdf(b, s, an)
        sd.guncelle(b, kimlik, {'durum': yeni, 'onaylayan': bg.kisi.kimlik, 'onay_ani': an, 'pdf': pdf,
                                'pdf_parmak_izi': iz, 'donmus_ozet': donmus_ozet(b, s)})
        sd.onay_kaydi(b, kimlik, 'ONAYLANDI', bg.kisi.kimlik, an)
        _gecmis(b, bg, s, yeni, an, hazirlayan_onaylayan_ayni=s['hazirlayan'] == bg.kisi.kimlik)
        return yanit(form(b, bg, kimlik), baglam=bg)


@yol.post('/surumler/{kimlik}/geri-gonder')
def geri_gonder(kimlik: int, govde: GerekceliGecis, bg: Baglam = Depends(erisimli)):
    """Gerekçeyle geri gönder: aynı sürüm düzeltilir. Gerekçe bilgi havuzuna girer (8.15)."""
    an = baglanti.simdi()
    with vt.islem() as b:
        s, yeni = _ac(b, bg, kimlik, govde, 'GERI_GONDER')
        sd.guncelle(b, kimlik, {'durum': yeni})
        sd.onay_kaydi(b, kimlik, 'DUZELTME_ISTENDI', bg.kisi.kimlik, an, govde.gerekce)
        _gecmis(b, bg, s, yeni, an, gerekce=govde.gerekce)
        return yanit(form(b, bg, kimlik), baglam=bg)


@yol.post('/surumler/{kimlik}/duzenlemeye-ac')
def duzenlemeye_ac(kimlik: int, govde: GerekceliGecis, bg: Baglam = Depends(erisimli)):
    """ONAYLANDI → TASLAK: PDF, donmuş özet ve onaylayan silinir."""
    an = baglanti.simdi()
    with vt.islem() as b:
        s, yeni = _ac(b, bg, kimlik, govde, 'DUZENLEMEYE_AC')
        sd.guncelle(b, kimlik, {'durum': yeni, 'onaylayan': None, 'onay_ani': None, 'pdf': None,
                                'pdf_parmak_izi': None, 'donmus_ozet': None})
        sd.onay_kaydi(b, kimlik, 'DUZENLEMEYE_ACILDI', bg.kisi.kimlik, an, govde.gerekce)
        _gecmis(b, bg, s, yeni, an, gerekce=govde.gerekce)
        return yanit(form(b, bg, kimlik), baglam=bg)


@yol.post('/surumler/{kimlik}/gonderildi')
def gonderildi(kimlik: int, govde: Gonderim, bg: Baglam = Depends(erisimli)):
    """Kapı: yalnızca ONAYLANDI sürüm. Modül e-posta göndermez; kullanıcı onaylı PDF'i indirip kendisi gönderir.
    Talep ACIK ya da BEKLEMEDE ise TEKLIF_VERILDI olur. Gönderilen sürüm donar."""
    an = baglanti.simdi()
    with vt.islem() as b:
        s, yeni = _ac(b, bg, kimlik, govde, 'GONDERILDI')
        t = td.bul(b, s['talep'], kilitle=True)
        talep_yeni = durum.talep_gecisi(t['durum'], 'GONDERIM', bg.kisi)
        sd.guncelle(b, kimlik, {'durum': yeni, 'gonderen': bg.kisi.kimlik, 'gonderim_ani': an,
                                'gonderim_sekli': govde.gonderim_sekli, 'gonderim_notu': govde.not_})
        _gecmis(b, bg, s, yeni, an, gonderim_sekli=govde.gonderim_sekli)
        if talep_yeni != t['durum']:
            td.guncelle(b, t['kimlik'], {'durum': talep_yeni})
            islem.yaz(b, t['kimlik'], 'DURUM_DEGISTI', bg.kisi.kimlik, an,
                      {'kayit': 'TALEP', 'eski': t['durum'], 'yeni': talep_yeni}, surum=kimlik)
        return yanit(form(b, bg, kimlik), baglam=bg)
