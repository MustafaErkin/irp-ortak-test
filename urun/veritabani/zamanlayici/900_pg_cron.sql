-- Yalnız Supabase yöneticisi, pg_cron hazır olduktan sonra uygular.
-- Yerel kurulum ve urun/kur.py bu alt dizini çalıştırmaz. Eklenti burada kurulmaz.
-- Bir çağrı bir bütçe parçasıdır; bekleyen iş bitince sonraki dakika saati ilerletir.
SELECT cron.schedule('irp-motor-saat','* * * * *','SELECT motor.saat_isi()');
