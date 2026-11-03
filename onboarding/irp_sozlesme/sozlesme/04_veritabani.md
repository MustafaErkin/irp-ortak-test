# 04 · Veritabanı: modülün kendi tabloları

## 1. Yer

- **Şema:** Modülün verisi çekirdekle aynı Supabase projesinde, **kendi şemasında** durur: `mod_<kod küçük harf>`, ör. `mod_kal` (karar 129).
- **Kurulumun açtıkları:** Şemayı ve modülün veritabanı rollerini kurulum açar. Modülün göçleri yalnızca şemanın içini doldurur.
- **Göç dosyaları:** `veritabani/NNN_ad.sql`, numara sırasıyla koşar. Örnek: `ornekler/kunyeler/KAL/veritabani/001_kalite.sql`, `ornekler/M3_mini/veritabani/001_siparisler.sql`.
- **Çekirdeğin baştan kurulması** modülün şemasına dokunmaz.

## 2. Kurallar (göç denetimi G01–G09)

| No | Kural |
|---|---|
| G01 | Oluşturulan, değiştirilen her nesne `mod_<kod>.` ile adlandırılır: `CREATE TABLE mod_kal.olcumler` |
| G02 | Çekirdeğin şemalarına dokunulmaz. Şu şemalar buna girer: `public`, `motor`, `kapi`, `test`, `auth`, `storage`, `realtime`, `cron`… Başka modülün şemasına da dokunulmaz.<br>Çağrılabilen fonksiyonlar yalnızca şunlar: `public.modul_bildirimi_birak/kaldir`, `public.simdi`, `public.servis_oku`, `auth.uid`, `auth.jwt`, `cron.schedule/unschedule`.<br>Dinamik SQL (`EXECUTE`) uyarı alır |
| G03 | Rol, şema, eklenti açılmaz; `GRANT` ve `REVOKE` yazılmaz. Haklar kurulumda künyeden verilir |
| G04 | `SECURITY DEFINER` fonksiyonu `SET search_path = mod_<kod>, pg_temp` ile sabitlenir |
| G05 | Başkasının nesnesi silinmez |
| G06 | Çekirdeğin tablosuna tetikleyici konmaz |
| G07 | Zamanlanmış işin adı `mod_<kod>_` ile başlar: `cron.schedule('mod_kal_sabah', …)` |
| G08 | Çekirdeğin tablosuna yabancı anahtar konmaz; kimlik değer olarak taşınır |
| G09 | `LISTEN`, `NOTIFY`, rol değiştirme, tetikleyiciyi susturma yok |

Denetleyici künyeyle birlikte göçleri de tarar (`03_kunye.md`).

## 3. Olay kimliğinin sırası

Arka yüz olay yazıyorsa (`olay_yolu: ARKA_YUZ`) kişi ve gün başına sırayı kendi tablosunda, **tek işlemle** artırır. Böylece modülün birden çok kopyası çalışsa da aynı kimlik iki kez verilmez.

```sql
CREATE TABLE mod_<kod>.olay_sayaci (kisi text, gun text, son integer NOT NULL DEFAULT 0, PRIMARY KEY (kisi, gun));

CREATE FUNCTION mod_<kod>.olay_sirasi(p_kisi text, p_gun text) RETURNS integer
LANGUAGE sql SET search_path = mod_<kod>, pg_temp AS $$
  INSERT INTO mod_<kod>.olay_sayaci AS s (kisi, gun, son) VALUES (p_kisi, p_gun, 1)
  ON CONFLICT (kisi, gun) DO UPDATE SET son = s.son + 1 RETURNING son; $$;
```

**Python'da** bunu çağıran bir nesneyi `Cekirdek.ac(..., sayac=...)` ile verirsin:

```python
class TabloSayac:
    def __init__(self, baglanti): self.b = baglanti
    def sonraki(self, kisi, gun):
        return self.b.execute('SELECT mod_kal.olay_sirasi(%s, %s)', (kisi, gun)).fetchone()[0]
```

**Sayaç kaybolursa** (yedekten dönüş gibi) çekirdek `CAKISMA` der; katman sırayı ilerletip yeniden dener.

## 4. İpuçları

- **Tarih ve saat:** `timestamptz`. Çekirdeğin saati `+03:00`'tür.
- **Çekirdeğin kimlikleri:** `text`. Örnekler: `K006-2610280001-P` (nesne, olay), `2614` (proje), `K017` (kişi), `CNC-02` (tezgâh).
- **Modülün kendi kayıtlarının kimliği** modülündür. Çekirdeğe bildirimde `kayit.modul_kaydi` alanında metin olarak geçebilir.
