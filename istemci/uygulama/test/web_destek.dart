import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:irp_cekirdek/irp_cekirdek.dart';
import 'package:irp_uygulama/bulut/uygulama_bulutu.dart';
import 'package:irp_uygulama/durum/kalici_depo.dart';
import 'package:irp_uygulama/durum/uygulama_durumu.dart';
import 'package:irp_uygulama/sahte/fikstur_bulutu.dart';
import 'package:irp_uygulama/ekranlar/telefon/ortak.dart';
import 'package:irp_uygulama/ekranlar/web/web.dart';

import 'destek.dart';

Future<(UygulamaDurumu, FiksturBulutu)> webHazir({
  String kisi = 'K009',
  String an = '1040',
  bool telefonKipi = false,
}) async {
  final b = FiksturBulutu(
    fikstur,
    webFikstur: birlestirFikstur(
      dosya('test/fikstur/web.json'),
      dosya('test/fikstur/yonetim.json'),
    ),
    webKisi: kisi,
  )..webAni = an;
  final d = UygulamaDurumu(
    bulut: b,
    depo: BellekKaliciDepo({
      'kayit': {
        'kisi': kisi,
        'ad': kisi,
        'harf': telefonKipi ? 'T' : 'W',
        'oturum': {'refresh_token': 'sentetik-$kisi'},
      },
    }),
    semalar: semalar,
    saat: Saat(b.webOkumalar.first['cevap']['hesap_ani']),
    telefonKipi: telefonKipi,
  );
  await d.yukle();
  d.acik = true;
  await d.yenile();
  addTearDown(() {
    d.dispose();
    unawaited(b.dispose());
    for (final k in d.gunluk) {
      olayDogrula(Json.from(k['olay'] as Map));
    }
  });
  return (d, b);
}

Future<void> webAc(
  WidgetTester t,
  UygulamaDurumu d,
  String sayfa, {
  Size olcu = const Size(1280, 800),
}) async {
  t.view.physicalSize = olcu;
  t.view.devicePixelRatio = 1;
  addTearDown(t.view.resetPhysicalSize);
  addTearDown(t.view.resetDevicePixelRatio);
  await t.pumpWidget(
    MaterialApp(
      theme: tema(Brightness.light),
      home: WebEkrani(durum: d, ilkSayfa: sayfa),
    ),
  );
  await t.runAsync(() async {
    await Future<void>.delayed(const Duration(milliseconds: 50));
  });
  await t.pumpAndSettle();
}

Future<void> dokun(WidgetTester t, Finder f) async {
  await t.ensureVisible(f.first);
  await t.pumpAndSettle();
  await t.runAsync(() async {
    await t.tap(f.first);
    await Future<void>.delayed(const Duration(milliseconds: 50));
  });
  await t.pumpAndSettle();
  await t.runAsync(() async {
    await Future<void>.delayed(const Duration(milliseconds: 50));
  });
  await t.pumpAndSettle();
}

Future<void> kapatWeb(WidgetTester t) async {
  await t.pumpWidget(const SizedBox());
  await t.pumpAndSettle();
}
