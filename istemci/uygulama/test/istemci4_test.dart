import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:irp_uygulama/bulut/uygulama_bulutu.dart';
import 'package:irp_uygulama/ekranlar/web/yonetim_formlari.dart';
import 'package:irp_uygulama/ekranlar/web/yonetim.dart' show adBul;

import 'destek.dart';
import 'web_destek.dart';

void main() {
  // Karar 132: ekran başına yalnız bir açılış/okuma duman testi.
  for (final (no, sayfa, okumalar) in [
    (
      15,
      'Görev Atama',
      ['KISILER', 'PROJELER', 'ETAPLAR', 'YUK', 'KAPASITE', 'ATAMA_UYARILARI'],
    ),
    (16, 'Onaylar', ['ONAY_LISTESI', 'DOSYA']),
    (17, 'Projeler', ['PROJE_DURUM', 'ETAP_DURUM', 'ETAPLAR']),
    (
      18,
      'Personel dağılımı',
      [
        'KIM_NEREDE',
        'BIRIM_DOLULUGU',
        'PROJE_DURUM',
        'SAAT_NEREYE_GITTI',
        'PERSONEL_DAGILIMI',
      ],
    ),
    (19, 'Raporlar', ['PROJE_MALIYETI', 'PROJE_ISCILIGI', 'TAHMIN_GERCEK']),
    (20, 'Maaş dağılımı', ['MAAS_DAGILIMI', 'MAAS']),
    (21, 'Adil Performans', ['PERFORMANS']),
    (
      22,
      'Parçalar ve belgeler',
      ['NESNELER', 'TOP_KIMDE', 'GECERLI_SURUM', 'SURUMLER'],
    ),
    (23, 'Gösteri saati', <String>[]),
    (
      24,
      'Yönetim',
      [
        'KISILER',
        'PROJELER',
        'ETAPLAR',
        'BIRIMLER',
        'YONLENDIRME',
        'KODLAR',
        'SUPHELILER',
      ],
    ),
  ]) {
    testWidgets('$no · $sayfa açılır ve doğru okumaları çağırır', (t) async {
      final (d, b) =
          await t.runAsync(
            () => webHazir(kisi: 'K001', an: no == 16 ? 'onay' : '1040'),
          ) ??
          (throw StateError('Kurulum'));
      await webAc(t, d, sayfa);
      if (no == 17) {
        final etaplar = d.satirlar('ETAPLAR', hedef: d.acikProje);
        etaplar.sort(
          (a, b) => t
              .getTopLeft(find.text(adBul(d, 'BIRIMLER', a['ad'])).first)
              .dy
              .compareTo(
                t.getTopLeft(find.text(adBul(d, 'BIRIMLER', b['ad'])).first).dy,
              ),
        );
        for (var i = 1; i < etaplar.length; i++) {
          expect(
            (etaplar[i - 1]['baslangic'] as String).compareTo(
              etaplar[i]['baslangic'],
            ),
            lessThanOrEqualTo(0),
          );
        }
      }
      if (no == 15) {
        await t.enterText(
          find.byKey(const ValueKey('gorev-adi-0')),
          'Çizim kontrolü',
        );
        await t.tap(find.text('Onayla · Özeti gör'));
        await t.pumpAndSettle();
      }
      if (no == 16) {
        await t.tap(find.text('sentetik_kontrol.png'));
        await t.pumpAndSettle();
      }
      for (final v in okumalar) {
        expect(b.cagrilar.any((q) => q['veri'] == v), isTrue, reason: v);
      }
      expect(d.baglanti, isTrue, reason: d.mesaj);
      expect(find.byType(CircularProgressIndicator), findsNothing);
      expect(t.takeException(), isNull);
      await kapatWeb(t);
    });
  }
  final kodlar = [
    ...yonetimBasliklari.keys,
    'GOREV.ATADIM',
    'IS.TANIMLADIM',
    'GOREV.ONAYLADIM',
    'GOREV.REDDETTIM',
    'AYAR.SAAT_KAYDIRDIM',
  ];
  for (final kod in kodlar) {
    test('İstemci 4 şema · $kod', () async {
      final (d, _) = await webHazir(kisi: 'K001');
      final x = {
        'kimlik': 'K001',
        'ad': 'Kemal Aksoy',
        'birim': 'YONETIM',
        'yaka': 'BEYAZ',
        'roller': ['YETKILI'],
        'surum':
            'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
      };
      var form = yonetimVarsayilan(kod, d, '2509084', x);
      if (form['ad'] == '') form['ad'] = 'Sentetik kayıt';
      if (form['kod'] == '') form['kod'] = 'SENTETIK';
      if (form['tutar'] == '') form['tutar'] = '20000';
      Json g;
      if (kod == 'GOREV.ATADIM' || kod == 'IS.TANIMLADIM') {
        g = atamaGirdisi(
          [
            {
              ...yeniGorev(d, '2509084'),
              'ad': 'Sentetik görev',
              'etap': 'ETAP-1',
              'birim': 'IMALAT',
              'olcum': kod == 'IS.TANIMLADIM' ? 'SAAT' : 'ZAMAN',
            },
          ],
          [],
          saat: kod == 'IS.TANIMLADIM',
        );
      } else if (kod == 'GOREV.REDDETTIM') {
        g = {
          'not': 'Ölçü kontrolü',
          'revizyon_ver': true,
          'kime': 'K041',
          'yeni_teslim_tarihi': '2026-10-30',
          'zaman_degeri': 1,
          'sorumlular': [
            {'tur': 'KISI', 'kimlik': 'K041', 'yuzde': 100},
          ],
        };
      } else if (kod == 'AYAR.SAAT_KAYDIRDIM') {
        g = {'hedef': '2026-10-22T11:40:00+03:00'};
      } else {
        g = yonetimGirdisi(kod, form);
      }
      final tur = semalar[kod]['zorunlu_hedef_turu'];
      final e = d.cihaz!.yonetimHazirla(
        kod,
        {'son_hesap_ani': d.cihaz!.simdiDuzeltilmis().isoformat()},
        eylemSemalari: semalar,
        baglanti: true,
        okumaAni: d.cihaz!.simdiDuzeltilmis().isoformat(),
        girdiler: g,
        hedefler: [
          if (tur != null)
            {
              'tur': tur,
              'kimlik': 'HEDEF-1',
              'surum': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
            },
        ],
      );
      olayDogrula(e);
    });
  }
}
