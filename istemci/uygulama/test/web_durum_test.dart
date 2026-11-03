import 'dart:convert';
import 'dart:async';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:desktop_drop/desktop_drop.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:irp_cekirdek/irp_cekirdek.dart';
import 'package:irp_uygulama/bulut/uygulama_bulutu.dart';
import 'package:irp_uygulama/durum/uygulama_durumu.dart';
import 'package:irp_uygulama/ekranlar/telefon/ortak.dart';
import 'package:irp_uygulama/ekranlar/web/teslim.dart';
import 'package:irp_uygulama/ekranlar/web/web.dart';

import 'web_destek.dart';

void main() {
  test(
    'Mavi yaka web ekranı birim rolü gerektirmeden sinyalle yenilenir',
    () async {
      final (d, b) = await webHazir(kisi: 'K041');
      final an = b.webFikstur!['anlar'][b.webAni]['K041']['okumalar'] as List;
      final kisiler =
          an.firstWhere((q) => q['veri'] == 'KISILER')['cevap']['deger']
              as List;
      final kisi = kisiler.firstWhere((k) => k['kimlik'] == 'K041');
      kisi['yaka'] = 'MAVI';
      kisi['roller'] = <String>[];
      an.add({
        'veri': 'LISTE',
        'hedef': 'K041',
        'g': null,
        'cevap': {
          'deger': {'isler': []},
          'hesap': 1,
          'hesap_ani': '2026-10-22T10:40:00+03:00',
        },
      });
      await d.yenile();
      await d.ekranOku([const Okuma('GOREV'), const Okuma('GUN_ISLERI')]);
      expect(d.webDuzeni, isFalse);
      expect(
        d.satirlar('GOREV').any((g) => g['ad'] == 'Sinyalle gelen görev'),
        isFalse,
      );
      final gorev = b.webOkumalar.firstWhere((q) => q['veri'] == 'GOREV');
      // Fikstür kopyaları yerine sunucunun kaynağı değişir; istemci yalnız sinyali alır.
      final kaynak = an.firstWhere((q) => q['veri'] == 'GOREV');
      kaynak['cevap'] = {
        ...gorev['cevap'],
        'deger': [
          {
            'kimlik': 'SINYAL-GOREV',
            'ad': 'Sinyalle gelen görev',
            'durum': 'ATANDI',
          },
        ],
      };
      b.sinyalVer('kisi:K041');
      await Future<void>.delayed(const Duration(milliseconds: 400));
      expect(
        d.satirlar('GOREV').any((g) => g['ad'] == 'Sinyalle gelen görev'),
        isTrue,
        reason: d.mesaj,
      );
    },
  );

  testWidgets('Açık yönetim formunda veri yaşlanınca Kaydet kapanır', (
    t,
  ) async {
    final (d, _) =
        await t.runAsync(() => webHazir(an: 'onay')) ??
        (throw StateError('Kurulum'));
    await webAc(t, d, 'Onaylar');
    await dokun(t, find.widgetWithText(FilledButton, 'Reddet').first);
    final saat = d.saat as Saat;
    saat.ilerlet(saat.simdi().ekle(const Duration(seconds: 31)));
    await t.pump(const Duration(seconds: 1));
    expect(
      t
          .widget<FilledButton>(find.widgetWithText(FilledButton, 'Kaydet'))
          .onPressed,
      isNull,
    );
    expect(d.gunluk, isEmpty);
    await dokun(t, find.text('Vazgeç'));
    await kapatWeb(t);
  });
  test(
    'Tek görev isteyen teslim iki hedefi kimlik üretmeden reddeder',
    () async {
      final (d, _) = await webHazir(kisi: 'K041');
      await expectLater(
        d.olay(
          'GOREV.TAMAMLADIM',
          hedefler: [
            {'tur': 'GOREV', 'kimlik': 'G1', 'surum': null},
            {'tur': 'GOREV', 'kimlik': 'G2', 'surum': null},
          ],
        ),
        throwsArgumentError,
      );
      expect(d.gunluk, isEmpty);
    },
  );
  test(
    'Yönetim zaman aşımında aynı kimlik ve içerikle yalnız bir kez yinelenir',
    () async {
      final (d, b) = await webHazir(an: 'atama');
      await d.ekranOku([
        Okuma('HAVUZ', hedef: d.birim),
        const Okuma('LISTE', hedef: 'K017'),
      ]);
      final i = d.satirlar('HAVUZ', hedef: d.birim).first;
      b.zamanAsimiAdedi = 1;
      await d.yonetim(
        'IS.ATADIM',
        girdiler: {'kisi': 'K017', 'sira': 2},
        hedefler: [hedef(i)],
      );
      expect(b.olaylar.length, 2);
      expect(b.olaylar[0], b.olaylar[1]);
      expect(d.gunluk.single['durum'], 'GONDERILDI');
      expect(d.bekleyen, 0);
    },
  );
  test(
    'İki zaman aşımı GONDERILEMEDI; tanıklık kuyruğu yönetimi tekrar göndermez',
    () async {
      final (d, b) = await webHazir(an: 'atama');
      await d.ekranOku([
        Okuma('HAVUZ', hedef: d.birim),
        const Okuma('LISTE', hedef: 'K017'),
      ]);
      b.zamanAsimiAdedi = 2;
      await d.yonetim(
        'IS.ATADIM',
        girdiler: {'kisi': 'K017', 'sira': 2},
        hedefler: [hedef(d.satirlar('HAVUZ', hedef: d.birim).first)],
      );
      expect(d.gunluk.single['durum'], 'GONDERILEMEDI');
      expect(d.bekleyen, 0);
      expect(b.olaylar.length, 2);
      await d.gonderici.tetikle();
      expect(b.olaylar.length, 2);
    },
  );
  test(
    'Lider birim sinyalini dinler; başka birim yenilemez; sinyaller birleşir',
    () async {
      final (d, b) = await webHazir();
      await d.ekranOku([Okuma('EKIP', hedef: d.birim)]);
      expect(
        b.cagrilar.where((x) => x['kapi'] == 'sinyaller').last['kanallar'],
        containsAll(['kisi:K009', 'firma', 'birim:IMALAT']),
      );
      var n = b.cagrilar.where((x) => x['veri'] == 'EKIP').length;
      b.sinyalVer('birim:IZINSIZ');
      await Future<void>.delayed(const Duration(milliseconds: 350));
      expect(b.cagrilar.where((x) => x['veri'] == 'EKIP').length, n);
      final yenilendi = Completer<void>();
      void kontrol() {
        if (b.cagrilar.where((x) => x['veri'] == 'EKIP').length == n + 1 &&
            !yenilendi.isCompleted) {
          yenilendi.complete();
        }
      }

      d.addListener(kontrol);
      b.sinyalVer('birim:IMALAT');
      b.sinyalVer('firma');
      b.sinyalVer('kisi:K009');
      await yenilendi.future.timeout(const Duration(seconds: 5));
      d.removeListener(kontrol);
      expect(b.cagrilar.where((x) => x['veri'] == 'EKIP').length, n + 1);
    },
  );
  test('Beyaz yaka başkasının görevünü ve performansını okuyamaz', () async {
    final (_, b) = await webHazir(kisi: 'K041');
    await expectLater(b.oku('GOREV', hedef: 'K017'), throwsStateError);
    await expectLater(b.oku('PERFORMANS', hedef: 'K017'), throwsStateError);
  });
  test('Çevrimdışı veya nesne sürümü eksik yönetim zarfı üretilmez', () async {
    final (d, b) = await webHazir(an: 'atama');
    await d.ekranOku([
      Okuma('HAVUZ', hedef: d.birim),
      const Okuma('LISTE', hedef: 'K017'),
    ]);
    final h = hedef(d.satirlar('HAVUZ', hedef: d.birim).first);
    d.baglanti = false;
    await expectLater(
      d.yonetim(
        'IS.ATADIM',
        girdiler: {'kisi': 'K017', 'sira': 1},
        hedefler: [h],
      ),
      throwsStateError,
    );
    d.baglanti = true;
    h['surum'] = null;
    await expectLater(
      d.yonetim(
        'IS.ATADIM',
        girdiler: {'kisi': 'K017', 'sira': 1},
        hedefler: [h],
      ),
      throwsA(isA<ModelHatasi>()),
    );
    expect(d.gunluk, isEmpty);
    expect(b.olaylar, isEmpty);
  });
  testWidgets(
    'Geç teslim dosyasız ve nedensiz kapanmaz; sürüklenen dosya kuyruğa girer',
    (t) async {
      final (d, b) =
          await t.runAsync(() => webHazir(kisi: 'K041')) ??
          (throw StateError('Kurulum'));
      await t.runAsync(() => d.ekranOku([const Okuma('GOREV')]));
      final g = {
        ...d.satirlar('GOREV').firstWhere((g) => g['durum'] == 'ACIK'),
        'dosya_gerekli': true,
        'son_teslim_ani': '2026-10-21T18:00:00+03:00',
      };
      var tamam = false;
      t.view.physicalSize = const Size(800, 1000);
      t.view.devicePixelRatio = 1;
      addTearDown(t.view.resetPhysicalSize);
      addTearDown(t.view.resetDevicePixelRatio);
      await t.pumpWidget(
        MaterialApp(
          theme: tema(Brightness.light),
          home: Scaffold(
            body: SingleChildScrollView(
              child: TeslimForm(durum: d, gorev: g, tamam: () => tamam = true),
            ),
          ),
        ),
      );
      await dokun(t, find.byKey(const Key('teslim-gonder')));
      expect(find.text('Teslim için dosya ekle'), findsOneWidget);
      expect(d.gunluk, isEmpty);
      final bytes = Uint8List.fromList(
        utf8.encode('Sentetik teknik belge\nOlcu: 52 mm\n'),
      );
      final drop = t.widget<DropTarget>(find.byType(DropTarget));
      await t.runAsync(() async {
        drop.onDragDone!(
          DropDoneDetails(
            files: [DropItemFile.fromData(bytes, name: 'kontrol.txt')],
            localPosition: Offset.zero,
            globalPosition: Offset.zero,
          ),
        );
        await Future<void>.delayed(const Duration(milliseconds: 50));
      });
      await t.pumpAndSettle();
      await dokun(t, find.byKey(const Key('teslim-gonder')));
      expect(find.text('Gecikme nedeni ve açıklaması gerekli'), findsOneWidget);
      await dokun(t, find.byKey(const Key('gecikme-nedeni')));
      await dokun(t, find.textContaining('Kendi').last);
      await t.enterText(
        find.byKey(const Key('teslim-aciklama')),
        'Ölçü kontrolü uzadı',
      );
      b.cevrimici = false;
      d.baglanti = false;
      await dokun(t, find.byKey(const Key('teslim-gonder')));
      expect(tamam, isTrue);
      expect(d.bekleyen, 1);
      final e = Json.from(d.gunluk.single['olay']);
      expect(e['eylem_kodu'], 'GOREV.TAMAMLADIM');
      expect(e['girdiler']['gecikme_nedeni'], 'DURUS_NEDENI.CALISAN_KENDI');
      expect(e['kanit'][0]['parmak_izi'], sha256.convert(bytes).toString());
      expect(d.yuklemeler.length, 1);
      b.cevrimici = true;
      await t.runAsync(d.gonderici.tetikle);
      await t.pumpAndSettle();
      expect(d.yuklemeler, isEmpty);
      expect(b.dosyalar.values.single, bytes);
      expect(
        b.cagrilar.indexWhere((x) => x['kapi'] == 'olay_ekle'),
        lessThan(b.cagrilar.indexWhere((x) => x['kapi'] == 'kanit_yukle')),
      );
      await kapatWeb(t);
    },
  );
  testWidgets('Plansız proje dışı iş PD kodlarını kullanır', (t) async {
    final (d, _) =
        await t.runAsync(() => webHazir()) ?? (throw StateError('Kurulum'));
    await webAc(t, d, 'Plansız iş');
    await t.enterText(find.byKey(const Key('plansiz-ad')), 'Atölye düzeni');
    await dokun(t, find.text('Proje dışı'));
    await dokun(t, find.text('Tanımla ve sıraya koy'));
    expect(d.gunluk.last['olay']['girdiler']['nereye'], 'PROJE_DISI');
    expect(d.gunluk.last['olay']['girdiler']['kategori'], startsWith('PD.'));
    await kapatWeb(t);
  });
}
