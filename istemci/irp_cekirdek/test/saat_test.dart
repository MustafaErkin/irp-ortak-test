import 'package:irp_cekirdek/irp_cekirdek.dart';
import 'package:test/test.dart';

void main() {
  test('An, farkı ve Python mikrosaniye yazımını korur', () {
    expect(an('2026-10-22T06:00:00Z').isoformat(), '2026-10-22T09:00:00+03:00');
    expect(
      an('2026-10-22T10:00:00+04:00').isoformat(),
      '2026-10-22T09:00:00+03:00',
    );
    expect(
      an('2026-10-22T09:00:00.1').isoformat(),
      '2026-10-22T09:00:00.100000+03:00',
    );
    final t = an('2026-10-22T23:59:59.999999+03:00');
    expect(
      t.ekle(const Duration(microseconds: 1)).isoformat(),
      '2026-10-23T00:00:00+03:00',
    );
    expect(
      t.farkAl(t.ekle(const Duration(microseconds: -1))).inMicroseconds,
      1,
    );
    expect(kodla({'an': t}), '{"an":"2026-10-22T23:59:59.999999+03:00"}');
  });

  test('SN-1: negatif fark, metinde modelin yorumuyla okunur', () {
    expect(
      an('2026-10-22T09:00:00-05:00').isoformat(),
      '2026-10-22T09:00:00+03:00',
    );
    expect(
      an(An.parse('2026-10-22T09:00:00-05:00')).isoformat(),
      '2026-10-22T17:00:00+03:00',
    );
  });

  test('Gün dönüşümü yerel gece yarısını ve saat farkını gözetir', () {
    expect(gun(an('2026-10-22T22:00:00Z')).isoformat(), '2026-10-23');
    expect(
      gunAni('2026-10-23', '17:00:00.000001').isoformat(),
      '2026-10-23T17:00:00.000001+03:00',
    );
    expect(
      gunAni(Gun(2026, 10, 23), '17:00+05:00').isoformat(),
      '2026-10-23T17:00:00+03:00',
    );
    expect(
      () => an(DateTime(2026, 10, 22)),
      throwsA(
        isA<ModelHatasi>().having(
          (e) => e.neden,
          'neden',
          'Saat dilimi zorunlu',
        ),
      ),
    );
    expect(() => gun('2026-02-30'), throwsA(isA<ModelHatasi>()));
  });

  test('Saat arayüzü gerçek saat ile demo saatini ayırır', () {
    final s = Saat('2026-10-22T09:00:00+03:00', demo: true);
    s.ilerlet('2026-10-22T10:00:00+03:00');
    expect(s.saatKaydirma, const Duration(hours: 1));
    expect(s.gercek().isoformat(), '2026-10-22T09:00:00+03:00');
    expect(
      () => s.ilerlet('2026-10-22T08:00:00+03:00'),
      throwsA(isA<ModelHatasi>()),
    );
  });

  test('Saat ölçümü gidiş dönüş ortasını kalıcı yazar', () {
    final depo = BellekDeposu();
    final c = Cihaz(
      'K017',
      'T',
      Saat('2026-10-22T09:00:00+03:00'),
      yerelDepo: depo,
    );
    c.saatFarkiOlc(
      '2026-10-22T09:00:00+03:00',
      '2026-10-22T09:00:05+03:00',
      '2026-10-22T09:00:02+03:00',
    );
    expect(depo.oku()!['fark_saniye'], 4);
    expect(c.simdiDuzeltilmis().isoformat(), '2026-10-22T09:00:04+03:00');
    // timedelta / 2 yarım mikrosaniyeyi en yakın çifte yuvarlar.
    c.saatFarkiOlc(
      '2026-10-22T09:00:00+03:00',
      '2026-10-22T09:00:00+03:00',
      '2026-10-22T09:00:00.000003+03:00',
    );
    expect(c.veri['fark_saniye'], -0.000002);
  });

  test('Tazelik geleceği reddeder, 30 saniye sınırı dahildir', () {
    final c = Cihaz('K017', 'T', Saat('2026-10-22T09:00:30+03:00'));
    expect(c.tazelik(true, '2026-10-22T09:00:00+03:00'), isTrue);
    expect(c.tazelik(true, '2026-10-22T08:59:59.999999+03:00'), isFalse);
    expect(c.tazelik(true, '2026-10-22T09:00:30.000001+03:00'), isFalse);
    expect(c.tazelik(false, '2026-10-22T09:00:30+03:00'), isFalse);
    expect(c.tazelik(true, null), isFalse);
  });
}
