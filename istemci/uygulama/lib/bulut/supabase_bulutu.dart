import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:http/http.dart' as http;

import 'uygulama_bulutu.dart';

/// SDK taşımasını dışarıdan almak, bütün kapıları ağsız sınamayı sağlar.
class SupabaseBulutu
    implements UygulamaBulutu, IslemSonucuBulutu, TelefonEsitlemeBulutu {
  SupabaseBulutu({SupabaseClient? istemci})
    : _istemci = istemci; // ignore: prefer_initializing_formals
  final SupabaseClient? _istemci;
  final _harfler = <String, String>{};
  int _abonelikSayaci = 0;
  Stream<Json> get oturumlar => _c.auth.onAuthStateChange
      .where((e) => e.session != null)
      .map((e) => _oturum(e.session));

  factory SupabaseBulutu.ayarli(String adres, String anon) {
    ayarlariDogrula(adres, anon);
    return SupabaseBulutu(istemci: SupabaseClient(adres, anon));
  }

  static void ayarlariDogrula(String adres, String anon) {
    final uri = Uri.tryParse(adres);
    var uygun = anon.startsWith('sb_publishable_');
    if (anon.split('.').length == 3) {
      try {
        uygun =
            jsonDecode(
              utf8.decode(
                base64Url.decode(base64Url.normalize(anon.split('.')[1])),
              ),
            )['role'] ==
            'anon';
      } catch (_) {
        uygun = false;
      }
    }
    if (uri == null ||
        uri.scheme != 'https' ||
        uri.host.isEmpty ||
        !uygun ||
        anon.startsWith('sb_secret_')) {
      throw StateError(
        'SUPABASE_URL ve genel SUPABASE_ANON ayarlarını kontrol et.',
      );
    }
  }

  @override
  bool get gosteriMi => false;
  SupabaseClient get _c =>
      _istemci ?? (throw StateError('Bulut yapılandırılmadı'));

  @override
  Future<Json> olayAkisi({int sonra = 0, int adet = 200}) => _istek(
    () async => Json.from(
      await _c.rpc('olay_akisi', params: {'sonra': sonra, 'adet': adet}) as Map,
    ),
  );

  Json _oturum(Session? s) {
    if (s == null) throw StateError('Oturum açılamadı');
    return {'refresh_token': s.refreshToken, 'access_token': s.accessToken};
  }

  Future<T> _istek<T>(Future<T> Function() islem) async {
    try {
      return await islem();
    } on http.ClientException {
      throw const BaglantiYok();
    }
  }

  @override
  Future<Json> giris(String kod, String parola) async => _oturum(
    (await _c.auth.signInWithPassword(
      email: '${kod.trim().toLowerCase()}@calisan.irp',
      password: parola,
    )).session,
  );
  @override
  Future<void> parolaDegistir(String pin) async {
    if (!RegExp(r'^\d{6}$').hasMatch(pin)) {
      throw ArgumentError('Şifre 6 rakam olmalı');
    }
    await _c.auth.updateUser(UserAttributes(password: pin));
  }

  @override
  Future<Json> oturumYenile(String refreshToken) async =>
      _oturum((await _c.auth.refreshSession(refreshToken)).session);
  @override
  Future<String> simdi() async => (await _c.rpc('simdi')) as String;
  @override
  Future<String> cihazKaydol(String cihaz) async => _harfler[cihaz] =
      (await _c.rpc('cihaz_kaydol', params: {'cihaz': cihaz})) as String;
  @override
  Future<List<String>> cihazEsitle(String cihaz, {String? harf}) async {
    await _c.rpc('cihaz_esitle', params: {'cihaz': cihaz});
    // Kayıt kapısı aynı cihaz için aynı harfi döndürür; yeniden açılışta da geçerli.
    final kayitHarfi = harf ?? _harfler[cihaz] ?? await cihazKaydol(cihaz);
    final r = await oku('BUGUNKU_KIMLIKLER', hedef: kayitHarfi);
    return List<String>.from(r['deger'] as List);
  }

  @override
  Future<Json> olayEkle(Json olay, {required String oturum, Json? hassasEk}) =>
      _istek(
        () async => Json.from(
          await _c.rpc(
            'olay_ekle',
            params: {'olay': olay, 'hassas_ek': hassasEk},
          ),
        ),
      );
  @override
  Future<Json> islemSonucu(String olay) => _istek(
    () async => Json.from(
      await _c.rpc('islem_sonucu', params: {'olay_kimligi': olay}) as Map,
    ),
  );
  @override
  Future<Json> telefonEsitle(List<String> olaylar) => _istek(
    () async => Json.from(
      await _c.rpc('telefon_esitle', params: {'olay_kimlikleri': olaylar})
          as Map,
    ),
  );
  @override
  Future<Json> oku(String veri, {String? hedef, Json? g}) => _istek(
    () async => Json.from(
      await _c.rpc('oku', params: {'veri': veri, 'hedef': hedef, 'g': g ?? {}}),
    ),
  );
  @override
  Stream<String> sinyaller(String kisi, {Set<String> ekKanallar = const {}}) {
    final abonelik = ++_abonelikSayaci;
    late StreamController<String> akim;
    final kanallar = <RealtimeChannel>[];
    akim = StreamController<String>(
      onListen: () {
        for (final kanal in {'kisi:$kisi', 'firma', ...ekKanallar}) {
          kanallar.add(
            _c
                .channel('irp-$abonelik-$kanal')
                .onPostgresChanges(
                  event: PostgresChangeEvent.insert,
                  schema: 'public',
                  table: 'degisim_sinyalleri',
                  filter: PostgresChangeFilter(
                    type: PostgresChangeFilterType.eq,
                    column: 'kanal',
                    value: kanal,
                  ),
                  callback: (_) => akim.add(kanal),
                )
                .subscribe((durum, hata) {
                  if (akim.isClosed) return;
                  if (durum == RealtimeSubscribeStatus.channelError ||
                      durum == RealtimeSubscribeStatus.timedOut) {
                    akim.addError(const BaglantiYok());
                  } else if (durum == RealtimeSubscribeStatus.subscribed) {
                    // İlk okuma ile aboneliğin açılması arasında sinyal kaçabilir.
                    // İlk bağlantıda da yeniden bağlantıda da açık ekranı tazele.
                    akim.add(kanal);
                  }
                }),
          );
        }
      },
      onCancel: () async {
        for (final kanal in kanallar) {
          await _c.removeChannel(kanal);
        }
      },
    );
    return akim.stream;
  }

  @override
  Future<void> kanitYukle(String kimlik, Uint8List bytes, String tur) async {
    await _c.storage
        .from('kanitlar')
        .uploadBinary(
          kimlik,
          bytes,
          fileOptions: FileOptions(contentType: tur, upsert: true),
        );
  }

  @override
  Future<void> gosteriSifirla() async {
    await _c.rpc('gosteri_sifirla');
  }
}
