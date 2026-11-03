import 'dart:convert';
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
import 'package:irp_uygulama/ekranlar/kisi_degistir.dart';
import 'package:irp_uygulama/ekranlar/telefon/ekibim.dart';
import 'package:irp_uygulama/ekranlar/telefon/giris.dart';
import 'package:irp_uygulama/ekranlar/telefon/telefon.dart';
import 'package:irp_uygulama/ekranlar/web/web.dart';
import 'package:irp_uygulama/main.dart';
import 'package:irp_uygulama/sahte/fikstur_bulutu.dart';

import 'destek.dart';
import 'web_destek.dart';

void main() => istemci7Test();

class _IzliDepo extends BellekKaliciDepo {
  final yazilanlar = <Map<String, dynamic>>[];
  @override
  Future<void> yaz(Map<String, dynamic> veri) async {
    yazilanlar.add(kopya(veri));
    await super.yaz(veri);
  }
}

void istemci7Test({bool ekran = false}) {
  testWidgets(
    'Kilit gösteri kişileriyle yok, normal kipte var; mesaiden çıkış ikisinde de var',
    (t) async {
      for (final telefon in [false, true]) {
        for (final gosteri in [false, true]) {
          final d = await t.runAsync(() async {
            final b = FiksturBulutu(fikstur);
            addTearDown(b.dispose);
            final d = UygulamaDurumu(
              bulut: b,
              depo: BellekKaliciDepo(),
              semalar: semalar,
              saat: Saat('2026-10-22T10:40:00+03:00'),
              telefonKipi: telefon,
              gosteriKisileri: gosteri
                  ? gosteriKisileriniCoz([
                      {
                        'etiket': 'Çalışan',
                        'kod': 'K017',
                        'sifre': '123456',
                        'yer': 'ikisi',
                      },
                    ])
                  : const [],
            );
            await d.yukle();
            if (!gosteri) await d.kaydol('K017', '123456', '654321', '654321');
            addTearDown(d.dispose);
            return d;
          });
          if (d == null) throw StateError('Kurulum');
          if (telefon) {
            await t.pumpWidget(
              MaterialApp(
                home: Telefon(durum: d, cizimler: harita),
              ),
            );
            await t.pumpAndSettle();
            await t.tap(find.byTooltip('Menü'));
            await t.pumpAndSettle();
            // Mesaiden çıkış iki kipte de var; gösteri kipinde ardından kilitlenmez.
            expect(find.text('Mesaiden çık'), findsOneWidget);
          } else {
            await webAc(t, d, 'İşlerim');
            expect(
              find.text('Kilitle'),
              gosteri ? findsNothing : findsOneWidget,
            );
          }
          await t.pumpWidget(const SizedBox.shrink());
          await t.pumpAndSettle();
        }
      }
    },
  );
  final anahtar = GlobalKey();
  Future<void> ac(WidgetTester t, UygulamaDurumu d) async {
    t.view.physicalSize = const Size(1080, 2340);
    t.view.devicePixelRatio = 3;
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
    await t.pumpWidget(
      RepaintBoundary(
        key: anahtar,
        child: IrpApp(durum: d, cizimler: harita, donanim: false),
      ),
    );
    await t.runAsync(
      () => Future<void>.delayed(const Duration(milliseconds: 50)),
    );
    await t.pumpAndSettle();
  }

  Future<void> goruntu(WidgetTester t, String ad) async {
    expect(t.takeException(), isNull);
    if (!ekran) return;
    await t.runAsync(() async {
      final klasor = Directory('../../codex/sonuclar/istemci7_ekranlar');
      await klasor.create(recursive: true);
      final im =
          await (anahtar.currentContext!.findRenderObject()
                  as RenderRepaintBoundary)
              .toImage(pixelRatio: 3);
      expect((im.width, im.height), (1080, 2340));
      final bytes = await im.toByteData(format: ui.ImageByteFormat.png);
      await File('${klasor.path}/$ad.png')
          .writeAsBytes(bytes!.buffer.asUint8List());
      im.dispose();
    });
  }

  for (final rol in ['calisan', 'lider', 'beyaz']) {
    testWidgets('Telefon yönlendirmesi: $rol; web yönetimi telefona gelmez', (
      t,
    ) async {
      for (final kisi
          in rol == 'beyaz'
              ? ['K041', 'K004', 'K001']
              : [rol == 'lider' ? 'K009' : 'K017']) {
        final d =
            await t.runAsync(() async {
              if (rol == 'calisan') return (await hazir(telefonKipi: true)).$1;
              return (await webHazir(kisi: kisi, telefonKipi: true)).$1;
            }) ??
            (throw StateError('Kurulum'));
        await ac(t, d);
        expect(find.byType(WebEkrani), findsNothing);
        if (rol == 'calisan') {
          expect(find.byType(Telefon), findsOneWidget);
          expect(find.text('TAMAMLA'), findsOneWidget);
        } else if (rol == 'lider') {
          expect(find.byType(Ekibim), findsOneWidget);
          expect(find.text('İş Ataması'), findsNothing);
        } else {
          expect(
            find.text('Bu hesap bilgisayardan kullanılır'),
            findsOneWidget,
          );
          expect(d.ekranOkumalari, isEmpty);
          final b = d.bulut as FiksturBulutu;
          expect(
            b.cagrilar
                .where((c) => c['kapi'] == 'oku')
                .map((c) => c['veri'])
                .toSet(),
            {'KISILER'},
          );
          if (kisi == 'K001') await goruntu(t, '03_beyaz_yaka');
        }
        expect(find.text('Bu telefonu başka kişiye kaydet'), findsNothing);
        await kapatWeb(t);
      }
    });
  }

  testWidgets('Ekibim: atama, sıradaki iş, devam onayı, sinyal ve tazelik', (
    t,
  ) async {
    final (d, b) =
        await t.runAsync(() => webHazir(an: 'atama', telefonKipi: true)) ??
        (throw StateError('Kurulum'));
    await ac(t, d);
    final havuz = d.satirlar('HAVUZ', hedef: d.birim).first;
    await dokun(t, find.byKey(const Key('ekip-K017')));
    await dokun(t, find.text('Havuzdan İş Ekle'));
    await dokun(t, find.byKey(Key('havuz-${havuz['kimlik']}')));
    expect(find.text('Yeni İş Sırası'), findsOneWidget);
    await dokun(t, find.text('Onayla'));
    expect(b.olaylar.last['eylem_kodu'], 'IS.ATADIM');
    expect(b.olaylar.last['girdiler'], {'kisi': 'K017', 'sira': 2});
    expect(
      b.olaylar.last['neyin_ustunde'],
      containsAll([
        {
          'tur': 'LISTE',
          'kimlik': 'K017',
          'surum': d.nesne('LISTE', hedef: 'K017')['surum'],
        },
      ]),
    );

    await dokun(t, find.byKey(const Key('ekip-K017')));
    await dokun(t, find.text('İş Sırasını Değiştir'));
    final listedeki = (d.nesne('LISTE', hedef: 'K017')['isler'] as List).first;
    await dokun(t, find.byKey(Key('siradaki-${listedeki['kimlik']}')));
    await dokun(t, find.text('Onayla'));
    expect(b.olaylar.last['eylem_kodu'], 'IS.SIRALADIM');
    expect(b.olaylar.last['girdiler'], {'kisi': 'K017', 'yeni_sira': 1});
    await dokun(t, find.byKey(const Key('ekip-K017')));
    await dokun(t, find.text('İş Sırasını Değiştir'));
    await dokun(t, find.byKey(Key('havuz-${havuz['kimlik']}')));
    await dokun(t, find.text('Onayla'));
    expect(b.olaylar.last['girdiler'], {'kisi': 'K017', 'sira': 1});

    b.webAni = 'onay';
    final p =
        (b.webOkumalar.firstWhere((r) => r['veri'] == 'EKIP')['cevap']['deger']
                as List)
            .firstWhere((p) => p['kisi'] == 'K023');
    p['hal']['durum'] = 'ARIZADA';
    p['hal']['devam_izni'] = false;
    await t.runAsync(d.yenile);
    await t.pumpAndSettle();
    expect(
      t.getTopLeft(find.byKey(const Key('ekip-K023'))).dy,
      lessThan(t.getTopLeft(find.byKey(const Key('ekip-K017'))).dy),
    );
    await goruntu(t, '01_ekibim');
    await dokun(t, find.byKey(const Key('ekip-K023')));
    await goruntu(t, '02_kisi_penceresi');
    final saat = d.saat as Saat;
    saat.ilerlet(saat.simdi().ekle(const Duration(seconds: 31)));
    await t.pump(const Duration(seconds: 1));
    expect(
      t
          .widget<FilledButton>(
            find.widgetWithText(FilledButton, 'Devam İzni Ver'),
          )
          .onPressed,
      isNull,
    );
    await t.runAsync(d.yenile);
    await t.pumpAndSettle();
    await dokun(t, find.text('Devam İzni Ver'));
    expect(b.olaylar.last['eylem_kodu'], 'IS.DEVAM_ONAYLADIM');

    final once = b.cagrilar.length;
    p['hal']['durum'] = 'MOLADA';
    b.sinyalVer('birim:IMALAT');
    await t.runAsync(
      () => Future<void>.delayed(const Duration(milliseconds: 350)),
    );
    await t.pumpAndSettle();
    expect(b.cagrilar.length, greaterThan(once));
    expect(find.textContaining('Molada'), findsWidgets);
    expect(find.text('Plansız iş'), findsNothing);
    expect(find.text('Gün sonu onayı'), findsNothing);
    await kapatWeb(t);
  });

  testWidgets(
    'Gösteri kişileri: otomatik giriş, onaylı sıfırlama, platform süzme ve yeniden açılış',
    (t) async {
      final kisiler = gosteriKisileriniCoz([
        {
          'etiket': 'Tasarım Çalışanı',
          'kod': 'K041',
          'sifre': '123456',
          'yer': 'web',
        },
        {
          'etiket': 'Atölye Çalışanı 1',
          'kod': 'K017',
          'sifre': '123456',
          'yer': 'telefon',
        },
        {
          'etiket': 'İmalat Ekip Lideri',
          'kod': 'K009',
          'sifre': '123456',
          'yer': 'ikisi',
        },
      ]);
      final b = FiksturBulutu(
        fikstur,
        webFikstur: birlestirFikstur(
          dosya('test/fikstur/web.json'),
          dosya('test/fikstur/yonetim.json'),
        ),
      );
      final depo = _IzliDepo();
      UygulamaDurumu durum(bool telefon, {KaliciDepo? depoSecimi}) =>
          UygulamaDurumu(
            bulut: b,
            depo: depoSecimi ?? depo,
            semalar: semalar,
            saat: Saat('2026-10-22T10:40:00+03:00'),
            telefonKipi: telefon,
            gosteriKisileri: kisiler,
          );
      final d =
          await t.runAsync(() async {
            final d = durum(true);
            await d.yukle();
            await d.gonderici.tetikle();
            return d;
          }) ??
          (throw StateError('Kurulum'));
      addTearDown(d.dispose);
      addTearDown(b.dispose);
      expect(d.kisi, 'K017');
      expect(d.gosteriKisileri.map((k) => k.kod), ['K017', 'K009']);
      await ac(t, d);
      expect(find.byType(Giris), findsNothing);
      expect(find.text('Atölye Çalışanı 1'), findsOneWidget);
      d.kilitle();
      expect(d.acik, isTrue);
      expect(b.cagrilar.where((c) => c['kapi'] == 'parolaDegistir'), isEmpty);
      final eskiKurulum = d.yerel['kurulum_kimligi'];
      d.yerel['eski_isaret'] = true;
      b.cevrimici = false;
      d.baglanti = false;
      await t.runAsync(() => d.olay('IS.MOLA_VERDIM'));
      await t.pumpAndSettle();
      expect(d.gonderilmemisKayitSayisi, 1);
      b.cevrimici = true;
      Future<void> kisiSec() async {
        await dokun(t, find.byIcon(Icons.more_horiz));
        await dokun(t, find.text('Kişi değiştir'));
        expect(find.text('Tasarım Çalışanı'), findsNothing);
        await dokun(t, find.text('İmalat Ekip Lideri'));
        expect(
          find.textContaining('1 gönderilmemiş kayıt var.'),
          findsOneWidget,
        );
      }

      await kisiSec();
      await dokun(t, find.text('Vazgeç'));
      expect(d.kisi, 'K017');
      expect(d.bekleyen, 1);
      await kisiSec();
      final yazimSayisi = depo.yazilanlar.length;
      await dokun(t, find.text('Evet, sıfırla'));
      expect(depo.yazilanlar.skip(yazimSayisi).first, isEmpty);
      expect(d.kisi, 'K009');
      expect(d.yerel.containsKey('eski_isaret'), isFalse);
      expect(d.yerel['kurulum_kimligi'], isNot(eskiKurulum));
      expect((d.yerel['cihazlar'] as Map).keys, ['K009']);
      expect(d.gunluk, isEmpty);
      expect(find.byType(Ekibim), findsOneWidget);
      expect(jsonEncode(depo.veri), isNot(contains('123456')));
      expect(b.cagrilar.where((c) => c['kapi'] == 'cihaz_kaydol').length, 2);
      await kapatWeb(t);
      final tekrar =
          await t.runAsync(() async {
            final tekrar = durum(true);
            await tekrar.yukle();
            return tekrar;
          }) ??
          (throw StateError('Kurulum'));
      addTearDown(tekrar.dispose);
      expect(tekrar.kisi, 'K009');
      expect(tekrar.acik, isTrue);
      expect(b.cagrilar.where((c) => c['kapi'] == 'cihaz_kaydol').length, 2);
      final web =
          await t.runAsync(() async {
            final web = durum(false, depoSecimi: _IzliDepo());
            await web.yukle();
            await web.gonderici.tetikle();
            return web;
          }) ??
          (throw StateError('Kurulum'));
      addTearDown(web.dispose);
      // Web'de telefonun yerel kaydı yerine ilk uygun kişi ile ilk açılış.
      expect(web.gosteriKisileri.map((k) => k.kod), ['K041', 'K009']);
      expect(web.kisi, 'K041');
      await ac(t, web);
      expect(find.byType(WebEkrani), findsOneWidget);
      expect(find.byType(Giris), findsNothing);
      expect(find.byType(KisiDegistirMenusu), findsOneWidget);
      await dokun(t, find.byTooltip('Menü'));
      await dokun(t, find.text('Kişi değiştir'));
      await dokun(t, find.text('İmalat Ekip Lideri'));
      await t.runAsync(() async {
        await t.tap(find.text('Evet, sıfırla'));
        await Future<void>.delayed(const Duration(milliseconds: 50));
      });
      await t.pump();
      await t.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 50)),
      );
      await t.pumpAndSettle();
      expect(web.kisi, 'K009');
      expect(find.text('İşlerim'), findsNothing);
      expect(find.text('Takip'), findsWidgets);
      await kapatWeb(t);
    },
  );
}
