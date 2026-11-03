import 'dart:typed_data';

import 'package:irp_cekirdek/irp_cekirdek.dart';

typedef Json = Map<String, dynamic>;

// Model: kurallar_v9.bildirim_kimligi. Çekirdek kutusu kimlik alanı vermez.
String bildirimKimligi(Json b) =>
    b['kimlik'] as String? ??
    '${b['doguran_olay']}/${b['kural']}/${b['alici']}';

/// T17 §2. Ağ ayrıntıları ekranlardan ve çekirdekten ayrılır.
abstract interface class UygulamaBulutu implements Bulut {
  bool get gosteriMi;
  Future<Json> olayAkisi({int sonra = 0, int adet = 200});
  @override
  Future<Json> olayEkle(Json olay, {required String oturum, Json? hassasEk});
  Future<Json> giris(String kod, String parola);
  Future<void> parolaDegistir(String pin);
  Future<Json> oturumYenile(String refreshToken);
  Future<String> simdi();
  Future<String> cihazKaydol(String cihaz);
  Future<List<String>> cihazEsitle(String cihaz, {String? harf});
  Future<Json> oku(String veri, {String? hedef, Json? g});
  Stream<String> sinyaller(String kisi, {Set<String> ekKanallar = const {}});
  Future<void> kanitYukle(String kimlik, Uint8List bytes, String tur);
  Future<void> gosteriSifirla();
}

/// Kabul edilen olayın hesaplanmış sonucunu bildiren canlı kapı.
abstract interface class IslemSonucuBulutu {
  Future<Json> islemSonucu(String olay);
}

/// Tek tutarlı yayın: telefon hali ve aynı yayının içerdiği kendi olayları.
abstract interface class TelefonEsitlemeBulutu {
  Future<Json> telefonEsitle(List<String> olaylar);
}

class BaglantiYok implements Exception {
  const BaglantiYok();
  @override
  String toString() => 'Bağlantı yok; kayıt cihazda bekliyor';
}

class Bakimda implements Exception {
  const Bakimda();
  @override
  String toString() => 'Sistem bakımda; kayıt sonra gönderilecek';
}

String cevapMetni(Json cevap) {
  final mesaj = cevap['mesaj'];
  if (mesaj is String &&
      mesaj.isNotEmpty &&
      !mesaj.contains('Nesnenin durumu bu işleme uygun değil')) {
    return mesaj;
  }
  return switch (cevap['kod'] ?? cevap['sonuc']) {
    'BAYAT' => 'Ekran güncellendi, yeniden bak',
    'DURUM' => 'İşlem uygulanamadı. Ekranı yenileyip kullanılabilen işlemleri kontrol edin.',
    'YETKI' => 'Bu işlem için yetkin yok',
    'HESAP_BEKLIYOR' => 'Sistem hesaplıyor, birazdan tekrar dene',
    'BAKIMDA' => 'Sistem bakımda; kayıt sonra gönderilecek',
    'CAKISMA' => 'Bu kayıt daha önce farklı gönderilmiş',
    'BASARILI' => 'Kaydedildi',
    _ => 'Beklenmeyen hata',
  };
}
