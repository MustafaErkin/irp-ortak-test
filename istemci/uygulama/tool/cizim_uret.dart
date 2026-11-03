// Sentetik ölçülendirme eskizleri ve çevrimdışı basılabilir QR sayfası.
import 'dart:convert';
import 'dart:io';

import 'package:image/image.dart' as im;
import 'package:qr/qr.dart';

void main() {
  final dizin = Directory('assets/cizimler')..createSync(recursive: true);
  final harita = <String, String>{};
  final sayfa = StringBuffer(
    '<!doctype html><html lang="tr"><meta charset="utf-8"><title>Sentetik çizim QR kartları</title><style>body{font:18px sans-serif;margin:30px}article{break-inside:avoid;display:inline-block;width:280px;margin:20px;padding:20px;border:1px solid #888;text-align:center}svg{width:210px;height:210px}@media print{button{display:none}}</style><h1>Gösteri çizimleri · SENTETİK</h1><button onclick="print()">Yazdır</button>',
  );
  const kodlar = ['2509084_07_04-63', '2509084_07_05-23', '2509084_07_06-31'];
  for (var n = 0; n < 3; n++) {
    final resim = im.Image(width: 1200, height: 900);
    im.fill(resim, color: im.ColorRgb8(250, 249, 243));
    final kalem = im.ColorRgb8(58, 67, 78);
    void ciz(int x, int y, int xx, int yy) {
      im.drawLine(
        resim,
        x1: x,
        y1: y,
        x2: xx,
        y2: yy,
        color: kalem,
        thickness: 3,
      );
      im.drawLine(
        resim,
        x1: x + 2,
        y1: y - 2,
        x2: xx - 1,
        y2: yy + 2,
        color: im.ColorRgb8(165, 166, 159),
      );
    }

    void yazi(String s, int x, int y) =>
        im.drawString(resim, s, font: im.arial24, x: x, y: y, color: kalem);
    for (var x = 40; x < 1200; x += 40) {
      im.drawLine(
        resim,
        x1: x,
        y1: 0,
        x2: x,
        y2: 900,
        color: im.ColorRgb8(232, 233, 225),
      );
    }
    for (var y = 40; y < 900; y += 40) {
      im.drawLine(
        resim,
        x1: 0,
        y1: y,
        x2: 1200,
        y2: y,
        color: im.ColorRgb8(232, 233, 225),
      );
    }
    yazi('SENTETIK ORNEK - URETIMDE KULLANILMAZ', 70, 60);
    yazi(
      '${kodlar[n]} / ${['SASE', 'BAGLANTI PLAKASI', 'DESTEK'][n]}',
      70,
      110,
    );
    final ust = 260 + n * 35;
    ciz(230, ust, 890, ust);
    ciz(890, ust, 890, 610);
    ciz(890, 610, 230, 610);
    ciz(230, 610, 230, ust);
    if (n == 0) {
      ciz(260, ust + 30, 860, ust + 30);
      ciz(260, 580, 860, 580);
    }
    if (n == 2) {
      ciz(230, 610, 890, ust);
    }
    for (final x in [310, 810]) {
      im.drawCircle(resim, x: x, y: ust + 70, radius: 28, color: kalem);
      ciz(x - 42, ust + 70, x + 42, ust + 70);
      ciz(x, ust + 28, x, ust + 112);
    }
    ciz(230, 700, 890, 700);
    ciz(230, 675, 230, 725);
    ciz(890, 675, 890, 725);
    yazi('${660 - n * 80} mm', 510, 665);
    ciz(970, ust, 970, 610);
    ciz(945, ust, 995, ust);
    ciz(945, 610, 995, 610);
    yazi('${350 - n * 35}', 990, 450);
    yazi('Elle eskiz / Olcek: temsili / Rev. 0', 70, 800);
    final ad = 'ornek_${n + 1}.png', yol = '${dizin.path}/$ad';
    File(yol).writeAsBytesSync(im.encodePng(resim));
    final qrMetni = 'IRP:NESNE:SENTETIK-${n + 1}';
    harita[qrMetni] = yol;
    harita[kodlar[n]] = yol;
    final qr = QrImage(
      QrCode(
        payload: QrPayload.fromString(qrMetni),
        errorCorrectLevel: QrErrorCorrectLevel.medium,
      ),
    );
    final boy = qr.moduleCount + 8;
    sayfa.write(
      '<article><h2>Örnek ${n + 1}</h2><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 $boy $boy"><rect width="$boy" height="$boy" fill="white"/>',
    );
    for (var y = 0; y < qr.moduleCount; y++) {
      for (var x = 0; x < qr.moduleCount; x++) {
        if (qr.isDark(y, x)) {
          sayfa.write('<rect x="${x + 4}" y="${y + 4}" width="1" height="1"/>');
        }
      }
    }
    sayfa.write('</svg><p>${kodlar[n]}</p><small>$qrMetni</small></article>');
  }
  File('${dizin.path}/harita.json').writeAsStringSync(
    '${const JsonEncoder.withIndent('  ').convert(harita)}\n',
  );
  File('${dizin.path}/qr_kartlari.html').writeAsStringSync('$sayfa</html>');
  stdout.writeln('3 sentetik PNG ve basılabilir QR sayfası hazır.');
}
