import 'dart:async';

/// Tek uçuş, sıralı gönderim; her tetikleyici aynı döngüye girer (SN-3).
class Gonderici {
  Gonderici({required this.gonder, required this.bekleyen, required this.hata});
  final Future<void> Function() gonder;
  final bool Function() bekleyen;
  final void Function(Object) hata;
  static const gecikmeler = [2, 4, 8, 16, 32, 60];
  Timer? _timer;
  Future<void>? _ucus;
  int _adim = 0;
  bool _kapali = false;
  int? siradakiSaniye;
  Future<void> tetikle() {
    if (_kapali) return Future.value();
    _timer?.cancel();
    return _ucus ??= _calis().whenComplete(() => _ucus = null);
  }

  Future<void> _calis() async {
    try {
      await gonder();
    } catch (e) {
      hata(e);
    }
    if (_kapali) return;
    if (bekleyen()) {
      siradakiSaniye = gecikmeler[_adim];
      if (_adim < gecikmeler.length - 1) _adim++;
      _timer = Timer(Duration(seconds: siradakiSaniye!), tetikle);
    } else {
      _adim = 0;
      siradakiSaniye = null;
    }
  }

  void dispose() {
    _kapali = true;
    _timer?.cancel();
  }

  void beklemeyiDurdur() {
    _timer?.cancel();
    _timer = null;
    _adim = 0;
    siradakiSaniye = null;
  }
}
