// Web ekran görüntüsü değildir: Flutter test motorunun 390×844 yerel çıktısı.
// Çalıştırma: flutter test tool/ekran_cikti.dart
import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:irp_uygulama/main.dart';
import 'package:irp_uygulama/ekranlar/telefon/not_ekle.dart';
import 'package:irp_uygulama/ekranlar/telefon/qr_cizim.dart';

import '../test/destek.dart';

void main() {
  testWidgets('telefon ekranlarının yerel görsel çıktıları', (t) async {
    t.view.physicalSize = const Size(390, 844);
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.resetPhysicalSize);
    addTearDown(t.view.resetDevicePixelRatio);
    final font = FontLoader('IRP')
      ..addFont(rootBundle.load('assets/fontlar/roboto-regular.ttf'))
      ..addFont(rootBundle.load('assets/fontlar/roboto-bold.ttf'));
    await font.load();
    await (FontLoader(
      'MaterialIcons',
    )..addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf'))).load();
    final cikti = Directory('../../codex/sonuclar/istemci2_ekranlar');
    await t.runAsync(() => cikti.create(recursive: true));
    final sinir = GlobalKey();
    Future<void> kaydet(String ad) async {
      await t.pumpAndSettle();
      expect(t.takeException(), isNull);
      final boundary =
          sinir.currentContext!.findRenderObject()! as RenderRepaintBoundary;
      await t.runAsync(() async {
        final image = await boundary.toImage(pixelRatio: 1);
        final veri = await image.toByteData(format: ui.ImageByteFormat.png);
        await File('${cikti.path}/${ad}_widget.png')
            .writeAsBytes(veri!.buffer.asUint8List());
        image.dispose();
      });
    }

    Future<void> bas(String metin) async {
      final finder = find.text(metin).last;
      await t.ensureVisible(finder);
      await t.tap(finder);
      await t.pumpAndSettle();
    }

    for (final ad in [
      'kayit',
      'giris',
      'hazir',
      'calisiyor',
      'molada',
      'durus',
      'devam_izinli',
      'onay',
      'ret',
      'kilitli',
      'sabit_mola',
      'devam_bekliyor',
      'bos_liste',
      'anlik',
    ]) {
      final (d, _, _) =
          await t.runAsync(
            () => hazir(
              durum: ['kayit', 'giris'].contains(ad) ? 'calisiyor' : ad,
            ),
          ) ??
          (throw StateError('Kurulum'));
      if (ad == 'kayit') {
        d.acik = false;
        d.yerel.remove('kayit');
        d.cihaz = null;
      }
      if (ad == 'giris') d.acik = false;
      await t.pumpWidget(
        RepaintBoundary(
          key: sinir,
          child: IrpApp(
            key: ValueKey(ad),
            durum: d,
            cizimler: harita,
            donanim: false,
          ),
        ),
      );
      await kaydet(ad);
      if (ad == 'calisiyor') {
        t.platformDispatcher.platformBrightnessTestValue = Brightness.dark;
        await kaydet('calisiyor_koyu');
        t.platformDispatcher.clearPlatformBrightnessTestValue();
        await t.pumpAndSettle();
        await bas('Günün işleri (1)');
        await kaydet('gunun_isleri');
        await bas('KAPAT');
        await bas('MOLA');
        await bas('Sigara');
        await kaydet('mola_penceresi');
        await bas('VAZGEÇ');
        await bas('DURUŞ');
        await bas('Makine');
        await bas('Kaynak');
        await t.enterText(
          find.byType(TextField),
          'Kaynak makinesi akım vermiyor',
        );
        await kaydet('durus_penceresi');
        await bas('VAZGEÇ');
        await bas('TAMAMLA');
        await kaydet('tamamlama_onayi');
        await bas('VAZGEÇ');
        await t.tap(find.byTooltip('Menü'));
        await t.pumpAndSettle();
        await kaydet('menu');
        await bas('Not ekle');
        expect(find.byType(NotEkle), findsOneWidget);
        await t.enterText(
          find.widgetWithText(TextField, 'Notun'),
          'Çizimdeki ölçüyü kontrol edebilir misiniz?',
        );
        await kaydet('not_ekle');
        await t.pageBack();
        await t.pumpAndSettle();
        await bas('QR');
        expect(find.byType(QrCizim), findsOneWidget);
        await kaydet('qr');
        await t.runAsync(
          () => precacheImage(
            AssetImage(harita['IRP:NESNE:SENTETIK-1']!),
            t.element(find.byType(QrCizim)),
          ),
        );
        await t.enterText(find.byType(TextField), 'IRP:NESNE:SENTETIK-1');
        await bas('ÇİZİMİ AÇ');
        await kaydet('cizim');
      }
      await t.pumpWidget(const SizedBox());
      await t.pump();
    }
  });
}
