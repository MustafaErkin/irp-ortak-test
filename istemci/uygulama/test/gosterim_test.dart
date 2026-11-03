import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:irp_uygulama/ekranlar/web/yonetim.dart';
import 'package:irp_uygulama/ekranlar/web/web.dart';
import 'package:irp_uygulama/main.dart';

import 'destek.dart' show dosya;

void main() => gosterimTest();

void gosterimTest({
  bool ekran = false,
  String ekranKlasoru = 'istemci5_ekranlar',
}) {
  testWidgets('Gösterim: dört salt okunur ekran ve hikâyenin maliyet toplamı', (
    t,
  ) async {
    t.view.physicalSize = const Size(1280, 800);
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.resetPhysicalSize);
    addTearDown(t.view.resetDevicePixelRatio);
    if (ekran) {
      await (FontLoader('IRP')
            ..addFont(rootBundle.load('assets/fontlar/roboto-regular.ttf'))
            ..addFont(rootBundle.load('assets/fontlar/roboto-bold.ttf')))
          .load();
      await (FontLoader(
        'MaterialIcons',
      )..addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf'))).load();
    }
    // Bulut ayarı verilse bile gösterim önce seçilir, bir SDK oluşturulmaz.
    final d = await uygulamayiHazirla(
      kip: 'GOSTERIM',
      bulutAdi: 'SUPABASE',
      adres: 'kullanilmaz',
      anon: 'kullanilmaz',
      jsonYukle: (yol) async => dosya(yol),
    );
    addTearDown(d.dispose);
    final key = GlobalKey();
    await t.pumpWidget(
      RepaintBoundary(
        key: key,
        child: IrpApp(durum: d, cizimler: const {}, donanim: false),
      ),
    );
    Future<void> kontrol(String ad) async {
      await t.pump();
      await t.pumpAndSettle();
      expect(t.takeException(), isNull);
      expect(find.text('Örnek veri'), findsOneWidget);
      expect(find.byType(Chip), findsNothing);
      final etiket = find
          .ancestor(
            of: find.text('Örnek veri'),
            matching: find.byType(DecoratedBox),
          )
          .first;
      expect(t.getSize(etiket).height, lessThanOrEqualTo(28));
      expect(find.text('15 Aralık 2026'), findsWidgets);
      expect(find.textContaining('Veri eksik'), findsNothing);
      expect(find.byType(YonetimDugmesi), findsNothing);
      expect(find.byType(FilledButton), findsNothing);
      expect(find.text('Gösteri saati'), findsNothing);
      expect(find.text('Görev Atama'), findsNothing);
      expect(d.baglanti, isTrue, reason: d.mesaj);
      if (ekran) {
        await t.runAsync(() async {
          final klasor = Directory('../../codex/sonuclar/$ekranKlasoru');
          await klasor.create(recursive: true);
          final im =
              await (key.currentContext!.findRenderObject()
                      as RenderRepaintBoundary)
                  .toImage(pixelRatio: 1);
          final bytes = await im.toByteData(format: ui.ImageByteFormat.png);
          await File('${klasor.path}/$ad.png')
              .writeAsBytes(bytes!.buffer.asUint8List());
          im.dispose();
        });
      }
    }

    await kontrol('17_projeler');
    const etaplar = [
      'Planlama',
      'Mekanik Tasarım',
      'Otomasyon Tasarım',
      'İmalat',
      'Mekatronik Montaj',
      'Kurulum ve Devreye Alma',
    ];
    for (var i = 1; i < etaplar.length; i++) {
      expect(
        t.getTopLeft(find.text(etaplar[i - 1])).dy,
        lessThan(t.getTopLeft(find.text(etaplar[i])).dy),
      );
    }
    expect(find.text('Rulman Çakma Presi'), findsWidgets);
    expect(d.kisi, 'K001');
    expect(d.cihaz, isNull);
    await expectLater(d.olay('NOT.YAZDIM'), throwsStateError);
    await expectLater(d.yonetim('IS.ATADIM'), throwsStateError);
    final hikaye = dosya('../../plan/gosterim/hikaye.json');
    await t.tap(find.text('Raporlar').first);
    await kontrol('19_rulman');
    final toplam = hikaye['projeler'][0]['ozet']['maliyet_toplam'];
    expect(find.text('Proje toplamı · ${para(toplam)}'), findsOneWidget);
    await t.tap(find.byType(DropdownButtonFormField<String>).first);
    await t.pumpAndSettle();
    await t.tap(find.text('Numune Test Fikstürü').last);
    await kontrol('19_numune');
    expect(
      find.text(
        'Proje toplamı · ${para(hikaye['projeler'][1]['ozet']['maliyet_toplam'])}',
      ),
      findsOneWidget,
    );
    await t.tap(find.text('Personel dağılımı').first);
    await kontrol('18_personel');
    expect(find.textContaining('3.528 sa'), findsOneWidget);
    expect(find.text('Sürekli'), findsOneWidget);
    await t.tap(find.text('Adil Performans').first);
    await kontrol('21_performans');
    expect(d.gunluk, isEmpty);
    await t.pumpWidget(const SizedBox());
  });
}
