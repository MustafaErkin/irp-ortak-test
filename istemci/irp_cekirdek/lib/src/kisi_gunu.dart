import 'veri.dart';

// Kaynak: referans/cevap_anahtari/model/irp/kisi_gunu.py:7 (CALISAN).
const calisan = {
  'MESAI.GIRDIM',
  'MESAI.CIKTIM',
  'IS.BASLADIM',
  'IS.MOLA_VERDIM',
  'IS.ARIZA_BILDIRDIM',
  'IS.DEVAM_ETTIM',
  'IS.TAMAMLADIM',
};

// Kaynak: referans/cevap_anahtari/model/irp/kisi_gunu.py:11 (bos_hal).
Sozluk bosHal() => {
  'durum': 'MESAI_DISI',
  'kova': null,
  'acik_is': null,
  'aralik_is': null,
  'neden': null,
  'onceki_kova': 'CALISMA',
  'devam_izni': false,
  'mola_onceki': null,
  'baslangic': null,
  'acan_olay': null,
  'acan_kural': null,
  'son_olay_ani': null,
};

// Kaynak: referans/cevap_anahtari/model/irp/kisi_gunu.py:15 (kapi).
bool kapi(
  Sozluk d,
  String kod,
  Sozluk? is_,
  String? bas, {
  bool sabit = false,
}) {
  if (sabit && calisan.contains(kod)) return false;
  final durum = d['durum'];
  if (kod == 'MESAI.GIRDIM') return durum == 'MESAI_DISI';
  if (kod == 'MESAI.CIKTIM') return durum != 'MESAI_DISI';
  if (is_ == null || is_.isEmpty) return false;
  final ayni = d['acik_is'] == is_['kimlik'];
  if (kod == 'IS.BASLADIM') {
    return durum == 'CALISMIYOR' &&
        bas == is_['kimlik'] &&
        is_['tur'] == 'SURELI' &&
        const {'SIRADA', 'YARIM'}.contains(is_['durum']) &&
        !dolu(is_['kilitli']);
  }
  if (kod == 'IS.MOLA_VERDIM') return durum == 'CALISIYOR' && ayni;
  if (kod == 'IS.ARIZA_BILDIRDIM') {
    return (durum == 'CALISIYOR' && ayni) ||
        (is_['tur'] == 'ANLIK' &&
            bas == is_['kimlik'] &&
            durum != 'MESAI_DISI');
  }
  if (kod == 'IS.DEVAM_ETTIM') {
    if (is_['durum'] == 'BITTI') return false;
    return (ayni &&
            (const {'MOLADA', 'DEVAM_BEKLIYOR'}.contains(durum) ||
                (durum == 'ARIZADA' && dolu(d['devam_izni'])))) ||
        (durum == 'CALISMIYOR' &&
            bas == is_['kimlik'] &&
            is_['durum'] == 'REDDEDILDI');
  }
  if (kod == 'IS.TAMAMLADIM') {
    return (is_['tur'] == 'SURELI' &&
            ayni &&
            const {'CALISIYOR', 'DEVAM_BEKLIYOR'}.contains(durum)) ||
        (is_['tur'] == 'ANLIK' &&
            durum == 'CALISMIYOR' &&
            bas == is_['kimlik'] &&
            is_['durum'] == 'SIRADA' &&
            !dolu(is_['kilitli']));
  }
  return true;
}

// Kaynak: referans/cevap_anahtari/model/irp/kisi_gunu.py:35 (gecis).
(Sozluk, List<String>) gecis(
  Sozluk hal,
  String kod, {
  Sozluk? is_,
  Sozluk? basIs,
  String? neden,
}) {
  Sozluk d = kopyala(hal);
  final yan = <String>[];
  // Kaynak: referans/cevap_anahtari/model/irp/kisi_gunu.py:39 (ac).
  void ac(String durum, String? kova, [String? isKimligi]) {
    d.addAll({
      'durum': durum,
      'kova': kova,
      'aralik_is': isKimligi,
      'neden': neden,
    });
  }

  // Kaynak: referans/cevap_anahtari/model/irp/kisi_gunu.py:41 (bosalt).
  void bosalt() {
    d['acik_is'] = null;
    if (dolu(basIs) &&
        dolu(al(basIs!, 'kilitli', basIs['durum'] == 'ON_IS_BEKLIYOR'))) {
      ac('ON_IS_BEKLIYOR', 'BEKLEME_ON_IS', basIs['kimlik']);
      yan.add('R04');
    } else {
      ac('CALISMIYOR', 'TANIMSIZ');
    }
  }

  if (kod == 'MESAI.GIRDIM') {
    bosalt();
    if (dolu(basIs) && basIs!['durum'] == 'ONAY_BEKLIYOR') {
      ac('ONAY_BEKLIYOR', 'BEKLEME_ONAY', basIs['kimlik']);
    } else if (dolu(basIs) && dolu(basIs!['acik_ariza'])) {
      d['acik_is'] = basIs['kimlik'];
      d['devam_izni'] = al(basIs, 'devam_izni', false);
      d['onceki_kova'] = al(basIs, 'calisma_kovasi', 'CALISMA');
      ac('ARIZADA', 'BEKLEME_ARIZA', basIs['kimlik']);
      d['neden'] = basIs['acik_ariza'];
    }
  } else if (kod == 'MESAI.CIKTIM' || kod == 'PAYDOS') {
    ac('MESAI_DISI', null);
    d['acik_is'] = null;
  } else if (kod == 'MOLA_BASI') {
    if (d['durum'] != 'MESAI_DISI') {
      d['mola_onceki'] = kopyala(hal);
      ac('SABIT_MOLADA', 'SABIT_MOLA');
    }
  } else if (kod == 'MOLA_SONU') {
    if (d['durum'] == 'SABIT_MOLADA') {
      final once = d['mola_onceki'] as Sozluk;
      d = kopyala(once);
      if (const {
        'CALISIYOR',
        'MOLADA',
        'DEVAM_BEKLIYOR',
      }.contains(once['durum'])) {
        ac(dolu(once['acik_is']) ? 'DEVAM_BEKLIYOR' : 'CALISMIYOR', 'TANIMSIZ');
      }
      d['mola_onceki'] = null;
    }
  } else if (kod == 'IS.BASLADIM') {
    d['acik_is'] = is_!['kimlik'];
    d['onceki_kova'] = 'CALISMA';
    ac('CALISIYOR', 'CALISMA', is_['kimlik']);
  } else if (kod == 'IS.MOLA_VERDIM') {
    ac('MOLADA', 'MOLA');
  } else if (kod == 'IS.ARIZA_BILDIRDIM') {
    d['acik_is'] = is_!['kimlik'];
    d['devam_izni'] = false;
    ac('ARIZADA', 'BEKLEME_ARIZA', is_['kimlik']);
    yan.add('R07');
  } else if (kod == 'IS.DEVAM_ONAYLADIM') {
    d['devam_izni'] = true;
  } else if (kod == 'IS.DEVAM_ETTIM') {
    d['acik_is'] = is_!['kimlik'];
    if (is_['durum'] == 'REDDEDILDI') d['onceki_kova'] = 'YENIDEN_ISLEME';
    if (is_['tur'] == 'ANLIK') {
      ac('CALISMIYOR', 'TANIMSIZ');
      d['acik_is'] = null;
    } else {
      ac('CALISIYOR', d['onceki_kova'], is_['kimlik']);
    }
  } else if (kod == 'IS.TAMAMLADIM') {
    if (dolu(is_!['onay_gerekli'])) {
      d['acik_is'] = null;
      ac('ONAY_BEKLIYOR', 'BEKLEME_ONAY', is_['kimlik']);
      yan.add('R05');
    } else if (is_['tur'] != 'ANLIK') {
      bosalt();
    }
  } else if (kod == 'IS.ONAYLADIM') {
    bosalt();
  } else if (kod == 'IS.REDDETTIM') {
    d['acik_is'] = null;
    ac('CALISMIYOR', 'GECIS');
  } else if (kod == 'LISTE_DEGISTI') {
    if (d['durum'] != 'MESAI_DISI' && !dolu(basIs)) {
      d['acik_is'] = null;
      ac('CALISMIYOR', 'TANIMSIZ');
      yan.add('R08');
    } else if (const {
          'CALISIYOR',
          'MOLADA',
          'ARIZADA',
          'DEVAM_BEKLIYOR',
          'ON_IS_BEKLIYOR',
        }.contains(d['durum']) &&
        (!dolu(basIs) || basIs!['kimlik'] != d['acik_is'])) {
      d['acik_is'] = null;
      if (dolu(basIs) && dolu(basIs!['kilitli'])) {
        ac('ON_IS_BEKLIYOR', 'BEKLEME_ON_IS', basIs['kimlik']);
        yan.add('R04');
      } else {
        ac('CALISMIYOR', 'GECIS');
      }
      yan.add('R01');
    } else if (d['durum'] == 'CALISMIYOR' &&
        dolu(basIs) &&
        dolu(basIs!['kilitli'])) {
      ac('ON_IS_BEKLIYOR', 'BEKLEME_ON_IS', basIs['kimlik']);
      yan.add('R04');
    }
  } else if (kod == 'ON_IS_BITTI' && d['durum'] == 'ON_IS_BEKLIYOR') {
    d['durum'] = 'CALISMIYOR';
  }
  return (d, yan);
}
