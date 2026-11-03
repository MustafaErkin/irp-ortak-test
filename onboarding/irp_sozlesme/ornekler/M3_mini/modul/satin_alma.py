"""Örnek modül: parçanın siparişini izler. Çekirdeğe yalnızca irp_sozlesme.baglanti ile konuşur.

Gösterdiği kalıplar (sozlesme/02_kurallar.md):
1. Kullanıcının işi = kullanıcının oturumuyla olay (sipariş verildi → parça SIPARISTE).
2. Yönetim kararı okunan sürümü taşır; BAYAT gelirse yeniden okunur, kullanıcıya gösterilir.
3. Modülün kendi verisi (tedarikçi, fiyat, termin) modülün tablosunda; çekirdekte yalnızca parçanın aşaması.
4. Modülün kuralı (termin geçti) olay yazmaz; bildirim bırakır. Kural tekrar tekrar çalışabilir.
"""
from datetime import datetime


class SatinAlma:
    def __init__(self, cekirdek):
        self.cekirdek = cekirdek
        self.siparisler = {}   # gerçek modülde mod_m3.siparisler tablosu

    # ---- kullanıcının işleri (ekrandan gelir; kullanıcının oturumuyla)
    def parca_ac(self, oturum, ad, kod, proje):
        """Parçanın çekirdekteki ana gövdesi. Proje alanı ile proje bağı aynı olmalı (karar 107)."""
        cevap = oturum.olay_gonder('NESNE.ACTIM', {
            'tur': 'PARCA', 'ad': ad, 'kod': kod, 'proje': proje, 'sorumlu': oturum.kisi,
            'baglar': [{'tur': 'PROJE', 'kimlik': proje}]})
        return cevap['olay_kimligi'] if cevap.basarili else None, cevap

    def siparis_ver(self, oturum, parca, tedarikci, birim_fiyat, termin):
        """Ekran parçayı okumuştu; karar o okumanın sürümüne dayanır."""
        okunan = oturum.oku('NESNE', parca).deger
        cevap = oturum.olay_gonder(
            'NESNE.ASAMA_GECIRDIM',
            {'hedef': parca, 'yeni_asama': 'SIPARISTE', 'gerekce': f'{tedarikci} siparişi'},
            neyin_ustunde=[oturum.hedef('NESNE', okunan)])
        if cevap.bayat:
            # Parça bu arada değişmiş: kullanıcıya güncel hali gösterilir, karar yeniden sorulur.
            return {'durum': 'YENIDEN_SOR', 'guncel': cevap.get('guncel')}
        if not cevap.basarili:
            return {'durum': 'RED', 'kod': cevap.kod, 'neden': cevap.get('neden')}
        self.siparisler[parca] = {'tedarikci': tedarikci, 'birim_fiyat': birim_fiyat, 'termin': termin}
        return {'durum': 'TAMAM'}

    # ---- modülün kuralı (zamanlanmış iş; servis gözüyle)
    def gecikenleri_bildir(self):
        """Termini geçmiş ve hâlâ SIPARISTE olan parçalar için bildirim; gelmişse bildirimi kaldırır.
        Bırakma ve kaldırma tekrar güvenlidir; iş her çalıştığında aynı sonuca varır (K-9)."""
        servis = self.cekirdek.servis()
        simdi = datetime.fromisoformat(self.cekirdek.simdi())
        sonuc = {'birakilan': 0, 'kaldirilan': 0}
        for parca, s in self.siparisler.items():
            asama = servis.oku('NESNE', parca).deger['asama']
            kayit = {'tur': 'NESNE', 'kimlik': parca, 'modul_kaydi': f'sipariş {s["tedarikci"]}'}
            if asama == 'SIPARISTE' and datetime.fromisoformat(s['termin']) < simdi:
                servis.bildirim_birak('SIPARIS_GECIKTI', kayit,
                                      [{'tur': 'NESNE_SORUMLUSU', 'kimlik': parca},
                                       {'tur': 'BIRIM_YONETICILERI', 'kimlik': 'PLANLAMA'}],
                                      f'{s["tedarikci"]} siparişinin termini geçti ({s["termin"][:10]})', 'UYARI')
                sonuc['birakilan'] += 1
            elif asama != 'SIPARISTE':
                if servis.bildirim_kaldir('SIPARIS_GECIKTI', kayit).get('kaldirilan'):
                    sonuc['kaldirilan'] += 1
        return sonuc
