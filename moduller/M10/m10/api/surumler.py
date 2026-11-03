"""Teklif sürümü (SPEC › 8.3–8.8): yeni sürüm, kopyalama, sürüm formu, kaydetme, öneriler, şablondan takvim.

Sürüm formu tek bütün olarak kaydedilir: genel alanlar + kalemler + işçilik + takvim + kurlar. İstek sürümün
`surum` sayacını taşır; uyuşmazsa 409 DEGISTI ve güncel hal.
"""
from decimal import Decimal

import hashlib

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from .. import baglanti, hatalar, vt
from ..alan import dogrulama, durum, hesap, kopyalama, oneri, takvim
from ..depo import ayarlar as ayar_deposu
from ..depo import gecmis as gecmis_deposu
from ..depo import islem
from ..depo import katalog as kd
from ..depo import musteriler as md
from ..depo import surumler as sd
from ..depo import talepler as td
from ..hatalar import ModulHatasi, hata
from ..pdf.teklif import dosya_adi, teklif_pdf
from .baglam import Baglam, duzenleyici, erisimli
from .semalar import SablondanTakvim, SurumFormu, YeniSurum
from .talepler import talep_bul
from .yanit import yanit

yol = APIRouter()


def surum_bul(b, kimlik, kilitle=False):
    s = sd.bul(b, kimlik, kilitle)
    if s is None:
        raise hatalar.bulunamadi('Teklif sürümü bulunamadı.')
    return s


def etiket(s):
    return f'{s["talep_no"]}/V{s["no"]}'


def bolumler(b, kimlik):
    return {'kalemler': sd.kalemler(b, kimlik), 'iscilik': sd.iscilik(b, kimlik), 'takvim': sd.takvim(b, kimlik),
            'kurlar': sd.kurlar(b, kimlik)}


def hesaplar(b, s, bol):
    """Sürümün bütün hesabı: maliyet, kırılım, kâr, marj, takvim, en erken teslim ve doğrulama."""
    kurlar = {k['para_birimi']: k['kur_try'] for k in bol['kurlar']}
    h = hesap.surum_hesabi(s['para_birimi'], kurlar, bol['kalemler'], bol['iscilik'], s['fiyat_girisi'],
                           s['kar_orani'], s['fiyat'])
    t = takvim.takvim_hesabi(bol['takvim'], bol['kalemler'])
    k = td.kapsam(b, s['talep'])
    talep = {'kapsam': k['dahil'] + k['haric'], 'gereksinimler': td.gereksinimler(b, s['talep'])}
    hatalar_, uyarilar = dogrulama.onaya_gonderim(
        {'teslim_suresi_hafta': s['teslim_suresi_hafta'], 'gecerlilik_gun': s['gecerlilik_gun'],
         'takvim': bol['takvim']}, h, t, talep)
    return h, t, {'hatalar': hatalar_, 'uyarilar': uyarilar}


def _izinler(s, kisi):
    def dene(f, *a):
        try:
            return f(*a) or True
        except ModulHatasi:
            return False
    izin = {e.lower(): bool(dene(durum.surum_gecisi, s['durum'], e, kisi, s['hazirlayan']))
            for e in durum.SURUM_GECISLERI}
    duzenleme = dene(durum.surum_duzenlenebilir, s['durum'], kisi)
    izin['duzenleme'] = duzenleme if duzenleme is not False else None
    izin['yeni_surum'] = kisi.duzenleyici and s['durum'] == durum.GONDERILDI and \
        s['talep_durumu'] in durum.SURUM_ACILABILIR
    return izin


def _takvim_ipuclari(b, s):
    """Satırın yanında, şablonun birim eşlemesine göre başlangıç tablosunun tipik süresi ("Tablo: 5 hf")."""
    makine = b.execute('SELECT makine_turu FROM talepler WHERE kimlik = %s', (s['talep'],)).fetchone()['makine_turu']
    sure = {r['birim']: r['tipik_sure_hafta'] for r in kd.baslangic_tablosu(b, makine)} if makine else {}
    return {r['kod']: sure.get(r['birim']) for r in kd.takvim_sablonu(b)}


def form(b, bg: Baglam, kimlik):
    s = surum_bul(b, kimlik)
    bol = bolumler(b, kimlik)
    h, t, d = hesaplar(b, s, bol)
    talep = td.bul(b, s['talep'])
    makine = kd.makine_turu(b, talep['makine_turu']) if talep['makine_turu'] else None
    ipucu = _takvim_ipuclari(b, s)
    for k in h['kalemler']:
        k['ortalama_temin_hafta'] = None      # M3 bağlanınca (istek M10-03)
    return dict(
        {a: s[a] for a in ('kimlik', 'no', 'durum', 'kaynak_surum', 'hazirlayan', 'olusturma_ani', 'onaya_gonderen',
                           'onaya_gonderim_ani', 'onaylayan', 'onay_ani', 'gonderen', 'gonderim_ani', 'gonderim_sekli',
                           'gonderim_notu', 'pdf_parmak_izi', 'surum', *sd.GENEL)},
        etiket=etiket(s),
        talep={'kimlik': talep['kimlik'], 'talep_no': talep['talep_no'], 'durum': talep['durum'], 'konu': talep['konu'],
               'musteri': talep['musteri'], 'musteri_adi': talep['musteri_adi'], 'makine_turu': talep['makine_turu'],
               'makine_turu_adi': talep['makine_turu_adi'], 'kazanan_surum': talep['kazanan_surum']},
        hazirlayan_adi=bg.kisi_adi(s['hazirlayan']), onaylayan_adi=bg.kisi_adi(s['onaylayan']),
        hazirlayan_onaylayan_ayni=bool(s['onaylayan']) and s['onaylayan'] == s['hazirlayan'],
        kalemler=h['kalemler'], iscilik=h['iscilik'],
        takvim=[dict(r, ipucu_sure_hafta=ipucu.get(r['etap_kodu'])) for r in bol['takvim']],
        kurlar=bol['kurlar'],
        hesap={**{a: h[a] for a in ('maliyet', 'kirilim', 'kar_orani', 'fiyat', 'marj_yuzde',
                                    'fiyatin_yuzdesi_olsaydi', 'eksik_kurlar')}, **t},
        dogrulama=d,
        varsayilan_toplam_hafta=makine['tipik_toplam_hafta'] if makine else None,
        izinler=_izinler(s, bg.kisi),
        onay_kayitlari=sd.onay_kayitlari(b, kimlik))


# ---------------------------------------------------------------- yeni sürüm

@yol.post('/talepler/{talep}/surumler', status_code=201)
def yeni(talep: int, govde: YeniSurum, bg: Baglam = Depends(duzenleyici)):
    an = baglanti.simdi()
    with vt.islem() as b:
        t = talep_bul(b, talep, kilitle=True)
        durum.yeni_surum_acilabilir(t['durum'], sd.acik_surum(b, talep) is not None, bg.kisi)
        ayarlar = ayar_deposu.hepsi(b)
        ayrinti = {'kaynak': govde.kaynak}
        if govde.kaynak == 'BOS':
            icerik = kopyalama.bos(ayarlar)
            kaynak_surum = None
        else:
            if not govde.kaynak_surum:
                raise hatalar.dogrulama([hata('kaynak_surum', 'Kopyalanacak sürüm seçilmeli.')])
            ks = sd.bul(b, govde.kaynak_surum)
            if ks is None:
                raise hatalar.dogrulama([hata('kaynak_surum', 'Kopyalanacak sürüm bulunamadı.')])
            ayni = ks['talep'] == talep
            ucretler = {u['birim']: u for u in kd.saat_ucretleri(b)}
            icerik = kopyalama.kopya({'genel': ks, **bolumler(b, ks['kimlik'])}, ayarlar, ucretler, ayni)
            kaynak_surum = ks['kimlik']
            ayrinti.update(kaynak_surum=kaynak_surum, kaynak_etiket=etiket(ks))
            if not ayni:
                # Bu talebin gereksinim ve kapsamı boşsa eski talebinkiler de gelir; müşteri gelmez.
                if not td.gereksinimler(b, talep):
                    td.gereksinimleri_yaz(b, talep, td.gereksinimler(b, ks['talep']), an)
                    ayrinti['gereksinimler_kopyalandi'] = True
                k = td.kapsam(b, talep)
                if not k['dahil'] and not k['haric']:
                    td.kapsam_yaz(b, talep, td.kapsam(b, ks['talep']))
                    ayrinti['kapsam_kopyalandi'] = True
        no = sd.son_no(b, talep) + 1
        kimlik = sd.ekle(b, talep, no, icerik['genel'], kaynak_surum, bg.kisi.kimlik, an)
        sd.cocuklari_yaz(b, kimlik, icerik['kalemler'], icerik['iscilik'], icerik['takvim'], icerik['kurlar'])
        islem.yaz(b, talep, 'SURUM_ACILDI', bg.kisi.kimlik, an, dict(ayrinti, no=no), surum=kimlik)
        if govde.revize:
            islem.yaz(b, talep, 'NOT', bg.kisi.kimlik, an, {'not': 'Müşteri revize istedi'}, surum=kimlik)
        td.arama_yenile(b, talep)
        return yanit(form(b, bg, kimlik), 201, bg)


# ---------------------------------------------------------------- sürüm formu

@yol.get('/surumler/{kimlik}')
def getir(kimlik: int, bg: Baglam = Depends(erisimli)):
    with vt.islem() as b:
        return yanit(form(b, bg, kimlik), baglam=bg)


def _satir_farklari(ad, eski, yeni, alanlar):
    """Bölümün satır satır farkları: [{alan: 'kalemler[2].birim_fiyat', eski, yeni}]."""
    fark = []
    for i in range(max(len(eski), len(yeni))):
        e = eski[i] if i < len(eski) else None
        y = yeni[i] if i < len(yeni) else None
        if e is None or y is None:
            ozet = lambda r: r and {a: r.get(a) for a in alanlar}  # noqa: E731
            fark.append({'alan': f'{ad}[{i + 1}]', 'eski': islem._jsonla(ozet(e)), 'yeni': islem._jsonla(ozet(y))})
            continue
        fark += [dict(f, alan=f'{ad}[{i + 1}].{f["alan"]}') for f in islem.farklar(e, y, alanlar)]
    return fark


def _denetle(b, bg, s, govde):
    """Formun modülün tablolarına karşı doğrulaması; birim çekirdeğin listesinden."""
    bg.birim_denetle([i.birim for i in govde.iscilik], 'iscilik.birim')
    yanlis = []
    paralar = {p['kod']: p for p in kd.para_birimleri(b)}
    unsurlar = {u['kod'] for u in kd.unsurlar(b)}
    dosyalar = {d['kimlik'] for d in td.dosyalar(b, s['talep'])}
    sablon = {r['kod'] for r in kd.takvim_sablonu(b)}
    if govde.para_birimi not in paralar:
        yanlis.append(hata('para_birimi', f'{govde.para_birimi} tanımlı değil.'))
    for i, k in enumerate(govde.kalemler, 1):
        if k.unsur not in unsurlar:
            yanlis.append(hata('kalemler.unsur', f'{k.unsur} unsuru yok.', i))
        if (k.birim_fiyat is None) != (k.para_birimi is None):
            yanlis.append(hata('kalemler.birim_fiyat', 'Birim fiyat ve para birimi birlikte girilir.', i))
        if k.para_birimi and k.para_birimi not in paralar:
            yanlis.append(hata('kalemler.para_birimi', f'{k.para_birimi} tanımlı değil.', i))
        if k.kaynak_dosyasi and k.kaynak_dosyasi not in dosyalar:
            yanlis.append(hata('kalemler.kaynak_dosyasi', 'Kaynak dosyası bu talebin dosya kaydı olmalı.', i))
        if k.katalog_kalemi and not kd.katalog_kalemi(b, k.katalog_kalemi):
            yanlis.append(hata('kalemler.katalog_kalemi', 'Katalog kalemi yok.', i))
        if k.katalog_kaydet and kd.katalog_kodu_var(b, k.katalog_kaydet.kod):
            yanlis.append(hata('kalemler.katalog_kaydet', f'{k.katalog_kaydet.kod} kodu katalogda var.', i))
    if len({i.birim for i in govde.iscilik}) != len(govde.iscilik):
        yanlis.append(hata('iscilik.birim', 'Her birim bir kez girilir.'))
    etaplar = [t.etap_kodu for t in govde.takvim if t.etap_kodu]
    for i, t in enumerate(govde.takvim, 1):
        if t.etap_kodu and t.etap_kodu not in sablon:
            yanlis.append(hata('takvim.etap_kodu', f'{t.etap_kodu} şablonda yok.', i))
    if len(set(etaplar)) != len(etaplar):
        yanlis.append(hata('takvim.etap_kodu', 'Her etap takvimde bir kez yer alır.'))
    kurlar = [k.para_birimi for k in govde.kurlar]
    if 'TRY' in kurlar or len(set(kurlar)) != len(kurlar):
        yanlis.append(hata('kurlar', "TL'nin kuru 1'dir; her para biriminin kuru bir kez girilir."))
    yanlis += [hata('kurlar', f'{p} tanımlı değil.') for p in kurlar if p not in paralar]
    if yanlis:
        raise hatalar.dogrulama(yanlis)


@yol.put('/surumler/{kimlik}')
def kaydet(kimlik: int, govde: SurumFormu, bg: Baglam = Depends(erisimli)):
    an = baglanti.simdi()
    with vt.islem() as b:
        s = surum_bul(b, kimlik, kilitle=True)
        kip = durum.surum_duzenlenebilir(s['durum'], bg.kisi)
        if s['surum'] != govde.surum:
            raise hatalar.degisti(form(b, bg, kimlik))
        _denetle(b, bg, s, govde)
        eski = bolumler(b, kimlik)

        # İşçilik: ücret satır eklenirken ayardan gelir ve satırda donar.
        donmus = {i['birim']: i for i in eski['iscilik']}
        ucretler = {u['birim']: u for u in kd.saat_ucretleri(b)}
        iscilik = []
        for i in govde.iscilik:
            satir = kopyalama.ucretle(i.birim, i.saat, i.aciklama, ucretler)
            if i.birim in donmus:
                satir.update(saat_ucreti=donmus[i.birim]['saat_ucreti'], para_birimi=donmus[i.birim]['para_birimi'])
            iscilik.append(satir)

        # Kalemler; "Kataloğa da kaydet" elle girilen kalemi yeni katalog kalemi yapar.
        kalemler = []
        for k in govde.kalemler:
            d = k.model_dump(exclude={'katalog_kaydet'})
            if k.katalog_kaydet:
                d['katalog_kalemi'] = kd.katalog_ekle(b, {
                    'kod': k.katalog_kaydet.kod, 'ad': k.aciklama, 'unsur': k.unsur, 'olcu_birimi': k.olcu_birimi,
                    'birim_fiyat': k.birim_fiyat, 'para_birimi': k.para_birimi, 'fiyat_tarihi': k.kaynak_tarihi or an.date(),
                    'fiyat_kaynagi': k.kaynak_notu, 'tipik_temin_hafta': k.temin_hafta, 'kritik': k.kritik, 'aktif': True})
            kalemler.append(d)
        takvim_ = [t.model_dump() for t in govde.takvim]
        kurlar = [k.model_dump() for k in govde.kurlar]

        # Fiyat ve kâr: girilen sabit kalır, öbürü hesaplanır; teslim süresi varsayılan olarak en erken teslim.
        butce = {u['kod']: u['butce_kalemi'] for u in kd.unsurlar(b)}
        h = hesap.surum_hesabi(govde.para_birimi, {k['para_birimi']: k['kur_try'] for k in kurlar},
                               [dict(k, butce_kalemi=butce[k['unsur']]) for k in kalemler], iscilik,
                               govde.fiyat_girisi, govde.kar_orani, govde.fiyat)
        t = takvim.takvim_hesabi(takvim_, kalemler)
        genel = {a: getattr(govde, a) for a in sd.GENEL}
        genel.update(kar_orani=h['kar_orani'], fiyat=h['fiyat'])
        if genel['teslim_suresi_hafta'] is None and t['en_erken_teslim_hafta'] > 0:
            genel['teslim_suresi_hafta'] = t['en_erken_teslim_hafta']

        degisiklikler = islem.farklar(s, genel, sd.GENEL)
        degisiklikler += _satir_farklari('kalemler', eski['kalemler'], kalemler, sd.KALEM)
        degisiklikler += _satir_farklari('iscilik', eski['iscilik'], iscilik, ('birim', 'saat', 'aciklama'))
        degisiklikler += _satir_farklari('takvim', eski['takvim'], takvim_, sd.TAKVIM)
        degisiklikler += _satir_farklari('kurlar', eski['kurlar'], kurlar, ('para_birimi', 'kur_try', 'kur_tarihi'))

        sd.guncelle(b, kimlik, genel)
        sd.cocuklari_yaz(b, kimlik, kalemler, iscilik, takvim_, kurlar)
        onayci = kip == 'ONAYCI'
        if onayci and degisiklikler and not _onayci_duzeltti(b, kimlik):
            sd.onay_kaydi(b, kimlik, 'ONAYCI_DUZELTTI', bg.kisi.kimlik, an)
        if degisiklikler:
            islem.yaz(b, s['talep'], 'SURUM_KAYDEDILDI', bg.kisi.kimlik, an, {'degisiklikler': degisiklikler},
                      surum=kimlik, onayci_duzeltmesi=onayci)
        son = ayar_deposu.oku(b, 'son_kurlar', {}) or {}
        son.update({k['para_birimi']: {'kur_try': str(k['kur_try'].quantize(Decimal('0.000001'))),
                                       'kur_tarihi': k['kur_tarihi'].isoformat()} for k in kurlar})
        ayar_deposu.yaz(b, 'son_kurlar', son, bg.kisi.kimlik, an)
        td.arama_yenile(b, s['talep'])
        return yanit(form(b, bg, kimlik), baglam=bg)


def _onayci_duzeltti(b, kimlik):
    """Bu onay turunda (son "onaya gönderildi"den sonra) onaycı düzeltmesi yazıldı mı?"""
    son = None
    for k in sd.onay_kayitlari(b, kimlik):
        son = k['karar'] if k['karar'] in ('ONAYA_GONDERILDI', 'ONAYCI_DUZELTTI') else son
    return son == 'ONAYCI_DUZELTTI'


# ---------------------------------------------------------------- öneriler ve şablondan takvim

@yol.get('/surumler/{kimlik}/oneriler')
def oneriler(kimlik: int, bg: Baglam = Depends(erisimli)):
    """İşçilik önerisi: başlangıç tablosu ve geçmiş ortalaması; "Önerileri doldur"un sonucu (dolu saate dokunmaz)."""
    with vt.islem() as b:
        s = surum_bul(b, kimlik)
        makine = td.bul(b, s['talep'])['makine_turu']
        tablo = {(r['makine_turu'], r['birim']): r['tipik_saat'] for r in kd.baslangic_tablosu(b)}
        gecmis = gecmis_deposu.oneri_gecmisi(b)
        mevcut = sd.iscilik(b, kimlik)
        birimler = sorted({i['birim'] for i in mevcut} | {br for (mt, br) in tablo if mt == makine})
        ucretler = {u['birim']: u for u in kd.saat_ucretleri(b)}
        doldurulmus = []
        for i in oneri.onerileri_doldur([{a: x[a] for a in ('birim', 'saat', 'aciklama')} for x in mevcut],
                                        makine, tablo, gecmis):
            if i['saat'] is None:
                continue
            eski = next((x for x in mevcut if x['birim'] == i['birim']), None)
            doldurulmus.append(eski or kopyalama.ucretle(i['birim'], i['saat'], None, ucretler))
        return yanit({'makine_turu': makine,
                      'oneriler': [{'birim': br, **oneri.iscilik_onerisi(makine, br, tablo, gecmis)} for br in birimler],
                      'doldurulmus': doldurulmus})


@yol.post('/surumler/{kimlik}/takvim/sablondan')
def sablondan(kimlik: int, govde: SablondanTakvim, bg: Baglam = Depends(erisimli)):
    """Şablonun aktif satırlarından takvim önerir; kaydetmez. Ekran var olan satırları sorup değiştirir ve
    formu kaydeder."""
    with vt.islem() as b:
        s = surum_bul(b, kimlik)
        durum.surum_duzenlenebilir(s['durum'], bg.kisi)
        satirlar = takvim.sablondan(kd.takvim_sablonu(b), govde.toplam_hafta)
        ipucu = _takvim_ipuclari(b, s)
        return yanit({'toplam_hafta': govde.toplam_hafta,
                      'satirlar': [dict(r, ipucu_sure_hafta=ipucu.get(r['etap_kodu'])) for r in satirlar],
                      'hesap': takvim.takvim_hesabi(satirlar, sd.kalemler(b, kimlik))})


# ---------------------------------------------------------------- PDF (8.9)

def pdf_uret(b, s, tarih, taslak, an=None):
    """Müşteriye giden PDF: maliyet, kalemler, işçilik ve kâr girmez."""
    t = td.bul(b, s['talep'])
    m = md.bul(b, t['musteri'])
    ilgili = next(iter(md.kisiler(b, m['kimlik'], yalniz_aktif=True)), None)
    sembol = next((p['sembol'] for p in kd.para_birimleri(b) if p['kod'] == s['para_birimi']), None)
    return teklif_pdf({
        'firma': ayar_deposu.oku(b, 'firma', {}) or {}, 'teklif_no': f'{t["talep_no"]} · V{s["no"]}', 'tarih': tarih,
        'gecerlilik_gun': s['gecerlilik_gun'], 'musteri': {'ad': m['ad'], 'adres': m['adres'], 'ilgili': ilgili},
        'konu': t['konu'], 'teknik_cozum': s['teknik_cozum'], 'kapsam': td.kapsam(b, s['talep']),
        'teslim_suresi_hafta': s['teslim_suresi_hafta'], 'fiyat': s['fiyat'], 'para_birimi': s['para_birimi'],
        'sembol': sembol, 'odeme_kosullari': s['odeme_kosullari'], 'teslim_kosullari': s['teslim_kosullari'],
        'notlar': s['notlar'], 'an': an}, taslak)


def onayli_pdf(b, s, an):
    """Onay anında üretilir ve sürüme yazılır; gönderilen ve M1.1A'ya giden budur. → (pdf, parmak_izi)"""
    icerik = pdf_uret(b, s, an.date(), taslak=False, an=an)
    return icerik, hashlib.sha256(icerik).hexdigest()


@yol.get('/surumler/{kimlik}/pdf')
def pdf(kimlik: int, bg: Baglam = Depends(erisimli)):
    """Taslakta istenince üretilir, saklanmaz; onaylı ve gönderilmişte saklanan döner."""
    with vt.islem() as b:
        s = surum_bul(b, kimlik)
        if s['durum'] in (durum.TASLAK, durum.ONAY_BEKLIYOR):
            icerik = pdf_uret(b, s, baglanti.simdi().date(), taslak=True)
        else:
            icerik = bytes(sd.pdf(b, kimlik)['pdf'])
        return Response(icerik, media_type='application/pdf', headers={
            'Content-Disposition': f'inline; filename="{dosya_adi(s["talep_no"], s["no"])}"'})
