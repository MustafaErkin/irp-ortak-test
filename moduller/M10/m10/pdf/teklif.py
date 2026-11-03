"""Teklif PDF'i (SPEC › 8.9). fpdf2; A4, kenar 18 mm, Barlow 10 pt, başlıklar Barlow Condensed.

Maliyet, kalem listesi ve fiyatları, işçilik ve kâr PDF'e girmez. Taslakta her sayfada çapraz, soluk
"TASLAK — ONAYLANMADI" yazar.
"""
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from fpdf import FPDF

YAZITIPI = Path(__file__).resolve().parent / 'yazitipi'
KENAR = 18
MUREKKEP = (27, 42, 58)        # --murekkep (Ek D.12)
IKINCIL = (85, 102, 122)       # --ikincil
CIZGI = (195, 204, 214)        # --cizgi
SEMBOLLER = {'EUR': '€', 'TRY': '₺', 'USD': '$'}


def tutar_bicimi(tutar, para_birimi=None, sembol=None):
    """56000 → "56.000,00 €": binlik nokta, ondalık virgül, simge sonda."""
    t = Decimal(tutar).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    tam, ondalik = f'{abs(t):,.2f}'.split('.')
    metin = ('-' if t < 0 else '') + tam.replace(',', '.') + ',' + ondalik
    s = sembol or SEMBOLLER.get(para_birimi) or para_birimi
    return f'{metin} {s}' if s else metin


def buyuk(metin):
    """Türkçe büyük harf: i → İ, ı → I."""
    return metin.replace('i', 'İ').replace('ı', 'I').upper()


def tarih_bicimi(t):
    return t.strftime('%d.%m.%Y')


class _Belge(FPDF):
    def __init__(self, taslak, gecerlilik_sonu):
        super().__init__(format='A4', unit='mm')
        self.taslak, self.gecerlilik_sonu = taslak, gecerlilik_sonu
        self.set_margins(KENAR, KENAR, KENAR)
        self.set_auto_page_break(True, margin=KENAR + 8)
        for ad, dosya in (('Barlow', 'Barlow-Regular.ttf'), ('BarlowM', 'Barlow-Medium.ttf'),
                          ('BarlowSB', 'Barlow-SemiBold.ttf'), ('BarlowI', 'Barlow-Italic.ttf'),
                          ('BarlowCond', 'BarlowCondensed-SemiBold.ttf'),
                          ('BarlowCondM', 'BarlowCondensed-Medium.ttf')):
            self.add_font(ad, '', str(YAZITIPI / dosya))
        self.alias_nb_pages('{nb}')

    def header(self):
        if not self.taslak:
            return
        with self.local_context(fill_opacity=0.12, text_color=(184, 50, 42)):
            self.set_font('BarlowCond', size=64)
            with self.rotation(angle=35, x=self.w / 2, y=self.h / 2):
                metin = 'TASLAK — ONAYLANMADI'
                self.text(self.w / 2 - self.get_string_width(metin) / 2, self.h / 2 + 8, metin)
        self.set_xy(KENAR, KENAR)

    def footer(self):
        self.set_y(-KENAR)
        self.set_draw_color(*CIZGI)
        self.line(KENAR, self.get_y() - 2, self.w - KENAR, self.get_y() - 2)
        self.set_font('Barlow', size=8)
        self.set_text_color(*IKINCIL)
        self.cell(0, 5, f'Bu teklif {tarih_bicimi(self.gecerlilik_sonu)} tarihine kadar geçerlidir.')
        self.set_x(KENAR)
        self.cell(0, 5, f'Sayfa {self.page_no()}/{{nb}}', align='R')


def teklif_pdf(v, taslak):
    """v: {firma, teklif_no, tarih, gecerlilik_gun, musteri: {ad, adres, ilgili}, konu, teknik_cozum,
    kapsam: {dahil, haric}, teslim_suresi_hafta, fiyat, para_birimi, sembol, odeme_kosullari, teslim_kosullari,
    notlar, an}. → PDF baytları."""
    tarih = v['tarih']
    sonu = tarih + timedelta(days=v['gecerlilik_gun'] or 0)
    p = _Belge(taslak, sonu)
    p.set_title(f'Teklif {v["teklif_no"]}')
    p.set_author(v['firma'].get('unvan') or '')
    p.set_creator('Sibernetik IRP · M1.0')
    if isinstance(v.get('an'), datetime):
        p.set_creation_date(v['an'])
    p.add_page()
    genislik = p.w - 2 * KENAR

    # 1. Üst bilgi: firma
    f = v['firma']
    p.set_text_color(*MUREKKEP)
    p.set_font('BarlowCond', size=18)
    p.cell(0, 8, f.get('unvan') or '', new_x='LMARGIN', new_y='NEXT')
    p.set_font('Barlow', size=9)
    p.set_text_color(*IKINCIL)
    iletisim = ' · '.join(x for x in (f.get('adres'), f.get('telefon'), f.get('eposta'), f.get('web')) if x)
    if iletisim:
        p.multi_cell(0, 4.5, iletisim, new_x='LMARGIN', new_y='NEXT')
    p.set_draw_color(*MUREKKEP)
    p.set_line_width(0.6)
    p.line(KENAR, p.get_y() + 2, p.w - KENAR, p.get_y() + 2)
    p.ln(7)

    # 2. TEKLİF, no, tarih, geçerlilik sonu
    p.set_text_color(*MUREKKEP)
    p.set_font('BarlowCond', size=22)
    p.cell(genislik / 2, 10, 'TEKLİF')
    p.set_font('Barlow', size=10)
    p.multi_cell(genislik / 2, 5, f'Teklif no: {v["teklif_no"]}\nTarih: {tarih_bicimi(tarih)}\n'
                                  f'Geçerlilik sonu: {tarih_bicimi(sonu)}', align='R', new_x='LMARGIN', new_y='NEXT')
    p.ln(4)

    def baslik(metin):
        p.ln(2)
        p.set_font('BarlowCond', size=12)
        p.set_text_color(*MUREKKEP)
        p.cell(0, 6, buyuk(metin), new_x='LMARGIN', new_y='NEXT')
        p.set_draw_color(*CIZGI)
        p.set_line_width(0.2)
        p.line(KENAR, p.get_y(), p.w - KENAR, p.get_y())
        p.ln(1.5)
        p.set_font('Barlow', size=10)

    def paragraf(metin):
        if metin:
            p.multi_cell(0, 5, metin, new_x='LMARGIN', new_y='NEXT')

    # 3. Müşteri
    m = v['musteri']
    baslik('Müşteri')
    p.set_font('BarlowSB', size=10)
    p.cell(0, 5, m['ad'], new_x='LMARGIN', new_y='NEXT')
    p.set_font('Barlow', size=10)
    paragraf(m.get('adres'))
    if m.get('ilgili'):
        k = m['ilgili']
        paragraf('İlgili: ' + ', '.join(x for x in (k.get('ad'), k.get('unvan')) if x))

    # 4. Konu, 5. Teknik çözüm
    baslik('Konu')
    paragraf(v['konu'])
    if v.get('teknik_cozum'):
        baslik('Teknik çözüm')
        paragraf(v['teknik_cozum'])

    # 6. Kapsam
    kapsam = v.get('kapsam') or {}
    if kapsam.get('dahil') or kapsam.get('haric'):
        baslik('Kapsam')
        for ad, liste in (('Kapsama dahil', kapsam.get('dahil')), ('Kapsam dışı', kapsam.get('haric'))):
            if liste:
                p.set_font('BarlowM', size=10)
                p.cell(0, 5.5, ad, new_x='LMARGIN', new_y='NEXT')
                p.set_font('Barlow', size=10)
                for madde in liste:
                    p.set_x(KENAR + 4)
                    p.multi_cell(genislik - 4, 5, f'• {madde}', new_x='LMARGIN', new_y='NEXT')

    # 7. Teslim süresi, 8. Fiyat
    baslik('Teslim süresi')
    paragraf(f'Siparişten itibaren {v["teslim_suresi_hafta"]} hafta' if v.get('teslim_suresi_hafta') else '—')
    baslik('Fiyat')
    p.set_font('BarlowCond', size=16)
    fiyat = tutar_bicimi(v['fiyat'], v['para_birimi'], v.get('sembol')) if v.get('fiyat') is not None else '—'
    p.cell(0, 8, fiyat, new_x='LMARGIN', new_y='NEXT')
    p.set_font('Barlow', size=9)
    p.set_text_color(*IKINCIL)
    p.cell(0, 4.5, f'Para birimi: {v["para_birimi"]}', new_x='LMARGIN', new_y='NEXT')
    p.set_text_color(*MUREKKEP)

    # 9. Ödeme koşulları, teslim koşulları, notlar
    for ad, anahtar in (('Ödeme koşulları', 'odeme_kosullari'), ('Teslim koşulları', 'teslim_kosullari'),
                        ('Notlar', 'notlar')):
        if v.get(anahtar):
            baslik(ad)
            paragraf(v[anahtar])
    return bytes(p.output())


def dosya_adi(talep_no, no):
    return f'{talep_no}-V{no}.pdf'
