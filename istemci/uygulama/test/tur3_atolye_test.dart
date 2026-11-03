import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:irp_cekirdek/irp_cekirdek.dart';
import 'package:irp_uygulama/bulut/uygulama_bulutu.dart';
import 'package:irp_uygulama/bulut/gosteri_kisisi.dart';
import 'package:irp_uygulama/durum/kalici_depo.dart';
import 'package:irp_uygulama/durum/uygulama_durumu.dart';
import 'package:irp_uygulama/sahte/fikstur_bulutu.dart';
import 'package:irp_uygulama/main.dart';
import 'package:irp_uygulama/ekranlar/telefon/eylem_penceresi.dart';
import 'package:irp_uygulama/ekranlar/telefon/ekibim.dart';
import 'package:irp_uygulama/ekranlar/telefon/is_gorunumu.dart';

import 'destek.dart';
import 'web_destek.dart';
import 'calisma_penceresi_test.dart' show pencere;

class YayinBulutu extends FiksturBulutu implements IslemSonucuBulutu {
  YayinBulutu()
    : super(
        fikstur,
        webFikstur: birlestirFikstur(
          dosya('test/fikstur/web.json'),
          dosya('test/fikstur/yonetim.json'),
        ),
        webKisi: 'K009',
      ) {
    webAni = 'atama';
  }
  String yayin = 'BEKLIYOR';
  final sorgular = <String>[];
  Completer<Json>? cevap;
  int hesapRetSayisi = 0;
  final denemeler = <Json>[];
  @override
  Future<Json> olayEkle(
    Json olay, {
    required String oturum,
    Json? hassasEk,
  }) async {
    denemeler.add(kopya(olay));
    if (hesapRetSayisi-- > 0) {
      return {'sonuc': 'REDDEDILDI', 'kod': 'HESAP_BEKLIYOR'};
    }
    return super.olayEkle(olay, oturum: oturum, hassasEk: hassasEk);
  }

  @override
  Future<Json> islemSonucu(String olay) async {
    sorgular.add(olay);
    return cevap?.future ?? {'durum': yayin};
  }
}

Future<(UygulamaDurumu, YayinBulutu)> kur() async {
  final b = YayinBulutu();
  final d = UygulamaDurumu(
    bulut: b,
    depo: BellekKaliciDepo({
      'kayit': {
        'kisi': 'K009',
        'ad': 'Ekip Lideri',
        'harf': 'T',
        'oturum': {'refresh_token': 'sentetik'},
      },
    }),
    semalar: semalar,
    saat: Saat(b.webOkumalar.first['cevap']['hesap_ani']),
    telefonKipi: true,
  );
  await d.yukle();
  d.acik = true;
  await d.yenile();
  addTearDown(() async {
    d.dispose();
    await b.dispose();
  });
  return (d, b);
}

Future<Json> ata(UygulamaDurumu d) {
  final i = d.satirlar('HAVUZ', hedef: d.birim).first;
  return d.yonetim(
    'IS.ATADIM',
    hedefler: [
      {'tur': 'IS', 'kimlik': i['kimlik'], 'surum': i['surum']},
    ],
    girdiler: {'kisi': 'K017', 'sira': 2},
    sonucuBekle: true,
  );
}

void main() {
  test(
    'liderin hesap bekleyen ataması aynı olayla sürer; tek kabul ve tek sonuç',
    () async {
      final (d, b) = await kur();
      b.hesapRetSayisi = 1;
      b.yayin = 'TAMAMLANDI';
      final result = await ata(d);
      expect(result['sonuc'], 'BASARILI');
      expect(b.denemeler, hasLength(2));
      expect(b.denemeler.first, b.denemeler.last);
      expect(b.olaylar, hasLength(1));
      expect(d.mesgul, false);
    },
  );
  test('lider işlemi kabulde bitmez; yayın gelene kadar meşgul, sonuçta liste tazedir', () async {
    final (d, b) = await kur();
    b.cevap = Completer<Json>();
    var bitti = false;
    final pending = ata(d).then((r) {
      bitti = true;
      return r;
    });
    while (b.sorgular.isEmpty) {
      await Future<void>.delayed(const Duration(milliseconds: 5));
    }
    expect(d.mesgul, true);
    expect(bitti, false);
    expect(b.olaylar.length, 1);
    b.cevap!.complete({'durum': 'TAMAMLANDI'});
    final r = await pending;
    expect(r['sonuc'], 'BASARILI');
    expect(r['islem_durumu'], 'TAMAMLANDI');
    expect(d.mesgul, false);
    expect(d.taze('LISTE', hedef: 'K017'), true);
  });
  test('yayın beklerken aynı sonucun kontrolü yeni olay üretmez', () async {
    final (d, b) = await kur();
    d.yayinZamanAsimi = const Duration(milliseconds: 1);
    final r = await ata(d);
    expect(r['sonuc'], 'BEKLIYOR');
    expect(b.olaylar.length, 1);
    b.yayin = 'TAMAMLANDI';
    final son = await d.yonetimSonucunuKontrolEt(r['olay_kimligi']);
    expect(son['sonuc'], 'BASARILI');
    expect(b.olaylar.length, 1);
    expect(b.sorgular.toSet().length, 1);
  });
  test('inceleme gerektiren kabul başarı sayılmaz', () async {
    final (d, b) = await kur();
    b.yayin = 'INCELEME_GEREKIYOR';
    final r = await ata(d);
    expect(r['sonuc'], 'REDDEDILDI');
    expect(r['islem_durumu'], 'INCELEME_GEREKIYOR');
  });
  test('eski sıra önizlemesinden yönetim olayı gönderilmez', () async {
    final (d, b) = await kur();
    final i = d.satirlar('HAVUZ', hedef: d.birim).first;
    await expectLater(
      d.yonetim(
        'IS.ATADIM',
        hedefler: [
          {'tur': 'IS', 'kimlik': i['kimlik'], 'surum': i['surum']},
        ],
        girdiler: {'kisi': 'K017', 'sira': 2},
        beklenenListeler: {'K017': 'eski'},
      ),
      throwsStateError,
    );
    expect(b.olaylar, isEmpty);
  });
  testWidgets(
    'mesai dışı ortalanmış metin ve altta Çıkış Yap; olay üretmeden uygulama kapanır',
    (t) async {
      final (d, b, _) = (await t.runAsync(() => hazir(telefonKipi: true)))!;
      b.okumalar['TELEFON']['deger']['calisma_penceresi'] = pencere(
        tatil: true,
      );
      await t.runAsync(d.yenile);
      await t.pumpWidget(IrpApp(durum: d, cizimler: harita, donanim: false));
      expect(find.text('Mesai Dışındasınız'), findsOneWidget);
      expect(find.byType(AppBar), findsNothing);
      expect(find.byType(IconButton), findsNothing);
      expect(find.text('Günün İşleri'), findsNothing);
      expect(find.text('Takvimi Yenile'), findsNothing);
      expect(find.text('Çıkış Yap'), findsOneWidget);
      final calls = <MethodCall>[];
      t.binding.defaultBinaryMessenger.setMockMethodCallHandler(
        SystemChannels.platform,
        (call) async {
          calls.add(call);
          return null;
        },
      );
      addTearDown(
        () => t.binding.defaultBinaryMessenger.setMockMethodCallHandler(
          SystemChannels.platform,
          null,
        ),
      );
      final before = b.olaylar.length;
      await t.tap(find.text('Çıkış Yap'));
      await t.pump();
      expect(
        calls.where((c) => c.method == 'SystemNavigator.pop'),
        hasLength(1),
      );
      expect(b.olaylar.length, before);
      b.okumalar['TELEFON']['deger']['calisma_penceresi'] = pencere();
      await t.runAsync(d.yenile);
      await t.pumpAndSettle();
      expect(find.text('Mesai Dışındasınız'), findsNothing);
      expect(find.text('TAMAMLA'), findsOneWidget);
      await kapatWeb(t);
    },
  );
  testWidgets(
    'MVP gösteri kişisi gece de işlem yapar; takvim ve olay saati aynı kalır',
    (t) async {
      const person = GosteriKisisi(
        etiket: 'Atölye Çalışanı',
        kod: 'K017',
        sifre: '123456',
        yer: 'telefon',
      );
      final (d, b, _) = (await t.runAsync(
        () => hazir(
          telefonKipi: true,
          mvpMesaiSerbest: true,
          gosteriKisileri: [person],
        ),
      ))!;
      b.okumalar['TELEFON']['deger']['calisma_penceresi'] = pencere(
        tatil: true,
      );
      await t.runAsync(d.yenile);
      expect(d.calismaPenceresi.mesaide, false);
      expect(d.mesaiDenetimi, false);
      expect(d.kapiAcik('IS.MOLA_VERDIM'), true);
      await t.pumpWidget(IrpApp(durum: d, cizimler: harita, donanim: false));
      expect(find.text('Mesai Dışındasınız'), findsNothing);
      expect(find.text('TAMAMLA'), findsOneWidget);
      final now = d.cihaz!.simdiDuzeltilmis().isoformat();
      await t.runAsync(() async {
        await d.olay('IS.MOLA_VERDIM');
        await d.gonderici.tetikle();
      });
      expect(b.olaylar.last['oldugu_an'], now);
      expect(
        b.olaylar.where(
          (e) =>
              '${e['eylem_kodu']}'.startsWith('TAKVIM.') ||
              '${e['eylem_kodu']}'.startsWith('EK_MESAI.'),
        ),
        isEmpty,
      );
      await kapatWeb(t);
    },
  );
  test(
    'MVP bayrağı tek başına normal çalışanın mesai denetimini kaldıramaz',
    () async {
      final (d, b, _) = await hazir(telefonKipi: true, mvpMesaiSerbest: true);
      b.okumalar['TELEFON']['deger']['calisma_penceresi'] = pencere(
        tatil: true,
      );
      await d.yenile();
      expect(d.mesaiDenetimi, true);
      expect(d.mesaiIcinde, false);
      expect(d.kapiAcik('IS.BASLADIM'), false);
    },
  );
  test('telefon işlem reddinin somut açıklamasını gösterir', () {
    expect(
      cevapMetni({'kod': 'DURUM', 'mesaj': 'İş teslim onayı beklemiyor.'}),
      'İş teslim onayı beklemiyor.',
    );
    expect(
      cevapMetni({'kod': 'DURUM'}),
      isNot(contains('Nesnenin durumu bu işleme uygun değil')),
    );
  });
  testWidgets(
    'duruş alt neden başlığı ve alan hatası; boş giriş olay üretmez',
    (t) async {
      final (d, b, _) = (await t.runAsync(() => hazir(telefonKipi: true)))!;
      await t.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: EylemPenceresi(durum: d, kod: 'IS.ARIZA_BILDIRDIM'),
          ),
        ),
      );
      await dokun(t, find.text('ONAYLA'));
      expect(find.text('Bir neden seçin veya açıklama yazın.'), findsOneWidget);
      expect(b.olaylar, isEmpty);
      await dokun(t, find.widgetWithText(ChoiceChip, 'Malzeme'));
      expect(find.text('Malzeme Sorunu Ayrıntısı'), findsOneWidget);
      await kapatWeb(t);
    },
  );
  testWidgets(
    'lider kendini ekipte görmez; teslim onayı devam iznine dönüşmez',
    (t) async {
      final (d, b) = (await t.runAsync(
        () => webHazir(an: 'onay', telefonKipi: true),
      ))!;
      final ekip =
          b.webOkumalar.firstWhere((r) => r['veri'] == 'EKIP')['cevap']['deger']
              as List;
      final p = ekip.firstWhere((p) => p['kisi'] == 'K023');
      p['hal']['durum'] = 'ONAY_BEKLIYOR';
      await t.runAsync(d.yenile);
      await t.pumpWidget(MaterialApp(home: Ekibim(durum: d)));
      await t.pumpAndSettle();
      expect(find.byKey(const Key('ekip-K009')), findsNothing);
      await dokun(t, find.byKey(const Key('ekip-K023')));
      expect(find.text('Devam İzni Ver'), findsNothing);
      expect(find.text('İş Sırasını Değiştir'), findsOneWidget);
      await kapatWeb(t);
    },
  );
  testWidgets(
    'telefon devir önizlemesi uzak ekibin listesini okur ve seçilen sırayı gönderir',
    (t) async {
      final (d, b) = (await t.runAsync(
        () => webHazir(an: 'atama', telefonKipi: true),
      ))!;
      final kaynak = d.nesne('LISTE', hedef: 'K017');
      final uzak = kopya(
        b.webOkumalar.firstWhere(
          (r) => r['veri'] == 'LISTE' && r['hedef'] == 'K017',
        ),
      );
      uzak['hedef'] = 'K701';
      uzak['cevap']['deger']['isler'][0]['islem'] = 'Sahadaki Mevcut İş';
      uzak['cevap']['deger']['isler'][0]['kimlik'] = 'SAHA-ONCEKI';
      final okumalar =
          b.webFikstur!['anlar']['atama']['K009']['okumalar'] as List;
      okumalar.removeWhere((r) => r['veri'] == 'LISTE' && r['hedef'] == 'K701');
      okumalar.add(uzak);
      await t.pumpWidget(MaterialApp(home: Ekibim(durum: d)));
      await t.pumpAndSettle();
      await dokun(t, find.byKey(const Key('ekip-K017')));
      await dokun(t, find.text('İşi Devret'));
      await dokun(
        t,
        find.byKey(Key('siradaki-${kaynak['isler'][0]['kimlik']}')),
      );
      await dokun(t, find.byType(DropdownButtonFormField<String>));
      await dokun(t, find.text(kisiAdi(d, 'K701')).last);
      expect(
        b.cagrilar.where(
          (c) =>
              c['kapi'] == 'oku' &&
              c['veri'] == 'LISTE' &&
              c['hedef'] == 'K701',
        ),
        isNotEmpty,
      );
      expect(find.textContaining('Sahadaki Mevcut İş'), findsWidgets);
      await dokun(t, find.text('Onayla'));
      expect(b.olaylar.last['eylem_kodu'], 'IS.DEVRETTIM');
      expect(b.olaylar.last['girdiler'], {
        'kimden': 'K017',
        'kime': 'K701',
        'kime_sira': 1,
      });
      expect(
        (b.olaylar.last['neyin_ustunde'] as List)
            .where((h) => h['tur'] == 'LISTE')
            .map((h) => h['kimlik'])
            .toSet(),
        {'K017', 'K701'},
      );
      await kapatWeb(t);
    },
  );
  for (final ret in [false, true]) {
    testWidgets(
      'telefon teslim penceresi: ${ret ? 'gerekçeli ret' : 'iş onayı'} doğru hedefe gider',
      (t) async {
        final (d, b) = (await t.runAsync(
          () => webHazir(an: 'onay', telefonKipi: true),
        ))!;
        final is_ = d
            .satirlar('ONAY_LISTESI')
            .firstWhere((i) => i['tur'] == 'SURELI');
        await t.pumpWidget(MaterialApp(home: Ekibim(durum: d)));
        await t.pumpAndSettle();
        await dokun(t, find.text(is_['islem']).first);
        expect(find.text('İş Teslim Onayı'), findsOneWidget);
        expect(find.text('Devam İzni Ver'), findsNothing);
        if (ret) {
          await dokun(t, find.text('Düzeltme İste'));
          await dokun(t, find.text('Düzeltmeye Gönder'));
          expect(find.text('Düzeltme gerekçesini yazın.'), findsOneWidget);
          expect(b.olaylar, isEmpty);
          await t.enterText(
            find.byType(TextField),
            'Ölçüleri tekrar kontrol edin.',
          );
          await dokun(t, find.text('Düzeltmeye Gönder'));
        } else {
          await dokun(t, find.text('İşi Onayla'));
        }
        expect(
          b.olaylar.last['eylem_kodu'],
          ret ? 'IS.REDDETTIM' : 'IS.ONAYLADIM',
        );
        expect(b.olaylar.last['neyin_ustunde'][0]['kimlik'], is_['kimlik']);
        if (ret) {
          expect(
            b.olaylar.last['girdiler']['not'],
            'Ölçüleri tekrar kontrol edin.',
          );
        }
        expect(find.text('İş Teslim Onayı'), findsNothing);
        await kapatWeb(t);
      },
    );
  }
}
