import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as im;
import 'package:json_schema/json_schema.dart';
import 'package:irp_uygulama/bulut/uygulama_bulutu.dart';
import 'package:irp_uygulama/durum/kalici_depo.dart';
import 'package:irp_uygulama/durum/kanit.dart';

import 'destek.dart';

void main() {
  final zarf = JsonSchema.create(
    dosya('../../referans/cevap_anahtari/olay_semasi.json'),
  );
  void denetle(Json e) {
    final sonuc = zarf.validate(e, validateFormats: true);
    expect(
      sonuc.isValid,
      isTrue,
      reason: '${e['eylem_kodu']}: ${sonuc.errors}',
    );
    final girdi = JsonSchema.create(semalar[e['eylem_kodu']]['girdi_semasi'])
        .validate(e['girdiler'], validateFormats: true);
    expect(girdi.isValid, isTrue, reason: '${girdi.errors}');
  }

  for (final (durum, kod, girdiler) in <(String, String, Json)>[
    ('mesai_disi', 'MESAI.GIRDIM', {}),
    ('calisiyor', 'MESAI.CIKTIM', {}),
    ('hazir', 'IS.BASLADIM', {}),
    ('calisiyor', 'IS.MOLA_VERDIM', {}),
    ('calisiyor', 'IS.MOLA_VERDIM', {'not': 'Sigara'}),
    (
      'calisiyor',
      'IS.ARIZA_BILDIRDIM',
      {'neden': 'DURUS_NEDENI.MAKINE_KAYNAK'},
    ),
    ('calisiyor', 'IS.ARIZA_BILDIRDIM', {'not': 'Akım vermiyor'}),
    (
      'calisiyor',
      'IS.ARIZA_BILDIRDIM',
      {'neden': 'DURUS_NEDENI.MAKINE_DIGER', 'not': 'Ses geliyor'},
    ),
    ('molada', 'IS.DEVAM_ETTIM', {}),
    ('calisiyor', 'IS.TAMAMLADIM', {}),
    (
      'anlik',
      'IS.TAMAMLADIM',
      {'makine_bitis_ani': '2026-10-22T10:39:00+03:00'},
    ),
    (
      'calisiyor',
      'NOT.YAZDIM',
      {
        'metin': 'Ölçü kontrolü',
        'etiketler': ['Ölçü'],
      },
    ),
    (
      'calisiyor',
      'BILDIRIM.GORDUM',
      {
        'bildirimler': ['B-SENTETIK-1'],
      },
    ),
    ('calisiyor', 'GOREV.KABUL_ETTIM', {}),
    ('calisiyor', 'GOREV.TAMAMLADIM', {}),
    ('calisiyor', 'GUN_SONU.GONDERDIM', {'gun': '2026-10-22'}),
    (
      'calisiyor',
      'DURUS.BASLADI',
      {'kapsam': 'FIRMA', 'neden': 'Sentetik elektrik kesintisi'},
    ),
  ]) {
    test('şema: $kod $girdiler', () async {
      final (d, b, _) = await hazir(durum: durum);
      b.cevrimici = false;
      final e = await d.olay(
        kod,
        girdiler: girdiler,
        hedefler: kod == 'NOT.YAZDIM'
            ? [
                {'tur': 'PARCA', 'kimlik': '2509084_07_04-63', 'surum': null},
              ]
            : kod.startsWith('GOREV.')
            ? [
                {'tur': 'GOREV', 'kimlik': 'K004-2610220003-M', 'surum': null},
              ]
            : [],
      );
      await d.gonderici.tetikle();
      denetle(e);
    });
  }
  test('şema: fotoğraflı not ve dört izinli hedef', () async {
    final (d, b, _) = await hazir();
    b.cevrimici = false;
    final foto = HazirFoto.hazirla(
      Uint8List.fromList(im.encodePng(im.Image(width: 16, height: 16))),
      'kanit.png',
    );
    for (final tur in ['PARCA', 'GOREV', 'PROJE', 'NESNE']) {
      final e = await d.olay(
        'NOT.YAZDIM',
        girdiler: {'metin': 'Deneme'},
        hedefler: [
          {'tur': tur, 'kimlik': 'SENTETIK', 'surum': null},
        ],
        fotograflar: [foto],
      );
      await d.gonderici.tetikle();
      denetle(e);
    }
  });
  test('şema negatif kontroller: kimlik, zaman, eksik not ve kanıt', () async {
    final (d, b, _) = await hazir();
    b.cevrimici = false;
    final e = await d.olay(
      'NOT.YAZDIM',
      girdiler: {'metin': 'Doğru'},
      hedefler: notHedefi,
    );
    await d.gonderici.tetikle();
    for (final degis in <Json>[
      {'olay_kimligi': 'yanlis'},
      {'oldugu_an': 'yarın'},
      {'girdiler': {}},
      {
        'kanit': [
          {'dosya_kimligi': 'yanlis', 'boyut': -1},
        ],
      },
    ]) {
      final yanlis = kopya(e)..addAll(degis);
      expect(
        zarf.validate(yanlis, validateFormats: true).isValid,
        isFalse,
        reason: '$degis',
      );
    }
  });
}
