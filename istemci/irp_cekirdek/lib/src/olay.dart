import 'dart:convert';

import 'saat.dart';
import 'veri.dart';

// Kaynak: referans/cevap_anahtari/model/irp/olay.py:8 (kodla).
String kodla(dynamic deger) {
  if (deger is Map) {
    final anahtarlar = deger.keys.cast<String>().toList()..sort(metinSirasi);
    return '{${anahtarlar.map((k) => '${jsonEncode(k)}:${kodla(deger[k])}').join(',')}}';
  }
  if (deger is List) return '[${deger.map(kodla).join(',')}]';
  if (deger is An) return jsonEncode(deger.isoformat());
  if (deger is Gun) return jsonEncode(deger.isoformat());
  if (deger is DateTime) {
    return jsonEncode(An(deger, deger.timeZoneOffset).isoformat());
  }
  if (deger is double) return _ondalikKodla(deger);
  if (deger == null || deger is String || deger is bool || deger is int) {
    return jsonEncode(deger);
  }
  return jsonEncode(deger.toString());
}

/// json.dumps'ın üs eşiği ve iki basamaklı üs yazımı.
String _ondalikKodla(double n) {
  if (n.isNaN) return 'NaN';
  if (n.isInfinite) return n.isNegative ? '-Infinity' : 'Infinity';
  if (n != 0 && (n.abs() < 1e-4 || n.abs() >= 1e16)) {
    final parcalar = n.toStringAsExponential().split('e');
    final us = int.parse(parcalar[1]);
    final katsayi = parcalar[0].replaceFirst(RegExp(r'\.0$'), '');
    return '${katsayi}e${us < 0 ? '-' : '+'}${us.abs().toString().padLeft(2, '0')}';
  }
  return n.toString();
}

// Kaynak: referans/cevap_anahtari/model/irp/olay.py:72 (hedefler).
List<String> hedefler(Sozluk e, String tur) => [
  for (final x in e['neyin_ustunde'] as List)
    if (x['tur'] == tur) x['kimlik'] as String,
];
