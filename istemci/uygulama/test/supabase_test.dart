import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:irp_cekirdek/irp_cekirdek.dart';
import 'package:irp_uygulama/bulut/supabase_bulutu.dart';
import 'package:irp_uygulama/bulut/uygulama_bulutu.dart';
import 'package:irp_uygulama/durum/kalici_depo.dart';
import 'package:irp_uygulama/durum/uygulama_durumu.dart';
import 'package:stream_channel/stream_channel.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import 'destek.dart' show dosya, semalar, notHedefi;

// Bellek içi Phoenix taşıması; HTTP ve WebSocket hiçbir soket açmaz.
class BellekSoket extends StreamChannelMixin implements WebSocketChannel {
  final giren = StreamController<dynamic>();
  final katilimlar = <String, Json>{};
  final kimlikler = <String, int>{};
  int sayac = 0;
  bool katilimlariBeklet = false;
  final bekleyenCevaplar = <String>[];
  void katilimlariTamamla() {
    katilimlariBeklet = false;
    for (final cevap in bekleyenCevaplar) {
      giren.add(cevap);
    }
    bekleyenCevaplar.clear();
  }

  @override
  Stream<dynamic> get stream => giren.stream;
  @override
  late final WebSocketSink sink = BellekSink(this);
  @override
  Future<void> get ready async {}
  @override
  String? get protocol => null;
  @override
  int? get closeCode => null;
  @override
  String? get closeReason => null;
  void al(dynamic veri) {
    final m = jsonDecode(veri as String) as List;
    Json cevap = {};
    if (m[3] == 'phx_join') {
      final filtre = Json.from(m[4]['config']['postgres_changes'].single);
      katilimlar[m[2]] = filtre;
      kimlikler[m[2]] = ++sayac;
      cevap = {
        'postgres_changes': [
          {...filtre, 'id': kimlikler[m[2]]},
        ],
      };
    }
    if (m[3] == 'phx_leave') katilimlar.remove(m[2]);
    final yanit = jsonEncode([
      m[0],
      m[1],
      m[2],
      'phx_reply',
      {'status': 'ok', 'response': cevap},
    ]);
    if (katilimlariBeklet && m[3] == 'phx_join') {
      bekleyenCevaplar.add(yanit);
    } else {
      giren.add(yanit);
    }
  }

  void sinyal(String kanal) {
    final konu = katilimlar.entries
        .lastWhere((e) => e.value['filter'] == 'kanal=eq.$kanal')
        .key;
    final id = kimlikler[konu];
    giren.add(
      jsonEncode([
        null,
        null,
        konu,
        'postgres_changes',
        {
          'ids': [id],
          'data': {
            'schema': 'public',
            'table': 'degisim_sinyalleri',
            'type': 'INSERT',
            'commit_timestamp': '2026-12-15T07:00:00Z',
            'columns': [],
            'record': {'kanal': kanal},
          },
        },
      ]),
    );
  }
}

class BellekSink implements WebSocketSink {
  BellekSink(this.soket);
  final BellekSoket soket;
  @override
  void add(dynamic data) => soket.al(data);
  @override
  void addError(Object error, [StackTrace? stackTrace]) => throw error;
  @override
  Future<void> addStream(Stream stream) async {
    await for (final v in stream) {
      add(v);
    }
  }

  @override
  Future<void> close([int? code, String? reason]) async {
    unawaited(soket.giren.close());
  }

  @override
  Future<void> get done => soket.giren.done;
}

class SahteSunucu {
  final istekler = <http.Request>[];
  final soket = BellekSoket();
  bool kesik = false, red = false;
  final kabul = <String>{};
  final telefon = dosya('test/fikstur/telefon.json');
  late final sdk = SupabaseClient(
    'https://ag-kullanilmaz.invalid',
    'sentetik-anon',
    httpClient: MockClient((r) async => yanit(r)),
    authOptions: const AuthClientOptions(autoRefreshToken: false),
    realtimeClientOptions: RealtimeClientOptions(transport: (_, _) => soket),
  );
  late final bulut = SupabaseBulutu(istemci: sdk);
  http.Response yanit(http.Request r) {
    istekler.add(r);
    if (kesik) throw http.ClientException('Sentetik ağ kesintisi');
    final yol = r.url.path;
    final b = r.body.isEmpty || yol.contains('/storage/')
        ? <String, dynamic>{}
        : Json.from(jsonDecode(r.body) as Map? ?? {});
    dynamic sonuc;
    var status = 200;
    if (yol.endsWith('/token')) {
      sonuc = {
        'access_token': 'sentetik-access',
        'refresh_token': 'yenilenmis-refresh',
        'token_type': 'bearer',
        'expires_in': 3600,
        'user': {
          'id': 'sahte-kullanici',
          'app_metadata': {},
          'user_metadata': {},
          'aud': 'authenticated',
          'created_at': '2026-10-01T00:00:00Z',
        },
      };
    } else if (yol.endsWith('/user')) {
      sonuc = {
        'id': 'sahte-kullanici',
        'app_metadata': {},
        'user_metadata': {},
        'aud': 'authenticated',
        'created_at': '2026-10-01T00:00:00Z',
      };
    } else if (yol.contains('/storage/')) {
      sonuc = {'Key': 'kanitlar/olay/0-kanit.jpg'};
    } else if (yol.endsWith('/simdi')) {
      sonuc = '2026-10-22T10:40:00+03:00';
    } else if (yol.endsWith('/cihaz_kaydol')) {
      sonuc = 'T';
    } else if (yol.endsWith('/cihaz_esitle')) {
      sonuc = null;
    } else if (yol.endsWith('/olay_ekle')) {
      final id = b['olay']['olay_kimligi'] as String;
      final tekrar = kabul.contains(id);
      if (!red) kabul.add(id);
      sonuc = {
        'sonuc': red ? 'REDDEDILDI' : 'BASARILI',
        'kod': red ? 'YETKI' : null,
        'neden': red ? 'Yetki yok' : null,
        'tekrar': tekrar,
        'alindi': !red,
        'hesap': 1,
      };
    } else if (yol.endsWith('/oku')) {
      if (b['veri'] == 'HATA') {
        status = 400;
        sonuc = {'message': 'IRP|YETKI|Okuma izni yok', 'code': 'P0001'};
      } else {
        final okumalar = telefon['durumlar']['calisiyor'];
        sonuc = b['veri'] == 'BUGUNKU_KIMLIKLER'
            ? {
                'deger': ['261022_K017_0001T'],
                'hesap': 1,
                'hesap_ani': '2026-10-22T10:40:00+03:00',
              }
            : okumalar[b['veri']] ??
                  {
                    'deger': [],
                    'hesap': 1,
                    'hesap_ani': '2026-10-22T10:40:00+03:00',
                  };
      }
    } else {
      throw StateError('Beklenmeyen yol: $yol');
    }
    return http.Response(
      jsonEncode(sonuc),
      status,
      request: r,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );
  }

  Future<UygulamaDurumu> durum() async {
    final d = UygulamaDurumu(
      bulut: bulut,
      depo: BellekKaliciDepo({
        'kayit': {
          'kisi': 'K017',
          'harf': 'T',
          'oturum': {'refresh_token': 'ilk-refresh'},
        },
      }),
      semalar: semalar,
      saat: Saat('2026-10-22T10:40:00+03:00'),
    );
    await d.yukle();
    d.acik = true;
    d.oturumIzle(bulut.oturumlar);
    addTearDown(d.dispose);
    return d;
  }
}

void main() {
  late SahteSunucu s;
  setUp(() {
    s = SahteSunucu();
  });
  tearDown(() async {
    await s.sdk.dispose();
  });
  test(
    'Auth, saat, cihaz ve kanıt kapıları gerçek SDK ile sahte HTTP kullanır',
    () async {
      final d = await s.durum();
      final oturum = await s.bulut.giris(' K017 ', 'ilk-parola');
      expect(jsonDecode(s.istekler.first.body)['email'], 'k017@calisan.irp');
      expect(oturum['refresh_token'], 'yenilenmis-refresh');
      await s.bulut.parolaDegistir('654321');
      expect(jsonDecode(s.istekler.last.body)['password'], '654321');
      await s.bulut.oturumYenile('ilk-refresh');
      await d.yenile(); // Kalıcı yazım sırasının tamamlanmasını da bekler.
      expect(
        (await d.depo.oku())['kayit']['oturum']['refresh_token'],
        'yenilenmis-refresh',
      );
      expect(await s.bulut.simdi(), '2026-10-22T10:40:00+03:00');
      expect(await s.bulut.cihazKaydol('IRP-sentetik-kurulum'), 'T');
      expect(await s.bulut.cihazEsitle('TEL-K017', harf: 'T'), [
        '261022_K017_0001T',
      ]);
      expect(jsonDecode(s.istekler[s.istekler.length - 2].body), {
        'cihaz': 'TEL-K017',
      });
      expect(jsonDecode(s.istekler.last.body)['hedef'], 'T');
      await s.bulut.kanitYukle(
        'olay/0-kanit.jpg',
        Uint8List.fromList([1, 2, 3]),
        'image/jpeg',
      );
      expect(
        s.istekler.last.url.path,
        '/storage/v1/object/kanitlar/olay/0-kanit.jpg',
      );
      expect(s.istekler.last.body, contains('content-type: image/jpeg'));
      expect(
        () => SupabaseBulutu.ayarli('https://ornek.invalid', 'sb_secret_yasak'),
        throwsStateError,
      );
    },
  );
  test('oku zarfı ve IRP hata gövdesi korunur', () async {
    final r = await s.bulut.oku('BUGUNKU_KIMLIKLER', hedef: 'T');
    expect(r.keys, containsAll(['deger', 'hesap', 'hesap_ani']));
    expect(jsonDecode(s.istekler.last.body), {
      'veri': 'BUGUNKU_KIMLIKLER',
      'hedef': 'T',
      'g': {},
    });
    await expectLater(
      s.bulut.oku('HATA'),
      throwsA(
        isA<PostgrestException>().having(
          (e) => e.message,
          'message',
          'IRP|YETKI|Okuma izni yok',
        ),
      ),
    );
  });
  test(
    'olay_ekle kabul, ret, tekrar ve hassas ek sözleşmesini korur',
    () async {
      final e = {'olay_kimligi': 'sentetik-1'};
      final ilk = await s.bulut.olayEkle(
        e,
        oturum: 'K017',
        hassasEk: {'neden': 'örnek'},
      );
      expect(ilk['alindi'], isTrue);
      expect(ilk['tekrar'], isFalse);
      expect(jsonDecode(s.istekler.last.body)['hassas_ek'], {'neden': 'örnek'});
      expect((await s.bulut.olayEkle(e, oturum: 'K017'))['tekrar'], isTrue);
      s.red = true;
      final ret = await s.bulut.olayEkle({
        'olay_kimligi': 'sentetik-2',
      }, oturum: 'K017');
      expect(ret['kod'], 'YETKI');
      expect(ret['alindi'], isFalse);
    },
  );
  test(
    'HTTP kesintisinde günlük kalıcı bekler; dönüşte aynı olay gönderilir',
    () async {
      final d = await s.durum();
      await d.yenile();
      s.kesik = true;
      final e = await d.olay(
        'NOT.YAZDIM',
        girdiler: {'metin': 'Ağsız kayıt'},
        hedefler: notHedefi,
      );
      await d.gonderici.tetikle();
      expect(d.bekleyen, 1);
      expect(d.baglanti, isFalse);
      expect((await d.depo.oku())['cihazlar']['K017']['gunluk'], isNotEmpty);
      s.kesik = false;
      await d.gonderici.tetikle();
      expect(d.bekleyen, 0);
      expect(s.kabul, contains(e['olay_kimligi']));
    },
  );
  test('İlk okuma ile abonelik arasındaki değişim bağlantı kurulunca alınır', () async {
    s.soket.katilimlariBeklet = true;
    final d = await s.durum();
    await d.yenile();
    await Future<void>.delayed(Duration.zero);
    expect(s.soket.bekleyenCevaplar, isNotEmpty);
    expect(d.telefon['yenileme_deneyi'], isNull);
    // İlk okuma bitti; sunucu değişti ama abone henüz hazır olmadığı için sinyal yok.
    s.telefon['durumlar']['calisiyor']['TELEFON']['deger']['yenileme_deneyi'] =
        'yeni';
    final yenilendi = Completer<void>();
    d.addListener(() {
      if (d.telefon['yenileme_deneyi'] == 'yeni' && !yenilendi.isCompleted) {
        yenilendi.complete();
      }
    });
    s.soket.katilimlariTamamla();
    await yenilendi.future.timeout(const Duration(seconds: 2));
    expect(d.telefon['yenileme_deneyi'], 'yeni');
  });
  test('INSERT aboneliği proje değişimini ve birleşen sinyalle yeniden okumayı taşır', () async {
    final d = await s.durum();
    await d.yenile();
    await Future<void>.delayed(Duration.zero);
    final birTur = s.istekler.length;
    d.acikProje = '2509084';
    await d.yenile();
    await Future<void>.delayed(Duration.zero);
    expect(
      s.soket.katilimlar.values.map((f) => f['filter']),
      containsAll([
        'kanal=eq.kisi:K017',
        'kanal=eq.firma',
        'kanal=eq.proje:2509084',
      ]),
    );
    expect(
      s.soket.katilimlar.values,
      everyElement(containsPair('table', 'degisim_sinyalleri')),
    );
    expect(
      s.soket.katilimlar.values.firstWhere(
        (f) => f['filter'] == 'kanal=eq.kisi:K017',
      ),
      containsPair('filter', 'kanal=eq.kisi:K017'),
    );
    final n = s.istekler.length;
    final yenilendi = Completer<void>();
    d.addListener(() {
      if (s.istekler.length > n && !yenilendi.isCompleted) {
        yenilendi.complete();
      }
    });
    s.soket.sinyal('kisi:K017');
    s.soket.sinyal('firma');
    s.soket.sinyal('proje:2509084');
    expect(s.istekler.length, n);
    await yenilendi.future.timeout(const Duration(seconds: 5));
    expect(s.istekler.length, n + birTur);
  });
}
