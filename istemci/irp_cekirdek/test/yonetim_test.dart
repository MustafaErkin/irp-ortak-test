import 'dart:convert';
import 'dart:io';

import 'package:irp_cekirdek/irp_cekirdek.dart';
import 'package:test/test.dart';

void main() {
  final semalar = Map<String, dynamic>.from(
    jsonDecode(File('../../referans/eylem_semalari.json').readAsStringSync())
        as Map,
  );
  const t = '2026-10-22T10:40:00+03:00';
  Cihaz cihaz() => Cihaz('K009', 'W', Saat(t));
  const isH = {'tur': 'IS', 'kimlik': 'IS-1', 'surum': 'okunan-is-surumu'};
  const listeH = {
    'tur': 'LISTE',
    'kimlik': 'K017',
    'surum': 'okunan-liste-surumu',
  };
  test('Yönetim okunan nesne ve liste sürümünü aynen taşır; tanıklık kuyruğuna girmez', () {
    final c = cihaz();
    final e = c.yonetimHazirla(
      'IS.ATADIM',
      {'son_hesap_ani': t},
      eylemSemalari: semalar,
      baglanti: true,
      okumaAni: t,
      hedefler: [isH, listeH],
      girdiler: {'kisi': 'K017', 'sira': 1},
    );
    expect(e['neyin_ustunde'], [isH, listeH]);
    expect(c.bekleyenSayisi(), 0);
    expect(c.veri['gunluk'][e['olay_kimligi']]['durum'], 'GONDERILEMEDI');
  });
  test('Bayat ve çevrimdışı yönetim kimlik tüketmeden kapanır', () {
    for (final online in [true, false]) {
      final c = cihaz();
      expect(
        () => c.yonetimHazirla(
          'IS.ATADIM',
          {},
          eylemSemalari: semalar,
          baglanti: online,
          okumaAni: '2026-10-22T10:39:00+03:00',
          hedefler: [isH, listeH],
          girdiler: {'kisi': 'K017', 'sira': 1},
        ),
        throwsA(isA<ModelHatasi>()),
      );
      expect(c.veri['gunluk'], isEmpty);
      expect(c.olayKimligiUret(), 'K009-2610220001-W');
    }
  });
  test('Devir her iki okunan liste sürümünü gerektirir', () {
    final c = cihaz();
    expect(
      () => c.yonetimHazirla(
        'IS.DEVRETTIM',
        {},
        eylemSemalari: semalar,
        baglanti: true,
        okumaAni: t,
        hedefler: [isH, listeH],
        girdiler: {'kimden': 'K017', 'kime': 'K023'},
      ),
      throwsA(isA<ModelHatasi>()),
    );
  });
  test(
    'Adına süre ekleme lider kimliğini korur; tanıklık bu kapıdan geçmez',
    () {
      final c = cihaz();
      final e = c.yonetimHazirla(
        'IS.SURE_EKLEDIM',
        {'son_hesap_ani': t},
        eylemSemalari: semalar,
        baglanti: true,
        okumaAni: t,
        hedefler: [isH],
        girdiler: {
          'baslangic': t,
          'bitis': t,
          'aciklama': 'Kayıt',
          'is_bitti': false,
        },
        adina: 'K017',
      );
      expect(e['adina'], 'K017');
      expect(e['kim'], 'K009');
      expect(
        () => c.yonetimHazirla(
          'NOT.YAZDIM',
          {},
          eylemSemalari: semalar,
          baglanti: true,
          okumaAni: t,
          hedefler: [],
          girdiler: {'metin': 'Not'},
        ),
        throwsA(isA<ModelHatasi>()),
      );
    },
  );
}
