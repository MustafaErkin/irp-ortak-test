import 'dart:convert';
import 'dart:io';

import 'package:irp_cekirdek/irp_cekirdek.dart';
import 'package:test/test.dart';

void main() {
  test('27 saf geçiş örneği Python modeliyle alan alan eşleşir', () {
    final ornekler = jsonDecode(
      File('test/veri/gecis_model.json').readAsStringSync(),
    ) as List;
    expect(ornekler, hasLength(27));
    for (final o in ornekler) {
      final g = o['girdi'], k = g['kwargs'];
      final once = kodla(g);
      final (hal, yan) = gecis(
        g['hal'],
        g['kod'],
        is_: k['is_'],
        basIs: k['bas_is'],
        neden: k['neden'],
      );
      expect([hal, yan], o['beklenen'], reason: o['ad']);
      expect(kodla(g), once, reason: '${o['ad']} girdisi değişti');
    }
  });
}
