// Yalnız yerel sınama: APK'nın kullandığı Cihaz sınıfı, gerçek SQL kabul kapısına yazar.
// Telefon arayüzü ve fiziksel cihaz provası yerine geçmez.
import 'dart:convert';
import 'dart:io';

import 'package:irp_cekirdek/irp_cekirdek.dart';

typedef Sozluk = Map<String, dynamic>;

class YerelTasimaci implements Bulut {
  YerelTasimaci(this.origin, this.kisi);
  final String origin, kisi;
  final http = HttpClient();

  Future<dynamic> rpc(String name, [Map<String, dynamic> body = const {}]) async {
    final request = await http.postUrl(Uri.parse('$origin/rest/v1/rpc/$name'));
    request.headers
      ..contentType = ContentType.json
      ..set('Authorization', 'Bearer LOCAL.$kisi');
    final bytes = utf8.encode(jsonEncode(body));
    request.contentLength = bytes.length;
    request.add(bytes);
    final response = await request.close();
    final value = jsonDecode(await utf8.decoder.bind(response).join());
    if (response.statusCode != 200) throw StateError('$kisi: $name başarısız');
    return value;
  }

  @override
  Future<Sozluk> olayEkle(Sozluk olay, {required String oturum}) async {
    final result = Sozluk.from(await rpc('olay_ekle', {'olay': olay}));
    if (result['sonuc'] != 'BASARILI') {
      throw StateError('$kisi: ${olay['eylem_kodu']} / ${result['kod']}');
    }
    stdout.writeln('Telefon çekirdeği: $kisi ${olay['eylem_kodu']} kabul edildi.');
    return result;
  }

  Future<Sozluk> telefon() async => Sozluk.from(
    (await rpc('oku', {'veri': 'TELEFON', 'g': {}}))['deger'],
  );
}

Future<void> main(List<String> args) async {
  final origin = args.single;
  if (Uri.parse(origin).host != '127.0.0.1') {
    throw StateError('Yalnız yerel sınama sunucusu kullanılabilir');
  }
  for (final person in ['K017', 'K031']) {
    final transport = YerelTasimaci(origin, person);
    try {
      final letter = await transport.rpc('cihaz_kaydol', {'cihaz': 'TEL-SENARYO1-$person'}) as String;
      final clock = SistemSaati();
      final device = Cihaz(person, letter, clock, telefon: true);
      final before = clock.simdi();
      final server = await transport.rpc('simdi');
      device.saatFarkiOlc(before, server, clock.simdi());
      await transport.rpc('cihaz_esitle', {'cihaz': 'TEL-SENARYO1-$person'});
      final ids = await transport.rpc('oku', {'veri': 'BUGUNKU_KIMLIKLER', 'hedef': letter, 'g': {}});
      device.sayaciEsitle(List<String>.from(ids['deger']));
      for (final code in ['MESAI.GIRDIM', 'IS.BASLADIM', 'IS.TAMAMLADIM']) {
        final phone = await transport.telefon();
        final state = Sozluk.from(phone['son_hal']);
        final jobs = (phone['isler'] as Map).map<String,Sozluk>((k,v)=>MapEntry('$k',Sozluk.from(v)));
        final list = List<String>.from(phone['liste']);
        if (code == 'MESAI.GIRDIM' && state['durum'] != 'MESAI_DISI') continue;
        await device.olayYaz(code, state, isler: jobs, liste: list,
          isKimligi: code == 'MESAI.GIRDIM' ? null : list.first,
          kanit: const [],
        );
        await device.gonderimDongusu(transport);
      }
      if (device.bekleyenSayisi() != 0) throw StateError('Gönderim kuyruğu boş değil');
    } finally {
      transport.http.close(force:true);
    }
  }
}
