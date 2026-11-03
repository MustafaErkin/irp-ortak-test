import 'dart:convert';

import 'package:idb_shim/idb_browser.dart';

import '../bulut/uygulama_bulutu.dart';
import 'kalici_depo.dart';

Future<KaliciDepo> platformDeposu({String senaryo = ''}) async =>
    IndexedDbDeposu.ac(
      idbFactoryNative,
      ad: senaryo.isEmpty ? 'irp-telefon-v1' : 'irp-telefon-v1:$senaryo',
    );

class IndexedDbDeposu implements KaliciDepo {
  IndexedDbDeposu._(this._db);
  final Database _db;
  int _surum = 0;
  static Future<IndexedDbDeposu> ac(
    IdbFactory factory, {
    String ad = 'irp-telefon-v1',
  }) async {
    final db = await factory.open(
      ad,
      version: 1,
      onUpgradeNeeded: (e) {
        e.database.createObjectStore('cihaz');
      },
    );
    return IndexedDbDeposu._(db);
  }

  @override
  Future<Json> oku() async {
    final tx = _db.transaction('cihaz', idbModeReadOnly);
    final s = await tx.objectStore('cihaz').getObject('durum') as String?;
    await tx.completed;
    if (s == null) return {};
    final zarf = jsonDecode(s) as Map;
    _surum = zarf['surum'] as int;
    return Json.from(zarf['veri'] as Map);
  }

  @override
  Future<void> yaz(Json veri) async {
    final tx = _db.transaction('cihaz', idbModeReadWrite);
    final store = tx.objectStore('cihaz');
    final eski = await store.getObject('durum') as String?;
    final surum = eski == null ? 0 : jsonDecode(eski)['surum'] as int;
    if (surum != _surum) {
      tx.abort();
      // Başka sekmenin sayacını ezerek aynı kimliği üretme.
      try {
        await tx.completed;
      } catch (_) {
        /* Beklenen işlem iptali. */
      }
      throw StateError('Bu cihaz başka sekmede açık. Sayfayı yeniden aç');
    }
    await store.put(jsonEncode({'surum': surum + 1, 'veri': veri}), 'durum');
    await tx.completed;
    _surum = surum + 1;
  }

  void kapat() => _db.close();
}
