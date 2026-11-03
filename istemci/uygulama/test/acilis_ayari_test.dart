import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:irp_uygulama/bulut/acilis_ayari.dart';

const adres = 'https://sentetik.supabase.co';
const anon = 'sb_publishable_sentetik-test-anahtari';
String jwt(String rol) =>
    'sentetik.${base64Url.encode(utf8.encode(jsonEncode({'role': rol}))).replaceAll('=', '')}.imza';

void main() {
  test(
    'Gösteri kişileri web ayarından ve telefon derlemesinden okunur',
    () async {
      final kisiler = [
        {
          'etiket': 'Atölye Çalışanı 1',
          'kod': 'K017',
          'sifre': 'sentetik-parola',
          'yer': 'telefon',
        },
        {
          'etiket': 'İmalat Ekip Lideri',
          'kod': 'K009',
          'sifre': 'sentetik-parola',
          'yer': 'ikisi',
        },
      ];
      final c = MockClient(
        (_) async => http.Response.bytes(
          utf8.encode(
            jsonEncode({
              'bulut': 'SUPABASE',
              'supabase_url': adres,
              'supabase_anon': anon,
              'gosteri_kisileri': kisiler,
            }),
          ),
          200,
        ),
      );
      final a = await acilisAyariniOku(
        web: true,
        sayfa: Uri.parse('http://localhost:8080/'),
        istemci: c,
      );
      expect(a.kisiler.map((k) => k.etiket), [
        'Atölye Çalışanı 1',
        'İmalat Ekip Lideri',
      ]);
      final telefon = await acilisAyariniOku(
        web: false,
        sayfa: Uri(),
        gosteriKisileri: jsonEncode(kisiler),
      );
      expect(telefon.kisiler.first.kod, 'K017');
      await expectLater(
        acilisAyariniOku(web: false, sayfa: Uri(), gosteriKisileri: '[bozuk'),
        throwsA(isA<BulutAyariHatasi>()),
      );
      c.close();
    },
  );
  test(
    'Ayar var: dosya okunur; gösterim ve derleme ayarı dosyadan önce gelir',
    () async {
      var n = 0;
      final c = MockClient((r) async {
        n++;
        expect(r.url.toString(), 'http://localhost:8080/alt/ayar.json');
        return http.Response(
          jsonEncode({
            'bulut': 'SUPABASE',
            'supabase_url': adres,
            'supabase_anon': anon,
          }),
          200,
        );
      });
      final sayfa = Uri.parse('http://localhost:8080/alt/?x=1');
      final a = await acilisAyariniOku(web: true, sayfa: sayfa, istemci: c);
      expect(a.supabase, isTrue);
      expect(a.adres, adres);
      expect(a.anon, anon);
      expect(
        (await acilisAyariniOku(
          web: true,
          sayfa: sayfa,
          kip: 'GOSTERIM',
          istemci: c,
        )).gosterim,
        isTrue,
      );
      expect(
        (await acilisAyariniOku(
          web: true,
          sayfa: sayfa.replace(query: 'kip=gosterim'),
          bulut: 'BOZUK',
          anon: 'sb_secret_reddedilmeli',
          istemci: c,
        )).gosterim,
        isTrue,
      );
      final derleme = await acilisAyariniOku(
        web: true,
        sayfa: sayfa,
        istemci: c,
        bulut: 'SUPABASE',
        adres: adres,
        anon: jwt('anon'),
      );
      expect(derleme.supabase, isTrue);
      expect(n, 1);
      c.close();
    },
  );
  test(
    'Ayar yok: yalnız 404 sahte bulutu seçer; telefon dosya okumaz',
    () async {
      var n = 0;
      final c = MockClient((_) async {
        n++;
        return http.Response('', 404);
      });
      final sayfa = Uri.parse('http://localhost:8080/');
      expect(
        (await acilisAyariniOku(web: true, sayfa: sayfa, istemci: c)).supabase,
        isFalse,
      );
      expect(
        (await acilisAyariniOku(web: false, sayfa: sayfa, istemci: c)).supabase,
        isFalse,
      );
      expect(n, 1);
      c.close();
    },
  );
  test(
    'Bozuk/eksik ayar, HTTP hatası ve bağlantı hatası açık hata verir',
    () async {
      for (final (icerik, durum) in [
        ('{bozuk', 200),
        ('{}', 200),
        ('[]', 200),
        ('hata', 500),
      ]) {
        final c = MockClient((_) async => http.Response(icerik, durum));
        await expectLater(
          acilisAyariniOku(
            web: true,
            sayfa: Uri.parse('http://localhost:8080/'),
            istemci: c,
          ),
          throwsA(
            isA<BulutAyariHatasi>().having(
              (e) => e.toString(),
              'mesaj',
              'Bulut ayarı okunamadı',
            ),
          ),
        );
        c.close();
      }
      final c = MockClient(
        (_) async => throw http.ClientException('Gizli içerik gösterilmemeli'),
      );
      await expectLater(
        acilisAyariniOku(
          web: true,
          sayfa: Uri.parse('http://localhost:8080/'),
          istemci: c,
        ),
        throwsA(isA<BulutAyariHatasi>()),
      );
      c.close();
    },
  );
  test('Servis ve gizli anahtar reddedilir; hata anahtarı sızdırmaz', () async {
    for (final anahtar in ['sb_secret_yasak', jwt('service_role'), 'bozuk']) {
      final c = MockClient(
        (_) async => http.Response(
          jsonEncode({
            'bulut': 'SUPABASE',
            'supabase_url': adres,
            'supabase_anon': anahtar,
          }),
          200,
        ),
      );
      await expectLater(
        acilisAyariniOku(
          web: true,
          sayfa: Uri.parse('http://localhost:8080/'),
          istemci: c,
        ),
        throwsA(
          isA<BulutAyariHatasi>().having(
            (e) => e.toString(),
            'mesaj',
            'Bulut ayarı okunamadı',
          ),
        ),
      );
      c.close();
    }
  });
}
