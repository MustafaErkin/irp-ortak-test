import 'dart:convert';
import 'dart:io';

import 'package:irp_cekirdek/irp_cekirdek.dart';
import 'package:test/test.dart';

import '../tool/vektor_kosucu.dart';

void main() {
  test('Referansın tüm kanonik JSON ve SHA-256 örnekleri eşleşir', () {
    final ornekler = jsonDecode(
      File('${referansKoku().path}/kanonik_ornekler.json').readAsStringSync(),
    ) as List;
    for (final o in ornekler) {
      final is_ = isAlanlari(o['girdi']);
      expect(is_, o['is_alanlari']);
      expect(kodla(is_), o['kanonik_json']);
      expect(ozet(is_), o['sha256']);
    }
  });

  test('Özet Türkçe, kod noktası sırası ve Python sayı biçimini korur', () {
    expect(
      kodla({'😀': 1, '\ue000': 2, 'ad': 'İş\n'}),
      '{"ad":"İş\\n","":2,"😀":1}',
    );
    expect(kodla([1.0, 1e-7, 1e16, -0.0]), '[1.0,1e-07,1e+16,-0.0]');
    expect(ozet(['A', 'B']), isNot(ozet(['B', 'A'])));
    expect(ozet({'surum': 'A'}), isNot(ozet({'surum': 'B'})));
  });

  test('B36 iç içe alanları dışlar, iş anlarını yerelle karşılaştırır', () {
    expect(
      farklar(
        {
          'x': {'surum': 1, 'kabul_ani': '2026-10-22T06:00:00Z'},
        },
        {
          'x': {'surum': 2, 'kabul_ani': '2026-10-22T09:00:00+03:00'},
        },
      ),
      isEmpty,
    );
    expect(
      farklar(
        {
          'x': {'durum': 'A'},
        },
        {
          'x': {'durum': 'B'},
        },
      ),
      isNotEmpty,
    );
    expect(farklar({'x': 1}, {'x': 1.0000009}), isEmpty);
    expect(farklar({'x': 1}, {'x': 1.000002}), isNotEmpty);
  });

  test('Karşılaştırma null, eksik, boş, bool ve parayı karıştırmaz', () {
    for (final (a, b) in [
      (<String, dynamic>{}, {'x': null}),
      ({'x': null}, {'x': []}),
      ({'x': true}, {'x': 1}),
      ({'x': '1.00'}, {'x': 1}),
      ({'x': '1.00'}, {'x': '1.0'}),
    ]) {
      expect(farklar(a, b), isNotEmpty);
    }
    expect(kanonik(coz({r'$ondalik': '1.005'})), '1.00');
    expect(kanonik(coz({r'$ondalik': '1.015'})), '1.02');
    expect(kanonik(coz({r'$ondalik': '-0.001'})), '-0.00');
  });

  test('Yalnız tanımlı dört dizi sırasızdır; tekrarlar korunur', () {
    for (final alan in [
      'araliklar',
      'hassas_ekler',
      'kisi_gecmisi',
      'olay_kimlikleri',
    ]) {
      expect(
        farklar(
          {
            alan: ['B', 'A'],
          },
          {
            alan: ['A', 'B'],
          },
        ),
        isEmpty,
      );
      expect(
        farklar(
          {
            alan: ['A', 'A'],
          },
          {
            alan: ['A'],
          },
        ),
        isNotEmpty,
      );
    }
    expect(
      farklar(
        {
          'listeler': ['B', 'A'],
        },
        {
          'listeler': ['A', 'B'],
        },
      ),
      isNotEmpty,
    );
    expect(
      kanonik(
        coz({
          r'$kume': ['B', 'A', 'A'],
        }),
      ),
      ['A', 'B'],
    );
  });

  test('Hata zarfı yalnız model hatalarını türü ve nedeni ile taşır', () {
    expect(
      dene(() => throw const ModelHatasi('ValueError', 'Cihaz kapisi kapali')),
      {'hata_turu': 'ValueError', 'neden': 'Cihaz kapisi kapali'},
    );
    expect(
      () => dene(() => throw StateError('Çeviri hatası')),
      throwsStateError,
    );
  });
}
