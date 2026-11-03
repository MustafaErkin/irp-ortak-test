"""Çekirdeğe giden tek yol: irp_sozlesme.baglanti (BASLA › Kural 2). Sürücüyü IRP_* ortam değişkenleri seçer."""
import sys
import json

import psycopg

from .ayarlar import KOK, ortam

if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from irp_sozlesme.baglanti import Cekirdek, CekirdekHatasi, Cevap, Okuma, Oturum, Servis  # noqa: E402

__all__ = ['Cekirdek', 'CekirdekHatasi', 'Cevap', 'Okuma', 'Oturum', 'Servis', 'TabloSayac', 'cekirdek_ac']


class TabloSayac:
    """Olay kimliğinin kişi ve gün başına sırası, modülün tablosunda; her çağrı kendi kısa işleminde
    (sozlesme/04_veritabani.md › 3, SPEC › 15.8)."""

    def __init__(self, vt_url: str):
        self.vt_url = vt_url

    def sonraki(self, kisi: str, gun: str) -> int:
        with psycopg.connect(self.vt_url, autocommit=True, prepare_threshold=None) as b:
            return b.execute('SELECT mod_m11a.olay_sirasi(%s, %s)', (kisi, gun)).fetchone()[0]

    def zarf(self,kisi,istek,olay):
        """Göndermeden önce kalıcılaştır; eşzamanlı tekrar aynı zarfı okur."""
        from psycopg.types.json import Jsonb
        if olay['eylem_kodu']!='PROJE.ACTIM':
            raise CekirdekHatasi('BICIM','Bu modülde kalıcı zarf yalnız proje açılışında kullanılır')
        with psycopg.connect(self.vt_url,autocommit=True,prepare_threshold=None) as b:
            with b.transaction():
                b.execute('INSERT INTO mod_m11a.acilis_zarflari(kisi,istek,proje,olay) VALUES(%s,%s,%s,%s) '
                          'ON CONFLICT(kisi,istek) DO NOTHING',(kisi,istek,olay['girdiler']['kod'],Jsonb(olay)))
                saved=b.execute('SELECT olay FROM mod_m11a.acilis_zarflari WHERE kisi=%s AND istek=%s',
                                (kisi,istek)).fetchone()[0]
        for key in ('kim','eylem_kodu','girdiler','neyin_ustunde','adina','kanit','duzelttigi_olay'):
            if saved[key]!=json.loads(json.dumps(olay[key])):
                raise CekirdekHatasi('DURUM','Bekleyen açılışın içeriği değişmiş; aynı istekle farklı karar gönderilemez')
        return saved


def cekirdek_ac(kunye=None, vt_url: str | None = None, **secenek) -> Cekirdek:
    o = ortam()
    return Cekirdek.ac(str(kunye or o.kunye), sayac=TabloSayac(vt_url or o.veritabani), **secenek)
