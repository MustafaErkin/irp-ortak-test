import 'dart:async';

import 'package:flutter/material.dart';

import '../../bulut/uygulama_bulutu.dart';
import '../../durum/uygulama_durumu.dart';
import '../kisi_degistir.dart';
import 'ortak.dart';
import 'is_gorunumu.dart';

Json _hedef(Json i) => {
  'tur': 'IS',
  'kimlik': i['kimlik'],
  'surum': i['surum'],
};
List<Json> _liste(UygulamaDurumu d, String kisi) =>
    (d.nesne('LISTE', hedef: kisi)['isler'] as List? ?? [])
        .map((i) => Json.from(i as Map))
        .toList();
List<Json> _ekip(UygulamaDurumu d) =>
    d.satirlar('EKIP', hedef: d.birim).where((p) {
      final kisi = d
          .satirlar('KISILER')
          .where((k) => k['kimlik'] == p['kisi'])
          .firstOrNull;
      return p['kisi'] != d.kisi &&
          kisi?['aktif'] != false &&
          kisi?['yaka'] == 'MAVI';
    }).toList();
List<Json> _onaylar(UygulamaDurumu d) => d
    .satirlar('ONAY_LISTESI')
    .where(
      (i) =>
          const ['SURELI', 'ANLIK'].contains(i['tur']) &&
          i['durum'] == 'ONAY_BEKLIYOR' &&
          i['tamamlayan'] != d.kisi,
    )
    .toList();
bool _dikkat(Json p) => p['hal']?['durum'] == 'ARIZADA';

class Ekibim extends StatefulWidget {
  const Ekibim({super.key, required this.durum});
  final UygulamaDurumu durum;
  @override
  State<Ekibim> createState() => _EkibimState();
}

class _EkibimState extends State<Ekibim> {
  late final Timer _timer;
  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _timer.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: widget.durum,
    builder: (context, _) {
      final d = widget.durum,
          ekip = _ekip(widget.durum),
          onaylar = _onaylar(widget.durum);
      ekip.sort((a, b) {
        final n = (_dikkat(b) ? 1 : 0).compareTo(_dikkat(a) ? 1 : 0);
        return n != 0
            ? n
            : kisiAdi(d, a['kisi']).compareTo(kisiAdi(d, b['kisi']));
      });
      return Scaffold(
        appBar: AppBar(
          title: const Text('Ekibim'),
          actions: [KisiDegistirMenusu(durum: d)],
        ),
        body: SafeArea(
          child: RefreshIndicator(
            onRefresh: d.yenile,
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(20),
              children: [
                if (!d.baglanti) const Bant('Bağlantı Bekleniyor'),
                if (d.mesgul) const Bant('İşlem Sürüyor…'),
                if (d.mesaj != null) Bant(d.mesaj!),
                if (onaylar.isNotEmpty) ...[
                  Text(
                    'İş Onayları (${onaylar.length})',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 14),
                  for (final i in onaylar)
                    Card(
                      child: ListTile(
                        key: Key('is-onayi-${i['kimlik']}'),
                        contentPadding: const EdgeInsets.all(18),
                        title: Text(
                          isAdi(i),
                          style: const TextStyle(
                            fontSize: 19,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        subtitle: Text(
                          '${kisiAdi(d, (i['tamamlayan'] ?? i['kisi']) as String)}\n${isBaglami(d, i)}',
                        ),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () =>
                            altPencere(context, _IsOnayi(durum: d, is_: i)),
                      ),
                    ),
                  const SizedBox(height: 26),
                ],
                if (ekip.isEmpty)
                  const Padding(
                    padding: EdgeInsets.all(20),
                    child: Text('Ekipte Çalışan Yok'),
                  ),
                for (final p in ekip)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: Card(
                      margin: EdgeInsets.zero,
                      child: ListTile(
                        key: Key('ekip-${p['kisi']}'),
                        contentPadding: const EdgeInsets.all(18),
                        title: Text(
                          kisiAdi(d, p['kisi']),
                          style: const TextStyle(
                            fontSize: 21,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        subtitle: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const SizedBox(height: 10),
                            Text(
                              isAdi(p['is_'] as Json?),
                              style: const TextStyle(fontSize: 18),
                            ),
                            if (p['is_'] != null) ...[
                              const SizedBox(height: 6),
                              Text(isBaglami(d, Json.from(p['is_']))),
                            ],
                            const SizedBox(height: 12),
                            DurumEtiketi(p['hal']?['durum']),
                          ],
                        ),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => altPencere(
                          context,
                          _KisiPenceresi(durum: d, kisi: p['kisi']),
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ),
      );
    },
  );
}

class _KisiPenceresi extends StatefulWidget {
  const _KisiPenceresi({required this.durum, required this.kisi});
  final UygulamaDurumu durum;
  final String kisi;
  @override
  State<_KisiPenceresi> createState() => _KisiPenceresiState();
}

class _KisiPenceresiState extends State<_KisiPenceresi> {
  String? _secim, _hata;
  bool _yaziliyor = false;
  late final Timer _timer;
  UygulamaDurumu get d => widget.durum;
  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _timer.cancel();
    super.dispose();
  }

  String? _bekleyen;

  Future<void> _yaz(
    String kod,
    Json is_,
    Json girdiler, {
    Map<String, dynamic> surumler = const {},
  }) async {
    if (_yaziliyor) return;
    setState(() {
      _yaziliyor = true;
      _hata = null;
    });
    final basarili = await isle(context, () async {
      final sonuc = _bekleyen != null
          ? await d.yonetimSonucunuKontrolEt(_bekleyen!)
          : await d.yonetim(
              kod,
              hedefler: [_hedef(is_)],
              girdiler: girdiler,
              beklenenListeler: surumler,
              sonucuBekle: true,
            );
      if (sonuc['sonuc'] != 'BASARILI') {
        _bekleyen = const ['BEKLIYOR', 'BAGLANTI_YOK'].contains(sonuc['sonuc'])
            ? sonuc['olay_kimligi'] as String?
            : null;
        throw StateError(d.mesaj ?? 'İşlem Tamamlanamadı');
      }
      _bekleyen = null;
    });
    if (!mounted) return;
    if (basarili) {
      Navigator.pop(context);
    } else {
      setState(() => _yaziliyor = false);
    }
  }

  Future<void> _sec(Json is_, {required bool listede}) async {
    final mevcut = _liste(d, widget.kisi),
        degistir = _secim == 'degistir',
        devret = _secim == 'devret';
    if (!devret &&
        mevcut.isNotEmpty &&
        mevcut.first['onay_beklet'] == true &&
        mevcut.first['durum'] == 'ONAY_BEKLIYOR' &&
        degistir) {
      setState(() => _hata = 'İlk iş onay bekliyor. Önüne başka iş konamaz.');
      return;
    }
    if ((is_['kisi_sayisi'] as num? ?? 1) > 1) {
      setState(
        () => _hata =
            'Çok kişili işi webde Görev Yönetimi üzerinden birlikte atayın.',
      );
      return;
    }
    final onizlemeler = <String, List<Json>>{widget.kisi: mevcut};
    String? alici;
    bool yukleniyor = false;
    String? onizlemeHatasi;
    var istek = 0;
    final alicilar = d
        .satirlar('KISILER')
        .where(
          (p) =>
              p['yaka'] == 'MAVI' &&
              p['aktif'] != false &&
              p['kimlik'] != widget.kisi &&
              p['kimlik'] != d.kisi,
        )
        .toList();
    var sira = degistir ? 1 : mevcut.length + 1;
    final surumler = <String, dynamic>{
      widget.kisi: d.nesne('LISTE', hedef: widget.kisi)['surum'],
    };
    if (devret && alicilar.isEmpty) {
      setState(() => _hata = 'İşi devralabilecek çalışan bulunamadı.');
      return;
    }
    final evet = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, degis) {
          final kisi = alici ?? widget.kisi;
          final once = (onizlemeler[kisi] ?? <Json>[])
              .where((i) => i['kimlik'] != is_['kimlik'])
              .toList();
          sira = sira.clamp(1, once.length + 1);
          final sonra = [...once]..insert(sira - 1, is_);
          return AlertDialog(
            scrollable: true,
            title: Text(devret ? 'İşi Devret' : 'Yeni İş Sırası'),
            content: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  isAdi(is_),
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 16),
                if (devret)
                  DropdownButtonFormField<String>(
                    initialValue: alici,
                    isExpanded: true,
                    decoration: const InputDecoration(
                      labelText: 'Devralan Çalışan',
                    ),
                    items: alicilar
                        .map(
                          (p) => DropdownMenuItem<String>(
                            value: p['kimlik'],
                            child: Text(kisiAdi(d, p['kimlik'])),
                          ),
                        )
                        .toList(),
                    onChanged: (v) async {
                      final token = ++istek;
                      degis(() {
                        alici = v;
                        sira = 1;
                        yukleniyor = true;
                        onizlemeHatasi = null;
                      });
                      try {
                        final gorunen = await d.listeOnizlemesi(v!);
                        if (!ctx.mounted || token != istek) return;
                        surumler[v] = gorunen['surum'];
                        onizlemeler[v] = (gorunen['isler'] as List? ?? [])
                            .map((x) => Json.from(x as Map))
                            .toList();
                      } catch (_) {
                        if (!ctx.mounted || token != istek) return;
                        onizlemeHatasi =
                            'Çalışanın iş sırası alınamadı. Tekrar seçin.';
                      }
                      if (ctx.mounted && token == istek) {
                        degis(() => yukleniyor = false);
                      }
                    },
                  ),
                if (yukleniyor) const LinearProgressIndicator(),
                if (onizlemeHatasi != null) Text(onizlemeHatasi!),
                if (!yukleniyor &&
                    onizlemeHatasi == null &&
                    (!devret || alici != null)) ...[
                  const SizedBox(height: 16),
                  Text(kisiAdi(d, kisi)),
                  const SizedBox(height: 14),
                  DropdownButtonFormField<int>(
                    key: ValueKey('$kisi-${once.length}'),
                    initialValue: sira,
                    decoration: const InputDecoration(labelText: 'Yeni Sıra'),
                    items: List.generate(
                      once.length + 1,
                      (i) => DropdownMenuItem(
                        value: i + 1,
                        child: Text('${i + 1}. Sıra'),
                      ),
                    ),
                    onChanged: (v) => degis(() => sira = v ?? 1),
                  ),
                  const SizedBox(height: 18),
                  const Text(
                    'Onay Sonrasında',
                    style: TextStyle(fontWeight: FontWeight.w700),
                  ),
                  for (var n = 0; n < sonra.length; n++)
                    Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: Text(
                        '${n + 1}. ${isAdi(sonra[n])}',
                        style: TextStyle(
                          fontWeight: sonra[n]['kimlik'] == is_['kimlik']
                              ? FontWeight.w700
                              : FontWeight.normal,
                        ),
                      ),
                    ),
                  const SizedBox(height: 16),
                  const Text(
                    'İlk iş değişirse önceki çalışma aralığı kapanır. Önceki emek korunur; yeni işi çalışan başlatır.',
                  ),
                ],
              ],
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: const Text('Vazgeç'),
              ),
              FilledButton(
                onPressed:
                    yukleniyor ||
                        onizlemeHatasi != null ||
                        (devret && alici == null)
                    ? null
                    : () => Navigator.pop(ctx, true),
                child: const Text('Onayla'),
              ),
            ],
          );
        },
      ),
    );
    if (evet != true || !mounted) return;
    if (devret) {
      await _yaz('IS.DEVRETTIM', is_, {
        'kimden': widget.kisi,
        'kime': alici,
        'kime_sira': sira,
      }, surumler: surumler);
    } else {
      await _yaz(listede ? 'IS.SIRALADIM' : 'IS.ATADIM', is_, {
        'kisi': widget.kisi,
        listede ? 'yeni_sira' : 'sira': sira,
      }, surumler: surumler);
    }
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: d,
    builder: (context, _) {
      final p = _ekip(d).where((p) => p['kisi'] == widget.kisi).firstOrNull;
      if (p == null) {
        return const Padding(
          padding: EdgeInsets.all(24),
          child: Text('Bu kişi artık ekipte değil.'),
        );
      }
      final is_ = p['is_'] as Json?,
          liste = _liste(d, widget.kisi),
          durus =
              p['hal']?['durum'] == 'ARIZADA' &&
              p['hal']?['devam_izni'] != true;
      final acik = d.yonetimAcik && !_yaziliyor && _bekleyen == null;
      Widget dugme(String yazi, VoidCallback bas) => Padding(
        padding: const EdgeInsets.only(bottom: 14),
        child: Dugme(yazi, bas: acik ? bas : null),
      );
      Widget satir(Json i, bool listede) => ListTile(
        key: Key('${listede ? 'siradaki' : 'havuz'}-${i['kimlik']}'),
        contentPadding: const EdgeInsets.symmetric(vertical: 12),
        title: Text(
          isAdi(i),
          style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w600),
        ),
        subtitle: Text(isBaglami(d, i)),
        trailing: const Icon(Icons.chevron_right),
        enabled: acik,
        onTap: () => _sec(i, listede: listede),
      );
      return PopScope(
        canPop: !_yaziliyor,
        child: SizedBox(
          height: MediaQuery.sizeOf(context).height * .85,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 28),
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      kisiAdi(d, widget.kisi),
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                  ),
                  IconButton(
                    onPressed: _yaziliyor ? null : () => Navigator.pop(context),
                    tooltip: 'Kapat',
                    icon: const Icon(Icons.close),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              DurumEtiketi(p['hal']?['durum']),
              const SizedBox(height: 16),
              const Text(
                'Şu Anki İş',
                style: TextStyle(fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 8),
              Text(isAdi(is_), style: const TextStyle(fontSize: 20)),
              if (is_ != null) ...[
                const SizedBox(height: 8),
                Text(isBaglami(d, is_)),
              ],
              const SizedBox(height: 24),
              if (_yaziliyor || d.mesgul) const Bant('İşlem Sürüyor…'),
              if (!d.yonetimAcik && !d.mesgul)
                Bant('Bağlantı Bekleniyor', bas: d.yenile),
              if (_hata != null) Bant(_hata!),
              if (_bekleyen != null)
                Dugme(
                  'Sonucu Kontrol Et',
                  bas: _yaziliyor ? null : () => _yaz('', {}, {}),
                ),
              if (_secim == null) ...[
                if (durus && is_ != null) ...[
                  const Text(
                    'Duruştan Devam İzni',
                    style: TextStyle(fontSize: 19, fontWeight: FontWeight.w700),
                  ),
                  if (is_['acik_ariza'] != null)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      child: Text(
                        '${is_['acik_ariza'] is Map ? is_['acik_ariza']['not'] ?? 'Duruş Bildirildi' : 'Duruş Bildirildi'}',
                      ),
                    ),
                  dugme(
                    'Devam İzni Ver',
                    () => _yaz('IS.DEVAM_ONAYLADIM', is_, {}),
                  ),
                  const SizedBox(height: 12),
                ],
                dugme('Havuzdan İş Ekle', () => setState(() => _secim = 'ata')),
                dugme(
                  'İş Sırasını Değiştir',
                  () => setState(() => _secim = 'degistir'),
                ),
                if (liste.any((i) => i['durum'] != 'ONAY_BEKLIYOR'))
                  dugme('İşi Devret', () => setState(() => _secim = 'devret')),
                const SizedBox(height: 12),
                const Text(
                  'Sıralı İşler',
                  style: TextStyle(fontSize: 19, fontWeight: FontWeight.w700),
                ),
                if (liste.isEmpty)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 16),
                    child: Text('Henüz Atanmış İş Yok'),
                  ),
                for (var i = 0; i < liste.length; i++)
                  ListTile(
                    contentPadding: const EdgeInsets.symmetric(vertical: 8),
                    leading: CircleAvatar(child: Text('${i + 1}')),
                    title: Text(isAdi(liste[i])),
                    subtitle: Text(isBaglami(d, liste[i])),
                  ),
              ] else ...[
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        _secim == 'ata'
                            ? 'Havuzdan İş Ekle'
                            : _secim == 'devret'
                            ? 'Devredilecek İş'
                            : 'Öne Alınacak İş',
                        style: const TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    TextButton(
                      onPressed: _yaziliyor
                          ? null
                          : () => setState(() {
                              _secim = null;
                              _hata = null;
                            }),
                      child: const Text('Geri'),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                if (_secim != 'ata') ...[
                  const Text('Kişinin Sıralı İşleri'),
                  for (final i in liste.where(
                    (i) => _secim != 'devret' || i['durum'] != 'ONAY_BEKLIYOR',
                  ))
                    satir(i, true),
                  const SizedBox(height: 20),
                ],
                if (_secim != 'devret') ...[
                  const Text(
                    'Ekip İş Havuzu',
                    style: TextStyle(fontWeight: FontWeight.w700),
                  ),
                  if (d.satirlar('HAVUZ', hedef: d.birim).isEmpty)
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 16),
                      child: Text('Havuzda Bekleyen İş Yok'),
                    ),
                  for (final i
                      in d
                          .satirlar('HAVUZ', hedef: d.birim)
                          .where((i) => i['ana_is'] == null))
                    satir(i, false),
                ],
              ],
            ],
          ),
        ),
      );
    },
  );
}

class _IsOnayi extends StatefulWidget {
  const _IsOnayi({required this.durum, required this.is_});
  final UygulamaDurumu durum;
  final Json is_;
  @override
  State<_IsOnayi> createState() => _IsOnayiState();
}

class _IsOnayiState extends State<_IsOnayi> {
  final _not = TextEditingController();
  bool _ret = false, _busy = false;
  String? _bekleyen;
  String? _hata;
  @override
  void dispose() {
    _not.dispose();
    super.dispose();
  }

  Future<void> _gonder(bool ret) async {
    if (_busy) return;
    if (ret && _not.text.trim().isEmpty) {
      setState(() => _hata = 'Düzeltme gerekçesini yazın.');
      return;
    }
    setState(() {
      _busy = true;
      _hata = null;
    });
    final ok = await isle(context, () async {
      final c = _bekleyen != null
          ? await widget.durum.yonetimSonucunuKontrolEt(_bekleyen!)
          : await widget.durum.yonetim(
              ret ? 'IS.REDDETTIM' : 'IS.ONAYLADIM',
              hedefler: [_hedef(widget.is_)],
              girdiler: ret ? {'not': _not.text.trim()} : {},
              sonucuBekle: true,
            );
      if (c['sonuc'] != 'BASARILI') {
        _bekleyen = const ['BEKLIYOR', 'BAGLANTI_YOK'].contains(c['sonuc'])
            ? c['olay_kimligi'] as String?
            : null;
        throw StateError(widget.durum.mesaj ?? 'İşlem Tamamlanamadı');
      }
      _bekleyen = null;
    });
    if (!mounted) return;
    if (ok) {
      Navigator.pop(context);
    } else {
      setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: widget.durum,
    builder: (context, _) {
      final d = widget.durum,
          acik = d.yonetimAcik && !_busy && _bekleyen == null;
      return PopScope(
        canPop: !_busy,
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 28),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      'İş Teslim Onayı',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                  ),
                  IconButton(
                    onPressed: _busy ? null : () => Navigator.pop(context),
                    tooltip: 'Kapat',
                    icon: const Icon(Icons.close),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              Text(
                isAdi(widget.is_),
                style: const TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 10),
              Text(
                kisiAdi(
                  d,
                  (widget.is_['tamamlayan'] ?? widget.is_['kisi']) as String,
                ),
              ),
              Text(isBaglami(d, widget.is_)),
              const SizedBox(height: 20),
              Text(
                widget.is_['onay_beklet'] == true
                    ? 'Çalışan bu işin onayını bekliyor.'
                    : 'Çalışan sıradaki uygun işine geçebilir.',
              ),
              const SizedBox(height: 24),
              if (_busy) const Bant('İşlem Sürüyor…'),
              if (_bekleyen != null)
                Dugme(
                  'Sonucu Kontrol Et',
                  bas: _busy ? null : () => _gonder(_ret),
                ),
              if (_ret) ...[
                TextField(
                  controller: _not,
                  enabled: !_busy && _bekleyen == null,
                  maxLines: 3,
                  decoration: InputDecoration(
                    labelText: 'Düzeltme Gerekçesi',
                    errorText: _hata,
                  ),
                ),
                const SizedBox(height: 20),
                Dugme(
                  'Düzeltmeye Gönder',
                  renk: 'kirmizi',
                  bas: acik ? () => _gonder(true) : null,
                ),
                const SizedBox(height: 12),
                TextButton(
                  onPressed: _busy ? null : () => setState(() => _ret = false),
                  child: const Text('Geri'),
                ),
              ] else ...[
                Dugme(
                  'İşi Onayla',
                  renk: 'yesil',
                  bas: acik ? () => _gonder(false) : null,
                ),
                const SizedBox(height: 14),
                Dugme(
                  'Düzeltme İste',
                  renk: 'sade',
                  bas: acik ? () => setState(() => _ret = true) : null,
                ),
              ],
            ],
          ),
        ),
      );
    },
  );
}
