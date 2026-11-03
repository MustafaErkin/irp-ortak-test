import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:irp_cekirdek/irp_cekirdek.dart';
import 'package:irp_uygulama/bulut/gosteri_kisisi.dart';
import 'package:irp_uygulama/durum/kalici_depo.dart';
import 'package:irp_uygulama/durum/uygulama_durumu.dart';
import 'package:irp_uygulama/ekranlar/web/web.dart';
import 'package:irp_uygulama/ekranlar/telefon/ortak.dart';
import 'package:irp_uygulama/sahte/fikstur_bulutu.dart';

import 'destek.dart';
import 'web_destek.dart';

void main() => istemci8Test();

void istemci8Test({bool ekran = false}) {
  testWidgets('Olay akışı: menü, ilk liste, canlı ekleme, süzgeç ve ayrıntı', (
    t,
  ) async {
    t.view.physicalSize = const Size(1280, 800);
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.resetPhysicalSize);
    addTearDown(t.view.resetDevicePixelRatio);
    final anahtar = GlobalKey();
    if (ekran) {
      await (FontLoader('IRP')
            ..addFont(rootBundle.load('assets/fontlar/roboto-regular.ttf'))
            ..addFont(rootBundle.load('assets/fontlar/roboto-bold.ttf')))
          .load();
      await (FontLoader(
        'MaterialIcons',
      )..addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf'))).load();
    }
    Future<void> goruntu(String ad) async {
      if (!ekran) return;
      void boya(RenderObject nesne) {
        nesne.markNeedsPaint();
        nesne.visitChildren(boya);
      }

      boya(anahtar.currentContext!.findRenderObject()!);
      await t.pump();
      await t.runAsync(() async {
        final sinir =
            anahtar.currentContext!.findRenderObject() as RenderRepaintBoundary;
        final im = await sinir.toImage();
        expect((im.width, im.height), (1280, 800));
        final veri = await im.toByteData(format: ui.ImageByteFormat.png);
        final yol = Directory('../../codex/sonuclar/istemci8_ekranlar');
        await yol.create(recursive: true);
        await File('${yol.path}/$ad.png')
            .writeAsBytes(veri!.buffer.asUint8List());
        im.dispose();
      });
    }

    final (normal, _) =
        await t.runAsync(() => webHazir()) ?? (throw StateError('Kurulum'));
    await webAc(t, normal, 'Takip');
    expect(find.byKey(const Key('menu-Olay akışı')), findsNothing);
    await kapatWeb(t);
    final b = FiksturBulutu(
      fikstur,
      webFikstur: birlestirFikstur(
        dosya('test/fikstur/web.json'),
        dosya('test/fikstur/yonetim.json'),
      ),
    );
    final d =
        await t.runAsync(() async {
          final d = UygulamaDurumu(
            bulut: b,
            depo: BellekKaliciDepo(),
            semalar: semalar,
            saat: Saat('2026-10-30T10:20:00+03:00'),
            gosteriKisileri: const [
              GosteriKisisi(
                etiket: 'İmalat Ekip Lideri',
                kod: 'K009',
                sifre: '123456',
                yer: 'web',
              ),
            ],
          );
          await d.yukle();
          return d;
        }) ??
        (throw StateError('Kurulum'));
    addTearDown(() async {
      d.dispose();
      await b.dispose();
    });

    b.akisOlaylari[0]['eylem'] = 'MESAI.GIRDIM';
    b.akisOlaylari[1]['eylem'] = 'BILINMEYEN.KOD';
    d.acik = true;
    await t.pumpWidget(
      RepaintBoundary(
        key: anahtar,
        child: MaterialApp(
          debugShowCheckedModeBanner: false,
          theme: tema(Brightness.light),
          home: WebEkrani(durum: d, ilkSayfa: 'Olay akışı'),
        ),
      ),
    );
    await t.pumpAndSettle();
    expect(find.byKey(const Key('menu-Olay akışı')), findsOneWidget);
    expect(find.byKey(const ValueKey('olay-3')), findsOneWidget);
    expect(find.text('Mesaiye girdi'), findsOneWidget);
    expect(find.text('BILINMEYEN.KOD'), findsOneWidget);
    expect(find.text('20 CNC Torna · 2509084_02_02-01'), findsNWidgets(3));
    b.akisOlaylari.add({
      ...b.akisOlaylari.first,
      'sira': 4,
      'eylem': 'IS.ATADIM',
      'olay': 'K017-yeni',
      'girdiler': {'kisi': 'K017'},
      'kisi_ad': 'Atölye Çalışanı 1',
      'hedef_etiket': 'Örnek parça',
      'cihaz': 'MAS-K009',
    });
    await t.pump(const Duration(seconds: 3));
    await t.pumpAndSettle();
    expect(find.byKey(const ValueKey('olay-4')), findsOneWidget);
    expect(
      t.getTopLeft(find.byKey(const ValueKey('olay-4'))).dy,
      lessThan(t.getTopLeft(find.byKey(const ValueKey('olay-3'))).dy),
    );
    await goruntu('01_olay_akisi');
    await t.tap(find.text('Yalnız telefon'));
    await t.pumpAndSettle();
    expect(find.byKey(const ValueKey('olay-4')), findsNothing);
    expect(find.byKey(const ValueKey('olay-2')), findsNothing);
    expect(find.byKey(const ValueKey('olay-3')), findsOneWidget);
    await t.tap(find.text('Yalnız telefon'));
    await t.pumpAndSettle();
    await t.tap(find.text('İş atadı → Atölye Çalışanı 1'));
    await t.pumpAndSettle();
    expect(find.textContaining('K017-yeni'), findsOneWidget);
    expect(
      find.textContaining('"kisi_ad": "Atölye Çalışanı 1"'),
      findsOneWidget,
    );
    expect(
      find.textContaining('"hedef_etiket": "Örnek parça"'),
      findsOneWidget,
    );
    await goruntu('02_ayrinti');
    await t.ensureVisible(find.text('Durdur'));
    await t.tap(find.text('Durdur'));
    await t.pumpAndSettle();
    b.akisOlaylari.add({...b.akisOlaylari.first, 'sira': 5});
    await t.pump(const Duration(seconds: 3));
    expect(find.byKey(const ValueKey('olay-5')), findsNothing);
    await t.tap(find.text('Sürdür'));
    await t.pumpAndSettle();
    expect(find.byKey(const ValueKey('olay-5')), findsOneWidget);
    b.cevrimici = false;
    await t.pump(const Duration(seconds: 3));
    await t.pumpAndSettle();
    expect(find.text('Bağlantı yok · Liste korunuyor'), findsOneWidget);
    expect(find.byKey(const ValueKey('olay-5')), findsOneWidget);
    await kapatWeb(t);
  });
}
