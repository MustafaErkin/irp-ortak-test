import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:irp_cekirdek/dosya_deposu.dart';
import 'package:irp_cekirdek/irp_cekirdek.dart';
import 'package:test/test.dart';

const zaman = '2026-10-22T09:00:00+03:00';
Cihaz cihaz({YerelDepo? depo}) =>
    Cihaz('K017', 'T', Saat(zaman), yerelDepo: depo, telefon: true);
Map<String, dynamic> isBilgisi([String kimlik = 'I1']) => {
  'kimlik': kimlik,
  'tur': 'SURELI',
  'durum': 'SIRADA',
  'onay_gerekli': false,
  'surum': 'ekran-is-surumu',
};
Map<String, dynamic> hal() => {
  ...bosHal(),
  'son_hesap_ani': zaman,
  'durum': 'CALISMIYOR',
};
Map<String, dynamic> olay(
  String kimlik,
  String t, {
  String kod = 'MESAI.GIRDIM',
  String? isKimligi,
}) => {
  'olay_kimligi': kimlik,
  'oldugu_an': t,
  'eylem_kodu': kod,
  'neyin_ustunde': [
    if (isKimligi != null) {'tur': 'IS', 'kimlik': isKimligi},
  ],
  'girdiler': <String, dynamic>{},
};

void main() {
  test('Kimlik günlük artar, saat geri alınsa da önceki sayaç korunur', () {
    final c = cihaz();
    expect(c.olayKimligiUret(), 'K017-2610220001-T');
    expect(c.olayKimligiUret(), 'K017-2610220002-T');
    c.veri['fark_saniye'] = 86400;
    expect(c.olayKimligiUret(), 'K017-2610230001-T');
    c.veri['fark_saniye'] = 0;
    expect(c.olayKimligiUret(), 'K017-2610220003-T');
  });

  test('9999 son kimliktir, taşma sayacı değiştirmez', () {
    final c = cihaz();
    c.veri['sayaclar']['261022'] = 9998;
    expect(c.olayKimligiUret(), 'K017-2610229999-T');
    expect(
      () => c.olayKimligiUret(),
      throwsA(
        isA<ModelHatasi>()
            .having((e) => e.hataTuru, 'tür', 'OverflowError')
            .having((e) => e.neden, 'neden', 'A1 kimlik alani doldu'),
      ),
    );
    expect(c.veri['sayaclar']['261022'], 9999);
  });

  test('Sayaç eşitleme kişi, gün ve harfi süzer; yereli geriletmez', () {
    final c = cihaz();
    c.veri['sayaclar'].addAll({'261022': 7, '261021': 80});
    c.sayaciEsitle([
      'K017-2610220003-T',
      'K018-2610229999-T',
      'K017-2610219999-T',
      'K017-2610229999-U',
    ]);
    expect(c.veri['sayaclar'], {'261022': 7, '261021': 80});
    c.sayaciEsitle(['K017-2610220012-T']);
    expect(c.olayKimligiUret(), 'K017-2610220013-T');
  });

  test('Yeniden kayıt tüm harfler doluysa null harf ve model hatası verir', () {
    final c = cihaz();
    final kullanilan = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('').toSet();
    expect(
      () => c.yenidenKaydol(kullanilan),
      throwsA(
        isA<ModelHatasi>().having(
          (e) => e.neden,
          'neden',
          'Cihaz harfleri doldu',
        ),
      ),
    );
    expect(c.harf, isNull);
    expect(() => c.olayKimligiUret(), throwsA(isA<ModelHatasi>()));
  });

  test('Bellek deposu yazılan ve okunan nesneleri ayırır', () {
    final d = BellekDeposu();
    final c = cihaz(depo: d);
    c.olayKimligiUret();
    c.veri['sayaclar']['261022'] = 100;
    d.oku()!['sayaclar']['261022'] = 200;
    expect(cihaz(depo: d).olayKimligiUret(), 'K017-2610220002-T');
  });

  test('Dosya deposu yarım geçici yazımdan sonra önceki kaydı açar', () {
    final dizin = Directory.systemTemp.createTempSync('irp_istemci1_');
    addTearDown(() => dizin.deleteSync(recursive: true));
    final dosya = File('${dizin.path}/cihaz #ö.json');
    final c = cihaz(depo: DosyaDeposu(dosya.path));
    c.olayKimligiUret();
    c.gunlukEkle(olay('A', zaman));
    c.saatFarkiOlc(zaman, '2026-10-22T09:00:02+03:00', zaman);
    final once = dosya.readAsStringSync();
    // Çökme kalıntısı: hedefin yanındaki .tmp dosyası yarım kalmıştır.
    File('${dizin.path}/cihaz #ö.tmp')
        .writeAsStringSync('{"sayaclar":', flush: true);
    final yeni = cihaz(depo: DosyaDeposu(dosya.path));
    expect(dosya.readAsStringSync(), once);
    expect(yeni.bekleyenSayisi(), 1);
    expect(yeni.veri['fark_saniye'], 2);
    expect(yeni.olayKimligiUret(), 'K017-2610220002-T');
    expect(jsonDecode(dosya.readAsStringSync())['sayaclar']['261022'], 2);
    expect(File('${dizin.path}/cihaz #ö.tmp').existsSync(), isFalse);
  });

  test('Başarısız kalıcı yazım kimliği çağırana vermez', () {
    final c = cihaz(depo: _YazamayanDepo());
    expect(() => c.olayKimligiUret(), throwsA(isA<FileSystemException>()));
  });

  test('Gönderim zamanı ve kimliği sıralar, her cevabı bekler', () async {
    final c = cihaz();
    c.gunlukEkle(olay('C', '2026-10-22T09:01:00+03:00'));
    c.gunlukEkle(olay('B', zaman));
    c.gunlukEkle(olay('A', zaman));
    final ilk = Completer<Map<String, dynamic>>();
    final bulut = SahteBulut(
      cevapla: (e, _) =>
          e['olay_kimligi'] == 'A' ? ilk.future : {'sonuc': 'BASARILI'},
    );
    final gonderim = c.gonderimDongusu(bulut);
    await Future<void>.delayed(Duration.zero);
    expect(bulut.cagrilar, hasLength(1));
    ilk.complete({'sonuc': 'BASARILI', 'tekrar': true});
    expect(await gonderim, isNull);
    expect(bulut.cagrilar.map((x) => x['olay']['olay_kimligi']), [
      'A',
      'B',
      'C',
    ]);
    expect(bulut.cagrilar.every((x) => x['oturum'] == 'K017'), isTrue);
    expect(c.bekleyenSayisi(), 0);
  });

  test(
    'SN-2: gönderim metin sırasını, ekran gerçek an sırasını kullanır',
    () async {
      final c = cihaz();
      c.gunlukEkle(olay('erken', '2026-10-22T09:00:00+03:00'));
      c.gunlukEkle(olay('gec', '2026-10-22T08:00:00Z', kod: 'MESAI.CIKTIM'));
      expect(
        (c.ekranHali({})['bekleyen'] as List).map((e) => e['olay_kimligi']),
        ['erken', 'gec'],
      );
      final b = SahteBulut();
      await c.gonderimDongusu(b);
      expect(b.cagrilar.map((x) => x['olay']['olay_kimligi']), [
        'gec',
        'erken',
      ]);
    },
  );

  test(
    'Bağlantı yokken sabit iki saniye bekler ve kayıt değiştirmez',
    () async {
      final c = cihaz();
      c.gunlukEkle(olay('A', zaman));
      final once = kodla(c.veri), b = SahteBulut();
      for (var n = 0; n < 3; n++) {
        expect(await c.gonderimDongusu(b, baglanti: false), {
          'bekle_saniye': 2,
          'bekleyen': 1,
        });
      }
      expect(b.cagrilar, isEmpty);
      expect(kodla(c.veri), once);
    },
  );

  test(
    'Gönderim reddi HATA olur; gönderilmiş ve hatalı kayıt tekrar gitmez',
    () async {
      final d = BellekDeposu();
      final c = cihaz(depo: d);
      c.gunlukEkle(olay('A', zaman));
      final b = SahteBulut(
        cevapla: (_, _) => {'sonuc': 'REDDEDILDI', 'neden': 'kapali'},
      );
      await c.gonderimDongusu(b);
      await c.gonderimDongusu(b);
      expect(b.cagrilar, hasLength(1));
      expect(c.veri['gunluk']['A']['durum'], 'HATA');
      expect(cihaz(depo: d).veri['gunluk']['A']['sonuc']['neden'], 'kapali');
    },
  );

  test('Temizlik yalnız 30 günden eski gönderilmiş kayıtları siler', () {
    final c = cihaz();
    for (final durum in [
      'GONDERILDI',
      'BEKLIYOR',
      'HATA',
      'RED',
      'GONDERILEMEDI',
    ]) {
      c.gunlukEkle(olay(durum, '2026-09-21T09:00:00+03:00'));
      c.veri['gunluk'][durum]['durum'] = durum;
    }
    c.gunlukEkle(olay('sinir', '2026-09-22T09:00:00+03:00'));
    c.veri['gunluk']['sinir']['durum'] = 'GONDERILDI';
    c.gunlukTemizle();
    expect(
      c.veri['gunluk'].keys,
      unorderedEquals(['BEKLIYOR', 'HATA', 'RED', 'GONDERILEMEDI', 'sinir']),
    );
  });

  test(
    'Çevrimdışı tanıklık tam olay zarfıyla kalıcı kuyruğa yazılır',
    () async {
      final d = BellekDeposu();
      final c = cihaz(depo: d);
      final b = SahteBulut();
      final e = await c.olayYaz('MESAI.GIRDIM', {}, baglanti: false, depo: b);
      expect(e, {
        'olay_kimligi': 'K017-2610220001-T',
        'eylem_kodu': 'MESAI.GIRDIM',
        'eylem_versiyonu': 1,
        'neyin_ustunde': [],
        'giris_sekli': 'LISTE',
        'kim': 'K017',
        'adina': null,
        'cihaz': 'TEL-K017',
        'uygulama_surumu': 'AND-0.1.0',
        'oldugu_an': zaman,
        'saat_dilimi': '+03:00',
        'bildigi_son_hal_ani': zaman,
        'girdiler': {},
        'kanit': [],
        'duzelttigi_olay': null,
        'yol': 'DISARIDA',
        'pc_ulasma_ani': null,
      });
      expect(b.cagrilar, isEmpty);
      expect(cihaz(depo: d).bekleyenSayisi(), 1);
    },
  );

  test('Kapalı kapı ve bayat yönetim kimlik tüketmez', () async {
    final c = cihaz();
    await expectLater(
      c.olayYaz('MESAI.CIKTIM', {}),
      throwsA(
        isA<ModelHatasi>().having(
          (e) => e.neden,
          'neden',
          'Cihaz kapisi kapali',
        ),
      ),
    );
    await expectLater(
      c.olayYaz('IS.ATADIM', {}),
      throwsA(
        isA<ModelHatasi>().having(
          (e) => e.neden,
          'neden',
          'Yonetim icin taze baglanti gerekli',
        ),
      ),
    );
    expect(c.veri['sayaclar'], isEmpty);
    expect(c.bekleyenSayisi(), 0);
  });

  test('Sabit mola kapısı açık işi engeller', () async {
    final c = cihaz();
    await expectLater(
      c.olayYaz(
        'IS.BASLADIM',
        hal(),
        isler: {'I1': isBilgisi()},
        liste: ['I1'],
        isKimligi: 'I1',
        sabitMola: true,
      ),
      throwsA(isA<ModelHatasi>()),
    );
    expect(c.veri['sayaclar'], isEmpty);
  });

  for (final (cevap, durum) in [
    ('BASARILI', 'GONDERILDI'),
    ('BAGLANTI_YOK', 'GONDERILEMEDI'),
    ('REDDEDILDI', 'RED'),
  ]) {
    test('Yönetim $cevap cevabında $durum olur ve kuyruğa girmez', () async {
      final c = Cihaz('K017', 'T', Saat(zaman)),
          b = SahteBulut(cevapla: (_, _) => {'sonuc': cevap});
      final e = await c.olayYaz(
        'IS.ATADIM',
        {
          ...hal(),
          'liste_surumleri': {'K017': 'ekran-liste-surumu'},
        },
        isler: {'I1': isBilgisi()},
        liste: ['I1'],
        isKimligi: 'I1',
        girdiler: {'kisi': 'K017', 'sira': 1},
        depo: b,
      );
      expect(e['cihaz'], 'MAS-K017');
      expect(e['uygulama_surumu'], 'WEB-0.1.0');
      expect(e['neyin_ustunde'], [
        {'tur': 'IS', 'kimlik': 'I1', 'surum': 'ekran-is-surumu'},
        {'tur': 'LISTE', 'kimlik': 'K017', 'surum': 'ekran-liste-surumu'},
      ]);
      expect(c.veri['gunluk'][e['olay_kimligi']]['durum'], durum);
      await c.gonderimDongusu(b);
      expect(b.cagrilar, hasLength(1));
    });
  }

  test('Yönetimde görülen liste özeti kullanılır, diğer kişinin eksik özeti null kalır', () async {
    final c = cihaz();
    final e = await c.olayYaz(
      'IS.DEVRETTIM',
      hal(),
      isler: {'I1': isBilgisi()},
      liste: ['I1'],
      isKimligi: 'I1',
      girdiler: {'kimden': 'K017', 'kime': 'K018'},
    );
    expect(e['neyin_ustunde'][1], {
      'tur': 'LISTE',
      'kimlik': 'K017',
      'surum': ozet(['I1']),
    });
    expect(e['neyin_ustunde'][2], {
      'tur': 'LISTE',
      'kimlik': 'K018',
      'surum': null,
    });
    expect(c.veri['gunluk'][e['olay_kimligi']]['durum'], 'GONDERILEMEDI');
  });

  test('Bekleyen olaylar ekrana yansır, eski gün ve bilinmeyen iş atlanır', () {
    final c = cihaz(), son = hal();
    final once = kodla(son);
    c.gunlukEkle(
      olay('eski', '2026-10-21T17:00:00+03:00', kod: 'MESAI.CIKTIM'),
    );
    c.gunlukEkle(olay('yok', zaman, kod: 'IS.BASLADIM', isKimligi: 'YOK'));
    c.gunlukEkle(
      olay(
        'basla',
        '2026-10-22T09:01:00+03:00',
        kod: 'IS.BASLADIM',
        isKimligi: 'I1',
      ),
    );
    c.gunlukEkle(
      olay(
        'mola',
        '2026-10-22T09:02:00+03:00',
        kod: 'IS.MOLA_VERDIM',
        isKimligi: 'I1',
      ),
    );
    final ekran = c.ekranHali(son, isler: {'I1': isBilgisi()}, liste: ['I1']);
    expect(ekran['son_hal']['durum'], 'MOLADA');
    expect(ekran['son_hal']['acik_is'], 'I1');
    expect(ekran['bekleyen'], hasLength(4));
    expect(kodla(son), once);
  });

  test('İç içe mola geçişi giriş halini değiştirmez', () {
    final bas = gecis(bosHal(), 'IS.BASLADIM', is_: isBilgisi()).$1;
    final once = kodla(bas), mola = gecis(bas, 'MOLA_BASI').$1;
    final son = gecis(mola, 'MOLA_SONU').$1;
    expect(son['durum'], 'DEVAM_BEKLIYOR');
    expect(son['acik_is'], 'I1');
    expect(son['mola_onceki'], isNull);
    expect(kodla(bas), once);
    expect(mola['durum'], 'SABIT_MOLADA');
  });

  test(
    'Görev teslimi açık saati, kişi takvimini ve varsayılanı sırayla kullanır',
    () {
      final g = {'teslim_tarihi': '2026-10-23', 'kisi': 'K017'};
      expect(sonTeslimAni(g)!.isoformat(), '2026-10-23T18:00:00+03:00');
      expect(
        sonTeslimAni({...g, 'takvim_teslim_saati': '17:00'})!.isoformat(),
        '2026-10-23T17:00:00+03:00',
      );
      expect(
        sonTeslimAni(g, _Takvim())!.isoformat(),
        '2026-10-23T16:30:00+03:00',
      );
      expect(
        sonTeslimAni({...g, 'teslim_saati': '15:00'}, _Takvim())!.isoformat(),
        '2026-10-23T15:00:00+03:00',
      );
      expect(sonTeslimAni({}), isNull);
    },
  );
}

class _YazamayanDepo implements YerelDepo {
  @override
  Map<String, dynamic>? oku() => null;
  @override
  void yaz(Map<String, dynamic> veri) =>
      throw const FileSystemException('Yazım kesildi');
}

class _Takvim implements TakvimKaynagi {
  @override
  Map<String, dynamic> takvim(Object tarih, String? kisi) {
    expect(kisi, 'K017');
    return {'mesai_bitis': '16:30'};
  }
}
