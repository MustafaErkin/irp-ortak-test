import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:irp_cekirdek/irp_cekirdek.dart';
import 'package:irp_uygulama/bulut/uygulama_bulutu.dart';
import 'package:irp_uygulama/bulut/gosteri_kisisi.dart';
import 'package:irp_uygulama/durum/kalici_depo.dart';
import 'package:irp_uygulama/durum/uygulama_durumu.dart';
import 'package:irp_uygulama/sahte/fikstur_bulutu.dart';
import 'package:irp_uygulama/main.dart';

import 'destek.dart';

// İş kurallarını tekrar yazmıyoruz: önce/sonra paketleri gerçek SQL motorundan.
final vakalar =
    (dosya('test/fikstur/telefon_esitle_sql.json')['vakalar'] as List)
        .cast<Json>();
Json vaka(String ad) => vakalar.singleWhere((v) => v['ad'] == ad);

class TelefonBulutu extends FiksturBulutu implements TelefonEsitlemeBulutu {
  TelefonBulutu(this.v) : paket = kopya(v['once']), super(fikstur);
  final Json v;
  Json paket;
  bool yayinlandi = false, cevapKaybolsun = false;
  Object? okumaHatasi, gonderimHatasi;
  Completer<void>? okumaBeklesin, gonderimBeklesin, oturumBeklesin;
  int okumalarAdedi = 0;
  final denemeler = <Json>[];
  final alinanlar = <String, Json>{};
  Json? ret;
  @override
  Future<Json> oturumYenile(String token) async {
    await oturumBeklesin?.future;
    return super.oturumYenile(token);
  }

  @override
  Future<String> simdi() async => v['olay']['oldugu_an'];
  @override
  Future<Json> telefonEsitle(List<String> olaylar) async {
    if (!cevrimici) throw const BaglantiYok();
    if (okumaHatasi != null) throw okumaHatasi!;
    okumalarAdedi++;
    final p = kopya(paket);
    p['olay_sonuclari'] = {
      for (final id in olaylar)
        id: alinanlar.containsKey(id)
            ? (yayinlandi ? 'TAMAMLANDI' : 'BEKLIYOR')
            : 'BULUNAMADI',
    };
    await okumaBeklesin?.future;
    return p;
  }

  @override
  Future<Json> olayEkle(
    Json olay, {
    required String oturum,
    Json? hassasEk,
  }) async {
    denemeler.add(kopya(olay));
    if (gonderimHatasi != null) throw gonderimHatasi!;
    await gonderimBeklesin?.future;
    if (!cevrimici) throw const BaglantiYok();
    if (ret != null) return ret!;
    alinanlar.putIfAbsent(olay['olay_kimligi'], () => kopya(olay));
    if (cevapKaybolsun) throw TimeoutException('Sentetik kayıp makbuz');
    return {'sonuc': 'BASARILI', 'hesap': 'BEKLIYOR'};
  }

  void yayinla() {
    paket = kopya(v['sonra']);
    yayinlandi = true;
  }
}

Future<(UygulamaDurumu, TelefonBulutu, BellekKaliciDepo)> telefonKur(
  Json v, {
  BellekKaliciDepo? depo,
  TelefonBulutu? bulut,
}) async {
  final b = bulut ?? TelefonBulutu(v);
  final p =
      depo ??
      BellekKaliciDepo({
        'kayit': {
          'kisi': v['olay']['kim'],
          'ad': 'Çalışan',
          'harf': 'Z',
          'oturum': {'refresh_token': 'sentetik'},
        },
      });
  final d = UygulamaDurumu(
    bulut: b,
    depo: p,
    semalar: semalar,
    saat: Saat(v['olay']['oldugu_an']),
    telefonKipi: true,
    mvpSadeceCalisan: true,
  );
  await d.yukle();
  d.acik = true;
  await d.yenile();
  addTearDown(() async {
    d.dispose();
    await b.dispose();
  });
  return (d, b, p);
}

Future<Json> uygula(UygulamaDurumu d, Json v) =>
    d.olay(v['olay']['eylem_kodu'], girdiler: Json.from(v['olay']['girdiler']));
Map<String, dynamic> kritik(Json h) => {
  for (final key in [
    'durum',
    'kova',
    'acik_is',
    'aralik_is',
    'devam_izni',
    'onceki_kova',
  ])
    key: h[key],
};

void main() {
  for (final v in vakalar) {
    test(
      'Gerçek motor karşılaştırması: ${v['ad']} — yerel, makbuz, yayın',
      () async {
        final (d, b, _) = await telefonKur(v);
        final expected = Json.from(v['sonra']['telefon']['deger']['son_hal']);
        final degisimler = <Json>[];
        d.addListener(() => degisimler.add(kritik(d.hal)));
        await uygula(d, v);
        expect(
          kritik(d.hal),
          kritik(expected),
          reason: 'Ağdan önceki çalışan hali',
        );
        await d.gonderici.tetikle();
        expect(d.bekleyen, 0);
        expect(d.gunluk.last['yerel_etki'], true);
        expect(
          kritik(d.hal),
          kritik(expected),
          reason: 'Alındı yerel etkiyi silmemeli',
        );
        expect(d.liste, v['sonra']['telefon']['deger']['liste']);
        b.yayinla();
        await d.yenile();
        expect(d.gunluk.last['yerel_etki'], false);
        expect(kritik(d.hal), kritik(expected));
        expect(
          degisimler.where((h) => h['durum'] == expected['durum']),
          isNotEmpty,
        );
        for (final e in b.denemeler) {
          olayDogrula(e);
        }
      },
    );
  }
  test(
    'Yavaş ağ yerel Mola/Devam yazımını kilitlemez; eski yanıt geri sarmaz',
    () async {
      final (d, b, _) = await telefonKur(vaka('Mola'));
      b.okumaBeklesin = Completer<void>();
      final okuma = d.yenile();
      await Future<void>.delayed(Duration.zero);
      await d.olay('IS.MOLA_VERDIM').timeout(const Duration(milliseconds: 500));
      expect(d.hal['durum'], 'MOLADA');
      expect(d.mesgul, false);
      await d.olay('IS.DEVAM_ETTIM').timeout(const Duration(milliseconds: 500));
      expect(d.hal['durum'], 'CALISIYOR');
      expect(d.bekleyen, 2);
      b.okumaBeklesin!.complete();
      await okuma;
      await d.gonderici.tetikle();
      expect(d.hal['durum'], 'CALISIYOR');
      expect(b.denemeler.map((e) => e['eylem_kodu']), [
        'IS.MOLA_VERDIM',
        'IS.DEVAM_ETTIM',
      ]);
    },
  );
  test(
    'Geciken gönderim yanıtı sırasında yeni tanıklık kalıcı yazılır',
    () async {
      final (d, b, p) = await telefonKur(vaka('Mola'));
      b.gonderimBeklesin = Completer<void>();
      await d.olay('IS.MOLA_VERDIM');
      await Future<void>.delayed(Duration.zero);
      await d.olay('IS.DEVAM_ETTIM').timeout(const Duration(milliseconds: 500));
      expect((p.veri['cihazlar'][d.kisi]['gunluk'] as Map).length, 2);
      b.gonderimBeklesin!.complete();
      await d.gonderici.tetikle();
      await d.gonderici.tetikle();
      expect(b.alinanlar.length, 2);
      expect(d.hal['durum'], 'CALISIYOR');
    },
  );
  test('Makbuz kaybolunca aynı kimlik yeniden gider; yeniden açılış mola halini korur', () async {
    final v = vaka('Mola');
    final (d, b, p) = await telefonKur(v);
    b.cevapKaybolsun = true;
    final e = await uygula(d, v);
    await d.gonderici.tetikle();
    expect(d.bekleyen, 1);
    expect(b.alinanlar.length, 1);
    expect(d.hal['durum'], 'MOLADA');
    d.gonderici.beklemeyiDurdur();
    final b2 = TelefonBulutu(v)..alinanlar.addAll(b.alinanlar);
    final (d2, _, _) = await telefonKur(v, depo: p, bulut: b2);
    expect(d2.hal['durum'], 'MOLADA');
    await d2.gonderici.tetikle();
    expect(b2.alinanlar.keys, [e['olay_kimligi']]);
    expect(d2.hal['durum'], 'MOLADA');
    b2.yayinla();
    await d2.yenile();
    expect(d2.gunluk.single['yerel_etki'], false);
  });
  test(
    'Okuma zaman aşımı tamamlanmış yerel yazımı veya iş kapısını bozmaz',
    () async {
      final (d, b, _) = await telefonKur(vaka('Mola'));
      b.okumaHatasi = TimeoutException('57014 sentetik');
      await d.olay('IS.MOLA_VERDIM');
      await d.gonderici.tetikle();
      await d.yenile();
      expect(d.hal['durum'], 'MOLADA');
      expect(d.kapiAcik('IS.DEVAM_ETTIM'), true);
      expect(d.islemHatasi, isNull);
    },
  );
  test('Kesin ret yerel etkiyi kaldırır ve anlaşılır hata bırakır', () async {
    final (d, b, _) = await telefonKur(vaka('Mola'));
    b.ret = {'sonuc': 'REDDEDILDI', 'kod': 'YETKI'};
    await d.olay('IS.MOLA_VERDIM');
    await d.gonderici.tetikle();
    expect(d.hal['durum'], 'CALISIYOR');
    expect(d.gunluk.last['durum'], 'RED');
    expect(d.islemHatasi, 'Bu işlem için yetkin yok');
    expect(d.gonderici.siradakiSaniye, isNull);
  });
  test(
    'Geçici hesap beklemesi olayı reddetmez; aynı kimlikle tekrarlar',
    () async {
      final (d, b, _) = await telefonKur(vaka('Mola'));
      b.ret = {'sonuc': 'REDDEDILDI', 'kod': 'HESAP_BEKLIYOR'};
      final e = await d.olay('IS.MOLA_VERDIM');
      await d.gonderici.tetikle();
      expect(d.bekleyen, 1);
      expect(d.hal['durum'], 'MOLADA');
      b.ret = null;
      await d.gonderici.tetikle();
      expect(b.denemeler.map((v) => v['olay_kimligi']).toSet(), {
        e['olay_kimligi'],
      });
      expect(d.bekleyen, 0);
      expect(d.hal['durum'], 'MOLADA');
    },
  );
  test('Bakım cevabı kalıcı ret değildir; aynı olay kuyrukta kalır', () async {
    final (d, b, _) = await telefonKur(vaka('Mola'));
    b.ret = {'sonuc': 'BAKIMDA'};
    await d.olay('IS.MOLA_VERDIM');
    await d.gonderici.tetikle();
    expect(d.bekleyen, 1);
    expect(d.hal['durum'], 'MOLADA');
    expect(d.islemHatasi, isNull);
  });
  test('Kesin biçim istisnası sonsuz yeniden denenmez', () async {
    final (d, b, _) = await telefonKur(vaka('Mola'));
    b.gonderimHatasi = StateError('IRP|BICIM|Sentetik');
    await d.olay('IS.MOLA_VERDIM');
    await d.gonderici.tetikle();
    expect(d.bekleyen, 0);
    expect(d.gunluk.single['durum'], 'RED');
    expect(d.hal['durum'], 'CALISIYOR');
    expect(d.islemHatasi, isNot(contains('IRP|')));
  });
  test(
    'MVP telefon rol listesi yalnız atölye/saha; webde lider korunur',
    () async {
      const people = [
        GosteriKisisi(
          etiket: 'Atölye Çalışanı',
          kod: 'K017',
          sifre: 'sentetik',
          yer: 'telefon',
        ),
        GosteriKisisi(
          etiket: 'Ekip Lideri',
          kod: 'K009',
          sifre: 'sentetik',
          yer: 'ikisi',
        ),
        GosteriKisisi(
          etiket: 'Saha Çalışanı',
          kod: 'K031',
          sifre: 'sentetik',
          yer: 'telefon',
        ),
      ];
      for (final phone in [false, true]) {
        final b = TelefonBulutu(vaka('Mola'));
        final d = UygulamaDurumu(
          bulut: b,
          depo: BellekKaliciDepo(),
          semalar: semalar,
          saat: Saat('2026-11-03T10:00:00+03:00'),
          telefonKipi: phone,
          mvpSadeceCalisan: true,
          gosteriKisileri: people,
        );
        expect(
          d.gosteriKisileri.map((p) => p.kod),
          phone ? ['K017', 'K031'] : ['K009'],
        );
        d.dispose();
        await b.dispose();
      }
    },
  );
  test(
    'Yerel teslimden sonra sonraki Başla yayın beklemeden doğru işi hedefler',
    () async {
      final (d, b, _) = await telefonKur(vaka('Onaysız Teslim'));
      b.cevrimici = false;
      await d.olay('IS.TAMAMLADIM');
      expect(d.hal['durum'], 'CALISMIYOR');
      final next = d.liste.first;
      expect(d.kapiAcik('IS.BASLADIM'), true);
      final e = await d.olay('IS.BASLADIM');
      expect(e['neyin_ustunde'][0]['kimlik'], next);
      expect(d.hal['acik_is'], next);
      await d.gonderici.tetikle();
    },
  );
  test(
    'Bekleten teslimde ikinci teslim ve sıradaki işe başlama kapalıdır',
    () async {
      final (d, b, _) = await telefonKur(vaka('Bekleten Teslim'));
      b.cevrimici = false;
      await d.olay('IS.TAMAMLADIM');
      expect(d.kapiAcik('IS.BASLADIM'), false);
      expect(d.kapiAcik('IS.TAMAMLADIM'), false);
      await d.gonderici.tetikle();
    },
  );
  test(
    'Sunucunun inceleme sonucu ve yeni ataması yerel durumun yerini alır',
    () async {
      final (d, b, _) = await telefonKur(vaka('Mola'));
      await d.olay('IS.MOLA_VERDIM');
      await d.gonderici.tetikle();
      b.paket = kopya(vaka('Bekleten Teslim')['sonra']);
      b.yayinlandi = true;
      await d.yenile();
      expect(d.hal['durum'], 'ONAY_BEKLIYOR');
      expect(d.gunluk.single['yerel_etki'], false);
    },
  );
  test(
    'Teslim edilmiş ama yayımlanmamış mola diskte yeniden açılınca korunur',
    () async {
      final v = vaka('Mola');
      final (d, b, p) = await telefonKur(v);
      await d.olay('IS.MOLA_VERDIM');
      await d.gonderici.tetikle();
      d.gonderici.beklemeyiDurdur();
      final b2 = TelefonBulutu(v)..alinanlar.addAll(b.alinanlar);
      final (d2, _, _) = await telefonKur(v, depo: p, bulut: b2);
      expect(d2.bekleyen, 0);
      expect(d2.hal['durum'], 'MOLADA');
      b2.yayinla();
      await d2.yenile();
      expect(d2.hal['durum'], 'MOLADA');
      expect(d2.gunluk.single['yerel_etki'], false);
    },
  );
  test(
    'Önbellekli gösteri açılışı oturum ağını beklemez; yerel mola yazılabilir',
    () async {
      final v = vaka('Mola');
      final (d, _, p) = await telefonKur(v);
      d.gonderici.beklemeyiDurdur();
      p.veri['kayit']['gosteri_kisisi'] = true;
      final b2 = TelefonBulutu(v)..oturumBeklesin = Completer<void>();
      final d2 = UygulamaDurumu(
        bulut: b2,
        depo: p,
        semalar: semalar,
        saat: Saat(v['olay']['oldugu_an']),
        telefonKipi: true,
        mvpSadeceCalisan: true,
        gosteriKisileri: const [
          GosteriKisisi(
            etiket: 'Atölye Çalışanı',
            kod: 'K017',
            sifre: '123456',
            yer: 'telefon',
          ),
        ],
      );
      await d2.yukle().timeout(const Duration(milliseconds: 500));
      expect(d2.acik, true);
      await d2
          .olay('IS.MOLA_VERDIM')
          .timeout(const Duration(milliseconds: 500));
      expect(d2.hal['durum'], 'MOLADA');
      b2.oturumBeklesin!.complete();
      await d2.gonderici.tetikle();
      // oneGeldi'nin sıraya aldığı son okuma da bitsin.
      await d2.yenile();
      d2.dispose();
      await b2.dispose();
    },
  );
  testWidgets(
    'Telefon sade; teknik bant ve günlük menüsü yok, durum ve çevrimiçi simgesi var',
    (t) async {
      final (d, b, _) = (await t.runAsync(() => telefonKur(vaka('Mola'))))!;
      d.mesaj = '57014 query canceled';
      d.baglanti = false;
      await t.pumpWidget(IrpApp(durum: d, cizimler: harita, donanim: false));
      expect(find.textContaining('57014'), findsNothing);
      expect(find.text('Hesaplanıyor'), findsNothing);
      expect(find.byTooltip('Çevrimdışı'), findsOneWidget);
      await t.tap(find.byTooltip('Menü'));
      await t.pumpAndSettle();
      expect(find.text('Bu cihazın kayıtları'), findsNothing);
      await t.pumpWidget(const SizedBox());
      await t.pumpAndSettle();
      await t.runAsync(() => b.dispose());
    },
  );
}
