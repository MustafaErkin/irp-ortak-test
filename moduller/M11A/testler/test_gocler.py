"""Göçler ve değişmezler (SPEC › 7, 14.4)."""
import json

import psycopg
import pytest

from m11a import vt
from m11a.ayarlar import ortam


def _proje(b, proje='2611001', surum=57, sira=1):
    b.execute(
        """INSERT INTO mod_m11a.projeler (proje, durum, teklif_surumu, teklif_etiketi, talep_no, musteri_adi, proje_adi,
             kaynak, sorumlu, satis_yoneticisi, siparis_tarihi, teslim_tarihi, yil, yillik_sira, para_birimi,
             sozlesme_tutari, guncel_tutar, donmus_teklif, pdf, pdf_ad, pdf_parmak_izi, acan, acilis_ani)
           VALUES (%s, 'ACIK', %s, 'T/V1', 'T-1', 'Autoliv', 'Proje', 'YENI_IS', 'K050', 'K050', '2026-11-02',
             '2027-05-16', 2026, %s, 'EUR', 56000, 56000, %s, '\\x00', 'a.pdf', %s, 'K050', now())""",
        (proje, surum, sira, json.dumps({'surum': surum}), 'a' * 64))
    b.execute("INSERT INTO mod_m11a.butce_satirlari VALUES (%s, 'MALZEME', 32500, 32500)", (proje,))


def test_gocler_bos_semada_sirayla(vt_baglanti):
    with vt.baglan(ortam().test_veritabani) as b:
        assert vt.sema_kur(b) == ['sema_ac.sql', '001_m11a.sql', '002_varsayilanlar.sql']
        ayarlar = {r['anahtar']: r['deger'] for r in b.execute('SELECT * FROM mod_m11a.ayarlar')}
    assert ayarlar['proje_kodu_deseni'] == '{YY}{AA}{SIRA3}'
    assert ayarlar['sapma_esigi_puan'] == 15


@pytest.mark.parametrize('alan, deger', [
    ('sozlesme_tutari', '50000'), ('para_birimi', "'TRY'"), ('teklif_surumu', '99'),
    ('donmus_teklif', "'{}'::jsonb"), ('kurlar', "'[{}]'::jsonb"), ('pdf_parmak_izi', "'" + 'b' * 64 + "'")])
def test_donmus_alanlar_degismez(vt_baglanti, alan, deger):
    _proje(vt_baglanti)
    with pytest.raises(psycopg.errors.RaiseException, match='değiştirilemez'):
        vt_baglanti.execute(f"UPDATE mod_m11a.projeler SET {alan} = {deger} WHERE proje = '2611001'")


def test_guncel_tutar_degisebilir(vt_baglanti):
    _proje(vt_baglanti)
    vt_baglanti.execute("UPDATE mod_m11a.projeler SET guncel_tutar = 50000 WHERE proje = '2611001'")
    vt_baglanti.execute("UPDATE mod_m11a.butce_satirlari SET guncel = 26500 WHERE proje = '2611001'")


def test_baslangic_butcesi_degismez(vt_baglanti):
    _proje(vt_baglanti)
    with pytest.raises(psycopg.errors.RaiseException, match='Başlangıç bütçesi'):
        vt_baglanti.execute("UPDATE mod_m11a.butce_satirlari SET baslangic = 1 WHERE proje = '2611001'")


def test_bir_teklif_surumu_bir_kez_donusur(vt_baglanti):
    _proje(vt_baglanti)
    with pytest.raises(psycopg.errors.UniqueViolation):
        _proje(vt_baglanti, proje='2611002', sira=2)


def test_tarih_kosulunda_tarih_zorunlu(vt_baglanti):
    _proje(vt_baglanti)
    with pytest.raises(psycopg.errors.CheckViolation):
        vt_baglanti.execute("""INSERT INTO mod_m11a.odeme_satirlari (proje, sira, kosul, tarih, tutar, para_birimi)
                               VALUES ('2611001', 1, 'TARIH', NULL, 1000, 'EUR')""")


def test_kapali_butcede_kapanis_alanlari(vt_baglanti):
    _proje(vt_baglanti)
    with pytest.raises(psycopg.errors.CheckViolation), vt_baglanti.transaction():
        vt_baglanti.execute("UPDATE mod_m11a.projeler SET butce_durumu = 'KAPALI' WHERE proje = '2611001'")
    vt_baglanti.execute("""UPDATE mod_m11a.projeler SET butce_durumu = 'KAPALI', kapanis_ani = now(),
                             kapanis_kesin_kabul = '2027-05-23', kapatan = 'K060' WHERE proje = '2611001'""")


def test_olay_sirasi_tek_islemle_artar(vt_baglanti):
    s = [vt_baglanti.execute("SELECT mod_m11a.olay_sirasi('K050', '261102') AS n").fetchone()['n'] for _ in range(3)]
    assert s == [1, 2, 3]
    assert vt_baglanti.execute("SELECT mod_m11a.sayac_ilerlet('PROJE_KODU', '2026') AS n").fetchone()['n'] == 1
