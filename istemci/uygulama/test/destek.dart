import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:json_schema/json_schema.dart';
import 'package:irp_cekirdek/irp_cekirdek.dart';
import 'package:irp_uygulama/bulut/uygulama_bulutu.dart';
import 'package:irp_uygulama/bulut/gosteri_kisisi.dart';
import 'package:irp_uygulama/durum/kalici_depo.dart';
import 'package:irp_uygulama/durum/pin.dart';
import 'package:irp_uygulama/durum/uygulama_durumu.dart';
import 'package:irp_uygulama/sahte/fikstur_bulutu.dart';

Json dosya(String yol) =>
    Json.from(jsonDecode(File(yol).readAsStringSync()) as Map);
final fikstur = dosya('test/fikstur/telefon.json');
final semalar = dosya('../../referans/eylem_semalari.json');
final harita = Map<String, String>.from(dosya('assets/cizimler/harita.json'));
final _pin = Pin.olustur('654321');
const notHedefi = <Json>[
  {'tur': 'PARCA', 'kimlik': '2509084_07_04-63', 'surum': null},
];
final _zarf = JsonSchema.create(
  dosya('../../referans/cevap_anahtari/olay_semasi.json'),
);

void olayDogrula(Json e) {
  final z = _zarf.validate(e, validateFormats: true);
  expect(z.isValid, isTrue, reason: '${e['eylem_kodu']} zarf: ${z.errors}');
  final g = JsonSchema.create(semalar[e['eylem_kodu']]['girdi_semasi'])
      .validate(e['girdiler'], validateFormats: true);
  expect(g.isValid, isTrue, reason: '${e['eylem_kodu']} girdi: ${g.errors}');
  final s = semalar[e['eylem_kodu']];
  if (s['zorunlu_hedef_turu'] != null) {
    expect(
      (e['neyin_ustunde'] as List).any(
        (h) => h['tur'] == s['zorunlu_hedef_turu'],
      ),
      isTrue,
    );
  }
  if (s['tek_gorev_hedefi'] == true) {
    expect(
      (e['neyin_ustunde'] as List).where((h) => h['tur'] == 'GOREV').length,
      1,
    );
  }
}

Future<(UygulamaDurumu, FiksturBulutu, BellekKaliciDepo)> hazir({
  String durum = 'calisiyor',
  bool acik = true,
  bool telefonKipi = false,
  bool mvpMesaiSerbest = false,
  List<GosteriKisisi> gosteriKisileri = const [],
}) async {
  final b = FiksturBulutu(fikstur, durum: durum);
  // Eski model fikstürüne yeni TELEFON okumasının açık mesai bağlamı eklenir.
  // İzin/tatil/eksik pencere vakaları kendi testlerinde bu değeri değiştirir.
  if (telefonKipi) {
    b.okumalar['TELEFON']['deger']['calisma_penceresi'] = {
      'gun': '2026-10-22',
      'mesai': [
        ['2026-10-22T08:00:00+03:00', '2026-10-22T18:00:00+03:00'],
      ],
      'calisma': [
        ['2026-10-22T08:00:00+03:00', '2026-10-22T12:00:00+03:00'],
        ['2026-10-22T13:00:00+03:00', '2026-10-22T18:00:00+03:00'],
      ],
      'kaynak_ani': '2026-10-22T10:40:00+03:00',
    };
  }
  final yerel = BellekKaliciDepo({
    'kayit': {
      'kisi': 'K017',
      'ad': 'K017',
      'harf': 'T',
      'pin': await _pin,
      'oturum': {'refresh_token': 'sentetik-oturum'},
      'yanlis': 0,
    },
  });
  final d = UygulamaDurumu(
    bulut: b,
    depo: yerel,
    semalar: semalar,
    saat: Saat('2026-10-22T10:40:00+03:00'),
    telefonKipi: telefonKipi,
    mvpMesaiSerbest: mvpMesaiSerbest,
    gosteriKisileri: gosteriKisileri,
  );
  await d.yukle();
  d.acik = true;
  await d.yenile();
  d.acik = acik;
  addTearDown(() async {
    await d.gonderici.tetikle();
    d.dispose();
    await b.dispose();
    // Ekran ve durum testlerinin ürettiği her olay da iki yetkili şemadan geçer.
    for (final k in d.gunluk) {
      final e = k['olay'];
      expect(
        _zarf.validate(e, validateFormats: true).isValid,
        isTrue,
        reason: '${e['eylem_kodu']} zarfı',
      );
      expect(
        JsonSchema.create(semalar[e['eylem_kodu']]['girdi_semasi'])
            .validate(e['girdiler'], validateFormats: true)
            .isValid,
        isTrue,
      );
    }
  });
  return (d, b, yerel);
}
