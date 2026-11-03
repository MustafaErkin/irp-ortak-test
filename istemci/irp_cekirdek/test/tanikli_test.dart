import 'dart:convert';
import 'dart:io';

import 'package:irp_cekirdek/irp_cekirdek.dart';
import 'package:test/test.dart';

void main() {
  final semalar = jsonDecode(
    File('../../referans/eylem_semalari.json').readAsStringSync(),
  ) as Map<String, dynamic>;
  Cihaz cihaz() =>
      Cihaz('K017', 'T', Saat('2026-10-22T10:40:00+03:00'), telefon: true);
  for (final kod in [
    'NOT.YAZDIM',
    'GOREV.KABUL_ETTIM',
    'GOREV.TAMAMLADIM',
    'BILDIRIM.GORDUM',
    'GUN_SONU.GONDERDIM',
    'DURUS.BASLADI',
  ]) {
    test('$kod kişi günü kapısından bağımsız aynı günlüğe yazılır', () {
      final c = cihaz();
      final e = c.tanikliYaz(
        kod,
        bosHal(),
        eylemSemalari: semalar,
        hedefler: [
          {'tur': 'PROJE', 'kimlik': '2509084', 'surum': null},
        ],
        girdiler: {'metin': 'Deneme'},
      );
      expect(e['olay_kimligi'], 'K017-2610220001-T');
      expect(e['kim'], 'K017');
      expect(e['cihaz'], 'TEL-K017');
      expect(e['neyin_ustunde'][0]['tur'], 'PROJE');
      expect(c.veri['gunluk'][e['olay_kimligi']]['durum'], 'BEKLIYOR');
    });
  }
  test('kişi günü ve tanıklı yazım ortak sayacı sürdürür', () async {
    final c = cihaz();
    final a = await c.olayYaz('MESAI.GIRDIM', bosHal());
    final b = c.tanikliYaz('NOT.YAZDIM', bosHal(), eylemSemalari: semalar);
    final yeniden = Cihaz('K017', 'T', c.saat, yerelDepo: c.yerelDepo);
    expect(a['olay_kimligi'], endsWith('0001-T'));
    expect(b['olay_kimligi'], endsWith('0002-T'));
    expect(yeniden.olayKimligiUret(), endsWith('0003-T'));
    expect(yeniden.bekleyenSayisi(), 2);
  });
  test('yönetim, bilinmeyen ve kişi günü eylemleri kapıyı aşamaz', () {
    final c = cihaz();
    for (final kod in ['IS.ATADIM', 'BILINMEYEN', 'IS.TAMAMLADIM']) {
      expect(
        () => c.tanikliYaz(kod, bosHal(), eylemSemalari: semalar),
        throwsA(isA<ModelHatasi>()),
      );
    }
    expect(c.bekleyenSayisi(), 0);
    expect(c.veri['sayaclar'], isEmpty);
  });
}
