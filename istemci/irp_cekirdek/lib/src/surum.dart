import 'dart:convert';

import 'package:crypto/crypto.dart';

import 'olay.dart';

// Kaynak: referans/cevap_anahtari/model/irp/surum.py:5 (META).
const meta = {
  'surum',
  'son_hesap_ani',
  'son_olay',
  'olusma_ani',
  'kural_versiyonu',
};

// Kaynak: referans/cevap_anahtari/model/irp/surum.py:7 (is_alanlari).
dynamic isAlanlari(dynamic x) {
  if (x is Map) {
    return <String, dynamic>{
      for (final e in x.entries)
        if (!meta.contains(e.key)) e.key as String: isAlanlari(e.value),
    };
  }
  if (x is List) return x.map(isAlanlari).toList();
  return x;
}

// Kaynak: referans/cevap_anahtari/model/irp/surum.py:12 (ozet).
String ozet(dynamic x) => sha256.convert(utf8.encode(kodla(x))).toString();
