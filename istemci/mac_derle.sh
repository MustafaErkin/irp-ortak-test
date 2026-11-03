#!/bin/bash
# Mac'te derleme ve dağıtım (29 Ekim, Mustafa: Codex kodu yazar ve gönderir; derleme, telefona kurma ve
# bulut işleri gösteri Mac'inde). Bulut anahtarı yalnız Mac'te: web için ~/irp_gosteri/web/ayar.json,
# APK için derleme anında ~/irp_gizli/supabase.env'den (geçici dosya, sonra silinir).
#
#   bash istemci/mac_derle.sh web      # web'i derler, ~/irp_gosteri/web'e koyar (ayar.json korunur)
#   bash istemci/mac_derle.sh apk      # gerçek buluta bağlı APK: ~/irp_gosteri/irp_canli.apk
#   bash istemci/mac_derle.sh ayar     # web'in ayar.json'u: bulut adresi, anon anahtarı, gösteri kişileri
#   bash istemci/mac_derle.sh kur      # APK'yı USB ile bağlı telefona kurar (adb)
set -euo pipefail
cd "$(dirname "$0")/uygulama"
FLUTTER=~/development/flutter/bin/flutter
export ANDROID_HOME=~/Library/Android/sdk
export JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-17.jdk/Contents/Home
HEDEF=~/irp_gosteri
anahtar_tara() {  # derleme çıktısında anahtar benzeri içerik olmamalı (web anahtarsız derlenir)
  if grep -rIlE 'sb_(secret|publishable)_[A-Za-z0-9_-]{16,}|eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.' "$1" >/dev/null 2>&1; then
    echo "HATA: derlemede anahtar benzeri içerik var; dağıtılmadı." >&2; exit 1
  fi
}
case "${1:-}" in
  web)
    # Yalnız ayrı yerel veritabanlarında yedek/geri dönüş sınaması; dağıtım yok.
    if [[ " $* " == *" --gosteri-yedek-sina "* ]]; then
      /Users/mustafaerkindal/.irp_venv/bin/python -I -B ../../modul_platformu/bagimliliklar.py
      /Users/mustafaerkindal/.irp_venv/bin/python -I -B ../../urun/veri/gosteri_yedegi_sina.py
      exit 0
    fi
    # Entegrasyon geliştirme sınaması; çalışan gösteri dağıtımını değiştirmez.
    if [[ " $* " == *" --moduller-sina "* ]]; then
      /Users/mustafaerkindal/.irp_venv/bin/python -I -B ../../modul_platformu/bagimliliklar.py
      /Users/mustafaerkindal/.irp_venv/bin/python -I -B ../../modul_platformu/butunlesik_sina.py "$@"
      exit 0
    fi
    # Paylaşım paketini ayrı tarayıcıda denetler; web derleme/dağıtımı ve canlı bağlantı yok.
    if [[ " $* " == *" --gelistirici-paketi-sina "* ]]; then
      /Users/mustafaerkindal/.irp_venv/bin/python -I -B ../../modul_kiti/gelistirici_paketi_sina.py --tarayici
      exit 0
    fi
    if [[ " $* " == *" --modul-"* ]]; then
      /Users/mustafaerkindal/.irp_venv/bin/python -I -B ../../modul_platformu/bagimliliklar.py
    fi
    /Users/mustafaerkindal/.irp_venv/bin/python -I -B ../web/derle.py
    if [[ " $* " == *" --modul-paket-sina "* ]]; then
      /Users/mustafaerkindal/.irp_venv/bin/python -I -B ../../modul_kiti/katalog_uret.py --denetle
      /Users/mustafaerkindal/.irp_venv/bin/python -I -B -m unittest discover -s ../../test/modul_sozlesmesi
    fi
    if [[ " $* " == *" --modul-sina "* ]]; then
      if [[ " $* " == *" --tam-sinama "* ]]; then
        /Users/mustafaerkindal/.irp_venv/bin/python -I -B ../../modul_platformu/sina.py --tarayici --cekirdek
      else
        /Users/mustafaerkindal/.irp_venv/bin/python -I -B ../../modul_platformu/sina.py --tarayici
      fi
    fi
    if [[ " $* " == *" --senaryo1-sina "* ]]; then
      /Users/mustafaerkindal/.irp_venv/bin/python -I -B ../web/test/senaryo1_sina.py
      /Users/mustafaerkindal/.irp_venv/bin/python -I -B ../web/test/tarayici.py --ornek
    elif [[ " $* " == *" --tam-sinama "* ]]; then
      /Users/mustafaerkindal/.irp_venv/bin/python -I -B ../web/test/tarayici.py --tam
    else
      /Users/mustafaerkindal/.irp_venv/bin/python -I -B ../web/test/tarayici.py --ornek
    fi
    if [[ " $* " == *" --safari-sina "* ]]; then
      /Users/mustafaerkindal/.irp_venv/bin/python -I -B ../web/test/safari_sina.py
    fi
    /Users/mustafaerkindal/.irp_venv/bin/python -I -B ../web/test/hesap_sina.py
    node --test ../web/test/*.test.js
    anahtar_tara ../web/build
    mkdir -p "$HEDEF/web"
    rsync -a --delete --exclude ayar.json ../web/build/ "$HEDEF/web/"
    cp ../web/sunucu.py "$HEDEF/sunucu.py"
    cp ../web/baslat.command "$HEDEF/baslat.command"
    cp ../web/olaylar.command "$HEDEF/olaylar.command"
    rsync -a --delete --exclude __pycache__ ../../modul_platformu/ "$HEDEF/modul_platformu/"
    rsync -a --delete --exclude __pycache__ ../../moduller/ "$HEDEF/moduller/"
    mkdir -p "$HEDEF/onboarding"
    rsync -a --delete --exclude __pycache__ ../../onboarding/irp_sozlesme/ "$HEDEF/onboarding/irp_sozlesme/"
    if [[ -d ../../.runtime/python ]]; then
      mkdir -p "$HEDEF/.runtime"
      rsync -a --delete --exclude __pycache__ ../../.runtime/python/ "$HEDEF/.runtime/python/"
    fi
    chmod +x "$HEDEF/baslat.command" "$HEDEF/olaylar.command"
    if [[ " $* " == *" --bulut-guncelle "* ]]; then
      (set -a; . ~/irp_gizli/supabase.env; set +a
       /Users/mustafaerkindal/.irp_venv/bin/python -I -B ../web/yayinla.py --bulut)
    fi
    if [[ " $* " == *" --modul-kur "* ]]; then
      (set -a; . ~/irp_gizli/supabase.env; set +a
       /Users/mustafaerkindal/.irp_venv/bin/python -I -B ../../modul_platformu/isletim.py)
    fi
    if [[ " $* " == *" --senaryo1-hazirla "* ]]; then
      (set -a; . ~/irp_gizli/supabase.env; set +a
       /Users/mustafaerkindal/.irp_venv/bin/python -I -B ../../urun/veri/senaryo1_hazirla.py --temiz-baslat)
      bash ../mac_derle.sh ayar
    fi
    if [[ " $* " == *" --calistir "* ]]; then
      /Users/mustafaerkindal/.irp_venv/bin/python -I -B ../web/yayinla.py --calistir
    fi
    if [[ " $* " == *" --canli-sina "* ]]; then
      if [[ " $* " == *" --modul-kur "* || " $* " == *" --modul-canli-sina "* ]]; then
        /Users/mustafaerkindal/.irp_venv/bin/python -I -B ../web/test/canli_sina.py --moduller
      else
        /Users/mustafaerkindal/.irp_venv/bin/python -I -B ../web/test/canli_sina.py
      fi
    fi
    echo "Web hazır: $HEDEF/web (ayar.json korundu). Başlatmak için $HEDEF/baslat.command"
    ;;
  apk)
    set -a; . ~/irp_gizli/supabase.env; set +a
    GECICI=$(mktemp /private/tmp/irp-apk-ayar.XXXXXX)
    trap 'rm -f "$GECICI"' EXIT
    /opt/homebrew/bin/python3.13 -I - "$GECICI" <<'PY'
import json, os, pathlib, sys
yol = pathlib.Path(sys.argv[1])
d = {'BULUT': 'SUPABASE', 'SUPABASE_URL': os.environ['IRP_SB_TEST_URL'], 'SUPABASE_ANON': os.environ['IRP_SB_TEST_ANON']}
g = pathlib.Path.home() / 'irp_gizli' / 'gosteri_kisileri.json'
if g.exists():  # gösteri kişileri: MVP telefonunda yalnız atölye ve saha çalışanları
    phone = [k for k in json.loads(g.read_text('utf-8')) if k['yer'] == 'telefon']
    phone.sort(key=lambda k: ['K017','K009','K031'].index(k['kod']))
    d['GOSTERI_KISILERI'] = json.dumps(phone, ensure_ascii=False)
    # Mustafa: test/MVP boyunca mesai saatini beklemeden telefon kullanılabilsin.
    # Takvim ve motor saati aynı kalır; normal derlemede varsayılan kapalıdır.
    d['MVP_MESAI_SERBEST'] = bool(phone)
    # 239: SQL162 geri alındı. Yeniden onaylı kurulum olmadan bu yolu açma.
    d['MVP_TELEFON_CALISAN'] = False
state = pathlib.Path.home() / 'irp_gizli' / 'senaryo1_durum.json'
if state.exists():
    d['GOSTERI_SENARYOSU'] = json.loads(state.read_text())['senaryo']
fd = os.open(yol, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False)
PY
    $FLUTTER build apk --release --dart-define-from-file="$GECICI"
    cp build/app/outputs/flutter-apk/app-release.apk "$HEDEF/irp_canli.apk"
    ls -lh "$HEDEF/irp_canli.apk"
    ;;
  ayar)
    # Web'in bulut ayarı ve gösteri kişileri (web ve ikisi olanlar); yalnız Mac'te, depo dışında.
    set -a; . ~/irp_gizli/supabase.env; set +a
    /opt/homebrew/bin/python3.13 -I - "$HEDEF/web/ayar.json" <<'PY'
import json, os, pathlib, sys
yol = pathlib.Path(sys.argv[1])
d = {'bulut': 'SUPABASE', 'supabase_url': os.environ['IRP_SB_TEST_URL'].rstrip('/'), 'supabase_anon': os.environ['IRP_SB_TEST_ANON']}
g = pathlib.Path.home() / 'irp_gizli' / 'gosteri_kisileri.json'
if g.exists():
    d['gosteri_kisileri'] = [k for k in json.loads(g.read_text('utf-8')) if k['yer'] in ('web', 'ikisi')]
state = pathlib.Path.home() / 'irp_gizli' / 'senaryo1_durum.json'
if state.exists():
    d['senaryo'] = json.loads(state.read_text())['senaryo']
fd = os.open(yol, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False)
    f.write('\n')
print('Web ayarı yazıldı:', yol, '| gösteri kişisi:', len(d.get('gosteri_kisileri', [])))
PY
    ;;
  kur)
    adb devices | sed 1d | grep -q 'device$' || { echo "Telefon görünmüyor: USB hata ayıklama açık ve izin verilmiş olmalı." >&2; exit 1; }
    APK="$HEDEF/irp_canli.apk"
    if [[ -f build/app/outputs/flutter-apk/app-release.apk && build/app/outputs/flutter-apk/app-release.apk -nt "$APK" ]]; then
      APK=build/app/outputs/flutter-apk/app-release.apk
    fi
    adb install -r "$APK"
    ;;
  *) echo "Kullanım: bash istemci/mac_derle.sh web|ayar|apk|kur" >&2; exit 2 ;;
esac
