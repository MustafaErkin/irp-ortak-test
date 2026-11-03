"""Sağlanan okumalar (SPEC › 8.16, Ek D.4–D.6). Çekirdek modüller arası okumayı yönlendirene kadar (istek M10-02)
modülün kendi arka yüzünde sunulur; çağıran kullanıcının anahtarıyla gelir.

- M10.KAZANAN_SURUM {surum}: GONDERILDI ve talebin kazananı olan sürümün donmuş içeriği. Tutarlar donmuştur:
  toplamlar onayda dondurulan özetten gelir, yeniden hesaplanmaz. Strateji notu ve işlem geçmişi gönderilmez.
- M10.KATALOG_TEMIN_SURELERI: aktif katalog kalemlerinin tipik temin süresi ve kritik işareti; fiyat yok.
"""
import base64

from .. import hatalar
from ..depo import katalog as kd
from ..depo import surumler as sd
from ..depo import talepler as td
from ..pdf.teklif import dosya_adi
from . import hesap
from .durum import GONDERILDI, KAZANILDI

KALEM = ('aciklama', 'adet', 'olcu_birimi', 'birim_fiyat', 'para_birimi')


def kazanan_surum(b, surum):
    s = sd.bul(b, surum)
    if s is None:
        raise hatalar.bulunamadi('Teklif sürümü bulunamadı.')
    if s['durum'] != GONDERILDI:
        raise hatalar.kapi('Sürüm müşteriye gönderilmemiş.', neden='GONDERILMEDI')
    t = td.bul(b, s['talep'])
    if t['durum'] != KAZANILDI or t['kazanan_surum'] != s['kimlik']:
        raise hatalar.kapi('Talep bu sürümle kazanılmamış.', neden='KAZANILMADI')
    oz = s['donmus_ozet']
    kurlar = sd.kurlar(b, surum)
    kur = {k['para_birimi']: k['kur_try'] for k in kurlar}
    donmus_kalem = {k['sira']: k for k in oz['kalemler']}
    kalemler = []
    for k in sd.kalemler(b, surum):
        d = donmus_kalem[k['sira']]
        tutar = hesap.kalem_tutari(k, s['para_birimi'], kur)
        kalemler.append({'sira': k['sira'], 'unsur': d['unsur'], 'unsur_adi': d['unsur_adi'],
                         'butce_kalemi': d['butce_kalemi'], 'katalog_kodu': d['katalog_kodu'],
                         **{a: k[a] for a in KALEM}, 'tutar': tutar['tutar'], 'tutar_teklif': tutar['tutar_teklif'],
                         'kaynak_etiketi': k['kaynak_etiketi'], 'temin_hafta': k['temin_hafta'], 'kritik': k['kritik']})
    iscilik = []
    for i in sd.iscilik(b, surum):
        tutar = hesap.iscilik_tutari(i, s['para_birimi'], kur)
        iscilik.append({a: i[a] for a in ('birim', 'saat', 'saat_ucreti', 'para_birimi')} |
                       {'tutar': tutar['tutar'], 'tutar_teklif': tutar['tutar_teklif']})
    pdf = sd.pdf(b, surum)
    return {
        'surum': s['kimlik'], 'etiket': f'{t["talep_no"]}/V{s["no"]}', 'talep': t['kimlik'], 'talep_no': t['talep_no'],
        'durum': s['durum'], 'talep_durumu': t['durum'], 'kaynak': t['kaynak'], 'bagli_proje': t['bagli_proje'],
        'tur': t['tur'], 'konu': t['konu'], 'makine_turu': t['makine_turu'],
        'musteri': oz['musteri'],
        'para_birimi': s['para_birimi'], 'kurlar': kurlar,
        'fiyat': s['fiyat'], 'kar_orani': s['kar_orani'], 'fiyat_girisi': s['fiyat_girisi'],
        'toplamlar': oz['toplamlar'],
        'kalemler': kalemler, 'iscilik': iscilik,
        'takvim': [{a: r[a] for a in ('sira', 'etap_kodu', 'ad', 'paralel_grup', 'baslangic_hafta', 'sure_hafta')}
                   for r in sd.takvim(b, surum)],
        'takvim_teslim_hafta': oz['takvim_teslim_hafta'], 'en_erken_teslim_hafta': oz['en_erken_teslim_hafta'],
        'teslim_suresi_hafta': s['teslim_suresi_hafta'],
        'gereksinimler': oz['gereksinimler'], 'kapsam': oz['kapsam'], 'dosyalar': oz['dosyalar'],
        'hazirlayan': s['hazirlayan'], 'onaylayan': s['onaylayan'], 'onay_ani': s['onay_ani'],
        'gonderim_ani': s['gonderim_ani'],
        'pdf': {'ad': dosya_adi(t['talep_no'], s['no']), 'parmak_izi': pdf['pdf_parmak_izi'],
                'icerik_base64': base64.b64encode(bytes(pdf['pdf'])).decode('ascii')},
    }


def katalog_temin_sureleri(b):
    return {'kalemler': [{'kod': k['kod'], 'ad': k['ad'], 'unsur': k['unsur'], 'butce_kalemi': k['butce_kalemi'],
                          'tipik_temin_hafta': k['tipik_temin_hafta'], 'ortalama_temin_hafta': None,
                          'kritik': k['kritik']} for k in kd.katalog(b, yalniz_aktif=True)]}
