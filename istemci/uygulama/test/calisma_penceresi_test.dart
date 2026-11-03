import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:irp_uygulama/durum/calisma_penceresi.dart';
import 'package:irp_uygulama/ekranlar/telefon/telefon.dart';

import 'destek.dart';

Map<String, dynamic> pencere({bool tatil = false}) => {
  'gun': '2026-10-22',
  'kaynak_ani': '2026-10-22T08:00:00+03:00',
  'mesai': tatil
      ? []
      : [
          ['2026-10-22T08:00:00+03:00', '2026-10-22T18:00:00+03:00'],
        ],
  'calisma': tatil
      ? []
      : [
          ['2026-10-22T08:00:00+03:00', '2026-10-22T12:00:00+03:00'],
          ['2026-10-22T13:00:00+03:00', '2026-10-22T18:00:00+03:00'],
        ],
};
void main() {
  test('mesai başlangıcı dahildir, bitişi dahil değildir; sabit mola mesai dışı olmaz', () {
    CalismaPenceresi at(String hour) => CalismaPenceresi(
      pencere(),
      DateTime.parse('2026-10-22T$hour:00+03:00'),
    );
    expect(at('07:59').mesaide, false);
    expect(at('08:00').calisabilir, true);
    expect(at('12:30').mesaide, true);
    expect(at('12:30').calisabilir, false);
    expect(at('13:00').calisabilir, true);
    expect(at('18:00').mesaide, false);
  });
  test('izin/tatil boşluğu ve onaylı ek mesai aralığı sunucudan geldiği gibi uygulanır', () {
    final now = DateTime.parse('2026-10-22T20:30:00+03:00'),
        p = pencere(tatil: true);
    expect(CalismaPenceresi(p, now).mesaide, false);
    p['mesai'] = [
      ['2026-10-22T20:00:00+03:00', '2026-10-22T21:00:00+03:00'],
    ];
    p['calisma'] = p['mesai'];
    expect(CalismaPenceresi(p, now).calisabilir, true);
  });
  test('önceki günün takvimi ve eksik cevap çalışma izni sayılmaz', () {
    final now = DateTime.parse('2026-10-23T10:00:00+03:00');
    expect(CalismaPenceresi(pencere(), now).biliniyor, false);
    expect(CalismaPenceresi(null, now).biliniyor, false);
  });
  testWidgets('gerçek telefon kipinde mesai dışında Başla gösterilmez', (
    tester,
  ) async {
    final (d, b, _) = (await tester.runAsync(() => hazir(telefonKipi: true)))!;
    b.okumalar['TELEFON']['deger']['calisma_penceresi'] = pencere(tatil: true);
    await tester.runAsync(d.yenile);
    expect(d.mesaiBiliniyor, true);
    expect(d.mesaiIcinde, false);
    expect(d.kapiAcik('IS.BASLADIM'), false);
    await tester.pumpWidget(
      MaterialApp(
        home: Telefon(durum: d, cizimler: harita),
      ),
    );
    expect(find.text('Mesai Dışındasınız'), findsOneWidget);
    expect(find.text('BAŞLA'), findsNothing);
    expect(find.text('DEVAM ET'), findsNothing);
  });
  test('mesai dışı ilk açılış otomatik giriş olayı üretmez', () async {
    final (d, b, _) = await hazir(telefonKipi: true, durum: 'mesai_disi');
    b.okumalar['TELEFON']['deger']['calisma_penceresi'] = pencere(tatil: true);
    await d.yenile();
    d.acik = false;
    await d.kilitAc('654321');
    await d.gonderici.tetikle();
    expect(b.olaylar.where((e) => e['eylem_kodu'] == 'MESAI.GIRDIM'), isEmpty);
  });
}
