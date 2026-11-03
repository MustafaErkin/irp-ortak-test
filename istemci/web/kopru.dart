// T20: Sınanmış Dart istemci çekirdeğini yerel web arayüzüne açar.
// İş kuralları ve kimlik algoritması bu dosyada yeniden yazılmaz.
import 'dart:convert';
import 'dart:js_interop';

import 'package:irp_cekirdek/irp_cekirdek.dart';

@JS('irpCoreCall')
external set coreCall(JSFunction value);

Cihaz? _cihaz;
Map<String, dynamic> _semalar = {};

Map<String, dynamic> map(dynamic x) =>
    Map<String, dynamic>.from(x as Map? ?? {});
List<Map<String, dynamic>> maps(dynamic x) =>
    (x as List? ?? []).map(map).toList();

Future<JSString> run(String source) async {
  try {
    final q = map(jsonDecode(source));
    dynamic value;
    switch (q['op']) {
      case 'init':
        _semalar = map(q['semalar']);
        _cihaz = Cihaz(
          q['kisi'] as String,
          q['harf'] as String?,
          SistemSaati(),
          yerelDepo: BellekDeposu(q['veri'] == null ? null : map(q['veri'])),
        );
        value = true;
      case 'sync':
        _cihaz!.sayaciEsitle(List<String>.from(q['kimlikler'] as List));
        if (q['sunucu'] != null) {
          _cihaz!.saatFarkiOlc(q['t0'], q['sunucu'], q['t1']);
        }
        value = true;
      case 'lists':
        value = listeHedefleri({
          'eylem_kodu': q['kod'],
          'girdiler': q['girdiler'],
        });
      case 'prepare':
        final kod = q['kod'] as String;
        final g = map(q['girdiler']);
        final hs = maps(q['hedefler']);
        final hal = map(q['hal']);
        if (_semalar[kod]?['sinif'] != 'TANIKLIK') {
          value = _cihaz!.yonetimHazirla(
            kod,
            hal,
            eylemSemalari: _semalar,
            baglanti: q['baglanti'] == true,
            okumaAni: q['okuma_ani'],
            hedefler: hs,
            girdiler: g,
            adina: q['adina'] as String?,
          );
        } else if (calisan.contains(kod)) {
          value = await _cihaz!.olayYaz(
            kod,
            hal,
            isler: map(q['isler']).map((k, v) => MapEntry(k, map(v))),
            liste: List<String>.from(q['liste'] as List? ?? []),
            isKimligi:
                hs.where((x) => x['tur'] == 'IS').firstOrNull?['kimlik']
                    as String?,
            girdiler: g,
            sabitMola: q['sabit_mola'] == true,
          );
        } else {
          value = _cihaz!.tanikliYaz(
            kod,
            hal,
            eylemSemalari: _semalar,
            hedefler: hs,
            girdiler: g,
          );
        }
        value['eylem_versiyonu'] = _semalar[kod]['eylem_versiyonu'];
        value['adina'] = q['adina'];
        value['kanit'] = q['kanit'] ?? [];
        if (kod == 'KISI.DEGISTIRDIM' &&
            value['girdiler']['gecerli_baslangic'] == null) {
          value['girdiler']['gecerli_baslangic'] = value['oldugu_an'];
        }
        _cihaz!.kaydet();
      case 'result':
        final entry = _cihaz!.veri['gunluk'][q['kimlik']];
        if (entry == null) throw StateError('Olay günlüğü bulunamadı');
        entry['sonuc'] = q['sonuc'];
        entry['durum'] = q['durum'];
        _cihaz!.kaydet();
        value = true;
      case 'screen':
        value = _cihaz!.ekranHali(
          map(q['hal']),
          isler: map(q['isler']).map((k, v) => MapEntry(k, map(v))),
          liste: List<String>.from(q['liste'] as List? ?? []),
        );
        final d = map(value['son_hal']);
        final list = List<String>.from(q['liste'] as List? ?? []);
        final isler = map(q['isler']);
        final selected =
            isler[d['acik_is'] ?? d['aralik_is'] ?? list.firstOrNull];
        value['kapilar'] = {
          for (final code in calisan)
            code: kapi(
              d,
              code,
              selected == null ? null : map(selected),
              list.firstOrNull,
              sabit: d['durum'] == 'SABIT_MOLADA',
            ),
        };
      default:
        throw ArgumentError('Bilinmeyen köprü işlemi');
    }
    return jsonEncode({'ok': true, 'value': value, 'state': _cihaz?.veri}).toJS;
  } catch (e) {
    return jsonEncode({'ok': false, 'error': e.toString()}).toJS;
  }
}

void main() {
  coreCall = ((JSString source) => run(source.toDart).toJS).toJS;
}
