import 'package:flutter/material.dart';

import '../bulut/gosteri_kisisi.dart';
import '../durum/uygulama_durumu.dart';
import 'telefon/ortak.dart';

Future<void> kisiDegistir(BuildContext context, UygulamaDurumu durum) async {
  final secilen = await showDialog<GosteriKisisi>(
    context: context,
    builder: (ctx) => SimpleDialog(
      title: const Text('Kişi değiştir'),
      children: [
        for (final k in durum.gosteriKisileri)
          SimpleDialogOption(
            onPressed: () => Navigator.pop(ctx, k),
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 18),
            child: Text(k.etiket),
          ),
      ],
    ),
  );
  if (secilen == null || !context.mounted) return;
  final sayi = durum.gonderilmemisKayitSayisi;
  final evet = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: const Text('Bu cihazdaki her şey sıfırlansın mı?'),
      content: Text(
        '${sayi > 0 ? '$sayi gönderilmemiş kayıt var.\n\n' : ''}'
        'Gönderilmemiş kayıtlar kaybolur. ${secilen.etiket} olarak açılacak.',
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(ctx, false),
          child: const Text('Vazgeç'),
        ),
        TextButton(
          onPressed: () => Navigator.pop(ctx, true),
          child: const Text('Evet, sıfırla'),
        ),
      ],
    ),
  );
  if (evet == true && context.mounted) {
    await isle(context, () => durum.gosteriKisisiniDegistir(secilen));
  }
}

class KisiDegistirMenusu extends StatelessWidget {
  const KisiDegistirMenusu({super.key, required this.durum});
  final UygulamaDurumu durum;
  @override
  Widget build(BuildContext context) => durum.gosteriKisileri.isEmpty
      ? const SizedBox.shrink()
      : PopupMenuButton<String>(
          tooltip: 'Menü',
          icon: const Icon(Icons.more_horiz),
          enabled: !durum.mesgul,
          onSelected: (_) => kisiDegistir(context, durum),
          itemBuilder: (_) => [
            const PopupMenuItem(value: 'kisi', child: Text('Kişi değiştir')),
          ],
        );
}

class GosteriGirisi extends StatelessWidget {
  const GosteriGirisi({super.key, required this.durum});
  final UygulamaDurumu durum;
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(actions: [KisiDegistirMenusu(durum: durum)]),
    body: Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              durum.mesgul
                  ? 'Giriş yapılıyor…'
                  : durum.mesaj ?? 'Gösteri hesabı açılıyor',
              textAlign: TextAlign.center,
            ),
            if (!durum.mesgul)
              TextButton(
                onPressed: () => isle(
                  context,
                  () => durum.gosteriKisisiniDegistir(
                    durum.gosteriKisileri.first,
                  ),
                ),
                child: const Text('Yeniden dene'),
              ),
          ],
        ),
      ),
    ),
  );
}

class BilgisayarHesabi extends StatelessWidget {
  const BilgisayarHesabi({super.key, required this.durum});
  final UygulamaDurumu durum;
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(actions: [KisiDegistirMenusu(durum: durum)]),
    body: SafeArea(
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                durum.ad,
                style: Theme.of(context).textTheme.titleLarge,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              const Text(
                'Bu hesap bilgisayardan kullanılır',
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    ),
  );
}
