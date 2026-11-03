import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:irp_cekirdek/irp_cekirdek.dart';
import 'package:irp_uygulama/ekranlar/web/web.dart';
import 'package:irp_uygulama/main.dart';

import 'destek.dart';
import 'web_destek.dart';

void main() {
  testWidgets(
    'Takip açıkken telefonun durum değişikliği birim sinyaliyle görünür',
    (t) async {
      final (d, b) =
          await t.runAsync(() => webHazir()) ?? (throw StateError('Kurulum'));
      await webAc(t, d, 'Takip');
      expect(find.textContaining('Molada'), findsNothing);
      final okumalar =
          b.webFikstur!['anlar'][b.webAni]['K009']['okumalar'] as List;
      final ekip =
          okumalar.firstWhere((q) => q['veri'] == 'EKIP')['cevap']['deger']
              as List;
      ekip.firstWhere((p) => p['kisi'] == 'K017')['hal']['durum'] = 'MOLADA';
      await t.runAsync(() async {
        b.sinyalVer('birim:IMALAT');
        await Future<void>.delayed(const Duration(milliseconds: 350));
      });
      await t.pumpAndSettle();
      await t.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 50)),
      );
      await t.pumpAndSettle();
      expect(find.textContaining('Molada'), findsOneWidget, reason: d.mesaj);
      expect(find.widgetWithText(AppBar, 'Takip'), findsOneWidget);
      await kapatWeb(t);
    },
  );

  for (final (sayfa, kisi, okumalar) in [
    ('İş Ataması', 'K009', ['HAVUZ', 'LISTE', 'KISILER', 'EKIP']),
    ('Plansız iş', 'K009', ['PROJELER', 'ETAPLAR', 'KODLAR', 'KISILER']),
    ('Onaylar', 'K009', ['ONAY_LISTESI', 'EKIP']),
    ('Takip', 'K009', ['EKIP', 'BILDIRIMLER']),
    ('Kişinin günü', 'K009', ['KISININ_GUNU']),
    ('Gün sonu onayı', 'K009', ['GUN_ISLERI', 'GUN']),
    ('İşlerim', 'K041', ['GOREV', 'GUN_ISLERI']),
    ('Benim performansım', 'K041', ['PERFORMANS', 'BIRIM_PERFORMANS']),
    ('Bildirimler', 'K041', ['BILDIRIMLER']),
  ]) {
    testWidgets('$sayfa doğru okumaları çağırır; 1280 ve dar düzende taşmaz', (
      t,
    ) async {
      final (d, b) =
          await t.runAsync(() => webHazir(kisi: kisi)) ??
          (throw StateError('Kurulum'));
      await webAc(t, d, sayfa);
      for (final v in okumalar) {
        expect(b.cagrilar.any((c) => c['veri'] == v), isTrue, reason: v);
      }
      expect(find.textContaining('Nereye yazılır'), findsNothing);
      expect(t.takeException(), isNull);
      t.view.physicalSize = const Size(390, 844);
      await t.pumpAndSettle();
      expect(t.takeException(), isNull);
      await kapatWeb(t);
    });
  }
  for (final (kisi, ilk) in [('K009', 'Takip'), ('K041', 'İşlerim')]) {
    testWidgets('$kisi rolüne göre $ilk ile açılır', (t) async {
      final (d, _) =
          await t.runAsync(() => webHazir(kisi: kisi)) ??
          (throw StateError('Kurulum'));
      t.view.physicalSize = const Size(1280, 800);
      t.view.devicePixelRatio = 1;
      addTearDown(t.view.resetPhysicalSize);
      addTearDown(t.view.resetDevicePixelRatio);
      await t.pumpWidget(IrpApp(durum: d, cizimler: harita, donanim: false));
      await t.runAsync(() async {
        await Future<void>.delayed(const Duration(milliseconds: 50));
      });
      await t.pumpAndSettle();
      expect(t.widget<WebEkrani>(find.byType(WebEkrani)).durum.kisi, kisi);
      expect(find.widgetWithText(AppBar, ilk), findsOneWidget);
      await kapatWeb(t);
    });
  }
  for (final surukle in [false, true]) {
    testWidgets(
      'Atama ${surukle ? 'sürükle bırak' : 'çift tık'} IS.ATADIM ve liste sürümünü yazar',
      (t) async {
        final (d, b) =
            await t.runAsync(() => webHazir(an: 'atama')) ??
            (throw StateError('Kurulum'));
        await webAc(t, d, 'İş Ataması');
        final i = d.satirlar('HAVUZ', hedef: d.birim).first;
        final kaynak = find.byKey(Key('havuz-${i['kimlik']}'));
        if (surukle) {
          final p = t.getCenter(kaynak);
          final hedef = t.getCenter(find.byKey(const Key('liste-K017')));
          final g = await t.startGesture(p);
          await g.moveBy(const Offset(20, 0));
          await t.pump();
          await g.moveTo(hedef);
          await t.pump();
          await g.up();
          await t.runAsync(() async {
            await Future<void>.delayed(const Duration(milliseconds: 50));
          });
          await t.pumpAndSettle();
        } else {
          await t.tap(kaynak);
          await t.pump(const Duration(milliseconds: 50));
          await t.tap(kaynak);
          await t.pumpAndSettle();
          await dokun(t, find.text('Ata'));
        }
        expect(d.gunluk, isNotEmpty, reason: d.mesaj);
        final e = d.gunluk.last['olay'];
        expect(e['eylem_kodu'], 'IS.ATADIM');
        expect(e['girdiler'], {'kisi': 'K017', 'sira': 2});
        expect(
          e['neyin_ustunde'],
          containsAll([
            hedef(i),
            {
              'tur': 'LISTE',
              'kimlik': 'K017',
              'surum': d.nesne('LISTE', hedef: 'K017')['surum'],
            },
          ]),
        );
        expect(b.olaylar.last, e);
        await kapatWeb(t);
      },
    );
  }
  testWidgets('Liste sırası IS.SIRALADIM; devret iki liste sürümünü taşır', (
    t,
  ) async {
    final (d, _) =
        await t.runAsync(() => webHazir(an: 'sirali')) ??
        (throw StateError('Kurulum'));
    await webAc(t, d, 'İş Ataması');
    final l = t.widget<ReorderableListView>(
      find.byType(ReorderableListView).first,
    );
    await t.runAsync(() async {
      l.onReorderItem!(0, 1);
      await Future<void>.delayed(const Duration(milliseconds: 50));
    });
    await t.pumpAndSettle();
    expect(d.gunluk.last['olay']['eylem_kodu'], 'IS.SIRALADIM');
    expect(d.gunluk.last['olay']['girdiler'], {'kisi': 'K017', 'yeni_sira': 2});
    await dokun(t, find.byTooltip('İş işlemleri').first);
    await dokun(t, find.text('Devret'));
    await dokun(t, find.widgetWithText(FilledButton, 'Devret'));
    final e = d.gunluk.last['olay'];
    expect(e['eylem_kodu'], 'IS.DEVRETTIM');
    expect(
      (e['neyin_ustunde'] as List)
          .where((h) => h['tur'] == 'LISTE')
          .map((h) => h['kimlik']),
      ['K017', 'K023'],
    );
    await kapatWeb(t);
  });
  for (final (sayfa, ornek, kod) in [
    ('İş Ataması', 'atama', 'IS.ATADIM'),
    ('Plansız iş', '1040', 'IS.PLANSIZ_TANIMLADIM'),
    ('Onaylar', 'onay', 'IS.ONAYLADIM'),
    ('Kişinin günü', '1040', 'IS.SURE_EKLEDIM'),
    ('Gün sonu onayı', 'gun_sonu', 'GUN_SONU.ONAYLADIM'),
  ]) {
    testWidgets(
      '$sayfa bayatken kapalı; BAYAT cevabında okur ve doğru olay yazar',
      (t) async {
        final (d, b) =
            await t.runAsync(() => webHazir(an: ornek)) ??
            (throw StateError('Kurulum'));
        await webAc(t, d, sayfa);
        final saat = d.saat as Saat;
        saat.ilerlet(saat.simdi().ekle(const Duration(seconds: 31)));
        await t.pump(const Duration(seconds: 1));
        expect(d.yonetimAcik, isFalse);
        expect(find.textContaining('Bağlantı bekleniyor'), findsOneWidget);
        expect(
          t
              .widgetList<FilledButton>(find.byType(FilledButton))
              .where(
                (w) =>
                    w.child is Text &&
                    !((w.child as Text).data ?? '').contains('Plansız'),
              )
              .every((w) => w.onPressed == null),
          isTrue,
        );
        await t.runAsync(d.yenile);
        await t.pumpAndSettle();
        b.sonrakiCevap = {'sonuc': 'REDDEDILDI', 'kod': 'BAYAT'};
        final once = b.cagrilar.where((c) => c['kapi'] == 'oku').length;
        if (sayfa == 'İş Ataması') {
          final i = d.satirlar('HAVUZ', hedef: d.birim).first;
          final f = find.byKey(Key('havuz-${i['kimlik']}'));
          await t.tap(f);
          await t.pump(const Duration(milliseconds: 50));
          await t.tap(f);
          await t.pumpAndSettle();
          await dokun(t, find.text('Ata'));
        }
        if (sayfa == 'Plansız iş') {
          await t.enterText(
            find.byKey(const Key('plansiz-ad')),
            'Kaynak çatlağı tamiri',
          );
          await dokun(t, find.text('Tanımla ve sıraya koy'));
        }
        if (sayfa == 'Onaylar') {
          await dokun(t, find.widgetWithText(FilledButton, 'Onayla').first);
        }
        if (sayfa == 'Kişinin günü') {
          await dokun(t, find.text('Günü tamamla'));
          await t.enterText(
            find.byKey(const Key('sure-aciklama')),
            'Telefon kapalıydı',
          );
          await dokun(t, find.widgetWithText(FilledButton, 'Kaydet'));
          expect(d.gunluk.last['olay']['adina'], 'K017');
        }
        if (sayfa == 'Gün sonu onayı') {
          await dokun(t, find.widgetWithText(FilledButton, 'Onayla').first);
        }
        expect(d.gunluk, isNotEmpty, reason: d.mesaj);
        expect(d.gunluk.last['olay']['eylem_kodu'], kod);
        expect(d.gunluk.last['durum'], 'RED');
        expect(
          b.cagrilar.where((c) => c['kapi'] == 'oku').length,
          greaterThan(once),
        );
        expect(find.text('Ekran güncellendi, yeniden bak'), findsOneWidget);
        await kapatWeb(t);
      },
    );
  }
  testWidgets(
    'Onay reddi not ister; duruştan devam onayı doğru hedefle gider',
    (t) async {
      final (d, b) =
          await t.runAsync(() => webHazir(an: 'onay')) ??
          (throw StateError('Kurulum'));
      await webAc(t, d, 'Onaylar');
      expect(find.text('Hakan Arslan · 10:40 itibarıyla'), findsOneWidget);
      await dokun(t, find.widgetWithText(FilledButton, 'Reddet').first);
      await t.enterText(find.byKey(const Key('gerekce')), 'Dikiş eksik');
      await dokun(t, find.widgetWithText(FilledButton, 'Kaydet'));
      expect(d.gunluk.last['olay']['girdiler'], {'not': 'Dikiş eksik'});
      final ekip =
          b.webOkumalar.firstWhere((r) => r['veri'] == 'EKIP')['cevap']['deger']
              as List;
      final p = ekip.firstWhere((p) => p['kisi'] == 'K023');
      p['hal']['durum'] = 'ARIZADA';
      p['hal']['devam_izni'] = false;
      await t.runAsync(d.yenile);
      await t.pumpAndSettle();
      await dokun(t, find.text('Devam onayı'));
      expect(d.gunluk.last['olay']['eylem_kodu'], 'IS.DEVAM_ONAYLADIM');
      await kapatWeb(t);
    },
  );
  testWidgets('Kişinin günü yanlış kaydı gerekçesiyle geçersiz sayar', (
    t,
  ) async {
    final (d, _) =
        await t.runAsync(() => webHazir()) ?? (throw StateError('Kurulum'));
    await webAc(t, d, 'Kişinin günü');
    await dokun(t, find.text('Kaydı geçersiz say'));
    await dokun(t, find.byType(SimpleDialogOption).first);
    await t.enterText(find.byKey(const Key('gerekce')), 'Yanlış düğme');
    await dokun(t, find.widgetWithText(FilledButton, 'Kaydet'));
    expect(d.gunluk.last['olay']['eylem_kodu'], 'KAYIT.GECERSIZ_SAYDIM');
    expect(d.gunluk.last['olay']['girdiler']['gerekce'], 'Yanlış düğme');
    await kapatWeb(t);
  });
  testWidgets('Gün sonu iadesi kişi gün ve gerekçe yazar', (t) async {
    final (d, _) =
        await t.runAsync(() => webHazir(an: 'gun_sonu')) ??
        (throw StateError('Kurulum'));
    await webAc(t, d, 'Gün sonu onayı');
    await dokun(t, find.widgetWithText(FilledButton, 'İade et').first);
    await t.enterText(find.byKey(const Key('gerekce')), 'Süreyi açıkla');
    await dokun(t, find.widgetWithText(FilledButton, 'Kaydet'));
    expect(d.gunluk.last['olay']['girdiler'], {
      'kisi': 'K901',
      'gun': '2026-10-22',
      'gerekce': 'Süreyi açıkla',
    });
    await kapatWeb(t);
  });
  testWidgets('İşlerim toplu kabul ve çevrimdışı gün sonu tanıklığı', (
    t,
  ) async {
    final (d, b) =
        await t.runAsync(() => webHazir(kisi: 'K041', an: 'gorevler')) ??
        (throw StateError('Kurulum'));
    await webAc(t, d, 'İşlerim');
    b.cevrimici = false;
    d.baglanti = false;
    await dokun(t, find.byKey(const Key('toplu-kabul')));
    expect(d.gunluk.last['olay']['eylem_kodu'], 'GOREV.KABUL_ETTIM');
    expect(
      d.gunluk.last['olay']['neyin_ustunde'].length,
      greaterThanOrEqualTo(2),
    );
    await dokun(t, find.text('Günü gönder').first);
    await dokun(t, find.widgetWithText(FilledButton, 'Gönder'));
    expect(d.gunluk.last['olay']['eylem_kodu'], 'GUN_SONU.GONDERDIM');
    expect(d.bekleyen, 2);
    await kapatWeb(t);
  });
  testWidgets(
    'Bildirim listesi açılınca görüldü tanıklığı; performans salt okunur',
    (t) async {
      final (d, b) =
          await t.runAsync(() => webHazir(kisi: 'K041')) ??
          (throw StateError('Kurulum'));
      final bs =
          b.webOkumalar.firstWhere(
                (r) => r['veri'] == 'BILDIRIMLER',
              )['cevap']['deger']
              as List;
      bs.add({
        'kimlik': 'sentetik-bildirim',
        'metin': 'Çizim güncellendi',
        'gecerli': true,
      });
      await webAc(t, d, 'Bildirimler');
      expect(d.gunluk.last['olay']['eylem_kodu'], 'BILDIRIM.GORDUM');
      await kapatWeb(t);
    },
  );
}
