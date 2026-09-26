/* Presentation-only bilingual layer. Clinical decision values remain unchanged. */
(() => {
  const stored = (localStorage.getItem("cerai-language") || "en").toLowerCase();
  const locale = stored === "tr" ? "tr" : "en";
  const TR = {
    "Corneal Ectasia Risk Assessment Intelligence":"Kornea Ektazi Risk Değerlendirme Zekâsı",
    "ASSESSMENT":"DEĞERLENDİRMESİ","definition":"Tanım","Applicability":"Uygulanabilirlik",
    "Not applicable to selected non-LASIK procedure":"Seçilen LASIK dışı işlem için uygulanamaz",
    "Points / disposition":"Puan / karar","Displayed component; not recalculated":"Gösterilen bileşen; yeniden hesaplanmadı",
    "Information / QC only":"Yalnızca bilgi / kalite kontrolü",
    "HWTW (mm; 4 Maps Refractive lower-left labeled box)":"HWTW (mm; 4 Maps Refractive sol alt etiketli kutu)",
    "applicable":"Uygulanabilir","assessment_gate":"Değerlendirme sonucu",
    "blade_recommendations":"Bıçak önerileri","primary_hinge":"Birincil menteşe",
    "steep_meridian_axis_deg":"Dik meridyen aksı (°)","hinge_location_preference":"Tercih edilen menteşe konumu",
    "hinge_location_alternative":"İkincil menteşe konumu","alternative_hinge":"Alternatif menteşe",
    "delta_k_d":"Dik-düz K farkı (D)","ring_tzone_clearance_mm":"Halka-geçiş zonu farkı (mm)",
    "alternative_rsb_um":"Alternatif RSB (µm)","alternative_pta_percent":"Alternatif PTA (%)",
    "alternative_safety":"Alternatifin güvenliği","warnings":"Uyarılar","notes":"Notlar",
    "status_independent":"Nihai karardan bağımsız","source":"Kaynak",
    "NOT_APPLICABLE":"Uygulanamaz","ALLOWED":"UYGULANABİLİR","NOT_ALLOWED":"UYGULANAMAZ",
    "English":"English","Turkish":"Türkçe","Language":"Dil",
    "Case inputs":"Vaka girdileri","Report identification":"Rapor kimlik bilgileri",
    "Patient name":"Hasta adı",
    "Reviewer / surgeon":"Değerlendiren / cerrah","Assessment date":"Değerlendirme tarihi",
    "Pentacam/topography and treatment-card images":"Pentacam/topografi ve tedavi kartı görüntüleri",
    "Required image confirmation":"Zorunlu görüntü doğrulaması","Optional treatment card":"İsteğe bağlı tedavi kartı",
    "present":"mevcut","missing":"eksik","not provided":"sağlanmadı",
    "unreadable — enter refraction":"okunamadı — refraksiyonu girin",
    "OD Four Maps Refractive":"OD Four Maps Refractive","OS Four Maps Refractive":"OS Four Maps Refractive",
    "OD Belin/Ambrosio Display":"OD Belin/Ambrosio Ekranı","OS Belin/Ambrosio Display":"OS Belin/Ambrosio Ekranı",
    "Show 2 Exams Topometric":"Show 2 Exams Topometric",
    "Upload each missing required image before assessment.":"Değerlendirmeden önce eksik olan her zorunlu görüntüyü yükleyin.",
    "No treatment card was provided. Enter complete manifest and intended refraction values for both eyes before assessment.":"Tedavi kartı sağlanmadı. Değerlendirmeden önce her iki göz için manifest ve hedeflenen refraksiyon değerlerini eksiksiz girin.",
    "The optional treatment card was unreadable. Enter complete manifest and intended refraction values for both eyes before assessment.":"İsteğe bağlı tedavi kartı okunamadı. Değerlendirmeden önce her iki göz için manifest ve hedeflenen refraksiyon değerlerini eksiksiz girin.",
    "Patient-level clinical modifiers":"Hasta düzeyinde klinik değiştiriciler","Select all that apply":"Uygun olanların tümünü seçin",
    "Select modifiers":"Değiştiricileri seçin","Chronic eye rubbing / repetitive ocular trauma":"Kronik göz ovalama / tekrarlayan oküler travma",
    "Family history of keratoconus":"Ailede keratokonus öyküsü",
    "Pregnancy or nursing":"Gebelik veya emzirme","Collagen / connective-tissue disease":"Kollajen / bağ dokusu hastalığı",
    "Relevant medication / drug usage":"İlgili ilaç kullanımı","Dry-eye disease / unstable ocular surface":"Kuru göz hastalığı / stabil olmayan oküler yüzey",
    "Other relevant systemic disease":"Diğer ilgili sistemik hastalık","None of the listed modifiers":"Listelenen değiştiricilerin hiçbiri",
    "Not documented / unknown":"Belgelenmedi / bilinmiyor",
    "Multiple modifiers may be selected. “None” and “Not documented” are exclusive choices.":"Birden fazla değiştirici seçilebilir. “Hiçbiri” ve “Belgelenmedi” seçenekleri tek başına seçilir.",
    "Contact-lens type at imaging":"Görüntüleme sırasındaki kontakt lens tipi","Days discontinued before Pentacam":"Pentacam öncesi bırakılan gün sayısı",
    "Eye-specific plans":"Göze özgü planlar","Prior corneal refractive surgery?":"Önceki korneal refraktif cerrahi?",
    "Procedure":"Prosedür","Preoperative manifest sphere (D)":"Preoperatif manifest sfer (D)",
    "Preoperative manifest cylinder (D; + or −)":"Preoperatif manifest silindir (D; + veya −)",
    "Intended treatment sphere (D)":"Hedef tedavi sferi (D)","Intended treatment cylinder (D; + or −)":"Hedef tedavi silindiri (D; + veya −)",
    "Cylinder axis (degrees)":"Silindir aksı (derece)","Actual maximum ablation (µm)":"Gerçek maksimum ablasyon (µm)",
    "Laser platform":"Lazer platformu","Planned LASIK flap (µm)":"Planlanan LASIK flebi (µm)",
    "PRK epithelial thickness (µm)":"PRK epitel kalınlığı (µm)","Optical zone (mm)":"Optik zon (mm)","Transition zone (mm)":"Geçiş zonu (mm)",
    "Randleman topography — surgeon confirmation required":"Randleman topografisi — cerrah onayı gerekli",
    "Randleman topography assessment":"Randleman topografi değerlendirmesi",
    "Category":"Kategori","What to look for":"Bakılacak bulgu","ERSS points":"ERSS puanı",
    "Normal / symmetric":"Normal / simetrik","Normal / symmetric bow-tie":"Normal / simetrik bow-tie",
    "Asymmetric bow-tie":"Asimetrik bow-tie","Inferior steepening / SRA":"İnferior dikleşme / SRA",
    "Inferior steepening and/or SRA":"İnferior dikleşme ve/veya SRA","Abnormal / ectatic":"Anormal / ektatik","Abnormal / ectatic pattern":"Anormal / ektatik patern",
    "CER-AI evaluates only the upper-left Axial/Sagittal Curvature (Front) map on the Pentacam 4 Maps Refractive page.":"CER-AI yalnız Pentacam 4 Maps Refractive sayfasındaki sol üst Axial/Sagittal Curvature (Front) haritasını değerlendirir.",
    "Normal or symmetric map":"Normal veya simetrik harita",
    "Mild asymmetric bow-tie: >0.5 D and <1.0 D, with no SRA/SRAX":"Hafif asimetrik bow-tie: >0,5 D ve <1,0 D; SRA/SRAX yok",
    "Inferior point ≥1.0 D steeper than the matching superior point with I-S <1.4 D, or SRAX ≥20°":"İnferior nokta, aynı uzaklıktaki superior noktadan ≥1,0 D daha dik ve I-S <1,4 D; veya SRAX ≥20°",
    "Abnormal or ectatic pattern, or I-S ≥1.4 D":"Anormal veya ektatik patern; ya da I-S ≥1,4 D",
    "If CER-AI cannot read the complete map with HIGH confidence, it asks the surgeon to choose the category. It never guesses a number. Only the highest applicable single category is scored; categories are not added.":"CER-AI tam haritayı YÜKSEK güvenle okuyamazsa kategoriyi cerrahın seçmesini ister. Sayısal değer tahmin etmez. Yalnızca en yüksek uygun tek kategori puanlanır; kategoriler toplanmaz.",
    "Superior steepening alone is not automatically assigned 3 points and requires surgeon review. BAD-D and other tomography indices are not substituted for Randleman topography.":"Yalnız superior dikleşmeye otomatik olarak 3 puan verilmez; cerrah değerlendirmesi gerekir. BAD-D ve diğer tomografi indeksleri Randleman topografisinin yerine kullanılmaz.",
    "Active CER-AI Randleman / ERSS points":"Aktif CER-AI Randleman / ERSS puanları",
    "Use the category table above":"Yukarıdaki kategori tablosunu kullanın",
    "Age — active CER-AI policy":"Yaş — aktif CER-AI politikası",
    "18 / 19–20 / ≥21 years":"18 / 19–20 / ≥21 yaş",
    "Preop corneal thickness — active CER-AI policy":"Preoperatif kornea kalınlığı — aktif CER-AI politikası",
    "Hard stop / 2 / 1 / 0":"Kesin durdurma / 2 / 1 / 0",
    "Randleman/ERSS is calculated from five independent LASIK inputs. BAD-D and NICE remain separate pathways. Overall ERSS disposition: 0–2 PASS if no other concern is present, 3 CAUTION without automatic defer, ≥4 STOP-DEFER.":"Randleman/ERSS beş bağımsız LASIK girdisinden hesaplanır. BAD-D ve NICE ayrı değerlendirme yollarıdır. Genel ERSS kararı: başka bir risk yoksa 0–2 UYGUN, 3 otomatik erteleme olmadan DİKKAT, ≥4 DURDUR-ERTELE.",
    "Source:":"Kaynak:",
    "Surgeon-confirmed I-S (D)":"Cerrah tarafından doğrulanan I-S (D)",
    "Surgeon-confirmed Randleman topography category":"Cerrah tarafından doğrulanan Randleman topografi kategorisi",
    "Select only when requested":"Yalnızca istendiğinde seçin",
    "Clinical eligibility and stability":"Klinik uygunluk ve stabilite","Clinical eligibility and stability — reviewed":"Klinik uygunluk ve stabilite — değerlendirildi",
    "Refraction stable?":"Refraksiyon stabil mi?","Documented progression?":"Belgelenmiş progresyon var mı?",
    "Unexplained CDVA <20/20?":"Açıklanamayan EİDGK <20/20 mi?",
    "Yes":"Evet","No":"Hayır","Unknown":"Bilinmiyor","Select":"Seçin","None":"Yok","Soft":"Yumuşak","Rigid / RGP":"Sert / RGP",
    "Assess images and run CER-AI assessment":"Görüntüleri değerlendir ve CER-AI değerlendirmesini çalıştır",
    "ERSS was originally developed for LASIK. CER-AI also applies its risk-assessment principles to PRK, using preoperative manifest refraction for the ERSS MRSE component in both procedures. Intended treatment correction is used for ablation and CER-AI treatment-range gates. Unless a different role-specific value is entered, the treatment card’s Düzeltme Miktarı auto-fills both manifest and intended correction. Every refraction field accepts positive or negative values; use the +/− buttons when a phone keyboard has no sign key. Equivalent plus-cylinder entries are safely transposed to minus-cylinder notation for calculation and disclosed in the report.":"ERSS başlangıçta LASIK için geliştirilmiştir. CER-AI, risk değerlendirme ilkelerini PRK için de uygular ve her iki işlemde ERSS MRSE bileşeni için preoperatif manifest refraksiyonu kullanır. Hedef tedavi düzeltmesi ablasyon ve CER-AI tedavi aralığı geçitlerinde kullanılır. Role özgü farklı bir değer girilmedikçe tedavi kartındaki Düzeltme Miktarı hem manifest hem hedef düzeltmeyi otomatik doldurur. Tüm refraksiyon alanları pozitif veya negatif değer kabul eder; telefon klavyesinde işaret tuşu yoksa +/− düğmelerini kullanın. Eşdeğer artı silindir girişleri hesaplama için güvenle eksi silindir gösterimine transpoze edilir ve raporda belirtilir.",
    "Download PDF":"PDF indir","Download Word":"Word indir","Open / Print one-page conclusion":"Tek sayfalık sonuç raporunu aç / yazdır","Share one-page PDF file":"Tek sayfalık PDF dosyasını paylaş","Print report":"Raporu yazdır",
    "CER-AI Clinical Decision Support":"CER-AI Klinik Karar Desteği","PREOPERATIVE ECTASIA RISK ASSESSMENT":"PREOPERATİF EKTAZİ RİSK DEĞERLENDİRMESİ",
    "Corneal refractive surgery assessment report":"Korneal refraktif cerrahi değerlendirme raporu","Eye-specific assessment":"Göze özgü değerlendirme",
    "Patient":"Hasta","Age":"Yaş","Date":"Tarih","Reviewer":"Değerlendiren","Eyes":"Gözler",
    "Not documented":"Belgelenmedi","Overall disposition":"Genel karar","PATIENT NAME NOT DOCUMENTED":"HASTA ADI BELGELENMEDİ","NOT ASSESSED":"DEĞERLENDİRİLMEDİ",
    "Automatically extracted source data":"Otomatik çıkarılan kaynak verileri","Complete machine-readable decision record":"Makine tarafından okunabilir tam karar kaydı",
    "Generated under the CER-AI Preoperative Ectasia Risk Assessment Protocol for corneal refractive surgery. CAUTION requires explicit surgeon review but does not automatically defer surgery. STOP-DEFER means surgery must not proceed unless the stated stop/defer condition is resolved. DATA INSUFFICIENT / NOT ASSESSED does not permit PASS. This clinical decision-support report does not replace independent surgeon review.":"Bu rapor, korneal refraktif cerrahi için CER-AI Preoperatif Ektazi Risk Değerlendirme Protokolü kapsamında oluşturulmuştur. DİKKAT açık cerrah değerlendirmesi gerektirir ancak cerrahiyi otomatik olarak ertelemez. DURDUR-ERTELE, belirtilen durdurma/erteleme koşulu giderilmeden cerrahiye devam edilmemesi anlamına gelir. VERİ YETERSİZ / DEĞERLENDİRİLMEDİ sonucu UYGUN kararına izin vermez. Bu klinik karar destek raporu cerrahın bağımsız değerlendirmesinin yerini almaz.",
    "Prior refractive surgery":"Önceki refraktif cerrahi","Score / category":"Puan / kategori","Randleman ERSS / category":"Randleman ERSS / kategori",
    "Final BAD-D / class":"Final BAD-D / sınıf","CER-AI-adapted NICE / class":"CER-AI uyarlanmış NICE / sınıf",
    "NICE (Navarro Index for Corneal Ectasia) combines K2, central pachymetry, posterior elevation and signed I-S. Each component contributes 1-3 points; total 4-12. CER-AI adaptation: posterior elevation <=15.5 um = 1, >15.5 to <18 um = 2, >=18 um = 3. The published table leaves 15 um unspecified. CER-AI uses only the explicitly labeled B. Ele.Th value on the Pentacam BAD Display page; no map or calculated substitute is accepted. Central pachymetry uses the plus-marked Pupil Center field (not Pachy Vertex N. or thinnest pachymetry), or a surgeon-confirmed central measurement. CER-AI disposition for LASIK and PRK: 4 = no NICE-specific escalation, 5-8 = CAUTION without automatic defer, >=9 = STOP-DEFER hard stop. NICE 4 does not establish surgical safety or override ERSS, BAD or other CER-AI stops. No individual absolute ectasia probability is inferred. Source: Navarro-Naranjo et al., Clin Ophthalmol 2024;18:881-883. DOI: 10.2147/OPTH.S464217.":"NICE (Navarro Korneal Ektazi İndeksi), K2, santral pakimetri, posterior elevasyon ve işaretli I-S değerini birleştirir. Her bileşen 1-3 puan verir; toplam 4-12'dir. CER-AI uyarlaması: posterior elevasyon ≤15,5 µm = 1, >15,5 ile <18 µm = 2, ≥18 µm = 3. Yayımlanmış tabloda 15 µm belirtilmemiştir. CER-AI yalnızca Pentacam BAD Display sayfasındaki açıkça etiketlenmiş B. Ele.Th değerini kullanır; harita veya hesaplanmış başka bir değer kabul edilmez. Santral pakimetri yalnızca artı işaretli Pupil Center alanından (Pachy Vertex N. veya en ince pakimetri değil) ya da cerrah doğrulamasından alınır. LASIK ve PRK için CER-AI kararı: 4 = NICE'a özgü artırım yok, 5-8 = otomatik erteleme olmadan DİKKAT, ≥9 = DURDUR-ERTELE kesin durdurma. NICE 4 cerrahi güvenliği kanıtlamaz ve ERSS, BAD veya diğer CER-AI durdurma kurallarını geçersiz kılmaz. Bireysel mutlak ektazi olasılığı çıkarımı yapılmaz. Kaynak: Navarro-Naranjo ve ark., Clin Ophthalmol 2024;18:881-883. DOI: 10.2147/OPTH.S464217.",
    "Stability / progression / CDVA flag":"Stabilite / progresyon / EİDGK uyarısı","Manifest entered notation":"Girilen manifest gösterim",
    "Manifest normalized (minus-cylinder)":"Normalize manifest (eksi silindir)","Intended entered notation":"Girilen hedef düzeltme gösterimi",
    "Intended normalized (minus-cylinder)":"Normalize hedef düzeltme (eksi silindir)","Correction source":"Düzeltme kaynağı",
    "Thinnest pachymetry":"En ince pakimetri","Intended MRSE":"Hedef MRSE","Preoperative Kmean":"Preoperatif Kort",
    "Manifest / intended pattern":"Manifest / hedef patern","Intended principal meridians":"Hedef ana meridyenler","Estimated final Kmean":"Tahmini final Kort",
    "Corneal effect factor":"Korneal etki katsayısı","Maximum ablation":"Maksimum ablasyon","PRK epithelium":"PRK epiteli",
    "Selected LASIK plan":"Seçilen LASIK planı","Selected plan parameters":"Seçilen plan parametreleri","Plan-selection priority":"Plan seçim önceliği","Optical / transition zone":"Optik / geçiş zonu","Tomography review":"Tomografi değerlendirmesi","Morphology category":"Morfoloji kategorisi",
    "Randleman I-S / source":"Randleman I-S / kaynak","Validated Randleman topography":"Doğrulanmış Randleman topografisi","Anterior-map read confidence":"Anterior harita okuma güveni",
    "Parameter":"Parametre","Result":"Sonuç","Value":"Değer","Clinical action:":"Klinik eylem:","Instrument/source:":"Cihaz/kaynak:",
    "NICE component audit":"NICE bileşen denetimi","NICE interpretation note":"NICE yorum notu","Reasons":"Nedenler","Hard stops":"Kesin durdurma nedenleri",
    "Missing / unresolved":"Eksik / çözümlenmemiş","Surgeon attention — hyperopic/mixed pathway":"Cerrahın dikkatine — hipermetropik/karma yol",
    "Tomography concern flags":"Tomografi endişe uyarıları","BAD display interpretation":"BAD ekran yorumu","Surgical-load evidence flags":"Cerrahi yük kanıt uyarıları",
    "Clinical modifiers":"Klinik değiştiriciler","Warnings":"Uyarılar","PRK Mitomycin-C guidance":"PRK Mitomycin-C rehberi","Extracted tomography":"Çıkarılan tomografi verileri",
    "Global clinical / source blockers":"Genel klinik / kaynak engelleri","Post-assessment ML7 microkeratome planning":"Değerlendirme sonrası ML7 mikrokeratom planlaması",
    "PENTACAM ACQUISITION QUALITY — SURGEON ATTENTION":"PENTACAM ÇEKİM KALİTESİ — CERRAHIN DİKKATİNE",
    "Planning warnings":"Planlama uyarıları","Planning notes":"Planlama notları","Assessment gate":"Değerlendirme geçidi","Vacuum ring":"Vakum halkası",
    "Vacuum pressure":"Vakum basıncı","Blade recommendation(s)":"Bıçak önerisi/önerileri","Primary hinge":"Birincil menteşe","Conditional alternative":"Koşullu alternatif","Steep meridian axis":"Dik meridyen aksı","Preferred hinge location":"Tercih edilen menteşe konumu","Secondary hinge location":"İkincil menteşe konumu","Horizontal white-to-white (HWTW)":"Horizontal white-to-white (HWTW)",
    "Alternative projected RSB / PTA":"Alternatif tahmini RSB / PTA","Alternative safety":"Alternatif güvenliği","Ring-zone clearance":"Halka-zon açıklığı","Source":"Kaynak",
    "Recommendation":"Öneri","Surgeon-review recommendation only; this module does not alter the ectasia disposition.":"Yalnızca cerrah değerlendirme önerisidir; bu modül ektazi kararını değiştirmez.",
    "PASS":"UYGUN","PASS WITH CAUTION":"DİKKATLE UYGUN","CAUTION":"DİKKAT","STOP-DEFER":"DURDUR-ERTELE",
    "DATA INSUFFICIENT":"VERİ YETERSİZ","ERROR":"HATA","ASSESSING...":"DEĞERLENDİRİLİYOR...",
    "Required information — no report has been generated":"Gerekli bilgiler — henüz rapor oluşturulmadı",
    "Pentacam examination-date conflict — surgeon review required":"Pentacam muayene tarihi çelişkisi — cerrah değerlendirmesi gerekli",
    "APPROVE_CONTINUE":"İnceledim — onayla ve devam et",
    "Source-date consistency":"Kaynak tarihi tutarlılığı",
    "4 Maps Refractive — OD and OS headers":"4 Maps Refractive — OD ve OS başlıkları",
    "Examination date":"Muayene tarihi",
    "PATIENT":"Hasta","Patient age (years)":"Hasta yaşı (yıl)",
    "Intended treatment initially follows manifest refraction. Edit intended values only when the planned treatment differs.":"Hedeflenen tedavi başlangıçta manifest refraksiyonu izler. Yalnızca planlanan tedavi farklıysa hedeflenen değerleri değiştirin.",
    "Intended treatment initially follows manifest refraction. An explicit zero cylinder also sets the intended cylinder and axis to zero; a nonzero cylinder requires an axis.":"Hedeflenen tedavi başlangıçta manifest refraksiyonu izler. Açıkça girilmiş sıfır silindir, hedef silindiri ve aksı da sıfıra ayarlar; sıfır olmayan silindir için aks gereklidir.",
    "Complete all items below, then continue. Existing inputs and image readings are retained. No calculation is required from the surgeon.":"Aşağıdaki tüm alanları tamamlayıp devam edin. Mevcut girdiler ve görüntü okumaları korunur. Cerrahın hesaplama yapması gerekmez.",
    "This cannot be completed by typing. Upload a source image that visibly shows QS: OK.":"Bu madde yazılarak tamamlanamaz. QS: OK ifadesini açıkça gösteren kaynak görüntüyü yükleyin.",
    "Explicit Pentacam QS: OK is required from the source image":"Kaynak görüntüde açıkça Pentacam QS: OK bulunması gerekir",
    "Explicitly printed Pentacam QS":"Açıkça basılı Pentacam QS",
    "Replace source images to continue":"Devam etmek için kaynak görüntüleri değiştirin",
    "A clearer/correct Pentacam or topography source image is required":"Daha net/doğru bir Pentacam veya topografi kaynak görüntüsü gereklidir",
    "This cannot be completed by typing. Replace the displayed limited/inadequate source image.":"Bu madde yazılarak tamamlanamaz. Gösterilen sınırlı/yetersiz kaynak görüntüyü değiştirin.",
    "Continue with completed information":"Tamamlanan bilgilerle devam et","Preparing...":"Hazırlanıyor...","This browser cannot share PDF files directly. Open the one-page conclusion, download the PDF, and attach that file in WhatsApp.":"Bu tarayıcı PDF dosyalarını doğrudan paylaşamıyor. Tek sayfalık sonuç raporunu açın, PDF'yi indirin ve dosyayı WhatsApp'ta ek olarak gönderin.",
    "Loading unread Pentacam/topography region...":"Pentacam/topografide okunamayan bölge yükleniyor...",
    "Pentacam/topography region the application could not read":"Uygulamanın okuyamadığı Pentacam/topografi bölgesi",
    "The unread source region could not be displayed. Enter the value from the original Pentacam/topography image.":"Okunamayan kaynak bölge gösterilemedi. Değeri özgün Pentacam/topografi görüntüsünden girin.",
    "Eye rubbing / ocular trauma":"Göz ovalama / oküler travma","Family history":"Aile öyküsü",
    "Pregnancy / nursing":"Gebelik / emzirme","Collagen-tissue disease":"Kollajen doku hastalığı","Medication / drug usage":"İlaç kullanımı",
    "Dry-eye disease":"Kuru göz hastalığı","Systemic disease":"Sistemik hastalık","Not documented":"Belgelenmedi",
    "Developed by Hüseyin Cengiz, MD. All rights reserved. Final responsibility rests with the surgeon at all times and under all circumstances.":"Hüseyin Cengiz, MD tarafından geliştirilmiştir. Tüm hakları saklıdır. Nihai sorumluluk her zaman ve her koşulda cerraha aittir.",
    "The final surgical decision and all associated responsibility and liability rest with the surgeon. This application is a clinical decision-support aid only.":"Nihai cerrahi karar ile buna bağlı tüm sorumluluk ve yükümlülük cerraha aittir. Bu uygulama yalnızca klinik karar destek aracıdır.",
    "No silent assumptions.":"Sessiz varsayım yoktur.",
    "Missing, conflicting or unreadable decision-critical data must be completed before any clinical report. OD and OS are assessed independently and are never averaged.":"Eksik, çelişkili veya okunamayan karar-kritik veriler herhangi bir klinik rapor oluşturulmadan önce tamamlanmalıdır. OD ve OS bağımsız değerlendirilir; değerlerin ortalaması alınmaz.",
    "The final surgical decision and all associated responsibility and liability rest with the surgeon.":"Nihai cerrahi karar ile buna bağlı tüm sorumluluk ve yükümlülük cerraha aittir.",
    "This application is a clinical decision-support aid only.":"Bu uygulama yalnızca klinik karar destek aracıdır.",
    "CER-AI BAD-D reference points":"CER-AI BAD-D referans puanları","CER-AI interpretation / action":"CER-AI yorumu / eylemi",
    "Variable":"Değişken","Finding":"Bulgu","Points":"Puan","Anterior topography":"Ön topografi","Normal / symmetrical":"Normal / simetrik",
    "Preop corneal thickness":"Preoperatif kornea kalınlığı","Residual stromal bed":"Rezidüel stromal yatak","MRSE":"MRSE",
    "yes":"evet","no":"hayır","unknown":"bilinmiyor","REASSURING":"RAHATLATICI","ADEQUATE":"YETERLİ","CONFIDENT":"GÜVENİLİR",
    "NORMAL_SYMMETRIC":"NORMAL_SİMETRİK","LOWER_FLAGGED_BURDEN":"DÜŞÜK UYARI YÜKÜ","MYOPIC":"MİYOPİK","HYPEROPIC":"HİPERMETROPİK","MIXED":"KARMA",
    "CER-AI Sign in":"CER-AI Girişi","Secure clinical workspace":"Güvenli klinik çalışma alanı",
    "Username":"Kullanıcı adı","Password":"Parola","Sign in":"Giriş yap","Sign-in failed.":"Giriş başarısız.",
    "Credentials are sent only to this CER-AI server over the active HTTPS session. The password is not stored in browser storage.":"Kimlik bilgileri yalnızca etkin HTTPS oturumu üzerinden bu CER-AI sunucusuna gönderilir. Parola tarayıcı depolamasında saklanmaz.",
    "IOL Calculation Surgery · Secure sign-in":"IOL Hesaplama Cerrahisi · Güvenli giriş",
    "Refractive Surgery · Secure sign-in":"Refraktif Cerrahi · Güvenli giriş",
    "CER-AI Clinical Modules":"CER-AI Klinik Modülleri","Choose a clinical module":"Bir klinik modül seçin",
    "You are signed in. Choose the surgical workflow to continue.":"Giriş yaptınız. Devam etmek için cerrahi iş akışını seçin.",
    "Refractive Surgery":"Refraktif Cerrahi","Corneal ectasia risk assessment and refractive-surgery planning.":"Korneal ektazi risk değerlendirmesi ve refraktif cerrahi planlaması.",
    "IOL Calculation Surgery":"IOL Hesaplama Cerrahisi","Pentacam, surgeon-defined parameters, and IOL category recommendation.":"Pentacam, cerrah tarafından tanımlanan parametreler ve IOL kategori önerisi.",
    "Open module →":"Modülü aç →","CER-AI provides clinical decision support only. Final treatment and lens selection remain the evaluating surgeon’s responsibility.":"CER-AI yalnızca klinik karar desteği sağlar. Nihai tedavi ve lens seçimi değerlendiren cerrahın sorumluluğundadır.",
    "CER-AI IOL Calculation Surgery":"CER-AI IOL Hesaplama Cerrahisi","Change clinical module":"Klinik modülü değiştir",
    "IOL Decision Assistant — Advanced Mode":"IOL Karar Asistanı — Gelişmiş Mod",
    "Stage 1 selects the eligible lens category. Stage 2 calculates spherical power with Cooke K6, then shows an embedded toric model and axis for surgeon testing when same-eye posterior corneal data are available. The manufacturer's toric calculator remains a separate optional comparison. Patient names must be readable and match on all three source reports.":"Aşama 1 uygun lens kategorisini seçer. Aşama 2 sferik gücü Cooke K6 ile hesaplar; aynı göze ait arka kornea verileri varsa cerrahın test etmesi için uygulama içindeki torik modeli ve aksı gösterir. Üreticinin torik hesaplayıcısı ayrı bir karşılaştırma seçeneğidir. Üç kaynak raporunda da hasta adı okunmalı ve aynı olmalıdır.",
    "1. Patient and source reports":"1. Hasta ve kaynak raporları","Age":"Yaş","Biological sex":"Biyolojik cinsiyet","Select manually":"Manuel seçin","Male":"Erkek","Female":"Kadın","Selected by the surgeon; never inferred from the patient name.":"Cerrah tarafından seçilir; hasta adından asla çıkarılmaz.","Eye":"Göz","OD — Right":"OD — Sağ","OS — Left":"OS — Sol",
    "Pentacam Cataract Pre-Op":"Pentacam Katarakt Pre-Op","Optical-quality fields plus Pachy Vertex, HWTW, and ACD (Int.). TCRP is not used.":"Optik kalite alanlarına ek olarak Pachy Vertex, HWTW ve ACD (Int.) kullanılır. TCRP kullanılmaz.",
    "Upload images (3)":"Görüntüleri yükleyin (3)","Select together: Pentacam Cataract Pre-Op, Pentacam 4 Maps Refractive for the same eye, and IOLMaster 500. The application identifies each report automatically. TCRP is not used.":"Üçünü birlikte seçin: Pentacam Cataract Pre-Op, aynı göze ait Pentacam 4 Maps Refractive ve IOLMaster 500. Uygulama her raporu otomatik tanır. TCRP kullanılmaz.",
    "Select exactly three images: Pentacam Cataract Pre-Op, same-eye 4 Maps Refractive, and IOLMaster 500.":"Tam üç görüntü seçin: Pentacam Cataract Pre-Op, aynı göze ait 4 Maps Refractive ve IOLMaster 500.",
    "Source identity verification failed. Check all three reports.":"Kaynak kimliği doğrulanamadı. Üç raporu da kontrol edin.",
    "Operative eye verification failed. Check all three reports.":"Ameliyat edilecek göz doğrulanamadı. Üç raporu da kontrol edin.",
    "Patient names differ across the three reports. Check the source images.":"Üç rapordaki hasta adları farklı. Kaynak görüntüleri kontrol edin.",
    "Patient name must be readable on all three reports before combining their measurements.":"Ölçümler birleştirilmeden önce üç raporda da hasta adı okunabilmelidir.",
    "The three images must contain one Pentacam Cataract Pre-Op, one 4 Maps Refractive, and one IOLMaster 500 report. Check the selected files.":"Üç görüntüde birer Pentacam Cataract Pre-Op, 4 Maps Refractive ve IOLMaster 500 raporu bulunmalıdır. Seçilen dosyaları kontrol edin.",
    "4 Maps Refractive Cornea Back could not be assigned to the operative eye.":"4 Maps Refractive Cornea Back, ameliyat edilecek gözle eşleştirilemedi.",
    "IOLMaster 500 report":"IOLMaster 500 raporu","Upper biometry block only: AL, K1/K2 and axes. K difference ≥1.00 D triggers toric evaluation.":"Yalnızca üst biyometri bloğu: AL, K1/K2 ve aksları. K farkı ≥1,00 D ise torik değerlendirme tetiklenir.",
    "Read from Pentacam":"Pentacam'dan oku","Operative-eye laterality is read only from the Pentacam Cataract Pre-Op report. IOLMaster is bilateral.":"Ameliyat edilecek gözün lateralitesi yalnızca Pentacam Cataract Pre-Op raporundan okunur. IOLMaster iki taraflıdır.",
    "Pentacam laterality was not read. Upload a readable Pentacam Cataract Pre-Op report showing OD or OS.":"Pentacam lateralitesi okunamadı. OD veya OS bilgisini gösteren okunabilir bir Pentacam Cataract Pre-Op raporu yükleyin.",
    "Conflicting Pentacam laterality was detected. Upload the Cataract Pre-Op report for one operative eye only.":"Çelişkili Pentacam lateralitesi saptandı. Yalnızca ameliyat edilecek tek göze ait Cataract Pre-Op raporunu yükleyin.",
    "The operative eye must come from a readable Pentacam Cataract Pre-Op report.":"Ameliyat edilecek göz bilgisi okunabilir bir Pentacam Cataract Pre-Op raporundan alınmalıdır.",
    "Extract approved fields":"Onaylı alanları çıkar","2. Lifestyle and visual goals":"2. Yaşam tarzı ve görsel hedefler",
    "Near-vision demand":"Yakın görme gereksinimi","Night driving":"Gece araç kullanımı","Halo/glare tolerance":"Halo/kamaşma toleransı",
    "Low":"Düşük","Moderate":"Orta","High":"Yüksek","Occasional":"Ara sıra","Frequent":"Sık",
    "3. Pentacam optical and complementary values":"3. Pentacam optik ve tamamlayıcı değerleri",
    "Total Corneal HOA (4 mm), µm":"Total Korneal HOA (4 mm), µm","Chord µ / kappa, mm":"Chord µ / kappa, mm","Chord α, mm":"Chord α, mm",
    "Pupil Dia (3D), mm":"Pupil Dia (3D), mm","Pachy Vertex / CCT, µm":"Pachy Vertex / CCT, µm","HWTW, mm":"HWTW, mm","ACD (Int.), mm":"ACD (Int.), mm",
    "Internal ACD excludes corneal thickness; ACD (Ext.) is never substituted.":"İnternal ACD kornea kalınlığını içermez; ACD (Ext.) hiçbir zaman yerine kullanılmaz.",
    "4. IOLMaster 500 biometry":"4. IOLMaster 500 biyometrisi","Axial length, mm":"Aksiyel uzunluk, mm","K1, D":"K1, D","K1 axis, degrees":"K1 aksı, derece","K2, D":"K2, D","K2 axis, degrees":"K2 aksı, derece",
    "Surgeon-editable; extracted original retained.":"Cerrah tarafından düzenlenebilir; çıkarılan özgün değer korunur.",
    "K difference":"K farkı","Toric trigger: ≥1.00 D and regular astigmatism.":"Torik tetikleyici: ≥1,00 D ve düzenli astigmatizma.",
    "Lens thickness, mm (if printed)":"Lens kalınlığı, mm (basılıysa)","Never estimated. Required with WTW for Cooke K6 when AL <22.00 mm.":"Asla tahmin edilmez. AL <22,00 mm olduğunda Cooke K6 için WTW ile birlikte gereklidir.",
    "Astigmatism regularity":"Astigmatizma düzenliliği","Not required below 1.00 D":"1,00 D altında gerekli değil","Regular":"Düzenli","Irregular":"Düzensiz",
    "5. Surgeon-defined ocular findings":"5. Cerrah tarafından tanımlanan oküler bulgular","Retinal disease":"Retina hastalığı","Mild":"Hafif","Significant":"Belirgin",
    "Macular pathology":"Maküler patoloji","Absent":"Yok","Present":"Var","Glaucoma":"Glokom","Suspect":"Şüpheli","Definite":"Kesin",
    "Ocular surface":"Oküler yüzey","Resolved after treatment":"Tedavi sonrası düzeldi","Repeat measurements":"Tekrarlanan ölçümler","Not stable":"Stabil değil","Stable":"Stabil",
    "Generate IOL recommendation":"IOL önerisi oluştur","Stage 1 — category decision":"Aşama 1 — kategori kararı",
    "Stage 2 — lens and power route":"Aşama 2 — lens ve güç yolu","Clinic lens":"Klinik lensi","Clinic lens family":"Klinik lens ailesi","Select an eligible lens":"Uygun bir lens seçin",
    "Pentacam 4 Maps Refractive (toric)":"Pentacam 4 Maps Refractive (torik)","Same operative eye. Cornea Back K1/K2, axes, and Rh/Rv are transcribed. Embedded toric results are unvalidated and for surgeon testing only.":"Ameliyat edilecek aynı göze ait Cornea Back K1/K2, akslar ve Rh/Rv aktarılır. Uygulama içindeki torik sonuçlar doğrulanmamıştır; yalnızca cerrah testi içindir.",
    "Incision axis, degrees (steep K2)":"İnsizyon aksı, derece (dik K2)","SIA axis, degrees (steep K2)":"SIA aksı, derece (dik K2)",
    "TEST ONLY":"YALNIZCA TEST","TEST ONLY — unvalidated toric optical prototype.":"YALNIZCA TEST — doğrulanmamış torik optik prototip.",
    "Independently check the source readings, model availability, implantation axis, and residual with the manufacturer's calculator before any clinical use.":"Herhangi bir klinik kullanımdan önce kaynak ölçümlerini, model bulunabilirliğini, yerleştirme aksını ve rezidüeli üreticinin hesaplayıcısıyla bağımsız olarak doğrulayın.",
    "Model":"Model","IOL cylinder":"IOL silindiri","Marker axis":"İşaretleme aksı","Predicted residual cylinder":"Tahmini rezidüel silindir",
    "No embedded toric model or axis available.":"Uygulama içinde torik model veya aks sonucu yok.","Upload the same-eye Pentacam 4 Maps Refractive image and verify Pachy Vertex.":"Aynı göze ait Pentacam 4 Maps Refractive görüntüsünü yükleyin ve Pachy Vertex değerini doğrulayın.","Review source measurements and the selected lens family.":"Kaynak ölçümlerini ve seçili lens ailesini gözden geçirin.",
    "Stage 1 — Cooke K6 spherical power":"Aşama 1 — Cooke K6 sferik güç","Cooke K6 power":"Cooke K6 gücü","K6 best option":"K6 en uygun seçenek","Optional manufacturer toric calculator comparison":"İsteğe bağlı üretici torik hesaplayıcısı karşılaştırması",
    "ACD target":"ACD hedefi","locked":"sabit","Second modern formula verification required":"İkinci bir modern formülle doğrulama gerekli","Use ESCRS where available and verify all values manually.":"Uygunsa ESCRS kullanın ve tüm değerleri elle doğrulayın.",
    "Embedded toric model, marker axis and predicted residual are shown for surgeon testing. This hybrid optical model is not clinically validated.":"Torik model, işaretleme aksı ve tahmini rezidüel cerrah testi için gösterilir. Bu birleşik optik model klinik olarak doğrulanmamıştır.",
    "Same-eye Pentacam 4 Maps Cornea Back K1/K2, axes, Rh/Rv and Pachy Vertex are required for the embedded toric calculation.":"Uygulama içindeki torik hesap için aynı göze ait Pentacam 4 Maps Cornea Back K1/K2, akslar, Rh/Rv ve Pachy Vertex gereklidir.",
    "Target refraction, D":"Hedef refraksiyon, D","Prior corneal surgery":"Önceki korneal cerrahi","Myopic LASIK/PRK":"Miyopik LASIK/PRK","Hyperopic LASIK/PRK":"Hipermetropik LASIK/PRK","RK":"RK",
    "Historical data":"Geçmiş veriler","Unavailable — no-history":"Mevcut değil — geçmiş verisiz","Available — history":"Mevcut — geçmiş verili",
    "Incision axis, degrees":"İnsizyon aksı, derece","Surgeon-specific SIA, D":"Cerraha özgü SIA, D","SIA axis, degrees (optional)":"SIA aksı, derece (isteğe bağlı)",
    "Continue to calculation":"Hesaplamaya devam et","Open Cooke K6":"Cooke K6'yı aç","Transfer values to ESCRS":"Değerleri ESCRS'ye aktar",
    "IOL power":"IOL gücü","Predicted refraction":"Tahmini refraksiyon","Selection":"Seçim","Best option":"En iyi seçenek",
    "CER-AI · Case Archive":"CER-AI · Vaka Arşivi","Loading…":"Yükleniyor…","Clinical workspace":"Klinik çalışma alanı","Sign out":"Çıkış yap",
    "Archived cases":"Arşivlenmiş vakalar","Search archived case revisions.":"Arşivlenmiş vaka revizyonlarını arayın.","Report date":"Rapor tarihi","Decision":"Karar","Reviewer":"Değerlendiren","Maximum results":"Azami sonuç sayısı",
    "Search":"Ara","Clear":"Temizle","Results":"Sonuçlar","Created by":"Oluşturan","Revision":"Revizyon","Reports":"Raporlar","Pentacam sources":"Pentacam kaynakları",
    "Run a search to list cases.":"Vakaları listelemek için arama yapın.","Owner tools":"Sahip araçları","Research export is pseudonymized and excludes direct identifiers. Audit records remain encrypted in the clinical archive.":"Araştırma dışa aktarımı takma adlıdır ve doğrudan tanımlayıcıları içermez. Denetim kayıtları klinik arşivde şifreli kalır.",
    "Research CSV · latest revisions":"Araştırma CSV · son revizyonlar","Research CSV · all revisions":"Araştırma CSV · tüm revizyonlar","Load recent audit events":"Son denetim olaylarını yükle","Archive status":"Arşiv durumu","Verify archive storage":"Arşiv depolamasını doğrula",
    "Archived Pentacam source images":"Arşivlenmiş Pentacam kaynak görüntüleri","Close":"Kapat","Archived CER-AI case":"Arşivlenmiş CER-AI vakası",
    "Modules":"Modüller","Case Archive":"Vaka Arşivi","Log out":"Çıkış yap","Return to CER-AI website":"CER-AI web sitesine dön",
    "Report attribution is bound to the authenticated CER-AI user.":"Rapor kaydı, kimliği doğrulanmış CER-AI kullanıcısına bağlıdır.",
    "CER-AI session expired. Sign in again.":"CER-AI oturumu sona erdi. Yeniden giriş yapın.","Logout failed":"Çıkış başarısız","Could not log out. Please try again.":"Çıkış yapılamadı. Lütfen yeniden deneyin.",
    "CER-AI Trial Access":"CER-AI Deneme Erişimi","Trial access":"Deneme erişimi","Doctor name":"Doktor adı","Continue":"Devam et",
    "No password is required during the trial. The name you enter is used as the doctor attribution for assessments you create.":"Deneme süresince parola gerekmez. Girdiğiniz ad, oluşturduğunuz değerlendirmelerde doktor kaydı olarak kullanılır.",
    "IOL Surgery":"IOL Cerrahisi","· IOL Surgery":"· IOL Cerrahisi","CER-AI Case Archive":"CER-AI Vaka Arşivi","Developed by Hüseyin Cengiz, MD. All rights reserved. Final responsibility rests with the surgeon at all times and under all circumstances.":"Hüseyin Cengiz, MD tarafından geliştirilmiştir. Tüm hakları saklıdır. Nihai sorumluluk her zaman ve her koşulda cerraha aittir.",
    "Required information is incomplete or invalid.":"Gerekli bilgiler eksik veya geçersiz.","Upload the Pentacam and IOLMaster 500 reports.":"Pentacam ve IOLMaster 500 raporlarını yükleyin.",
    "Transcribing source-locked fields…":"Kaynağa bağlı alanlar aktarılıyor…","Three reports extracted. Review values before evaluation.":"Üç rapor okundu. Değerlendirme öncesinde değerleri gözden geçirin.",
    "Image transcription failed.":"Görüntü aktarımı başarısız oldu.","Applying canonical IOL rules…":"Kanonik IOL kuralları uygulanıyor…","Recommendation generated. Select the lens for Stage 2.":"Öneri oluşturuldu. Aşama 2 için lensi seçin.",
    "Recommendation could not be generated.":"Öneri oluşturulamadı.","Select a clinic lens.":"Bir klinik lensi seçin.","Determining the canonical calculation route…":"Kanonik hesaplama yolu belirleniyor…","Power route could not be completed.":"Güç hesaplama yolu tamamlanamadı.",
    "IOLMaster printed an edited-value (*) marker; retained for visibility.":"IOLMaster düzenlenmiş değer (*) işareti yazdırdı; görünürlük için korundu.",
    "MULTIFOCAL":"MULTİFOKAL","MONOFOCAL":"MONOFOKAL","TORIC":"TORİK","NON_TORIC":"TORİK OLMAYAN","EDOF":"EDOF","Best option":"En iyi seçenek",
    "Session expired.":"Oturum sona erdi.","Date":"Tarih","De-identified":"Kimliksizleştirilmiş","Original":"Özgün",
    "Open case":"Vakayı aç","View source images":"Kaynak görüntüleri göster","Restricted to case creator":"Yalnızca vakayı oluşturan kullanıcı erişebilir","No matching archived cases.":"Eşleşen arşivlenmiş vaka yok.",
    "Searching…":"Aranıyor…","Secure archive is not enabled yet.":"Güvenli arşiv henüz etkin değil.","Archive search failed.":"Arşiv araması başarısız oldu.",
    "Retrieving authenticated archive file…":"Kimliği doğrulanmış arşiv dosyası alınıyor…","Archive file retrieved.":"Arşiv dosyası alındı.","Unable to retrieve archive file.":"Arşiv dosyası alınamadı.",
    "Opening authenticated archived case…":"Kimliği doğrulanmış arşiv vakası açılıyor…","Unable to reopen archived case.":"Arşivlenmiş vaka yeniden açılamadı.",
    "Loading encrypted source inventory…":"Şifrelenmiş kaynak envanteri yükleniyor…","No source images are archived for this case.":"Bu vaka için arşivlenmiş kaynak görüntüsü yok.","Unable to load archived source images.":"Arşivlenmiş kaynak görüntüleri yüklenemedi.",
    "Preview unavailable for this file type.":"Bu dosya türü için önizleme kullanılamıyor.","Open full size":"Tam boyutu aç","Download":"İndir","Download all source images (ZIP)":"Tüm kaynak görüntülerini indir (ZIP)",
    "Surgeon / reviewer":"Cerrah / değerlendiren","Archived by":"Arşivleyen","Overall decision":"Genel karar","Eye decisions":"Göz kararları","Legacy / unassigned":"Eski kayıt / atanmamış",
    "This application provides clinical decision support only. Final responsibility rests with the surgeon at all times and under all circumstances.":"Bu uygulama yalnızca klinik karar desteği sağlar. Nihai sorumluluk her zaman ve her koşulda cerraha aittir.",
    "Prior RK requires the external post-RK calculation pathway.":"Önceki RK, harici post-RK hesaplama yolunu gerektirir.",
    "Regular IOLMaster K difference is at least 1.00 D. Continue in the selected lens manufacturer's official toric calculator.":"Düzenli IOLMaster K farkı en az 1,00 D'dir. Seçilen lens üreticisinin resmi torik hesaplayıcısında devam edin.",
    "No verified official toric calculator is configured for this manufacturer; calculation is unavailable.":"Bu üretici için doğrulanmış resmi torik hesaplayıcı yapılandırılmamıştır; hesaplama kullanılamıyor.",
    "Cooke K6 calculation completed. The ESCRS calculator is provided as the external comparison route.":"Cooke K6 hesaplaması tamamlandı. ESCRS hesaplayıcısı harici karşılaştırma yolu olarak sunulmuştur.",
    "ACD target":"Ön kamara derinliğine göre hedef","locked":"kilitli",
    "Second modern formula verification required":"İkinci modern formülle doğrulama gerekli",
    "Use ESCRS where available and verify all values manually.":"Uygun olduğunda ESCRS kullanın ve tüm değerleri elle doğrulayın.",
    "Creating a secure, de-identified ESCRS transfer…":"Güvenli, kimliksizleştirilmiş ESCRS aktarımı oluşturuluyor…",
    "Biometry transferred to ESCRS. Verify every imported value before calculation.":"Biyometri ESCRS'ye aktarıldı. Hesaplamadan önce içe aktarılan her değeri doğrulayın.",
    "ESCRS transfer could not be completed.":"ESCRS aktarımı tamamlanamadı.",
    "Selected lens is not in the clinic-approved catalog.":"Seçilen lens, klinik tarafından onaylanmış katalogda bulunmuyor.",
    "Astigmatism regularity is required for toric routing.":"Torik yönlendirme için astigmatizma düzenliliği gereklidir.","Incision axis and surgeon-specific SIA are required for toric routing.":"Torik yönlendirme için insizyon aksı ve cerraha özgü SIA gereklidir.",
    "Cooke K6 requires lens thickness and WTW when axial length is below 22.00 mm.":"Aksiyel uzunluk 22,00 mm'nin altındaysa Cooke K6 lens kalınlığı ve WTW gerektirir.",
    "Research export is not enabled.":"Araştırma dışa aktarımı etkin değil.","Preparing research CSV…":"Araştırma CSV'si hazırlanıyor…","Research CSV generated.":"Araştırma CSV'si oluşturuldu.","Research export failed.":"Araştırma dışa aktarımı başarısız oldu.",
    "Audit review is not enabled.":"Denetim incelemesi etkin değil.","Loading audit records…":"Denetim kayıtları yükleniyor…","No audit records.":"Denetim kaydı yok.","Audit search failed.":"Denetim araması başarısız oldu.",
    "Loading protected archive status…":"Korunan arşiv durumu yükleniyor…","Protected archive status loaded.":"Korunan arşiv durumu yüklendi.","Unable to load archive status.":"Arşiv durumu yüklenemedi.",
    "Run the encrypted non-patient archive storage verification now?":"Şifrelenmiş, hasta verisi içermeyen arşiv depolama doğrulaması şimdi çalıştırılsın mı?","Writing and reading the encrypted non-patient canary…":"Şifrelenmiş, hasta verisi içermeyen doğrulama kaydı yazılıyor ve okunuyor…",
    "Archive storage verification passed. No patient data was used.":"Arşiv depolama doğrulaması başarılı. Hasta verisi kullanılmadı.","Archive storage verification failed.":"Arşiv depolama doğrulaması başarısız oldu.",
    "OWNER scope: cases created under your account retain original identity, reports, and source images; other doctors’ cases remain masked and de-identified.":"SAHİP kapsamı: hesabınız altında oluşturulan vakalar özgün kimlik, rapor ve kaynak görüntülerini korur; diğer doktorların vakaları maskeli ve kimliksizleştirilmiş kalır.",
    "DOCTOR scope: only cases created under your account, with original identity and source material.":"DOKTOR kapsamı: yalnızca hesabınız altında oluşturulan, özgün kimlik ve kaynak materyali içeren vakalar.",
    "Search your own identifiable cases":"Kimliği görülebilen kendi vakalarınızda arayın","Secure archive is configured off. No patient data will be listed until archive activation is verified.":"Güvenli arşiv kapalı olarak yapılandırılmıştır. Arşiv etkinleştirmesi doğrulanana kadar hasta verileri listelenmez.","Unable to load archive workspace.":"Arşiv çalışma alanı yüklenemedi.",
  };
  const CLINICAL = {
    "Temporal hinge (default)":"Temporal menteşe (varsayılan)",
    "Plano/standard blade unless another rule or clinical factor applies":"Başka bir kural veya klinik faktör yoksa plano/standart bıçak",
    "Recommendation only; surgeon must verify anatomy, device setup, and the active ML7 manual before use.":"Yalnızca öneridir; cerrah kullanımdan önce anatomiyi, cihaz ayarlarını ve güncel ML7 kılavuzunu doğrulamalıdır.",
    "If the selected ring leaks, does not hold vacuum, or is too large, the active ML7 reference directs selection of one smaller ring.":"Seçilen halka kaçırıyor, vakumu tutmuyor veya fazla büyükse güncel ML7 referansı bir küçük halka seçilmesini belirtir.",
    "Hyperopic W2W xx.60+ rounded upward under the active ML7 reference.":"Hipermetropik W2W xx.60+ güncel ML7 referansına göre yukarı yuvarlandı.",
    "Steepest K is outside the supplied nomogram range; no ring is inferred.":"En dik K, sağlanan nomogram aralığının dışındadır; halka seçimi yapılmamıştır.",
    "Canonical K1/K2 unavailable: confirm the missing Cornea Front values; no ML7 vacuum-ring recommendation was generated.":"Kanonik K1/K2 mevcut değil: eksik Cornea Front değerlerini doğrulayın; ML7 vakum halkası önerisi oluşturulmadı.",
    "Verified horizontal white-to-white (HWTW) unavailable: enter HWTW from the 4 Maps Refractive lower-left labeled box; no vacuum-ring recommendation was generated.":"Doğrulanmış yatay beyazdan beyaza mesafe (HWTW) mevcut değil: HWTW değerini 4 Maps Refractive ekranının sol alt etiketli kutusundan girin; vakum halkası önerisi oluşturulmadı.",
    "Active ML7 reference advises 580-590 mmHg when pachymetry is <530 µm, with corneal K taking priority.":"Güncel ML7 referansı, pakimetri <530 µm olduğunda korneal K öncelikli olmak üzere 580-590 mmHg önerir.",
    "Pachymetry <=500 µm: active ML7 reference recommends -10 blade when seeking a thinner flap/more residual stroma.":"Pakimetri <=500 µm: güncel ML7 referansı daha ince flep / daha fazla rezidüel stroma hedefleniyorsa -10 bıçak önerir.",
    "K <=39 D: active ML7 reference recommends +10 or +20 blade.":"K <=39 D: güncel ML7 referansı +10 veya +20 bıçak önerir.",
    "Ablation/transition zone is not 0.4-0.5 mm smaller than the selected ring (active ML7 reference optimum).":"Ablasyon / geçiş zonu seçilen halkadan 0,4-0,5 mm daha küçük değildir (güncel ML7 referansının ideal farkı).",
    "MED-LOGICS ML7 Rev. 22 active Turkish reference + CER-AI hinge amendment":"MED-LOGICS ML7 Rev. 22 güncel Türkçe referans + CER-AI menteşe değişikliği",
    "STOP-DEFER; do not proceed with elective corneal refractive surgery.":"DURDUR-ERTELE; elektif korneal refraktif cerrahiye devam etmeyin.",
    "STOP/DEFER; repeat relevant ectasia screening and reassess after at least 6 months.":"DURDURUN/ERTELEYİN; ilgili ektazi taramasını tekrarlayın ve en az 6 ay sonra yeniden değerlendirin.",
    "CER-AI assessment PASS; this is not a guarantee of zero ectasia risk.":"CER-AI değerlendirmesi UYGUN; bu sonuç ektazi riskinin sıfır olduğunu garanti etmez.",
    "Decision-critical or required clinical data are missing/unresolved; PASS is prohibited.":"Karar için kritik veya zorunlu klinik veriler eksik/çözümlenmemiştir; UYGUN kararı verilemez.",
    "No surgical clearance; resolve the stated review/data requirement.":"Cerrahi onay yoktur; belirtilen değerlendirme/veri gereksinimini giderin.",
    "Overall result reflects the least favorable eye. Each eye remains independently scored; values are never averaged.":"Genel sonuç daha olumsuz olan gözü yansıtır. Her göz bağımsız puanlanır; değerlerin ortalaması alınmaz.",
    "CER-AI operational hard stop: thinnest preoperative cornea <480 µm.":"CER-AI kesin durdurma kuralı: preoperatif en ince kornea <480 µm.",
    "CER-AI operational LASIK RSB hard stop: RSB <300 µm.":"CER-AI LASIK kesin durdurma kuralı: RSB <300 µm.",
    "CER-AI operational PRK RST hard stop: RST <310 µm.":"CER-AI PRK kesin durdurma kuralı: RST <310 µm.",
    "Mitomycin-C use is REQUIRED for hyperopic PRK.":"Hipermetropik PRK'de Mitomycin-C kullanımı ZORUNLUDUR.",
    "Mitomycin-C use is REQUIRED for myopic PRK with intended MRSE magnitude 4.00 D or greater (for example, -4.00 D or -5.00 D).":"Hedef MRSE miyopi büyüklüğü 4,00 D veya daha fazla olan PRK'de Mitomycin-C kullanımı ZORUNLUDUR (örneğin -4,00 D veya -5,00 D).",
    "Mitomycin-C use is RECOMMENDED for myopic PRK with intended MRSE magnitude below 4.00 D (for example, -3.99 D).":"Hedef MRSE miyopi büyüklüğü 4,00 D'nin altında olan PRK'de Mitomycin-C kullanımı ÖNERİLİR (örneğin -3,99 D).",
    "The myopic and hyperopic PRK Mitomycin-C rules do not classify mixed astigmatism; surgeon review is required.":"Miyopik ve hipermetropik PRK Mitomycin-C kuralları karma astigmatizmayı sınıflandırmaz; cerrah değerlendirmesi gerekir.",
    "Refractive instability or documented progression: defer and re-evaluate after >=6 months.":"Refraktif instabilite veya belgelenmiş progresyon: erteleyin ve ≥6 ay sonra yeniden değerlendirin.",
    "Unexplained preoperative CDVA <20/20 requires investigation.":"Açıklanamayan preoperatif EİDGK <20/20 araştırılmalıdır.",
    "Prior PRK/LASIK/SMILE or other corneal refractive surgery requires a separate pathway.":"Önceki PRK/LASIK/SMILE veya başka korneal refraktif cerrahi ayrı bir değerlendirme yolu gerektirir.",
    "Pregnancy or nursing reported; separate refractive-surgery eligibility review required.":"Gebelik veya emzirme bildirildi; ayrı refraktif cerrahi uygunluk değerlendirmesi gerekir.",
    "Collagen/connective-tissue disease reported; separate clinical eligibility review required.":"Kollajen/bağ dokusu hastalığı bildirildi; ayrı klinik uygunluk değerlendirmesi gerekir.",
    "Relevant medication/drug usage reported; medication-specific clinical review required.":"İlgili ilaç kullanımı bildirildi; ilaca özgü klinik değerlendirme gerekir.",
    "Dry-eye disease reported; ocular-surface optimization and eligibility review required.":"Kuru göz hastalığı bildirildi; oküler yüzey optimizasyonu ve uygunluk değerlendirmesi gerekir.",
    "Systemic disease reported; disease-specific refractive-surgery eligibility review required.":"Sistemik hastalık bildirildi; hastalığa özgü refraktif cerrahi uygunluk değerlendirmesi gerekir.",
    "Override gate negative; procedure-specific score and required tomography/clinical review are reassuring.":"Öncelikli dışlama ölçütü yoktur; prosedüre özgü puan ile zorunlu tomografi/klinik değerlendirme rahatlatıcıdır.",
    "Inter-eye tomography concern: NO MAJOR INTER-EYE DISCORDANCE DETECTED. No major categorical inter-eye tomography discordance detected. This is not a clearance criterion and does not change the CER-AI score or final disposition.":"Gözler arası tomografi değerlendirmesi: BELİRGİN GÖZLER ARASI UYUMSUZLUK SAPTANMADI. Belirgin kategorik gözler arası tomografi uyumsuzluğu saptanmadı. Bu bir cerrahi onay ölçütü değildir ve CER-AI puanını veya nihai kararı değiştirmez.",
    "Plan A — flap 100 µm; optical zone 6.5 mm; transition zone 9.0 mm":"Plan A — flep 100 µm; optik zon 6,5 mm; geçiş zonu 9,0 mm",
    "Plan B — flap 100 µm; optical zone 6.0 mm; transition zone 8.5 mm":"Plan B — flep 100 µm; optik zon 6,0 mm; geçiş zonu 8,5 mm",
    "Plan C — flap 90 µm; optical zone 6.0 mm; transition zone 8.5 mm":"Plan C — flep 90 µm; optik zon 6,0 mm; geçiş zonu 8,5 mm",
    "Select the first safe plan only: Plan A → Plan B → Plan C":"Yalnızca ilk güvenli planı seçin: Plan A → Plan B → Plan C",
    "NICE interpretation: no NICE escalation. NICE is an independent screening pathway and is not added to the CER-AI numeric score.":"NICE yorumu: NICE artırımı yoktur. NICE bağımsız bir tarama yoludur ve CER-AI sayısal puanına eklenmez.",
    "CER-AI SCORE — SOURCE & BREAKDOWN: PRK-EWSS v1.0 provisional evidence-weighted triage score (not validated); CER-AI-modified age bands. morphology: +0 (morphology NORMAL_SYMMETRIC); pachymetry: +0 (thinnest pachymetry 560 µm); age: +0 (age 35 years). TOTAL: 0 (LOWER_FLAGGED_BURDEN). Hard stops are independent of this numeric score and are not counted as score points.":"CER-AI PUANI — KAYNAK VE DÖKÜM: PRK-EWSS v1.0 geçici kanıt ağırlıklı triyaj puanı (doğrulanmamıştır); CER-AI'ye uyarlanmış yaş aralıkları. morfoloji: +0 (NORMAL_SİMETRİK); pakimetri: +0 (en ince pakimetri 560 µm); yaş: +0 (35 yaş). TOPLAM: 0 (DÜŞÜK UYARI YÜKÜ). Kesin durdurma kuralları bu sayısal puandan bağımsızdır ve puana eklenmez.",
    "ECTASIA RISK INTERPRETATION: In the cited post-PRK ectasia series with complete ERSS data, 77% of ectasia eyes had cumulative ERSS >=4, 9% had score 3, and 14% had score <=2. The surgical cohort incidence reported in that study was 9/31,045 eyes (0.029%). ABSOLUTE PROBABILITY: Not established for an individual PRK score. LIMITATION: These are distributions among ectasia cases and an overall cohort incidence, not score-specific patient probabilities. The LASIK ERSS is not validated as an absolute-risk calculator for PRK; the 0.029% cohort incidence must not be assigned to an individual score. SOURCE: Risk Assessment for Corneal Ectasia following Photorefractive Keratectomy.":"EKTAZİ RİSK YORUMU: Tam ERSS verisi bulunan atıf yapılan PRK sonrası ektazi serisinde ektazili gözlerin %77'sinde toplam ERSS ≥4, %9'unda puan 3 ve %14'ünde puan ≤2 idi. Çalışmadaki cerrahi kohort insidansı 9/31.045 göz (%0,029) olarak bildirildi. MUTLAK OLASILIK: Tek bir PRK puanı için belirlenmemiştir. SINIRLAMA: Bunlar ektazi vakaları arasındaki dağılımlar ve genel kohort insidansıdır; puana özgü hasta olasılıkları değildir. LASIK ERSS, PRK için mutlak risk hesaplayıcısı olarak doğrulanmamıştır; %0,029 kohort insidansı bireysel bir puana atanamaz. KAYNAK: Fotorefraktif keratektomi sonrası korneal ektazi risk değerlendirmesi."
  };
  const translate = value => {
    const text = String(value ?? "");
    if (locale !== "tr" || !text) return text;
    if (CLINICAL[text]) return CLINICAL[text];
    if (TR[text]) return TR[text];
    if (text.startsWith("ML7 ") && TR[text.slice(4)]) return `ML7 ${TR[text.slice(4)]}`;
    return text
      .replace(/^CER-AI SCORE — SOURCE & BREAKDOWN:/,"CER-AI PUANI — KAYNAK VE DÖKÜM:")
      .replace(/^ECTASIA RISK INTERPRETATION:/,"EKTAZİ RİSK YORUMU:")
      .replace(/^ABSOLUTE PROBABILITY:/,"MUTLAK OLASILIK:")
      .replace(/^LIMITATION:/,"SINIRLAMA:")
      .replace(/^Inter-eye tomography concern:/,"Gözler arası tomografi değerlendirmesi:")
      .replace(/^Recommended IOL:\s*/,"Önerilen IOL: ")
      .replace(/^Selected images \((\d+)\): /,"Seçilen görüntüler ($1): ")
      .replace(/^Embedded toric calculation — ([\d.]+) D K6 spherical equivalent$/,"Uygulama içi torik hesap — $1 D K6 sferik eşdeğer")
      .replace(/^([A-Z0-9]+) · ([\d.]+)° marker axis$/,"$1 · $2° işaretleme aksı")
      .replace(/^Predicted residual cylinder: ([\d.]+) D at ([\d.]+)° \(prototype estimate\)\.$/,"Tahmini rezidüel silindir: $1 D, $2° (prototip tahmini).")
      .replace(/^Eligible:\s*/,"Uygun: ")
      .replace(/\bToric Multifocal\b/g,"Torik Multifokal")
      .replace(/\bToric Monofocal\b/g,"Torik Monofokal")
      .replace(/\bToric EDOF\b/g,"Torik EDOF")
      .replace(/^Age: (\d+) years \(([^)]+)\)\.$/,"Yaş: $1 yıl ($2).")
      .replace(/^Near-vision demand is (\w+) and halo\/glare tolerance is (\w+)\.$/,"Yakın görme gereksinimi $1 ve halo/kamaşma toleransı $2.")
      .replace(/^Night-driving requirement is (\w+)\.$/,"Gece araç kullanma gereksinimi $1.")
      .replace(/^Total Corneal HOA \(4 mm\) is ([\d.]+) µm \((\w+)\)\.$/,"Total Korneal HOA (4 mm) $1 µm ($2).")
      .replace(/^Pentacam Pupil Dia \(3D\) is ([\d.]+) mm; the multifocal permitted range is 2\.00–4\.00 mm inclusive\.$/,"Pentacam Pupil Dia (3D) $1 mm'dir; izin verilen multifokal aralık 2,00–4,00 mm'dir (sınırlar dahil).")
      .replace(/^Angle kappa is ([\d.]+) mm and angle alpha is ([\d.]+) mm\.$/,"Kappa açısı $1 mm ve alfa açısı $2 mm'dir.")
      .replace(/^Retinal status is ([^;]+); macular pathology is ([^;]+); glaucoma status is ([^.]+)\.$/,"Retina durumu $1; maküler patoloji $2; glokom durumu $3.")
      .replace(/^Ocular-surface status is ([^.]+)\.$/,"Oküler yüzey durumu $1.")
      .replace(/^Active IOLMaster 500 K difference is ([\d.]+) D \(([^)]+)\); the toric-evaluation threshold is 1\.00 D inclusive\.$/,"Aktif IOLMaster 500 K farkı $1 D'dir ($2); torik değerlendirme eşiği 1,00 D'dir (dahil).")
      .replace(/^Prior LASIK\/PRK overrides the standard route\. Use the Barrett True-K (history|no-history) pathway externally\.$/,"Önceki LASIK/PRK standart yolu geçersiz kılar. Barrett True-K $1 yolunu harici olarak kullanın.")
      .replace(/^Cooke K6 could not complete the calculation\. No substitute was used \(([^)]+)\)\.$/,"Cooke K6 hesaplamayı tamamlayamadı. Yerine başka bir yöntem kullanılmadı ($1).")
      .replace(/\b(not required below threshold|resolved after treatment|occasional|frequent|moderate|significant|suspect|definite|regular|irregular|present|absent|mild|high|low|none)\b/gi,word=>({"not required below threshold":"eşik altında gerekli değil","resolved after treatment":"tedavi sonrası düzeldi","occasional":"ara sıra","frequent":"sık","moderate":"orta","significant":"belirgin","suspect":"şüpheli","definite":"kesin","regular":"düzenli","irregular":"düzensiz","present":"var","absent":"yok","mild":"hafif","high":"yüksek","low":"düşük","none":"yok"})[word.toLowerCase()]||word)
      .replace(/^Open (.+)$/,(_,name)=>`${name} aracını aç`)
      .replace(/^(\d+) archived revision\(s\) found\.$/,"$1 arşivlenmiş revizyon bulundu.")
      .replace(/^(\d+) source image\(s\)\./,"$1 kaynak görüntüsü.")
      .replace(/^Extraction completed\. Surgeon entry is required only for unreadable fields: (.+)\.$/,"Çıkarma tamamlandı. Yalnızca okunamayan alanlar için cerrah girişi gereklidir: $1.")
      .replace(/NO MAJOR INTER-EYE DISCORDANCE DETECTED/g,"BELİRGİN GÖZLER ARASI UYUMSUZLUK SAPTANMADI")
      .replace(/No major categorical inter-eye tomography discordance detected\./g,"Belirgin kategorik gözler arası tomografi uyumsuzluğu saptanmadı.")
      .replace(/This is not a clearance criterion and does not change the CER-AI score or final disposition\./g,"Bu bir cerrahi onay ölçütü değildir ve CER-AI puanını veya nihai kararı değiştirmez.")
      .replace(/device QS is NOT_OK/g,"cihaz QS değeri NOT_OK")
      .replace(/explicit QS: OK was not confirmed/g,"açık QS: OK doğrulanmadı")
      .replace(/source image quality is LIMITED/g,"kaynak görüntü kalitesi SINIRLI")
      .replace(/source image quality is INADEQUATE/g,"kaynak görüntü kalitesi YETERSİZ")
      .replace(/The assessment was generated from the readable data, but acquisition quality is not confirmed as OK\. The surgeon must review the source images and interpret all findings with caution\./g,"Değerlendirme okunabilen verilerden oluşturuldu; ancak çekim kalitesinin uygun olduğu doğrulanmadı. Cerrah kaynak görüntüleri incelemeli ve tüm bulguları dikkatle yorumlamalıdır.")
      .replace(/Hard stops are independent of this numeric score and are not counted as score points\./g,"Kesin durdurma kuralları bu sayısal puandan bağımsızdır ve puana eklenmez.")
      .replace(/NICE is an independent screening pathway and is not added to the CER-AI numeric score\./g,"NICE bağımsız bir tarama yoludur ve CER-AI sayısal puanına eklenmez.")
      .replace(/Superior hinge at the vertical steep meridian/g,"Dikey dik meridyende superior menteşe")
      .replace(/Temporal hinge preferred at the horizontal steep meridian/g,"Yatay dik meridyende temporal menteşe tercih edilir")
      .replace(/surgeon determines the anatomical hinge location/g,"cerrah anatomik menteşe konumunu belirler")
      .replace(/Astigmatic disparity within validation thresholds: magnitude difference ([\d.]+) D; axis difference ([\d.]+)°; no PS3 consequence\./g,"Astigmatik uyumsuzluk doğrulama sınırları içindedir: büyüklük farkı $1 D; aks farkı $2°; PS3 sonucu etkilenmez.")
      .replace(/\bdefinition:/g,"Tanım:")
      .replace(/Temporal hinge \(default\)/g,"Temporal menteşe (varsayılan)")
      .replace(/^Superior$/,"Superior")
      .replace(/^Temporal$/,"Temporal")
      .replace(/^Nasal$/,"Nazal")
      .replace(/\bNot documented\b/gi,"Belgelenmedi")
      .replace(/\bNot applicable\b/gi,"Uygulanamaz")
      .replace(/\baxis unavailable\b/gi,"aks mevcut değil")
      .replace(/\bLOWER_FLAGGED_BURDEN\b/g,"DÜŞÜK UYARI YÜKÜ")
      .replace(/\bNORMAL_SYMMETRIC\b/g,"NORMAL_SİMETRİK")
      .replace(/\bREASSURING\b/g,"RAHATLATICI")
      .replace(/\bADEQUATE\b/g,"YETERLİ")
      .replace(/\bMYOPIC\b/g,"MİYOPİK")
      .replace(/\bHYPEROPIC\b/g,"HİPERMETROPİK")
      .replace(/\bMIXED\b/g,"KARMA")
      .replace(/\bNO_NICE_ESCALATION\b/g,"NICE ARTIRIMI YOK")
      .replace(/\bPENTACAM_PRINTED\b/g,"PENTACAM YAZILI DEĞER")
      .replace(/\bPENTACAM_LABELED_K2\b/g,"PENTACAM ETİKETLİ K2")
      .replace(/\bPENTACAM_LABELED_IS\b/g,"PENTACAM ETİKETLİ I-S")
      .replace(/\byes\b/gi,"evet")
      .replace(/\bno\b/gi,"hayır")
      .replace(/\bunknown\b/gi,"bilinmiyor")
      .replace(/point\(s\)/gi,"puan")
      .replace(/\bcentral_pachymetry\b/gi,"santral pakimetri")
      .replace(/\bposterior_elevation\b/gi,"posterior elevasyon")
      .replace(/\bB_Ele_Th\b/g,"B. Ele.Th")
      .replace(/\bcentral_pachy\b/gi,"santral pakimetri")
      .replace(/\bB_Ele_Th_um\b/g,"B. Ele.Th (µm)")
      .replace(/\bcentral_pachy_um\b/gi,"santral pakimetri (µm)")
      .replace(/\bI_S\b/g,"I-S")
      .replace(/\bK2_D\b/g,"K2 (D)")
      .replace(/\bI_S_D\b/g,"I-S (D)")
      .replace(/\bsource\b/gi,"kaynak");
  };
  const translateDOM = root => {
    if (locale !== "tr" || !root) return;
    if (root.nodeType === Node.TEXT_NODE) {
      if (!root.parentElement?.closest("script,style,pre")) {
        const raw=root.nodeValue, trimmed=raw.trim();
        if(trimmed){const translated=translate(trimmed);if(translated!==trimmed)root.nodeValue=raw.replace(trimmed,translated);}
      }
      return;
    }
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes=[]; while(walker.nextNode()) nodes.push(walker.currentNode);
    for(const node of nodes){
      if(node.parentElement?.closest("script,style,pre")) continue;
      const raw=node.nodeValue, trimmed=raw.trim(); if(!trimmed)continue;
      const translated=translate(trimmed); if(translated!==trimmed)node.nodeValue=raw.replace(trimmed,translated);
    }
    const attributed=[...(root.matches?.("[aria-label],[title],[placeholder]")?[root]:[]),...(root.querySelectorAll?.("[aria-label],[title],[placeholder]")||[])];
    attributed.forEach(el=>{
      for(const attr of ["aria-label","title","placeholder"]){const raw=el.getAttribute(attr),translated=raw?translate(raw):raw;if(raw&&translated!==raw)el.setAttribute(attr,translated);}
    });
  };
  const setLocale = next => { localStorage.setItem("cerai-language", next === "tr" ? "tr" : "en"); location.reload(); };
  window.CERAI_I18N={locale,translate,clinical:translate,translateDOM,setLocale};
  document.documentElement.lang=locale;
  const initialize = () => {
    document.title=translate(document.title);
    translateDOM(document.body);
    if(!document.querySelector("[data-language]")){
      const switcher=document.createElement("div");
      switcher.id="cerai-language-switch";
      switcher.setAttribute("aria-label",translate("Language"));
      switcher.style.cssText="position:fixed;right:12px;bottom:12px;z-index:10000;display:flex;gap:4px;padding:4px;border:1px solid #8ca2b2;border-radius:8px;background:#fff;box-shadow:0 2px 10px rgba(0,0,0,.16)";
      for(const code of ["en","tr"]){
        const button=document.createElement("button");
        button.type="button";button.dataset.language=code;button.textContent=code.toUpperCase();
        button.setAttribute("aria-pressed",String(locale===code));
        button.style.cssText=`width:auto;margin:0;padding:6px 9px;border:0;border-radius:5px;cursor:pointer;font:700 12px Arial,sans-serif;color:${locale===code?"#fff":"#173b57"};background:${locale===code?"#173b57":"#eef3f6"}`;
        button.addEventListener("click",()=>setLocale(code));switcher.appendChild(button);
      }
      document.body.appendChild(switcher);
    }
    document.querySelectorAll("[data-language]").forEach(button=>{
      button.setAttribute("aria-pressed",String(button.dataset.language===locale));
      if(!button.dataset.ceraiLanguageBound){button.addEventListener("click",()=>setLocale(button.dataset.language));button.dataset.ceraiLanguageBound="true";}
    });
    if(locale==="tr"){
      const observer=new MutationObserver(records=>records.forEach(record=>{
        record.addedNodes.forEach(node=>translateDOM(node));
        if(record.type==="attributes")translateDOM(record.target);
      }));
      observer.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:["aria-label","title","placeholder"]});
    }
  };
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",initialize,{once:true});else initialize();
})();
