import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:irp_uygulama/main.dart';
import 'package:irp_uygulama/durum/uygulama_durumu.dart';
import 'package:irp_uygulama/ekranlar/telefon/ortak.dart';
import 'package:irp_uygulama/ekranlar/telefon/eylem_penceresi.dart';
import 'package:irp_uygulama/ekranlar/telefon/not_ekle.dart';
import 'package:irp_uygulama/ekranlar/telefon/qr_cizim.dart';

import 'destek.dart';

void main() {
  Future<void> ac(WidgetTester t, UygulamaDurumu d) async {
    t.view.physicalSize = const Size(390, 844);
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.resetPhysicalSize);
    addTearDown(t.view.resetDevicePixelRatio);
    await t.pumpWidget(IrpApp(durum: d, cizimler: harita, donanim: false));
    await t.pump();
  }

  Future<void> bas(WidgetTester t, String yazi) async {
    final bul = find.text(yazi).last;
    await t.ensureVisible(bul);
    await t.runAsync(() async {
      await t.tap(bul);
      final d = t.widget<IrpApp>(find.byType(IrpApp)).durum;
      while (d.mesgul) {
        await Future<void>.delayed(const Duration(milliseconds: 10));
      }
      await Future<void>.delayed(Duration.zero);
    });
    await t.pumpAndSettle();
  }

  Future<void> kapat(WidgetTester t) async {
    await t.pumpWidget(const SizedBox());
    await t.pump();
  }

  testWidgets('1: kayıt alanları; KAYDET cihaz kaydı ve sabah girişi', (
    t,
  ) async {
    final (d, b, _) =
        await t.runAsync(() => hazir(durum: 'mesai_disi', acik: false)) ??
        (throw StateError('Kurulum'));
    d.yerel.remove('kayit');
    d.cihaz = null;
    await ac(t, d);
    final alan = find.byType(TextField);
    await t.enterText(alan.at(0), 'K017');
    await t.enterText(alan.at(1), '123456');
    await t.enterText(alan.at(2), '654321');
    await t.enterText(alan.at(3), '654321');
    await t.ensureVisible(find.text('KAYDET'));
    await t.runAsync(() async {
      await t.tap(find.text('KAYDET'));
      while (d.mesgul) {
        await Future<void>.delayed(const Duration(milliseconds: 20));
      }
    });
    await t.pumpAndSettle();
    await t.runAsync(d.gonderici.tetikle);
    await t.pump();
    expect(d.acik, isTrue);
    expect(b.olaylar.any((e) => e['eylem_kodu'] == 'MESAI.GIRDIM'), isTrue);
    await kapat(t);
  });
  testWidgets('1: sonraki açılış yalnız ad ve altı rakam ister', (t) async {
    final (d, _, _) =
        await t.runAsync(() => hazir(acik: false)) ??
        (throw StateError('Kurulum'));
    await ac(t, d);
    expect(find.text('Hakan Arslan'), findsOneWidget);
    expect(find.byType(TextField), findsNothing);
    for (final r in ['6', '5', '4', '3', '2']) {
      await bas(t, r);
    }
    await t.runAsync(() async {
      await t.tap(find.text('1'));
      while (d.mesgul) {
        await Future<void>.delayed(const Duration(milliseconds: 20));
      }
    });
    await t.pumpAndSettle();
    expect(d.acik, isTrue);
    await kapat(t);
  });
  testWidgets('2: TELEFON okur, BAŞLA doğru işe tanıklık yazar', (t) async {
    final (d, b, _) =
        await t.runAsync(() => hazir(durum: 'hazir')) ??
        (throw StateError('Kurulum'));
    b.cevrimici = false;
    await ac(t, d);
    await bas(t, 'BAŞLA');
    expect(
      b.cagrilar.any((e) => e['veri'] == 'TELEFON' && e['hedef'] == 'K017'),
      isTrue,
    );
    expect(d.gunluk.single['olay']['eylem_kodu'], 'IS.BASLADIM');
    expect(
      d.gunluk.single['olay']['neyin_ustunde'][0]['kimlik'],
      d.liste.first,
    );
    expect(d.hal['durum'], 'CALISIYOR');
    await kapat(t);
  });
  testWidgets('2: TAMAMLA üstte; MOLA ve DURUŞ aynı alt satırda; 56 px', (
    t,
  ) async {
    final (d, _, _) =
        await t.runAsync(() => hazir()) ?? (throw StateError('Kurulum'));
    await ac(t, d);
    final tamam = t.getRect(find.widgetWithText(FilledButton, 'TAMAMLA'));
    final mola = t.getRect(find.widgetWithText(FilledButton, 'MOLA'));
    final durus = t.getRect(find.widgetWithText(FilledButton, 'DURUŞ'));
    expect(tamam.bottom, lessThan(mola.top));
    expect(mola.top, durus.top);
    for (final r in [tamam, mola, durus]) {
      expect(r.height, greaterThanOrEqualTo(56));
    }
    expect(t.takeException(), isNull);
    await kapat(t);
  });
  for (final (ad, yazi, kod, acikMi) in [
    ('molada', 'DEVAM ET', 'IS.DEVAM_ETTIM', true),
    ('durus', 'DEVAM ET', 'IS.DEVAM_ETTIM', false),
    ('devam_izinli', 'DEVAM ET', 'IS.DEVAM_ETTIM', true),
    ('onay', 'BAŞLA', 'IS.BASLADIM', false),
    ('ret', 'DEVAM ET', 'IS.DEVAM_ETTIM', true),
    ('kilitli', 'BAŞLA', 'IS.BASLADIM', false),
    ('devam_bekliyor', 'İŞİNE DEVAM ET', 'IS.DEVAM_ETTIM', true),
  ]) {
    testWidgets('3: $ad kapısı ve olay', (t) async {
      final (d, b, _) =
          await t.runAsync(() => hazir(durum: ad)) ??
          (throw StateError('Kurulum'));
      b.cevrimici = false;
      await ac(t, d);
      final dugme = t.widget<FilledButton>(
        find.widgetWithText(FilledButton, yazi),
      );
      expect(dugme.onPressed != null, acikMi);
      if (acikMi) {
        await bas(t, yazi);
        expect(d.gunluk.last['olay']['eylem_kodu'], kod);
      } else {
        expect(d.gunluk, isEmpty);
      }
      expect(t.takeException(), isNull);
      await kapat(t);
    });
  }
  testWidgets('3: boş liste ve anlık iş', (t) async {
    final (d, b, _) =
        await t.runAsync(() => hazir(durum: 'bos_liste')) ??
        (throw StateError('Kurulum'));
    await ac(t, d);
    expect(find.text('Bugün için işin yok'), findsOneWidget);
    b.sec('anlik');
    await t.runAsync(d.yenile);
    await t.pump();
    expect(find.text('Anlık'), findsOneWidget);
    expect(find.text('00:00:00'), findsNothing);
    await kapat(t);
  });
  testWidgets('4: mola KODLAR okur ve Sigara notunu yazar', (t) async {
    final (d, b, _) =
        await t.runAsync(() => hazir()) ?? (throw StateError('Kurulum'));
    b.cevrimici = false;
    await ac(t, d);
    await bas(t, 'MOLA');
    await bas(t, 'Sigara');
    await bas(t, 'ONAYLA');
    expect(d.gunluk.single['olay']['girdiler'], {'not': 'Sigara'});
    expect(b.cagrilar.any((e) => e['veri'] == 'KODLAR'), isTrue);
    await kapat(t);
  });
  testWidgets('4: duruş kategorisi, neden ve Diğer not zorunluluğu', (t) async {
    final (d, b, _) =
        await t.runAsync(() => hazir()) ?? (throw StateError('Kurulum'));
    b.cevrimici = false;
    await ac(t, d);
    await bas(t, 'DURUŞ');
    await bas(t, 'Makine');
    await bas(t, 'Diğer');
    await bas(t, 'ONAYLA');
    expect(d.gunluk, isEmpty);
    await t.enterText(find.byType(TextField), 'Akım vermiyor');
    await bas(t, 'ONAYLA');
    expect(d.gunluk.single['olay']['girdiler'], {
      'neden': 'DURUS_NEDENI.MAKINE_DIGER',
      'not': 'Akım vermiyor',
    });
    await kapat(t);
  });
  testWidgets('4: tamamla ikinci basışı bekler; vazgeç olay yazmaz', (t) async {
    final (d, b, _) =
        await t.runAsync(() => hazir()) ?? (throw StateError('Kurulum'));
    b.cevrimici = false;
    await ac(t, d);
    await bas(t, 'TAMAMLA');
    expect(find.text('Onaylıyor musun?'), findsOneWidget);
    expect(d.gunluk, isEmpty);
    await bas(t, 'VAZGEÇ');
    expect(d.gunluk, isEmpty);
    await bas(t, 'TAMAMLA');
    await bas(t, 'TAMAMLA');
    expect(d.gunluk.single['olay']['eylem_kodu'], 'IS.TAMAMLADIM');
    await kapat(t);
  });
  testWidgets('4: açık pencerede kapı kapanınca onay pasif olur', (t) async {
    final (d, b, _) =
        await t.runAsync(() => hazir()) ?? (throw StateError('Kurulum'));
    await ac(t, d);
    await bas(t, 'MOLA');
    b.sec('sabit_mola');
    await t.runAsync(d.yenile);
    await t.pump();
    expect(
      t
          .widget<FilledButton>(find.widgetWithText(FilledButton, 'ONAYLA'))
          .onPressed,
      isNull,
    );
    expect(find.byType(EylemPenceresi), findsOneWidget);
    await kapat(t);
  });
  testWidgets('5: menüden not; izinli PARCA hedefi ve etiketler', (t) async {
    final (d, b, _) =
        await t.runAsync(() => hazir()) ?? (throw StateError('Kurulum'));
    b.cevrimici = false;
    await ac(t, d);
    await t.tap(find.byTooltip('Menü'));
    await t.pumpAndSettle();
    await bas(t, 'Not ekle');
    expect(find.byType(NotEkle), findsOneWidget);
    await t.enterText(
      find.widgetWithText(TextField, 'Notun'),
      'Ölçü kontrolü gerekli',
    );
    await t.enterText(
      find.widgetWithText(TextField, 'Etiketler (virgülle, isteğe bağlı)'),
      'Ölçü, Kontrol',
    );
    await bas(t, 'KAYDET');
    final e = d.gunluk.single['olay'];
    expect(e['eylem_kodu'], 'NOT.YAZDIM');
    expect(e['neyin_ustunde'][0]['tur'], 'PARCA');
    expect(e['girdiler']['etiketler'], ['Ölçü', 'Kontrol']);
    await kapat(t);
  });
  testWidgets('5: çalışan ekranı bildirim onayı istemez', (t) async {
    final (d, b, _) =
        await t.runAsync(() => hazir()) ?? (throw StateError('Kurulum'));
    b.okumalar['BILDIRIMLER']['deger'] = [
      {
        'kimlik': 'B-SENTETIK-1',
        'metin': 'Ekip lideri işini değiştirdi',
        'gorulme_ani': null,
      },
    ];
    await t.runAsync(d.yenile);
    await ac(t, d);
    expect(d.gunluk, isEmpty);
    expect(find.text('Ekip lideri işini değiştirdi'), findsNothing);
    await kapat(t);
  });
  testWidgets('6: bilinmeyen QR ve aynı çizime giden iki anahtar', (t) async {
    final (d, _, _) =
        await t.runAsync(() => hazir()) ?? (throw StateError('Kurulum'));
    await ac(t, d);
    await bas(t, 'QR');
    expect(find.byType(QrCizim), findsOneWidget);
    await t.enterText(find.byType(TextField), 'bilinmeyen');
    await bas(t, 'ÇİZİMİ AÇ');
    expect(find.text('Bu QR tanınmadı'), findsOneWidget);
    await t.enterText(find.byType(TextField), 'IRP:NESNE:SENTETIK-1');
    await bas(t, 'ÇİZİMİ AÇ');
    expect(find.byType(InteractiveViewer), findsOneWidget);
    expect(d.gunluk, isEmpty);
    expect(harita['IRP:NESNE:SENTETIK-1'], harita['2509084_07_04-63']);
    await kapat(t);
  });
  testWidgets('günün işleri salt okunur ve menüde teknik günlük yok', (
    t,
  ) async {
    final (d, b, _) =
        await t.runAsync(() => hazir()) ?? (throw StateError('Kurulum'));
    b.cevrimici = false;
    await ac(t, d);
    await bas(t, 'Günün işleri (1)');
    for (final tile in t.widgetList<ListTile>(find.byType(ListTile))) {
      expect(tile.onTap, isNull);
    }
    await bas(t, 'KAPAT');
    await t.tap(find.byTooltip('Menü'));
    await t.pumpAndSettle();
    expect(find.text('Bu cihazın kayıtları'), findsNothing);
    expect(d.gunluk, isEmpty);
    await kapat(t);
  });
  testWidgets('dar koyu ekran ve büyük yazı taşmaz', (t) async {
    final (d, _, _) =
        await t.runAsync(() => hazir()) ?? (throw StateError('Kurulum'));
    await ac(t, d);
    t.view.physicalSize = const Size(320, 740);
    t.platformDispatcher.platformBrightnessTestValue = Brightness.dark;
    t.platformDispatcher.textScaleFactorTestValue = 1.4;
    addTearDown(t.platformDispatcher.clearPlatformBrightnessTestValue);
    addTearDown(t.platformDispatcher.clearTextScaleFactorTestValue);
    await t.pumpAndSettle();
    expect(t.takeException(), isNull);
    final context = t.element(find.byType(Dugme).first);
    expect(Theme.of(context).brightness, Brightness.dark);
    await kapat(t);
  });
  testWidgets(
    'fotoğraf seçicinin geçici arka plana geçişi not formunu kapatmaz',
    (t) async {
      final (d, _, _) =
          await t.runAsync(() => hazir()) ?? (throw StateError('Kurulum'));
      await ac(t, d);
      await t.tap(find.byTooltip('Menü'));
      await t.pumpAndSettle();
      await bas(t, 'Not ekle');
      final gozlemci = t.state(find.byType(IrpApp)) as WidgetsBindingObserver;
      gozlemci.didChangeAppLifecycleState(AppLifecycleState.paused);
      await t.pump();
      expect(d.acik, isTrue);
      expect(find.byType(NotEkle), findsOneWidget);
      await kapat(t);
    },
  );
}
