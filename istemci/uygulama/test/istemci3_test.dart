import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:irp_cekirdek/irp_cekirdek.dart';
import 'package:irp_uygulama/bulut/supabase_bulutu.dart';
import 'package:irp_uygulama/durum/kalici_depo.dart';
import 'package:irp_uygulama/durum/uygulama_durumu.dart';
import 'package:irp_uygulama/ekranlar/telefon/giris.dart';
import 'package:irp_uygulama/ekranlar/telefon/telefon.dart';
import 'package:irp_uygulama/main.dart';

import 'destek.dart';
import 'web_destek.dart';

void main() {
  testWidgets('Ad soyad okumadan gelir; telefon ve kilitte kalır', (t) async {
    final (d, _, _) =
        await t.runAsync(() => hazir()) ?? (throw StateError('Kurulum'));
    await t.pumpWidget(IrpApp(durum: d, cizimler: harita, donanim: false));
    await t.pumpAndSettle();
    expect(find.text('Hakan Arslan'), findsOneWidget);
    d.kilitle();
    await t.pumpAndSettle();
    expect(find.text('Hakan Arslan'), findsOneWidget);
    expect(find.byType(Giris), findsOneWidget);
    await kapatWeb(t);
  });
  testWidgets(
    'Sayaç açık aralıktan başlar ve çekirdek saatiyle saniye ilerler',
    (t) async {
      final (d, _, _) =
          await t.runAsync(() => hazir()) ?? (throw StateError('Kurulum'));
      await t.pumpWidget(
        MaterialApp(
          home: Scaffold(body: Sayac(durum: d)),
        ),
      );
      final bas = d.hal['baslangic'];
      final saniye = d.cihaz!.simdiDuzeltilmis().farkAl(an(bas)).inSeconds;
      expect(saniye, greaterThan(0));
      String yaz(int s) => [
        s ~/ 3600,
        s ~/ 60 % 60,
        s % 60,
      ].map((n) => '$n'.padLeft(2, '0')).join(':');
      expect(find.text(yaz(saniye)), findsOneWidget);
      (d.saat as Saat).ilerlet(d.saat.simdi().ekle(const Duration(seconds: 1)));
      await t.pump(const Duration(seconds: 1));
      expect(find.text(yaz(saniye + 1)), findsOneWidget);
      await kapatWeb(t);
    },
  );
  testWidgets('Örnek hesap ipucu gerçek bulutta görünmez', (t) async {
    final d = UygulamaDurumu(
      bulut: SupabaseBulutu(),
      depo: BellekKaliciDepo(),
      semalar: semalar,
      saat: Saat('2026-10-22T10:40:00+03:00'),
    );
    await t.runAsync(d.yukle);
    addTearDown(d.dispose);
    await t.pumpWidget(IrpApp(durum: d, cizimler: harita, donanim: false));
    await t.pumpAndSettle();
    expect(find.textContaining('İlk şifre: 123456'), findsNothing);
    await kapatWeb(t);
  });
  testWidgets(
    'Sabit molada iş düğmeleri gizli; bitince tamamla ve devam görünür',
    (t) async {
      final (d, b, _) =
          await t.runAsync(() => hazir(durum: 'sabit_mola')) ??
          (throw StateError('Kurulum'));
      await t.pumpWidget(IrpApp(durum: d, cizimler: harita, donanim: false));
      await t.pumpAndSettle();
      for (final y in ['BAŞLA', 'TAMAMLA', 'İŞİNE DEVAM ET', 'MOLA', 'DURUŞ']) {
        expect(find.widgetWithText(FilledButton, y), findsNothing);
      }
      b.sec('devam_bekliyor');
      await t.runAsync(d.yenile);
      await t.pumpAndSettle();
      expect(find.text('TAMAMLA'), findsOneWidget);
      expect(find.text('İŞİNE DEVAM ET'), findsOneWidget);
      await kapatWeb(t);
    },
  );
  testWidgets('Kilitli iş beklenen iş ve kişi adını okur; yoksa genel metin', (
    t,
  ) async {
    final (d, b, _) =
        await t.runAsync(() => hazir(durum: 'kilitli')) ??
        (throw StateError('Kurulum'));
    await t.pumpWidget(IrpApp(durum: d, cizimler: harita, donanim: false));
    await t.pumpAndSettle();
    expect(find.text('Önce 052 bitmeli · Murat Koç'), findsOneWidget);
    for (final i in (b.okumalar['TELEFON']['deger']['isler'] as Map).values) {
      i.remove('beklenen_isler');
    }
    await t.runAsync(d.yenile);
    await t.pumpAndSettle();
    expect(find.text('Önceki işin bitmesi bekleniyor'), findsOneWidget);
    await kapatWeb(t);
  });
}
