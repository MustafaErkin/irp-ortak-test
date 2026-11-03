import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:irp_uygulama/ortak/eylem_adlari.dart';

void main() {
  test('Kataloğun bütün eylemlerinin geçmiş zamanlı adı vardır', () {
    final katalog = jsonDecode(
      File('../../modul_kiti/cekirdek_katalogu.json').readAsStringSync(),
    ) as Map;
    expect(eylemAdlari.keys.toSet(), (katalog['eylemler'] as Map).keys.toSet());
    expect(eylemAdlari.length, 91);
    for (final ad in eylemAdlari.values) {
      expect(ad.trim(), isNotEmpty);
      expect(ad, isNot(contains('.')));
    }
    expect(eylemAdi('BILDIRIM.GORDUM'), 'Bildirimi gördü');
    expect(eylemAdi('YENI.KOD'), 'YENI.KOD');
  });
}
