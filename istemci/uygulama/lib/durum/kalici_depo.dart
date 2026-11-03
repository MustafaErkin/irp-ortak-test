import 'dart:convert';

import '../bulut/uygulama_bulutu.dart';

/// Tüm oturum, sayaç, günlük, önbellek ve kanıtlar tek işlemde saklanır.
abstract interface class KaliciDepo {
  Future<Json> oku();
  Future<void> yaz(Json veri);
}

Json kopya(Json veri) => Json.from(jsonDecode(jsonEncode(veri)) as Map);

class BellekKaliciDepo implements KaliciDepo {
  BellekKaliciDepo([Json? ilk]) : veri = kopya(ilk ?? {});
  Json veri;
  @override
  Future<Json> oku() async => kopya(veri);
  @override
  Future<void> yaz(Json veri) async {
    this.veri = kopya(veri);
  }
}
