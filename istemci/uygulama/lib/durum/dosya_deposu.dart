import 'dart:convert';
import 'dart:io';

import 'package:path_provider/path_provider.dart';

import '../bulut/uygulama_bulutu.dart';
import 'kalici_depo.dart';

Future<KaliciDepo> platformDeposu({String senaryo = ''}) async {
  final ek = senaryo.isEmpty ? '' : '-${Uri.encodeComponent(senaryo)}';
  return DosyaKaliciDepo(
    File('${(await getApplicationSupportDirectory()).path}/irp-telefon$ek.json'),
  );
}

class DosyaKaliciDepo implements KaliciDepo {
  DosyaKaliciDepo(this.dosya);
  final File dosya;
  @override
  Future<Json> oku() async => await dosya.exists()
      ? Json.from(jsonDecode(await dosya.readAsString()) as Map)
      : {};
  @override
  Future<void> yaz(Json veri) async {
    await dosya.parent.create(recursive: true);
    final gecici = File('${dosya.path}.yeni');
    await gecici.writeAsString(jsonEncode(veri), flush: true);
    await gecici.rename(dosya.path);
  }
}
