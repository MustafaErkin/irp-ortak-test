import {displayText} from './presentation.js';

// Çekirdek bildirimlerinde kimlik alanı yoktur. Dış kimlik üç parçadan oluşur
// (T9 / k9.bildirim_bul); modül bildirimi kendi kimliğini taşır.
export function notificationId(row){
 return row.kimlik??(row.doguran_olay&&row.kural&&row.alici?[row.doguran_olay,row.kural,row.alici].join('/'):null);
}

const rules={
 R04:['Ön İş Bekleniyor','Önceki iş tamamlanmadığı için çalışma bekliyor.'],
 R05:['Teslim Onayı Bekleniyor','Çalışma teslim edildi. Onayınızı bekliyor.'],
 R07:['Duruş Bildirildi','Çalışan duruş bildirdi. Devam onayını değerlendirin.'],
 R08:['İş Listesi Tamamlandı','Çalışanın listesinde bekleyen iş kalmadı.'],
 R10:['İşlem İncelenmeli','Bir çalışma bildirimi inceleme bekliyor.'],
 R28:['Yeni Çalışan','Ekibe yeni bir çalışan eklendi.'],
 R29:['Çalışan Bilgisi Değişti','Çalışanın ekip veya istihdam bilgisi güncellendi.'],
 R30:['Yeni İş Ataması','Ekibinizdeki çalışana yeni iş atandı.'],
 R31:['Mesai Dışı Çalışma','Mesai saatleri dışında çalışma bildirildi.'],
 R32:['Gün Özeti Bekleniyor','Çalışanın mesai sonu özeti henüz gönderilmedi.'],
 R33:['Gün Onayı Bekleniyor','Çalışanın gün özeti değerlendirme bekliyor.'],
 R34:['Çalışma Takvimi Değişti','Çalışma takvimi güncellendi.'],
 R35:['İzin Talebi','Yeni izin talebi değerlendirmenizi bekliyor.'],
 R36:['İzin Talebi Sonuçlandı','İzin talebine ilişkin karar verildi.'],
 R37:['İzin Ve İş Planı Çakışıyor','Planlanan iş, çalışanın izin dönemiyle çakışıyor.'],
 R38:['Sorumluluk Değerlendirmesi','Sorumluluk dağılımı değerlendirmenizi bekliyor.'],
 R39:['Sorumluluk İtirazı','Sorumluluk dağılımına itiraz edildi.'],
 R40:['Gecikmeli Teslim','Görev, planlanan teslim zamanından sonra teslim edildi.'],
 R41:['İzin İçin İK Onayı','İzin talebi insan kaynakları onayını bekliyor.'],
 R42:['Proje Erişimi Değişti','Proje erişim yetkiniz güncellendi.'],
 R43:['Belge Sürümü Güncellendi','Belgenin sürüm veya onay bilgisi güncellendi.']
};

export function notificationContent(row,name=id=>displayText(id),refs=[]){
 const core=!row.kaynak||row.kaynak==='CEKIRDEK';
 if(row.is_akisi&&row.baslik)return {title:displayText(row.baslik),text:displayText(row.metin)};
 if(!core)return {title:displayText(row.baslik??'İş Güncellemesi'),text:displayText(row.metin||'İlgili işte yeni bir gelişme var.')};
 const rule=rules[row.kural]??['İş Güncellemesi','İlgili çalışmada yeni bir gelişme var.'];
 const [title,description]=rule,related=row.metin?name(row.metin):'';
 const tasks=refs.filter(r=>r.doguran_olay===row.doguran_olay&&r.tur!=='ONAY'&&(!row.metin||r.kisi===row.metin));
 const jobs=[...new Set(tasks.map(r=>displayText(r.ad??r.islem??r.is_tanimi??'')))].filter(Boolean);
 return {title,text:[related&&related!=='—'?related+' — '+description:description,jobs.join(' · ')].filter(Boolean).join(' ')};
}
