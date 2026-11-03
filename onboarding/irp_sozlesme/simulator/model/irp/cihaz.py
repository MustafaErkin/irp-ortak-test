"""A1–A4: dosyaya bağlı kimlik sayacı, yerel günlük ve kapılar."""
import json
from pathlib import Path
from datetime import timedelta, datetime
from threading import RLock
from .saat import an
from .olay import kodla
from .kisi_gunu import kapi, bos_hal, gecis
from .olay import hedefler


class Cihaz:
    def __init__(self, kisi, harf, saat, dosya=None):
        self.kisi, self.harf, self.saat = kisi, harf, saat
        self.dosya = Path(dosya) if dosya else None
        self._kilit = RLock()
        self.veri = {'sayaclar': {}, 'gunluk': {}, 'fark_saniye': 0}
        if self.dosya and self.dosya.exists(): self.veri = json.loads(self.dosya.read_text(encoding='utf-8'))

    def kaydet(self):
        if self.dosya:
            self.dosya.parent.mkdir(parents=True, exist_ok=True)
            gecici = self.dosya.with_suffix('.tmp')
            gecici.write_text(kodla(self.veri), encoding='utf-8')
            gecici.replace(self.dosya)

    def simdi_duzeltilmis(self):
        return self.saat.simdi() + timedelta(seconds=self.veri['fark_saniye'])

    def saat_farki_olc(self, t0, sunucu, t1):
        self.veri['fark_saniye'] = (an(sunucu) - (an(t0) + (an(t1) - an(t0)) / 2)).total_seconds()
        self.kaydet()

    def olay_kimligi_uret(self):
        with self._kilit:
            if not self.harf: raise ConnectionError('Yeni cihaz kaydi cevrimici ister')
            return self._kimlik_uret()

    def depo_kayboldu(self):
        self.harf = None
        self.veri = {'sayaclar': {}, 'gunluk': {}, 'fark_saniye': 0}

    def yeniden_kaydol(self, kullanilan_harfler, baglanti=True):
        if not baglanti: raise ConnectionError('Cihaz kaydi cevrimici ister')
        with self._kilit:
            self.harf = next((h for h in 'TUVWXYZABCDEFGHIJKLMNOPQRS' if h not in kullanilan_harfler), None)
            if not self.harf: raise OverflowError('Cihaz harfleri doldu')
            kullanilan_harfler.add(self.harf)
            self.kaydet()
            return self.harf

    def _kimlik_uret(self):
        tarih = self.simdi_duzeltilmis().strftime('%y%m%d')
        sayac = self.veri['sayaclar'].get(tarih, 0) + 1
        if sayac > 9999: raise OverflowError('A1 kimlik alani doldu')
        self.veri['sayaclar'][tarih] = sayac
        self.kaydet()
        return '{}-{}{:04d}-{}'.format(self.kisi, tarih, sayac, self.harf)

    def sayaci_esitle(self, depo):
        tarih = self.simdi_duzeltilmis().strftime('%y%m%d')
        bas = self.kisi + '-' + tarih
        sayilar = [int(k.split('-')[1][6:]) for k in depo.olaylar if k.startswith(bas) and k.endswith('-' + self.harf)]
        self.veri['sayaclar'][tarih] = max([self.veri['sayaclar'].get(tarih, 0)] + sayilar)
        # T0 karar 51 / T4 v4 A1: tum gunlerin sayaclari kalici kalir.
        self.kaydet()

    def gunluk_ekle(self, e):
        self.veri['gunluk'][e['olay_kimligi']] = {'olay': e, 'durum': 'BEKLIYOR'}
        self.kaydet()

    def gonderim_dongusu(self, depo, baglanti=True):
        if not baglanti: return {'bekle_saniye': 2, 'bekleyen': self.bekleyen_sayisi()}
        for kayit in sorted(self.veri['gunluk'].values(), key=lambda x: (x['olay']['oldugu_an'], x['olay']['olay_kimligi'])):
            if kayit['durum'] != 'BEKLIYOR': continue
            sonuc = depo.olay_ekle(kayit['olay'], oturum=self.kisi)
            kayit['durum'] = 'GONDERILDI' if sonuc['sonuc'] == 'BASARILI' else 'HATA'
            kayit['sonuc'] = sonuc
        self.kaydet()

    def bekleyen_sayisi(self):
        return sum(k['durum'] == 'BEKLIYOR' for k in self.veri['gunluk'].values())

    def gunluk_temizle(self):
        sinir = self.simdi_duzeltilmis() - timedelta(days=30)
        self.veri['gunluk'] = {k: v for k, v in self.veri['gunluk'].items() if v['durum'] != 'GONDERILDI' or an(v['olay']['oldugu_an']) >= sinir}
        self.kaydet()

    def ekran_hali(self, son_hal, isler=None, liste=None):
        d = dict(son_hal)
        if not d.get('son_hesap_ani') or an(d['son_hesap_ani']).date() != self.simdi_duzeltilmis().date(): d = bos_hal()
        bekleyen = sorted([k['olay'] for k in self.veri['gunluk'].values() if k['durum'] == 'BEKLIYOR'], key=lambda e: (an(e['oldugu_an']), e['olay_kimligi']))
        isler, liste = isler or {}, liste or []
        for e in bekleyen:
            if an(e['oldugu_an']).date() != self.simdi_duzeltilmis().date(): continue
            ids = hedefler(e, 'IS')
            is_ = isler.get(ids[0]) if ids else None
            if not ids or is_:
                d, _ = gecis(d, e['eylem_kodu'], is_, isler.get(liste[0]) if liste else None, e['girdiler'].get('neden'))
        return {'son_hal': d, 'bekleyen': bekleyen}

    def tazelik(self, baglanti, son_esitleme):
        return bool(baglanti and son_esitleme and 0 <= (self.simdi_duzeltilmis()-an(son_esitleme)).total_seconds() <= 30)

    def olay_yaz(self, kod, son_hal, isler=None, liste=None, is_kimligi=None, girdiler=None, kanit=None, sabit_mola=False, depo=None, baglanti=True):
        from .kabul import TANIKLIK
        if kod not in TANIKLIK and not self.tazelik(baglanti,son_hal.get('son_hesap_ani')): raise ValueError('Yonetim icin taze baglanti gerekli')
        isler, liste = isler or {}, liste or []
        ekran = self.ekran_hali(son_hal, isler, liste)
        if not kapi(ekran['son_hal'], kod, isler.get(is_kimligi), liste[0] if liste else None, sabit_mola):
            raise ValueError('Cihaz kapisi kapali')
        t = self.simdi_duzeltilmis().isoformat()
        e = {'olay_kimligi': self.olay_kimligi_uret(), 'eylem_kodu': kod, 'eylem_versiyonu': 1, 'neyin_ustunde': [{'tur': 'IS', 'kimlik': is_kimligi, 'surum': None}] if is_kimligi else [], 'giris_sekli': 'LISTE', 'kim': self.kisi, 'adina': None, 'cihaz': ('TEL-' if self.harf in 'TUV' else 'MAS-') + self.kisi, 'uygulama_surumu': 'AND-0.1.0' if self.harf in 'TUV' else 'WEB-0.1.0', 'oldugu_an': t, 'saat_dilimi': '+03:00', 'bildigi_son_hal_ani': son_hal.get('son_hesap_ani', t), 'girdiler': girdiler or {}, 'kanit': kanit or [], 'duzelttigi_olay': None, 'yol': 'DISARIDA', 'pc_ulasma_ani': None}
        if kod in TANIKLIK: self.gunluk_ekle(e)
        else:
            for x in e['neyin_ustunde']: x['surum']=isler.get(x['kimlik'],{}).get('surum',0)
            from .kapilar_v3 import liste_hedefleri
            from .surum import ozet
            # Ekranın gördüğü liste sürümleri; sunucunun güncel sürümünü
            # burada okuyup eski ekranı tazeymiş gibi göstermemelidir.
            for k in liste_hedefleri(e):
                e['neyin_ustunde'].append({'tur':'LISTE','kimlik':k,'surum':son_hal.get('liste_surumleri',{}).get(k,ozet(liste) if k==self.kisi else None)})
            sonuc=depo.olay_ekle(e,oturum=self.kisi) if depo and baglanti else {'sonuc':'BAGLANTI_YOK'}
            self.veri['gunluk'][e['olay_kimligi']]={'olay':e,'durum':'GONDERILDI' if sonuc['sonuc']=='BASARILI' else 'GONDERILEMEDI' if sonuc['sonuc']=='BAGLANTI_YOK' else 'RED','sonuc':sonuc}
            self.kaydet()
        return e


def atama_uyarilari(depo, satirlar):
    from .gorunumler import yuk, kapasite, is_gunleri
    from .saat import gun
    sonuc = []
    for n, satir in enumerate(satirlar, 1):
        teslim = gun(satir['teslim_tarihi'])
        etap = depo.etaplar.get(satir.get('etap'))
        if etap and teslim > gun(etap['bitis']): sonuc.append({'satir': n, 'kural': 'R24', 'metin': 'Teslim etabin bitisini asiyor'})
        bas = teslim - timedelta(days=teslim.weekday()); bit = bas + timedelta(days=6)
        kisi = satir['kisi']
        yeni_yuk = 0.0
        for aday in satirlar:
            if aday['kisi'] != kisi: continue
            gunler = is_gunleri(depo, depo.saat.simdi(), aday['teslim_tarihi'],kisi)
            if gunler: yeni_yuk += aday['zaman_degeri'] * sum(bas <= d <= bit for d in gunler) / len(gunler)
        if yuk(depo, kisi, bas, bit) + yeni_yuk > kapasite(depo, kisi, bas, bit): sonuc.append({'satir': n, 'kural': 'R23', 'metin': 'Teslim haftasi kapasite asiliyor'})
    return sonuc


def sonraki_is_hazirla(depo, kaynak):
    if kaynak in depo.gorevler:
        g = depo.gorevler[kaynak]
        sonuc = {k: g.get(k) for k in ('nereye', 'proje', 'etap', 'parca_kodu')}
        sonuc.update(kaynak=kaynak, on_kosul=[kaynak])
        teslimler = [e for e in depo.olaylar.values() if e['eylem_kodu'] == 'GOREV.TAMAMLADIM' and kaynak in hedefler(e, 'GOREV')]
        sonuc['kanit'] = max(teslimler, key=lambda e: (an(e['oldugu_an']), e['olay_kimligi']))['kanit'] if teslimler else []
        return sonuc
    n = depo.notlar[kaynak]
    return {'kaynak': kaynak, 'neyin_ustunde': n['neyin_ustunde'], 'talimat': n['metin'], 'kanit': n['kanit'], 'sorun_kaynakli': True}
