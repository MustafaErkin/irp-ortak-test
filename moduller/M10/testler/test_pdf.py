"""Adım 7: teklif PDF'i (SPEC › 8.9, 14.4)."""
import hashlib
import io
from decimal import Decimal

import pytest
from pypdf import PdfReader

from m10 import baglanti, vt
from m10.api.surumler import onayli_pdf
from m10.depo import surumler as sd
from m10.pdf.teklif import buyuk, tutar_bicimi
from ornek import d5_formu, d5_talebi, kaydet, yeni_surum


def metin(icerik):
    return '\n'.join(s.extract_text() for s in PdfReader(io.BytesIO(icerik)).pages)


@pytest.fixture
def surum(istemci, h):
    talep = d5_talebi(istemci, h)
    s = yeni_surum(istemci, h, talep)['kimlik']
    kaydet(istemci, h, s, d5_formu(istemci, h, s))
    return s


def test_turkce_buyuk_harf():
    assert buyuk('Teslim süresi, ödeme koşulları') == 'TESLİM SÜRESİ, ÖDEME KOŞULLARI'


def test_tutar_bicimi():
    assert tutar_bicimi(Decimal('56000')) + ' €' == tutar_bicimi(Decimal('56000'), 'EUR') == '56.000,00 €'
    assert tutar_bicimi(Decimal('35200'), 'TRY') == '35.200,00 ₺'
    assert tutar_bicimi(Decimal('1234567.005'), 'USD') == '1.234.567,01 $'
    assert tutar_bicimi(Decimal('0.5'), 'GBP') == '0,50 GBP'


def test_taslak_pdf(istemci, h, surum):
    r = istemci.get(f'/api/surumler/{surum}/pdf', headers=h('K050'))
    assert r.status_code == 200 and r.headers['content-type'] == 'application/pdf'
    assert 'T-2026-0001-V1.pdf' in r.headers['content-disposition']
    assert r.content.startswith(b'%PDF')
    m = metin(r.content)
    # girenler: fiyat, kapsam, teslim süresi, müşteri, ilgili kişi, koşullar, geçerlilik
    for parca in ('TEKLİF', 'MÜŞTERİ', 'TEKNİK ÇÖZÜM', 'TESLİM SÜRESİ', 'T-2026-0001 · V1', '56.000,00 €',
                  'Mekanik ve otomasyon tasarımı', 'Saha elektrik altyapısı', 'Siparişten itibaren 28 hafta', 'Autoliv', 'Ayşe Demir', '%40 sipariş ile', 'Sayfa 1/1',
                  'Bu teklif 02.12.2026 tarihine kadar geçerlidir.', 'TASLAK'):
        assert parca in m, parca
    # girmeyenler: maliyet, kâr, marj, kalem fiyatları ve listesi, işçilik, strateji notu
    for parca in ('43.500', '28,74', '22,32', '28.000', '4.500', '35.200', 'Robot, 6 eksen', 'PLC ve HMI seti',
                  '1.760', 'İyi fiyat ver', 'Maliyet', 'Kâr'):
        assert parca not in m, parca


def test_onayli_pdf_parmak_izi_saklananla_ayni(istemci, h, surum):
    an = baglanti.simdi()
    with vt.islem() as b:
        s = sd.bul(b, surum)
        icerik, iz = onayli_pdf(b, s, an)
        b.execute("UPDATE teklif_surumleri SET durum = 'ONAYLANDI', onaylayan = 'K001', onay_ani = %s, pdf = %s, "
                  "pdf_parmak_izi = %s, donmus_ozet = '{}' WHERE kimlik = %s", (an, icerik, iz, surum))
    r = istemci.get(f'/api/surumler/{surum}/pdf', headers=h('K050'))
    assert hashlib.sha256(r.content).hexdigest() == iz
    m = metin(r.content)
    assert 'TASLAK' not in m and '56.000,00 €' in m and 'Tarih: 02.11.2026' in m


def test_pdf_yetki(istemci, h, surum):
    assert istemci.get(f'/api/surumler/{surum}/pdf', headers=h('K041')).status_code == 403
