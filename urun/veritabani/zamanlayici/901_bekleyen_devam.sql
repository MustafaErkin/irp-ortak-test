-- 158 sonrasında, 900'deki saat işine ek olarak kurulur.
-- pg_cron >= 1.6: aynı iş eşzamanlı çalışmaz. İçerideki try-lock, saat işi ve
-- kullanıcı işlemleriyle de ortak kilidi korur. Boşta motor hesabı yapılmaz.
SELECT cron.schedule('irp-motor-bekleyen','1 second','SELECT motor.bekleyen_isi()');
-- Saniyelik çalışmanın işletim izleri sınırsız büyümesin. Yalnız bu yeni işin
-- bitmiş, 24 saatten eski cron izleri silinir; kaynak olaylara dokunulmaz.
SELECT cron.schedule('irp-motor-log-temizle','17 * * * *',
 $$DELETE FROM cron.job_run_details WHERE jobid IN
   (SELECT jobid FROM cron.job WHERE jobname='irp-motor-bekleyen')
   AND end_time < now()-interval '24 hours'$$);
