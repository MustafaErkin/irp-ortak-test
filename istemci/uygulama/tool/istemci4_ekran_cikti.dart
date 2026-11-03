// Flutter test motoru çıktıları: masaüstü 1280×800; telefon 390×844.
import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:irp_cekirdek/irp_cekirdek.dart';
import 'package:irp_uygulama/ekranlar/telefon/ortak.dart';
import 'package:irp_uygulama/ekranlar/web/web.dart';
import 'package:irp_uygulama/ekranlar/web/teslim.dart';
import 'package:irp_uygulama/main.dart';
import 'package:irp_uygulama/durum/uygulama_durumu.dart';

import '../test/destek.dart';
import '../test/web_destek.dart';

void main() {
  testWidgets('İstemci 4 ekranlarının görsel çıktıları', (t) async {
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.resetDevicePixelRatio);
    addTearDown(t.view.resetPhysicalSize);
    await (FontLoader('IRP')
          ..addFont(rootBundle.load('assets/fontlar/roboto-regular.ttf'))
          ..addFont(rootBundle.load('assets/fontlar/roboto-bold.ttf')))
        .load();
    await (FontLoader(
      'MaterialIcons',
    )..addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf'))).load();
    final klasor = Directory('../../codex/sonuclar/istemci4_ekranlar');
    await t.runAsync(() => klasor.create(recursive: true));
    final key = GlobalKey();
    Future<void> kaydet(String ad) async {
      await t.pumpAndSettle();
      expect(t.takeException(), isNull);
      await t.runAsync(() async {
        final b =
            key.currentContext!.findRenderObject() as RenderRepaintBoundary;
        final im = await b.toImage(pixelRatio: 1);
        final bytes = await im.toByteData(format: ui.ImageByteFormat.png);
        await File('${klasor.path}/$ad.png')
            .writeAsBytes(bytes!.buffer.asUint8List());
        im.dispose();
      });
    }

    for (final (no, sayfa, kisi, an) in [
      ('15', 'Görev Atama', 'K004', 'onay'),
      ('16', 'Onaylar', 'K004', 'onay'),
      ('17', 'Projeler', 'K001', 'ay_sonu'),
      ('18', 'Personel dağılımı', 'K001', 'ay_sonu'),
      ('19', 'Raporlar', 'K001', 'ay_sonu'),
      ('20', 'Maaş dağılımı', 'K001', 'ay_sonu'),
      ('21', 'Adil Performans', 'K001', 'ay_sonu'),
      ('22', 'Parçalar ve belgeler', 'K001', '1040'),
      ('23', 'Gösteri saati', 'K001', '1040'),
      ('24', 'Yönetim', 'K001', '1040'),
      ('07', 'İş Ataması', 'K009', 'atama'),
      ('08', 'Plansız iş', 'K009', '1040'),
      ('09', 'Onaylar', 'K009', 'onay'),
      ('10', 'Takip', 'K009', '1320'),
      ('10_yetkili', 'Takip', 'K001', '1320'),
      ('11', 'Kişinin günü', 'K009', '1040'),
      ('12', 'Gün sonu onayı', 'K009', 'gun_sonu'),
      ('13', 'İşlerim', 'K041', 'gorevler'),
      ('14', 'Benim performansım', 'K041', '1515'),
      ('bildirimler', 'Bildirimler', 'K041', '1040'),
    ]) {
      final (d, _) =
          await t.runAsync(() => webHazir(kisi: kisi, an: an)) ??
          (throw StateError('Kurulum'));
      t.view.physicalSize = const Size(1280, 800);
      await t.pumpWidget(
        RepaintBoundary(
          key: key,
          child: MaterialApp(
            debugShowCheckedModeBanner: false,
            theme: tema(Brightness.light),
            darkTheme: tema(Brightness.dark),
            home: WebEkrani(durum: d, ilkSayfa: sayfa),
          ),
        ),
      );
      await t.runAsync(() async {
        await Future<void>.delayed(const Duration(milliseconds: 70));
      });
      if (no == '08') {
        await t.pumpAndSettle();
        await t.enterText(
          find.byKey(const Key('plansiz-ad')),
          'Kaynak çatlağı tamiri',
        );
      }
      if (no == '15') {
        await t.pumpAndSettle();
        await t.enterText(
          find.byKey(const ValueKey('gorev-adi-0')),
          'Teknik resim son kontrolü',
        );
        await t.tap(find.text('Onayla · Özeti gör'));
        await kaydet('15_ozet');
        await t.tap(find.text('Geri dön'));
      }
      if (no == '22') {
        await t.pumpAndSettle();
        await t.tap(find.text('T10 montaj resmi'));
      }
      await kaydet('${no}_web');
      if (no == '18') {
        t.view.physicalSize = const Size(390, 844);
        await kaydet('18_dar');
      }
      if (no == '22') {
        await t.tap(find.byType(DropdownButtonFormField<String>).first);
        await t.pumpAndSettle();
        await t.tap(find.text('2614 · Belge örneği').last);
        await t.pumpAndSettle();
        await t.tap(find.text('2614_02_003 teknik resmi'));
        await kaydet('22_modul3');
      }
      if (no == '19') {
        await t.ensureVisible(find.text('Tahmin ile gerçek'));
        await kaydet('19_tahmin');
      }
      if (no == '23') {
        await t.tap(find.text('+15 dk'));
        await t.pumpAndSettle();
        await t.pump(const Duration(seconds: 5));
        await kaydet('23_ilerletildi');
      }
      if (no == '24') {
        await t.tap(find.text('Etap tanımlama'));
        await t.pumpAndSettle();
        await t.enterText(
          find.byWidgetPredicate(
            (w) => w is TextFormField && w.initialValue == '',
          ),
          'Son kontrol',
        );
        await kaydet('24_etap');
      }
      if (no == '10') {
        t.platformDispatcher.platformBrightnessTestValue = Brightness.dark;
        await t.pumpAndSettle();
        await kaydet('10_web_koyu');
        t.platformDispatcher.clearPlatformBrightnessTestValue();
        await t.pumpAndSettle();
        t.view.physicalSize = const Size(390, 844);
        await kaydet('10_takip_dar');
      }
      await kapatWeb(t);
    }
    final (d, _) =
        await t.runAsync(() => webHazir(kisi: 'K041', an: 'gorevler')) ??
        (throw StateError('Kurulum'));
    await t.runAsync(() => d.ekranOku([const Okuma('GOREV')]));
    final g = {
      ...d.satirlar('GOREV').firstWhere((x) => x['ad'] == 'Teknik resim 14/20'),
      'son_teslim_ani': '2026-10-21T18:00:00+03:00',
    };
    t.view.physicalSize = const Size(1280, 800);
    await t.pumpWidget(
      RepaintBoundary(
        key: key,
        child: MaterialApp(
          debugShowCheckedModeBanner: false,
          theme: tema(Brightness.light),
          home: Scaffold(
            appBar: AppBar(title: const Text('Görev teslimi')),
            body: Padding(
              padding: const EdgeInsets.all(32),
              child: Center(
                child: SizedBox(
                  width: 640,
                  child: SingleChildScrollView(
                    child: TeslimForm(durum: d, gorev: g, tamam: () {}),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
    await kaydet('13_teslim');
    await kapatWeb(t);
    for (final ad in [
      'kayit',
      'giris',
      'calisiyor',
      'sabit_mola',
      'devam_bekliyor',
      'kilitli',
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
      t.view.physicalSize = const Size(390, 844);
      await t.pumpWidget(
        RepaintBoundary(
          key: key,
          child: IrpApp(durum: d, cizimler: harita, donanim: false),
        ),
      );
      await kaydet('telefon_$ad');
      if (ad == 'calisiyor') {
        (d.saat as Saat).ilerlet(
          d.saat.simdi().ekle(const Duration(seconds: 1)),
        );
        await t.pump(const Duration(seconds: 1));
        await kaydet('telefon_sayac_1sn');
        t.platformDispatcher.platformBrightnessTestValue = Brightness.dark;
        await t.pumpAndSettle();
        await kaydet('telefon_koyu');
        t.platformDispatcher.clearPlatformBrightnessTestValue();
        await t.pumpAndSettle();
      }
      await kapatWeb(t);
    }
  });
}
