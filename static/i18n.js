/* Presentation-only bilingual layer. Clinical decision values remain unchanged. */
(() => {
  const stored = (localStorage.getItem("cerai-language") || "en").toLowerCase();
  const locale = stored === "tr" ? "tr" : "en";
  const TR = {
    "English":"English","Turkish":"Türkçe","Language":"Dil",
    "Case inputs":"Vaka girdileri","Report identification":"Rapor kimlik bilgileri",
    "Patient name":"Hasta adı","Patient ID / record number":"Hasta kimliği / dosya numarası",
    "Patient age (Pentacam age unreadable; enter years)":"Hasta yaşı (Pentacam yaşı okunamadı; yıl olarak girin)",
    "Reviewer / surgeon":"Değerlendiren / cerrah","Assessment date":"Değerlendirme tarihi",
    "Pentacam/topography and treatment-card images":"Pentacam/topografi ve tedavi kartı görüntüleri",
    "Patient-level clinical modifiers":"Hasta düzeyinde klinik değiştiriciler","Select all that apply":"Uygun olanların tümünü seçin",
    "Select modifiers":"Değiştiricileri seçin","Chronic eye rubbing / repetitive ocular trauma":"Kronik göz ovalama / tekrarlayan oküler travma",
    "Family history of keratoconus":"Ailede keratokonus öyküsü","Marked inter-eye asymmetry":"Belirgin gözler arası asimetri",
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
    "Leave blank for image reading. Enter only when requested or to explicitly correct a reading. Central pachymetry is read only from Pupil Center (+). NICE posterior elevation is read only from the B. Ele.Th box on the BAD Display page.":"Görüntüden okuma için boş bırakın. Yalnızca istendiğinde veya bir okumayı açıkça düzeltmek için girin. Santral pakimetri yalnızca Pupil Center (+) alanından okunur. NICE posterior elevasyonu yalnızca BAD Display sayfasındaki B. Ele.Th kutusundan okunur.",
    "Surgeon-confirmed I-S (D)":"Cerrah tarafından doğrulanan I-S (D)",
    "Surgeon-confirmed Randleman topography category":"Cerrah tarafından doğrulanan Randleman topografi kategorisi",
    "Select only when requested":"Yalnızca istendiğinde seçin",
    "NICE — optional surgeon-confirmed measurements":"NICE — cerrah tarafından doğrulanabilecek isteğe bağlı ölçümler",
    "Central pachymetry (µm)":"Santral pakimetri (µm)","B. Ele.Th (µm; BAD Display)":"B. Ele.Th (µm; BAD Display)",
    "Clinical eligibility and stability":"Klinik uygunluk ve stabilite","Clinical eligibility and stability — reviewed":"Klinik uygunluk ve stabilite — değerlendirildi",
    "Refraction stable?":"Refraksiyon stabil mi?","Documented progression?":"Belgelenmiş progresyon var mı?",
    "Unexplained CDVA <20/20?":"Açıklanamayan EİDGK <20/20 mi?","Enhancement anticipated?":"Ek düzeltme öngörülüyor mu?",
    "Yes":"Evet","No":"Hayır","Unknown":"Bilinmiyor","Select":"Seçin","None":"Yok","Soft":"Yumuşak","Rigid / RGP":"Sert / RGP",
    "Assess images and run CER-AI assessment":"Görüntüleri değerlendir ve CER-AI değerlendirmesini çalıştır",
    "Preoperative manifest refraction is used only for LASIK ERSS MRSE. Intended treatment correction is used for ablation and CER-AI treatment-range gates. Unless a different role-specific value is entered, the treatment card’s Düzeltme Miktarı auto-fills both manifest and intended correction. Every refraction field accepts positive or negative values; use the +/− buttons when a phone keyboard has no sign key. Equivalent plus-cylinder entries are safely transposed to minus-cylinder notation for calculation and disclosed in the report.":"Preoperatif manifest refraksiyon yalnızca LASIK ERSS MRSE için kullanılır. Hedef tedavi düzeltmesi ablasyon ve CER-AI tedavi aralığı geçitlerinde kullanılır. Role özgü farklı bir değer girilmedikçe tedavi kartındaki Düzeltme Miktarı hem manifest hem hedef düzeltmeyi otomatik doldurur. Tüm refraksiyon alanları pozitif veya negatif değer kabul eder; telefon klavyesinde işaret tuşu yoksa +/− düğmelerini kullanın. Eşdeğer artı silindir girişleri hesaplama için güvenle eksi silindir gösterimine transpoze edilir ve raporda belirtilir.",
    "Download PDF":"PDF indir","Download Word":"Word indir","Print report":"Raporu yazdır",
    "CER-AI Clinical Decision Support":"CER-AI Klinik Karar Desteği","PREOPERATIVE ECTASIA RISK ASSESSMENT":"PREOPERATİF EKTAZİ RİSK DEĞERLENDİRMESİ",
    "Corneal refractive surgery assessment report":"Korneal refraktif cerrahi değerlendirme raporu","Eye-specific assessment":"Göze özgü değerlendirme",
    "Patient":"Hasta","Patient ID":"Hasta kimliği","Age":"Yaş","Date":"Tarih","Reviewer":"Değerlendiren","Eyes":"Gözler",
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
    "Selected LASIK plan":"Seçilen LASIK planı","Optical / transition zone":"Optik / geçiş zonu","Tomography review":"Tomografi değerlendirmesi","Morphology category":"Morfoloji kategorisi",
    "Randleman I-S / source":"Randleman I-S / kaynak","Validated Randleman topography":"Doğrulanmış Randleman topografisi","Anterior-map read confidence":"Anterior harita okuma güveni",
    "Parameter":"Parametre","Result":"Sonuç","Value":"Değer","Clinical action:":"Klinik eylem:","Instrument/source:":"Cihaz/kaynak:",
    "NICE component audit":"NICE bileşen denetimi","NICE interpretation note":"NICE yorum notu","Reasons":"Nedenler","Hard stops":"Kesin durdurma nedenleri",
    "Missing / unresolved":"Eksik / çözümlenmemiş","Surgeon attention — hyperopic/mixed pathway":"Cerrahın dikkatine — hipermetropik/karma yol",
    "Tomography concern flags":"Tomografi endişe uyarıları","BAD display interpretation":"BAD ekran yorumu","Surgical-load evidence flags":"Cerrahi yük kanıt uyarıları",
    "Clinical modifiers":"Klinik değiştiriciler","Warnings":"Uyarılar","PRK Mitomycin-C guidance":"PRK Mitomycin-C rehberi","Extracted tomography":"Çıkarılan tomografi verileri",
    "Global clinical / source blockers":"Genel klinik / kaynak engelleri","Post-assessment ML7 microkeratome planning":"Değerlendirme sonrası ML7 mikrokeratom planlaması",
    "PENTACAM ACQUISITION QUALITY — SURGEON ATTENTION":"PENTACAM ÇEKİM KALİTESİ — CERRAHIN DİKKATİNE",
    "Planning warnings":"Planlama uyarıları","Planning notes":"Planlama notları","Assessment gate":"Değerlendirme geçidi","Vacuum ring":"Vakum halkası",
    "Vacuum pressure":"Vakum basıncı","Blade recommendation(s)":"Bıçak önerisi/önerileri","Primary hinge":"Birincil menteşe","Conditional alternative":"Koşullu alternatif","Horizontal white-to-white (HWTW)":"Horizontal white-to-white (HWTW)",
    "Alternative projected RSB / PTA":"Alternatif tahmini RSB / PTA","Alternative safety":"Alternatif güvenliği","Ring-zone clearance":"Halka-zon açıklığı","Source":"Kaynak",
    "Recommendation":"Öneri","Surgeon-review recommendation only; this module does not alter the ectasia disposition.":"Yalnızca cerrah değerlendirme önerisidir; bu modül ektazi kararını değiştirmez.",
    "PASS":"UYGUN","CAUTION":"DİKKAT","STOP-DEFER":"DURDUR-ERTELE",
    "DATA INSUFFICIENT":"VERİ YETERSİZ","ERROR":"HATA","ASSESSING...":"DEĞERLENDİRİLİYOR...",
    "Required information — no report has been generated":"Gerekli bilgiler — henüz rapor oluşturulmadı",
    "PATIENT":"Hasta","Patient age (years)":"Hasta yaşı (yıl)",
    "Intended treatment initially follows manifest refraction. Edit intended values only when the planned treatment differs.":"Hedeflenen tedavi başlangıçta manifest refraksiyonu izler. Yalnızca planlanan tedavi farklıysa hedeflenen değerleri değiştirin.",
    "Complete all items below, then continue. Existing inputs and image readings are retained. No calculation is required from the surgeon.":"Aşağıdaki tüm alanları tamamlayıp devam edin. Mevcut girdiler ve görüntü okumaları korunur. Cerrahın hesaplama yapması gerekmez.",
    "This cannot be completed by typing. Upload a source image that visibly shows QS: OK.":"Bu madde yazılarak tamamlanamaz. QS: OK ifadesini açıkça gösteren kaynak görüntüyü yükleyin.",
    "Explicit Pentacam QS: OK is required from the source image":"Kaynak görüntüde açıkça Pentacam QS: OK bulunması gerekir",
    "Explicitly printed Pentacam QS":"Açıkça basılı Pentacam QS",
    "Replace source images to continue":"Devam etmek için kaynak görüntüleri değiştirin",
    "A clearer/correct Pentacam or topography source image is required":"Daha net/doğru bir Pentacam veya topografi kaynak görüntüsü gereklidir",
    "This cannot be completed by typing. Replace the displayed limited/inadequate source image.":"Bu madde yazılarak tamamlanamaz. Gösterilen sınırlı/yetersiz kaynak görüntüyü değiştirin.",
    "Continue with completed information":"Tamamlanan bilgilerle devam et","Preparing...":"Hazırlanıyor...",
    "Loading unread Pentacam/topography region...":"Pentacam/topografide okunamayan bölge yükleniyor...",
    "Pentacam/topography region the application could not read":"Uygulamanın okuyamadığı Pentacam/topografi bölgesi",
    "The unread source region could not be displayed. Enter the value from the original Pentacam/topography image.":"Okunamayan kaynak bölge gösterilemedi. Değeri özgün Pentacam/topografi görüntüsünden girin.",
    "Eye rubbing / ocular trauma":"Göz ovalama / oküler travma","Family history":"Aile öyküsü","Inter-eye asymmetry":"Gözler arası asimetri",
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
  };
  const CLINICAL = {
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
    "NICE interpretation: no NICE escalation. NICE is an independent screening pathway and is not added to the CER-AI numeric score.":"NICE yorumu: NICE artırımı yoktur. NICE bağımsız bir tarama yoludur ve CER-AI sayısal puanına eklenmez.",
    "CER-AI SCORE — SOURCE & BREAKDOWN: PRK-EWSS v1.0 provisional evidence-weighted triage score (not validated); CER-AI-modified age bands. morphology: +0 (morphology NORMAL_SYMMETRIC); pachymetry: +0 (thinnest pachymetry 560 µm); age: +0 (age 35 years). TOTAL: 0 (LOWER_FLAGGED_BURDEN). Hard stops are independent of this numeric score and are not counted as score points.":"CER-AI PUANI — KAYNAK VE DÖKÜM: PRK-EWSS v1.0 geçici kanıt ağırlıklı triyaj puanı (doğrulanmamıştır); CER-AI'ye uyarlanmış yaş aralıkları. morfoloji: +0 (NORMAL_SİMETRİK); pakimetri: +0 (en ince pakimetri 560 µm); yaş: +0 (35 yaş). TOPLAM: 0 (DÜŞÜK UYARI YÜKÜ). Kesin durdurma kuralları bu sayısal puandan bağımsızdır ve puana eklenmez.",
    "ECTASIA RISK INTERPRETATION: In the cited post-PRK ectasia series with complete ERSS data, 77% of ectasia eyes had cumulative ERSS >=4, 9% had score 3, and 14% had score <=2. The surgical cohort incidence reported in that study was 9/31,045 eyes (0.029%). ABSOLUTE PROBABILITY: Not established for an individual PRK score. LIMITATION: These are distributions among ectasia cases and an overall cohort incidence, not score-specific patient probabilities. The LASIK ERSS is not validated as an absolute-risk calculator for PRK; the 0.029% cohort incidence must not be assigned to an individual score. SOURCE: Risk Assessment for Corneal Ectasia following Photorefractive Keratectomy.":"EKTAZİ RİSK YORUMU: Tam ERSS verisi bulunan atıf yapılan PRK sonrası ektazi serisinde ektazili gözlerin %77'sinde toplam ERSS ≥4, %9'unda puan 3 ve %14'ünde puan ≤2 idi. Çalışmadaki cerrahi kohort insidansı 9/31.045 göz (%0,029) olarak bildirildi. MUTLAK OLASILIK: Tek bir PRK puanı için belirlenmemiştir. SINIRLAMA: Bunlar ektazi vakaları arasındaki dağılımlar ve genel kohort insidansıdır; puana özgü hasta olasılıkları değildir. LASIK ERSS, PRK için mutlak risk hesaplayıcısı olarak doğrulanmamıştır; %0,029 kohort insidansı bireysel bir puana atanamaz. KAYNAK: Fotorefraktif keratektomi sonrası korneal ektazi risk değerlendirmesi."
  };
  const translate = value => {
    const text = String(value ?? "");
    if (locale !== "tr" || !text) return text;
    if (CLINICAL[text]) return CLINICAL[text];
    if (TR[text]) return TR[text];
    return text
      .replace(/^CER-AI SCORE — SOURCE & BREAKDOWN:/,"CER-AI PUANI — KAYNAK VE DÖKÜM:")
      .replace(/^ECTASIA RISK INTERPRETATION:/,"EKTAZİ RİSK YORUMU:")
      .replace(/^ABSOLUTE PROBABILITY:/,"MUTLAK OLASILIK:")
      .replace(/^LIMITATION:/,"SINIRLAMA:")
      .replace(/^Inter-eye tomography concern:/,"Gözler arası tomografi değerlendirmesi:")
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
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes=[]; while(walker.nextNode()) nodes.push(walker.currentNode);
    for(const node of nodes){
      if(node.parentElement?.closest("script,style,pre")) continue;
      const raw=node.nodeValue, trimmed=raw.trim(); if(!trimmed)continue;
      const translated=translate(trimmed); if(translated!==trimmed)node.nodeValue=raw.replace(trimmed,translated);
    }
    root.querySelectorAll?.("[aria-label],[title],[placeholder]").forEach(el=>{
      for(const attr of ["aria-label","title","placeholder"]){const raw=el.getAttribute(attr);if(raw)el.setAttribute(attr,translate(raw));}
    });
  };
  const setLocale = next => { localStorage.setItem("cerai-language", next === "tr" ? "tr" : "en"); location.reload(); };
  window.CERAI_I18N={locale,translate,clinical:translate,translateDOM,setLocale};
  document.documentElement.lang=locale;
})();
