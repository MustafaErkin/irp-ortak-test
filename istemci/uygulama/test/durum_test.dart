import 'dart:convert';
import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:fake_async/fake_async.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:idb_shim/idb_client_memory.dart';
import 'package:image/image.dart' as im;
import 'package:crypto/crypto.dart';
import 'package:irp_cekirdek/irp_cekirdek.dart';
import 'package:irp_uygulama/bulut/supabase_bulutu.dart';
import 'package:irp_uygulama/bulut/uygulama_bulutu.dart';
import 'package:irp_uygulama/durum/dosya_deposu.dart';
import 'package:irp_uygulama/durum/indexeddb_deposu.dart';
import 'package:irp_uygulama/durum/kalici_depo.dart';
import 'package:irp_uygulama/durum/gonderici.dart';
import 'package:irp_uygulama/durum/kanit.dart';
import 'package:irp_uygulama/durum/pin.dart';
import 'package:irp_uygulama/durum/uygulama_durumu.dart';
import 'package:irp_uygulama/sahte/fikstur_bulutu.dart';

import 'destek.dart';

void main() {
  test('PBKDF2 tuzları farklı, doğru PIN açar, yanlış açmaz', () async {
    final a = await Pin.olustur('123456'), b = await Pin.olustur('123456');
    expect(a['tuz'], isNot(b['tuz']));
    expect(a['ozet'], isNot(b['ozet']));
    expect(await Pin.dogrula('123456', a), isTrue);
    expect(await Pin.dogrula('123455', a), isFalse);
    expect(jsonEncode(a), isNot(contains('123456')));
    await expectLater(Pin.olustur('123'), throwsArgumentError);
  });
  test(
    'ilk kayıt ve çevrimdışı yerel açılış; sabah yalnız bir kez giriş',
    () async {
      final b = FiksturBulutu(fikstur, durum: 'mesai_disi');
      final depo = BellekKaliciDepo();
      final d = UygulamaDurumu(
        bulut: b,
        depo: depo,
        semalar: semalar,
        saat: Saat('2026-10-22T10:40:00+03:00'),
      );
      await d.yukle();
      await d.kaydol('k017', '123456', '654321', '654321');
      await d.gonderici.tetikle();
      expect(d.acik, isTrue);
      expect(d.kayit!['harf'], 'T');
      final kayitAnahtari = d.kayit!['cihaz_kimligi'];
      expect(kayitAnahtari, matches(RegExp(r'^IRP-[0-9a-f]{32}$')));
      expect(
        b.cagrilar.firstWhere((x) => x['kapi'] == 'cihaz_kaydol')['cihaz'],
        kayitAnahtari,
      );
      expect(
        b.cagrilar.firstWhere((x) => x['kapi'] == 'cihaz_esitle')['cihaz'],
        'MAS-K017',
      );
      expect(
        b.cagrilar.firstWhere((x) => x['kapi'] == 'cihaz_esitle')['harf'],
        'T',
      );
      expect(
        b.olaylar.where((e) => e['eylem_kodu'] == 'MESAI.GIRDIM'),
        hasLength(1),
      );
      expect(jsonEncode(depo.veri), isNot(contains('654321')));
      b.cevrimici = false;
      d.dispose();
      final yeni = UygulamaDurumu(
        bulut: b,
        depo: depo,
        semalar: semalar,
        saat: Saat('2026-10-22T10:40:00+03:00'),
      );
      await yeni.yukle();
      expect(yeni.kayit!['cihaz_kimligi'], kayitAnahtari);
      expect(await yeni.kilitAc('654321'), isTrue);
      await yeni.gonderici.tetikle();
      expect(yeni.bekleyen, 0);
      expect(yeni.kayit!['oturum']['refresh_token'], 'sentetik-K017');
      yeni.dispose();
      await b.dispose();
    },
  );
  test('telefonda W harfiyle cihaz adı TEL kalır', () async {
    final b = FiksturBulutu(fikstur, durum: 'mesai_disi');
    // Bu test cihaz harfini sınar; yeni sunucu sözleşmesine göre mesai açıktır.
    b.okumalar['TELEFON']['deger']['calisma_penceresi'] = {
      'gun': '2026-10-22',
      'mesai': [
        ['2026-10-22T08:00:00+03:00', '2026-10-22T18:00:00+03:00'],
      ],
      'calisma': [
        ['2026-10-22T08:00:00+03:00', '2026-10-22T18:00:00+03:00'],
      ],
      'kaynak_ani': '2026-10-22T10:40:00+03:00',
    };
    addTearDown(b.dispose);
    for (var i = 0; i < 3; i++) {
      await b.cihazKaydol('onceki-$i');
    }
    b.cagrilar.clear();
    final d = UygulamaDurumu(
      bulut: b,
      depo: BellekKaliciDepo(),
      semalar: semalar,
      saat: Saat('2026-10-22T10:40:00+03:00'),
      telefonKipi: true,
    );
    addTearDown(d.dispose);
    await d.yukle();
    await d.kaydol('k017', '123456', '654321', '654321');
    await d.gonderici.tetikle();
    expect(d.kayit!['harf'], 'W');
    expect(
      b.cagrilar.firstWhere((c) => c['kapi'] == 'cihaz_kaydol')['cihaz'],
      d.kayit!['cihaz_kimligi'],
    );
    expect(d.kayit!['cihaz_kimligi'], matches(RegExp(r'^IRP-[0-9a-f]{32}$')));
    expect(
      b.cagrilar.firstWhere((c) => c['kapi'] == 'cihaz_esitle')['cihaz'],
      'TEL-K017',
    );
    expect(b.olaylar, isNotEmpty);
    for (final olay in b.olaylar) {
      expect(olay['cihaz'], 'TEL-K017');
      expect(olay['uygulama_surumu'], 'AND-0.1.0');
      expect(olay['olay_kimligi'], endsWith('-W'));
    }
  });
  test(
    '5 yanlış 30 saniye, yeniden açılışta korunur; 10 yanlış yeniden kayıt',
    () async {
      final (eski, b, depo) = await hazir(acik: false);
      var simdi = DateTime.utc(2026, 10, 22);
      final d = UygulamaDurumu(
        bulut: b,
        depo: depo,
        semalar: semalar,
        saat: eski.saat,
        guvenlikSaati: () => simdi,
      );
      await d.yukle();
      for (var i = 0; i < 5; i++) {
        expect(await d.kilitAc('000000'), isFalse);
      }
      expect(d.kilitSaniye, 30);
      expect(await d.kilitAc('654321'), isFalse);
      d.dispose();
      final yeni = UygulamaDurumu(
        bulut: b,
        depo: depo,
        semalar: semalar,
        saat: eski.saat,
        guvenlikSaati: () => simdi,
      );
      await yeni.yukle();
      expect(yeni.kilitSaniye, 30);
      for (var i = 5; i < 10; i++) {
        simdi = simdi.add(const Duration(seconds: 31));
        await yeni.kilitAc('000000');
      }
      expect(yeni.kayit, isNull);
      expect(yeni.acik, isFalse);
      yeni.dispose();
    },
  );
  test(
    'üç çevrimdışı tanıklık yeniden açılınca korunur ve sırayla gönderilir',
    () async {
      final (d, b, depo) = await hazir();
      b.cevrimici = false;
      final olaylar = <Json>[];
      for (final kod in ['IS.MOLA_VERDIM', 'IS.DEVAM_ETTIM', 'IS.TAMAMLADIM']) {
        olaylar.add(await d.olay(kod));
        await d.gonderici.tetikle();
      }
      expect(d.bekleyen, 3);
      expect(d.hal['durum'], 'CALISMIYOR');
      final yeni = UygulamaDurumu(
        bulut: b,
        depo: depo,
        semalar: semalar,
        saat: d.saat,
      );
      await yeni.yukle();
      yeni.acik = true;
      expect(yeni.bekleyen, 3);
      b.cevrimici = true;
      await yeni.baglantiDegisti(true);
      expect(
        b.olaylar.map((e) => e['olay_kimligi']),
        olaylar.map((e) => e['olay_kimligi']),
      );
      expect(yeni.bekleyen, 0);
      yeni.dispose();
      // Eski oturumun ikinci bir gönderimini sınamanın dışına al.
      d.acik = false;
    },
  );
  test('beklemeler 2 4 8 16 32 60; tek uçuş ve başarıda sıfırlama', () {
    fakeAsync((zaman) {
      var bekliyor = true, sayi = 0;
      final g = Gonderici(
        gonder: () async {
          sayi++;
        },
        bekleyen: () => bekliyor,
        hata: (_) {},
      );
      g.tetikle();
      g.tetikle();
      zaman.flushMicrotasks();
      expect(sayi, 1);
      for (final saniye in [2, 4, 8, 16, 32, 60, 60]) {
        expect(g.siradakiSaniye, saniye);
        zaman.elapse(Duration(seconds: saniye));
        zaman.flushMicrotasks();
      }
      bekliyor = false;
      g.tetikle();
      zaman.flushMicrotasks();
      expect(g.siradakiSaniye, isNull);
      bekliyor = true;
      g.tetikle();
      zaman.flushMicrotasks();
      expect(g.siradakiSaniye, 2);
      g.dispose();
    });
  });
  test('BAKIMDA bekler, ret HATA olur, tekrar başarıdır', () async {
    final (d, b, _) = await hazir();
    b.sonrakiCevap = {'sonuc': 'BAKIMDA'};
    await d.olay(
      'NOT.YAZDIM',
      girdiler: {'metin': 'Bekle'},
      hedefler: notHedefi,
    );
    await Future<void>.delayed(Duration.zero);
    expect(d.bekleyen, 1);
    b.sonrakiCevap = {'sonuc': 'REDDEDILDI', 'kod': 'DURUM'};
    await d.gonderici.tetikle();
    expect(d.gunluk.last['durum'], 'HATA');
    expect(d.mesaj, 'İşlem uygulanamadı. Ekranı yenileyip kullanılabilen işlemleri kontrol edin.');
    b.sonrakiCevap = {'sonuc': 'BASARILI', 'tekrar': true};
    await d.olay(
      'NOT.YAZDIM',
      girdiler: {'metin': 'Tekrar'},
      hedefler: notHedefi,
    );
    await d.gonderici.tetikle();
    expect(d.gunluk.last['durum'], 'GONDERILDI');
  });
  test('dosya deposu yeni nesnede günlüğü ve sayacı açar', () async {
    final dir = await Directory.systemTemp.createTemp('irp-istemci2-');
    addTearDown(() => dir.delete(recursive: true));
    final f = File('${dir.path}/cihaz.json');
    await DosyaKaliciDepo(f).yaz({
      'sayac': 17,
      'bekleyen': ['a', 'b'],
    });
    expect(await DosyaKaliciDepo(f).oku(), {
      'sayac': 17,
      'bekleyen': ['a', 'b'],
    });
    await DosyaKaliciDepo(f).yaz({'sayac': 18});
    expect(await DosyaKaliciDepo(f).oku(), {'sayac': 18});
  });
  test(
    'IndexedDB işlem atomikliği ve ikinci sekmenin eski sürümü ezememesi',
    () async {
      final factory = newIdbFactoryMemory();
      final a = await IndexedDbDeposu.ac(factory),
          b = await IndexedDbDeposu.ac(factory);
      expect(await a.oku(), isEmpty);
      expect(await b.oku(), isEmpty);
      await a.yaz({
        'sayac': 5,
        'gunluk': ['a'],
      });
      await expectLater(b.yaz({'sayac': 1}), throwsStateError);
      expect(await b.oku(), {
        'sayac': 5,
        'gunluk': ['a'],
      });
      await b.yaz({'sayac': 6});
      expect(await a.oku(), {'sayac': 6});
      a.kapat();
      b.kapat();
    },
  );
  test(
    'fotoğraf küçülür; özet son baytlardan, olaydan sonra kalıcı kuyruk yükler',
    () async {
      final kaynak = Uint8List.fromList(
        im.encodePng(im.Image(width: 2400, height: 1200)),
      );
      final foto = HazirFoto.hazirla(kaynak, 'olcu.png');
      final resim = im.decodeJpg(foto.bytes)!;
      expect([resim.width, resim.height], [1600, 800]);
      final (d, b, depo) = await hazir();
      b.cevrimici = false;
      final e = await d.olay(
        'NOT.YAZDIM',
        girdiler: {'metin': 'Ölçü'},
        hedefler: [
          {'tur': 'PARCA', 'kimlik': '2509084_07_04-63', 'surum': null},
        ],
        fotograflar: [foto],
      );
      await d.gonderici.tetikle();
      expect(
        e['kanit'][0]['parmak_izi'],
        sha256.convert(foto.bytes).toString(),
      );
      expect(e['kanit'][0]['dosya_kimligi'], 'F-${e['olay_kimligi']}/1');
      expect(depo.veri['yuklemeler'], hasLength(1));
      b.cevrimici = true;
      await d.baglantiDegisti(true);
      expect(d.yuklemeler, isEmpty);
      expect(b.dosyalar.values.single, foto.bytes);
      final kapilar = b.cagrilar.map((e) => e['kapi']).toList();
      expect(
        kapilar.indexOf('olay_ekle'),
        lessThan(kapilar.indexOf('kanit_yukle')),
      );
    },
  );
  test('kalıcı yazım hatasında olay ağa çıkmaz', () async {
    final (ilk, b, bellek) = await hazir();
    final depo = _HataDeposu(await bellek.oku());
    final d = UygulamaDurumu(
      bulut: b,
      depo: depo,
      semalar: semalar,
      saat: ilk.saat,
    );
    await d.yukle();
    d.acik = true;
    await expectLater(
      d.olay(
        'NOT.YAZDIM',
        girdiler: {'metin': 'Kaybolmasın'},
        hedefler: notHedefi,
      ),
      throwsStateError,
    );
    await d.gonderici.tetikle();
    expect(b.olaylar, isEmpty);
    expect(d.kaliciHata, isTrue);
    d.dispose();
  });
  test('önbellek 30 saniye tazedir ve sorgu anahtarlarını ayırır', () async {
    final (d, _, _) = await hazir();
    expect(d.taze('TELEFON'), isTrue);
    expect(d.okunmus('TELEFON', g: {'farkli': true}), isNull);
    (d.saat as Saat).ilerlet('2026-10-22T10:40:31+03:00');
    expect(d.taze('TELEFON'), isFalse);
  });
  test('Supabase yapılandırması yoksa ağ istemcisi kurulmaz', () async {
    await expectLater(SupabaseBulutu().simdi(), throwsStateError);
  });
  test(
    'sinyaller kişi/firma kanallarını 300 ms içinde tek yenilemede birleştirir',
    () async {
      final (d, b, _) = await hazir(acik: false);
      await d.kilitAc('654321');
      await d.gonderici.tetikle();
      final once = b.cagrilar.where((c) => c['veri'] == 'TELEFON').length;
      b.sinyalVer('kisi:K999');
      await Future<void>.delayed(const Duration(milliseconds: 340));
      expect(b.cagrilar.where((c) => c['veri'] == 'TELEFON').length, once);
      final yenilendi = Completer<void>();
      void kontrol() {
        if (b.cagrilar.where((c) => c['veri'] == 'TELEFON').length ==
                once + 1 &&
            !yenilendi.isCompleted) {
          yenilendi.complete();
        }
      }

      d.addListener(kontrol);
      b.sinyalVer('kisi:K017');
      b.sinyalVer('firma');
      b.sinyalVer('kisi:K017');
      await yenilendi.future.timeout(const Duration(seconds: 5));
      d.removeListener(kontrol);
      expect(b.cagrilar.where((c) => c['veri'] == 'TELEFON').length, once + 1);
    },
  );
  test('yanıtlar kullanıcı metniyle eşlenir; başarı ve ret ayrılır', () {
    for (final (kod, yazi) in [
      ('BAYAT', 'Ekran güncellendi, yeniden bak'),
      ('DURUM', 'İşlem uygulanamadı. Ekranı yenileyip kullanılabilen işlemleri kontrol edin.'),
      ('YETKI', 'Bu işlem için yetkin yok'),
      ('HESAP_BEKLIYOR', 'Sistem hesaplıyor, birazdan tekrar dene'),
      ('BAKIMDA', 'Sistem bakımda; kayıt sonra gönderilecek'),
      ('CAKISMA', 'Bu kayıt daha önce farklı gönderilmiş'),
      ('BICIM', 'Beklenmeyen hata'),
    ]) {
      expect(cevapMetni({'kod': kod}), yazi);
    }
  });
  test(
    'birinci kabulden sonra ağ kesilince kabul kalıcı, kalanlar sıralı bekler',
    () async {
      final (ilk, _, depo) = await hazir();
      final b = _KesilenBulut(fikstur)..cevrimici = false;
      final d = UygulamaDurumu(
        bulut: b,
        depo: depo,
        semalar: semalar,
        saat: ilk.saat,
      );
      await d.yukle();
      d.acik = true;
      for (var i = 0; i < 3; i++) {
        await d.olay(
          'NOT.YAZDIM',
          girdiler: {'metin': 'Not $i'},
          hedefler: notHedefi,
        );
        await d.gonderici.tetikle();
      }
      b.cevrimici = true;
      await d.gonderici.tetikle();
      expect(d.gunluk.map((k) => k['durum']), [
        'GONDERILDI',
        'BEKLIYOR',
        'BEKLIYOR',
      ]);
      final sakli = (await depo.oku())['cihazlar']['K017']['gunluk'] as Map;
      expect(sakli.values.first['durum'], 'GONDERILDI');
      await d.gonderici.tetikle();
      expect(d.bekleyen, 0);
      expect(b.olaylar, hasLength(3));
      d.dispose();
      await b.dispose();
    },
  );
  test('sunucu biçim istisnası HATA olur ve ayrıntı günlükte kalır', () async {
    final (ilk, _, depo) = await hazir();
    final b = _BicimBulutu(fikstur);
    final d = UygulamaDurumu(
      bulut: b,
      depo: depo,
      semalar: semalar,
      saat: ilk.saat,
    );
    await d.yukle();
    d.acik = true;
    await d.olay('NOT.YAZDIM', girdiler: {'metin': 'Not'}, hedefler: notHedefi);
    await d.gonderici.tetikle();
    expect(d.gunluk.single['durum'], 'HATA');
    expect(d.mesaj, 'Beklenmeyen hata');
    expect(d.gunluk.single['sonuc']['neden'], contains('IRP|BICIM|'));
    d.dispose();
    await b.dispose();
  });
}

class _HataDeposu extends BellekKaliciDepo {
  _HataDeposu(super.veri);
  @override
  Future<void> yaz(Json veri) async => throw StateError('Disk dolu');
}

class _KesilenBulut extends FiksturBulutu {
  _KesilenBulut(super.fikstur);
  int _sayi = 0;
  @override
  Future<Json> olayEkle(
    Json olay, {
    required String oturum,
    Json? hassasEk,
  }) async {
    if (cevrimici && ++_sayi == 2) throw const BaglantiYok();
    return super.olayEkle(olay, oturum: oturum);
  }
}

class _BicimBulutu extends FiksturBulutu {
  _BicimBulutu(super.fikstur);
  @override
  Future<Json> olayEkle(
    Json olay, {
    required String oturum,
    Json? hassasEk,
  }) async => throw StateError('IRP|BICIM|sentetik denetim');
}
