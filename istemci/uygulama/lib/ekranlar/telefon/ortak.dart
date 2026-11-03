import 'package:flutter/material.dart';

ThemeData tema(Brightness parlaklik) {
  final koyu = parlaklik == Brightness.dark;
  final renk =
      ColorScheme.fromSeed(
        seedColor: const Color(0xff1d5fbf),
        brightness: parlaklik,
      ).copyWith(
        primary: Color(koyu ? 0xff7fb0ff : 0xff1d5fbf),
        surface: Color(koyu ? 0xff1f2228 : 0xffffffff),
        onSurface: Color(koyu ? 0xffe8e9ec : 0xff1c1f24),
        outline: Color(koyu ? 0xff343840 : 0xffdddad3),
      );
  return ThemeData(
    fontFamily: 'IRP',
    useMaterial3: true,
    colorScheme: renk,
    scaffoldBackgroundColor: Color(koyu ? 0xff16181c : 0xfff5f4f0),
    textTheme: const TextTheme(
      bodyLarge: TextStyle(fontSize: 17, height: 1.45),
      bodyMedium: TextStyle(fontSize: 16, height: 1.4),
      titleLarge: TextStyle(fontSize: 25, fontWeight: FontWeight.w700),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: renk.surface,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 18),
    ),
    chipTheme: const ChipThemeData(
      padding: EdgeInsets.symmetric(horizontal: 12, vertical: 18),
    ),
    bottomSheetTheme: BottomSheetThemeData(backgroundColor: renk.surface),
    iconButtonTheme: IconButtonThemeData(
      style: IconButton.styleFrom(minimumSize: const Size(56, 56)),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(minimumSize: const Size(56, 56)),
    ),
  );
}

class Dugme extends StatelessWidget {
  const Dugme(this.yazi, {super.key, this.bas, this.renk = 'mavi'});
  final String yazi, renk;
  final VoidCallback? bas;
  @override
  Widget build(BuildContext context) {
    final koyu = Theme.of(context).brightness == Brightness.dark;
    final (zemin, yaziRengi) = switch (renk) {
      'yesil' => (
        Color(koyu ? 0xff18301f : 0xffe5f4ea),
        Color(koyu ? 0xff6fd19a : 0xff1d8048),
      ),
      'sari' => (
        Color(koyu ? 0xff6e5d1f : 0xfff5e6a8),
        Color(koyu ? 0xfffff3c4 : 0xff4f4100),
      ),
      'kirmizi' => (
        Color(koyu ? 0xff3d1d1b : 0xfffbe7e5),
        Color(koyu ? 0xffff8a80 : 0xffb3261e),
      ),
      'sade' => (
        Theme.of(context).colorScheme.surface,
        Theme.of(context).colorScheme.onSurface,
      ),
      _ => (
        Color(koyu ? 0xff1e2b42 : 0xffe6eefb),
        Theme.of(context).colorScheme.primary,
      ),
    };
    return SizedBox(
      width: double.infinity,
      child: FilledButton(
        onPressed: bas,
        style: FilledButton.styleFrom(
          minimumSize: const Size(56, 60),
          backgroundColor: zemin,
          foregroundColor: yaziRengi,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          textStyle: const TextStyle(
            fontFamily: 'IRP',
            fontSize: 17,
            fontWeight: FontWeight.w800,
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 12),
          child: Text(yazi, textAlign: TextAlign.center),
        ),
      ),
    );
  }
}

class Bant extends StatelessWidget {
  const Bant(this.metin, {super.key, this.bas});
  final String metin;
  final VoidCallback? bas;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: Material(
      color: Theme.of(context).colorScheme.secondaryContainer,
      borderRadius: BorderRadius.circular(10),
      child: InkWell(
        onTap: bas,
        borderRadius: BorderRadius.circular(10),
        child: ConstrainedBox(
          constraints: const BoxConstraints(minHeight: 56),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Row(
              children: [
                Expanded(child: Text(metin)),
                if (bas != null) const Icon(Icons.chevron_right),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}

Future<bool> isle(BuildContext context, Future<void> Function() eylem) async {
  try {
    await eylem();
    return true;
  } catch (e) {
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            e is ArgumentError ? e.message.toString() : e.toString(),
          ),
        ),
      );
    }
    return false;
  }
}

Future<void> altPencere(BuildContext context, Widget child) =>
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      useSafeArea: true,
      constraints: const BoxConstraints(maxWidth: 480),
      builder: (context) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.viewInsetsOf(context).bottom,
        ),
        child: child,
      ),
    );

String etiket(String kod) =>
    const {
      'CALISAN': 'Çalışan',
      'MALZEME': 'Malzeme',
      'MAKINE': 'Makine',
      'BEKLEME': 'Bekleme',
      'TEKNIK': 'Teknik',
      'HATA': 'Hata',
      'ISLETME': 'İşletme',
      'KENDI': 'Kendi',
      'DIGER': 'Diğer',
      'EKSIK': 'Eksik',
      'HATALI': 'Hatalı',
      'GECIKTI': 'Gecikti',
      'KAYNAK': 'Kaynak',
      'TORNA': 'Torna',
      'RESIM': 'Resim',
      'OLCU': 'Ölçü',
      'LISTE': 'Liste',
      'TASARIM': 'Tasarım',
      'BIRIM': 'Birim',
      'MUSTERI': 'Müşteri',
      'BILGI': 'Bilgi',
      'KIRILMA': 'Kırılma',
      'BOZULMA': 'Bozulma',
      'ELEKTRIK': 'Elektrik',
      'TOPLANTI': 'Toplantı',
      'EGITIM': 'Eğitim',
      'YONLENDIRME': 'Yönlendirme',
      'KISISEL': 'Kişisel',
    }[kod] ??
    kod;
