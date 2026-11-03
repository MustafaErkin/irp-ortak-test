"""Siparişe dönüştürmek (SPEC › 8.1): önizleme, dönüştürme, yeniden dene, ek iş ve serviste ana proje.

Çekirdeğe giden tek olay PROJE.ACTIM'dır; kullanıcının gözüyle gönderilir. Kapı M1.0'dadır ve M1.1A ayrıca denetler."""
import base64
import binascii
from datetime import date
import hashlib
import logging
import re

import psycopg

from ..api.hatalar import ModulHatasi, dogrulama, yetki as yetki_hatasi
from ..baglanti import CekirdekHatasi
from ..depo import ayarlar as ayar_deposu, projeler as depo
from ..saglayicilar import SaglayiciHatasi
from . import butce, eksik, kod, tarih, yetki

gunluk = logging.getLogger('m11a.donusturme')

KAPI_MESAJI = 'Yalnızca gönderilmiş ve kazanılmış teklif siparişe dönüştürülür.'
PARMAK_IZI = re.compile(r'^[0-9a-f]{64}$')
M11B_MESAJI = "Proje ekibine devir (M1.1B): M1.1B'de 'Devri başlat'a {kod} yazın."


# ------------------------------------------------------------------ M1.0'dan okumak

def kazanan_surum(i, surum: int) -> dict:
    try:
        k = i.uyg.saglayici.kazanan_surum(i.anahtar, surum)
    except SaglayiciHatasi as h:
        if h.kod == 'KAPI':
            raise ModulHatasi(409, 'KAPI', KAPI_MESAJI, neden=h.neden) from h
        if h.kod == 'SAGLAYICI_YOK':
            raise ModulHatasi(503, 'SAGLAYICI_YOK',
                              'Teklif modülüne (M1.0) ulaşılamıyor; dönüştürme şu an yapılamaz.') from h
        if h.kod == 'YETKI':
            raise yetki_hatasi('Bu teklifi görme yetkiniz yok.') from h
        if h.kod == 'OTURUM':
            raise ModulHatasi(401, 'OTURUM', 'Oturum düşmüş; yeniden giriş yapın.') from h
        if h.kod == 'BULUNAMADI':
            raise ModulHatasi(404, 'BULUNAMADI', 'Teklif sürümü bulunamadı.') from h
        gunluk.error('M1.0 beklenmeyen cevap: %s %s', h.kod, h.govde)
        raise ModulHatasi(502, 'BEKLENMEYEN', 'Teklif modülünden beklenmeyen cevap geldi.') from h
    if k.get('hesaplaniyor'):
        i.hesaplaniyor = True
    if int(k.get('surum', -1)) != int(surum) or k.get('durum') != 'GONDERILDI' or k.get('talep_durumu') != 'KAZANILDI':
        raise ModulHatasi(409, 'KAPI', KAPI_MESAJI)
    return k


def _zaten(p: dict) -> ModulHatasi:
    return ModulHatasi(409, 'ZATEN_DONUSTU', f'Bu teklif {p["proje"]} olarak açıldı.', proje=p['proje'],
                       durum=p['durum'])


def _ana_proje(k: dict) -> str | None:
    return k.get('bagli_proje') if k.get('kaynak') in ('EK_IS', 'SERVIS') else None


# ------------------------------------------------------------------ kod

def onerilen_kod(b, a: dict, siparis: date) -> str:
    """Önizleme sayacı ilerletmez: o anki değere bakar; modülün tablosunda olan kod atlanır."""
    donem = kod.sira_donemi(siparis, a['proje_kodu_sira_kapsami'])
    n = depo.sayac_degeri(b, 'PROJE_KODU', donem) + 1
    while depo.kod_var_mi(b, k := kod.proje_kodu(a['proje_kodu_deseni'], siparis, n)):
        n += 1
    return k


def _kod_al(b, a: dict, siparis: date) -> tuple[str, tuple]:
    donem = kod.sira_donemi(siparis, a['proje_kodu_sira_kapsami'])
    for _ in range(1000):
        n = depo.sayac_ilerlet(b, 'PROJE_KODU', donem)
        k = kod.proje_kodu(a['proje_kodu_deseni'], siparis, n)
        if not depo.kod_var_mi(b, k):
            return k, ('PROJE_KODU', donem, n)
    raise ModulHatasi(409, 'KOD_KULLANILIYOR', 'Kalıptan boş kod üretilemedi; kodu elle yazın.')


# ------------------------------------------------------------------ önizleme

def onizleme(i, surum: int) -> dict:
    i.rol_gerek(yetki.DONUSTURME)
    if p := depo.surumden(i.b, surum):
        return {'zaten_donustu': True, 'proje': p['proje'], 'durum': p['durum'],
                'mesaj': f'Bu teklif {p["proje"]} olarak açıldı.'}
    k = kazanan_surum(i, surum)
    a = ayar_deposu.oku(i.b)
    siparis = date.fromisoformat(i.simdi()[:10])
    proje_kodu = onerilen_kod(i.b, a, siparis)
    yillik_sira = depo.sayac_degeri(i.b, 'SIPARIS', str(siparis.year)) + 1
    t = tarih.oneriler(siparis, k)
    bt = butce.baslangic_butcesi(k)
    return i.cevap({
        'zaten_donustu': False, 'surum': k['surum'], 'etiket': k['etiket'], 'talep_no': k['talep_no'],
        'kaynak': k['kaynak'], 'ana_proje': _ana_proje(k),
        'proje_kodu': proje_kodu, 'siparis_adi_deseni': a['siparis_adi_deseni'], 'yillik_sira': yillik_sira,
        'siparis_adi': kod.siparis_adi(a['siparis_adi_deseni'], siparis, yillik_sira, proje_kodu,
                                       k['musteri']['ad'], k['konu'], None),
        'proje_adi': k['konu'], 'musteri': k['musteri']['ad'], 'sorumlu': i.kisi,
        'siparis_tarihi': siparis.isoformat(), 'teslim_tarihi': _iso(t['teslim_tarihi']),
        'kesin_kabul_tarihi': _iso(t['kesin_kabul_tarihi']), 'kayma_hafta': t['kayma_hafta'],
        'teslim_suresi_hafta': k.get('teslim_suresi_hafta'), 'para_birimi': k['para_birimi'],
        'sozlesme_tutari': butce.metin(butce.para(k['fiyat'])),
        'butce': {kalem: butce.metin(v) for kalem, v in bt.items()},
        'baslangic_plani': [dict(s, baslangic=s['baslangic'].isoformat(), bitis=s['bitis'].isoformat())
                            for s in t['baslangic_plani']],
    })


def _iso(t: date | None) -> str | None:
    return t.isoformat() if t else None


# ------------------------------------------------------------------ dönüştürme

def _dogrula(i, g, k: dict) -> None:
    hatalar = []
    if g.proje_kodu is not None and not kod.elle_kod_gecerli(g.proje_kodu):
        hatalar.append({'alan': 'proje_kodu', 'sira': None,
                        'mesaj': 'Kod 2–20 harf, rakam ya da tire olmalı.'})
    if not g.proje_adi.strip():
        hatalar.append({'alan': 'proje_adi', 'sira': None, 'mesaj': 'Proje adı boş olamaz.'})
    sorumlu = next((x for x in i.kisiler() if x['kimlik'] == g.sorumlu), None)
    if not sorumlu or not sorumlu.get('aktif'):
        hatalar.append({'alan': 'sorumlu', 'sira': None, 'mesaj': 'Sorumlu aktif bir kişi olmalı.'})
    if g.teslim_tarihi < g.siparis_tarihi:
        hatalar.append({'alan': 'teslim_tarihi', 'sira': None, 'mesaj': 'Teslim sipariş tarihinden önce olamaz.'})
    if g.kesin_kabul_tarihi and g.kesin_kabul_tarihi < g.teslim_tarihi:
        hatalar.append({'alan': 'kesin_kabul_tarihi', 'sira': None, 'mesaj': 'Kesin kabul teslimden önce olamaz.'})
    for alan in ('po_dosyasi', 'sozlesme_dosyasi'):
        d = getattr(g, alan)
        if d and (not d.ad.strip() or not d.konum.strip()):
            hatalar.append({'alan': alan, 'sira': None, 'mesaj': 'Dosyanın adı ve konumu gerekli.'})
        if d and d.parmak_izi and not PARMAK_IZI.match(d.parmak_izi):
            hatalar.append({'alan': alan, 'sira': None, 'mesaj': 'Parmak izi 64 haneli SHA-256 olmalı.'})
    if k.get('kaynak') in ('EK_IS', 'SERVIS') and not k.get('bagli_proje'):
        hatalar.append({'alan': 'ana_proje', 'sira': None, 'mesaj': 'Ek işin ya da servisin bağlı projesi yok.'})
    if hatalar:
        raise dogrulama(hatalar)


def _pdf(k: dict) -> bytes:
    try:
        pdf = base64.b64decode(k['pdf']['icerik_base64'], validate=True)
    except (KeyError, TypeError, binascii.Error) as h:
        raise ModulHatasi(502, 'BEKLENMEYEN', 'Teklifin PDF\'i okunamadı.') from h
    if hashlib.sha256(pdf).hexdigest() != k['pdf'].get('parmak_izi'):
        gunluk.error('PDF parmak izi uyuşmuyor: sürüm %s', k.get('surum'))
        raise ModulHatasi(502, 'BEKLENMEYEN', 'Teklifin PDF\'inin parmak izi uyuşmuyor.')
    return pdf


def _actim_girdileri(p: dict) -> dict:
    g = {'kimlik': p['proje'], 'kod': p['proje'], 'ad': p['proje_adi'], 'musteri': p['musteri_adi'],
         'sorumlu': p['sorumlu'], 'baslangic_tarihi': _iso(p['siparis_tarihi']),
         'teslim_tarihi': _iso(p['teslim_tarihi'])}
    if p.get('kesin_kabul_tarihi'):
        g['kesin_kabul_tarihi'] = _iso(p['kesin_kabul_tarihi'])
    if p.get('ana_proje'):
        g['ana_proje'] = p['ana_proje']
    return g


def donustur(i, g) -> dict:
    i.rol_gerek(yetki.DONUSTURME)
    if p := depo.surumden(i.b, g.surum):
        raise _zaten(p)
    k = kazanan_surum(i, g.surum)          # önizleme eski olabilir: yeniden okunur, kapı yeniden denetlenir
    _dogrula(i, g, k)
    ana = _ana_proje(k)
    ana_kayit = None
    if ana:
        ana_kayit = i.proje(ana)
        if ana_kayit is None:
            raise ModulHatasi(409, 'ANA_PROJE', f'Ana proje {ana} çekirdekte bulunamadı.')
    pdf = _pdf(k)
    a = ayar_deposu.oku(i.b)
    an = i.simdi()
    sayaclar = []
    try:
        with i.b.transaction():
            if g.proje_kodu:
                proje_kodu = g.proje_kodu
                if depo.kod_var_mi(i.b, proje_kodu):
                    raise ModulHatasi(409, 'KOD_KULLANILIYOR', f'{proje_kodu} kodu kullanılıyor.',
                                      onerilen_kod=onerilen_kod(i.b, a, g.siparis_tarihi))
            else:
                proje_kodu, s = _kod_al(i.b, a, g.siparis_tarihi)
                sayaclar.append(s)
            yil = g.siparis_tarihi.year
            yillik_sira = depo.sayac_ilerlet(i.b, 'SIPARIS', str(yil))
            sayaclar.append(('SIPARIS', str(yil), yillik_sira))
            p = {'proje': proje_kodu, 'durum': 'ACILIYOR', 'teklif_surumu': k['surum'], 'teklif_etiketi': k['etiket'],
                 'talep_no': k['talep_no'], 'm10_musteri': k['musteri'].get('kimlik'),
                 'musteri_adi': k['musteri']['ad'], 'proje_adi': g.proje_adi.strip(), 'kaynak': k['kaynak'],
                 'ana_proje': ana, 'sorumlu': g.sorumlu, 'satis_yoneticisi': i.kisi,
                 'siparis_tarihi': g.siparis_tarihi, 'teslim_tarihi': g.teslim_tarihi,
                 'kesin_kabul_tarihi': g.kesin_kabul_tarihi, 'yil': yil, 'yillik_sira': yillik_sira,
                 'po_no': (g.po_no or '').strip() or None, 'para_birimi': k['para_birimi'],
                 'sozlesme_tutari': butce.para(k['fiyat']), 'guncel_tutar': butce.para(k['fiyat']),
                 'kurlar': k.get('kurlar') or [], 'teslim_suresi_hafta': k.get('teslim_suresi_hafta'),
                 'donmus_teklif': {x: v for x, v in k.items() if x not in ('pdf', 'hesaplaniyor')},
                 'pdf': pdf, 'pdf_ad': k['pdf']['ad'], 'pdf_parmak_izi': k['pdf']['parmak_izi'],
                 'acan': i.kisi, 'acilis_ani': an}
            depo.ac(i.b, p, butce.baslangic_butcesi(k), butce.saat_ucretleri(k),
                    tarih.baslangic_plani(g.siparis_tarihi, k.get('takvim') or []))
            po = depo.dosya_ekle(i.b, proje_kodu, 'PO', g.po_dosyasi.model_dump(), i.kisi, an) if g.po_dosyasi else None
            sz = (depo.dosya_ekle(i.b, proje_kodu, 'SOZLESME', g.sozlesme_dosyasi.model_dump(), i.kisi, an)
                  if g.sozlesme_dosyasi else None)
            depo.dosyalari_bagla(i.b, proje_kodu, po, sz)
    except psycopg.errors.UniqueViolation as h:
        if (p := depo.surumden(i.b, g.surum)):
            raise _zaten(p) from h
        raise
    return _cekirdege_ac(i, depo.getir(i.b, proje_kodu), ana_kayit, sayaclar, a)


def _geri_al(i, proje: str, sayaclar: list[tuple]) -> None:
    with i.b.transaction():
        depo.sil(i.b, proje)
        for ad, donem, n in reversed(sayaclar):
            depo.sayac_geri_al(i.b, ad, donem, n)


def _cekirdege_ac(i, p: dict, ana_kayit: dict | None, sayaclar: list[tuple], a: dict, koru: bool = False) -> dict:
    """koru: proje çekirdekte var olabilir ama açan göremiyor; DURUM'da kayıt silinmez."""
    neyin_ustunde = [i.oturum.hedef('PROJE', ana_kayit)] if ana_kayit else []
    try:
        cevap = i.oturum.olay_gonder('PROJE.ACTIM', _actim_girdileri(p), neyin_ustunde=neyin_ustunde,
                                     istek_kimligi='PROJE.ACTIM:'+p['proje'])
    except CekirdekHatasi as h:
        if h.tur in ('BAGLANTI','URUN','DURUM'):
            raise ModulHatasi(503, 'BAGLANTI', 'Çekirdeğe ulaşılamıyor; "Yeniden dene" ile tamamlayın.',
                              proje=p['proje'], durum='ACILIYOR') from h
        _geri_al(i, p['proje'], sayaclar)
        raise
    if cevap.basarili:
        return _acildi(i, p, cevap.get('olay_kimligi'))
    if koru and cevap.kod == 'DURUM':
        # Proje çekirdekte var ama açan göremiyor (sorumlu başkası; M11A-01): kayıt korunur, açılış bekler.
        raise ModulHatasi(409, 'DURUM', 'Proje çekirdekte var ama göremiyorsunuz; yetkili erişim vermeli (M11A-01).',
                          proje=p['proje'])
    _geri_al(i, p['proje'], sayaclar)
    if cevap.kod == 'YETKI':
        raise yetki_hatasi('Çekirdekte proje açma yetkiniz yok (PROJE.ACTIM).')
    if cevap.kod == 'DURUM':
        if ana_kayit and ana_kayit.get('ana_proje'):
            raise ModulHatasi(409, 'ANA_PROJE', f'{ana_kayit["kimlik"]} bir ek işin projesi; ek iş ana projeye '
                                                f'bağlanır ({ana_kayit["ana_proje"]}).', ana_proje=ana_kayit['kimlik'])
        raise ModulHatasi(409, 'DURUM', 'Proje açılamadı. Proje kodunu ve varsa ana projenin durumunu kontrol edin.')
    if cevap.bayat:
        raise ModulHatasi(409, 'DEGISTI', 'Ana proje bu arada değişti; yeniden açın.')
    gunluk.error('PROJE.ACTIM beklenmeyen ret: %s', dict(cevap))
    raise ModulHatasi(400, 'BEKLENMEYEN', 'Çekirdek proje açılışını beklenmedik biçimde reddetti.')


def _acildi(i, p: dict, olay: str | None) -> dict:
    try:
        depo.acildi(i.b, p['proje'], olay)
    except psycopg.Error as h:
        gunluk.exception('Çekirdek %s projesini açtı, modülün kaydı yazılamadı', p['proje'])
        raise ModulHatasi(500, 'BEKLENMEYEN', 'Proje çekirdekte açıldı ama kayıt tamamlanamadı; "Yeniden dene".',
                          proje=p['proje'], durum='ACILIYOR') from h
    p = depo.getir(i.b, p['proje'])
    from . import teknik
    try:
        teknik_devir=teknik.devret(i,p)
    except Exception:
        teknik_devir={'dosya_aktarimi_tamam':False}
    a = ayar_deposu.oku(i.b)
    sozlesme = p['sozlesme_dosyasi']
    eksikler = eksik.eksik_alanlar(p['po_no'], sozlesme, {}, 0, 0)
    return i.cevap({
        'proje': p['proje'], 'durum': p['durum'], 'acilis_olayi': p['acilis_olayi'],
        'siparis_adi': siparis_adi(a, p), 'po_bekleniyor': p['po_no'] is None,
        'eksikler': [{'alan': e, 'ne': eksik.ALANLAR[e]} for e in eksikler],
        'm11b': {'proje': p['proje'], 'mesaj': M11B_MESAJI.format(kod=p['proje'])},
        'teknik_devir':teknik_devir,
    })


def siparis_adi(a: dict, p: dict) -> str:
    return kod.siparis_adi(a['siparis_adi_deseni'], p['siparis_tarihi'], p['yillik_sira'], p['proje'],
                           p['musteri_adi'], p['proje_adi'], p['po_no'])


# ------------------------------------------------------------------ yeniden dene

def yeniden_dene(i, proje: str) -> dict:
    i.rol_gerek(yetki.DONUSTURME)
    p = depo.getir(i.b, proje)
    if not p or (p['durum'] == 'ACILIYOR' and p['acan'] != i.kisi):
        raise ModulHatasi(404, 'BULUNAMADI', 'Tamamlanmamış açılış bulunamadı.')
    if p['durum'] == 'ACIK':
        raise ModulHatasi(409, 'DURUM', 'Proje zaten açık.', proje=proje)
    ana_kayit = i.proje(p['ana_proje']) if p['ana_proje'] else None
    return _cekirdege_ac(i, p, ana_kayit, [], ayar_deposu.oku(i.b))
