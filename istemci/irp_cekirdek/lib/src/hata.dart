/// Python modelinin hata türünü ve nedenini değiştirmeden taşır.
class ModelHatasi implements Exception {
  const ModelHatasi(this.hataTuru, this.neden);

  final String hataTuru;
  final String neden;

  @override
  String toString() => '$hataTuru: $neden';
}
