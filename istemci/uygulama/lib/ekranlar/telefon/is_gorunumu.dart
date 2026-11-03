import 'package:flutter/material.dart';

import '../../bulut/uygulama_bulutu.dart';
import '../../durum/uygulama_durumu.dart';

String isAdi(Json? is_) =>
    is_?['islem'] as String? ??
    is_?['is_tanimi'] as String? ??
    is_?['ad'] as String? ??
    'İş Yok';
String kisiAdi(UygulamaDurumu d, String id) =>
    d.gosteriKisileri.where((p) => p.kod == id).firstOrNull?.etiket ??
    d.satirlar('KISILER').where((p) => p['kimlik'] == id).firstOrNull?['ad']
        as String? ??
    'Çalışan';
String isBaglami(UygulamaDurumu d, Json is_) {
  final proje = d
      .satirlar('PROJELER')
      .where((p) => p['kimlik'] == is_['proje'])
      .firstOrNull;
  final etap = d
      .satirlar('ETAPLAR', hedef: is_['proje'] as String?)
      .where((p) => p['kimlik'] == is_['etap'])
      .firstOrNull;
  return [
    if (is_['proje'] != null)
      is_['proje_adi'] ?? proje?['ad'] ?? 'Proje Bilgisi Bekleniyor',
    if (is_['etap_adi'] != null || etap != null) is_['etap_adi'] ?? etap!['ad'],
    if (is_['parca_kodu'] != null) 'Parça ${is_['parca_kodu']}',
    if (is_['nereye'] == 'PROJE_DISI') 'Proje Dışı',
  ].join(' · ');
}

String durumAdi(String? durum) =>
    const {
      'CALISIYOR': 'Çalışıyor',
      'CALISILIYOR': 'Çalışıyor',
      'MOLADA': 'Molada',
      'SABIT_MOLADA': 'Molada',
      'ARIZADA': 'Duruşta',
      'ONAY_BEKLIYOR': 'Onay Bekliyor',
      'MESAI_DISI': 'Mesai Dışı',
      'DEVAM_BEKLIYOR': 'Devam Bekliyor',
      'ON_IS_BEKLIYOR': 'Ön İş Bekliyor',
      'CALISMIYOR': 'Çalışmıyor',
      'SIRADA': 'Sırada',
      'YARIM': 'Yarım Kaldı',
      'REDDEDILDI': 'Düzeltme Bekliyor',
      'BITTI': 'Tamamlandı',
      'IPTAL': 'İptal',
      'HAVUZDA': 'Havuzda',
    }[durum] ??
    'Çalışmıyor';

class DurumEtiketi extends StatelessWidget {
  const DurumEtiketi(this.durum, {super.key});
  final String? durum;
  @override
  Widget build(BuildContext context) {
    final (zemin, yazi) = switch (durum) {
      'CALISIYOR' ||
      'CALISILIYOR' => (const Color(0xffe5f4ea), const Color(0xff166534)),
      'MOLADA' ||
      'SABIT_MOLADA' ||
      'ONAY_BEKLIYOR' ||
      'ON_IS_BEKLIYOR' => (const Color(0xfffff3c4), const Color(0xff715409)),
      'ARIZADA' => (const Color(0xffffe7e5), const Color(0xffb42318)),
      'MESAI_DISI' => (const Color(0xff475467), Colors.white),
      _ => (const Color(0xfff2f4f7), const Color(0xff344054)),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
      decoration: BoxDecoration(
        color: zemin,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        durumAdi(durum),
        style: TextStyle(
          color: yazi,
          fontSize: 15,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}
