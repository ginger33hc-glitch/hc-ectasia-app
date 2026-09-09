/* CER-AI public website bilingual presentation layer. Clinical logic is untouched. */
(() => {
  const STORAGE_KEY = "cerai-public-language";
  const SUPPORTED = new Set(["en", "tr"]);
  const requested = (localStorage.getItem(STORAGE_KEY) || "en").toLowerCase();
  let locale = SUPPORTED.has(requested) ? requested : "en";

  const TR = {
    "Learning Center":"Eğitim Merkezi",
    "Evaluation":"Değerlendirme",
    "Ectasia Assessment":"Ektazi Değerlendirmesi",
    "User Guide":"Kullanım Kılavuzu",
    "Clinical Evidence":"Klinik Kanıtlar",
    "About":"Hakkında",
    "Developer":"Geliştirici",
    "Access CER-AI":"CER-AI'ye Eriş",
    "Clinical decision support for refractive surgery":"Refraktif cerrahi için klinik karar desteği",
    "Corneal Ectasia Risk Assessment Intelligence":"Kornea Ektazi Riski Değerlendirmesinde Yapay Zeka",
    "CER-AI — Corneal Ectasia Risk Assessment Intelligence":"CER-AI — Kornea Ektazi Riski Değerlendirmesinde Yapay Zeka",
    "Structured preoperative ectasia risk assessment combining independent ectasia-risk pathways, Pentacam-derived data, tissue-safety calculations, and procedure-specific safeguards.":"Bağımsız ektazi risk yollarını, Pentacam verilerini, doku güvenliği hesaplamalarını ve prosedüre özgü güvenlik önlemlerini birleştiren yapılandırılmış preoperatif ektazi risk değerlendirmesi.",
    "Designed to make refractive-surgery screening more structured, transparent, and reproducible without replacing surgeon judgment.":"Cerrahın klinik değerlendirmesinin yerini almadan refraktif cerrahi taramasını daha yapılandırılmış, şeffaf ve tekrarlanabilir hale getirmek için tasarlanmıştır.",
    "Evaluation Framework":"Değerlendirme Çerçevesi",
    "A structured, multi-system approach":"Yapılandırılmış, çok sistemli yaklaşım",
    "CER-AI keeps major assessment pathways independent, identifies missing or conflicting information, and documents the reasoning behind the final assessment.":"CER-AI temel değerlendirme yollarını birbirinden bağımsız tutar, eksik veya çelişkili bilgileri belirler ve nihai değerlendirmenin gerekçesini belgeler.",
    "Tissue Safety":"Doku Güvenliği",
    "Ectasia-risk evaluation":"Ektazi risk değerlendirmesi",
    "Multiple independent assessment pathways":"Birden fazla bağımsız değerlendirme yolu",
    "CER-AI does not blend the major ectasia-risk systems into one proprietary score. Each pathway is evaluated independently, with its own inputs, interpretation, and procedural consequence.":"CER-AI temel ektazi risk sistemlerini tek bir özel puanda birleştirmez. Her yol kendi girdileri, yorumu ve prosedürel sonucu ile bağımsız olarak değerlendirilir.",
    "Established clinical risk profile":"Yerleşik klinik risk profili",
    "Evaluates age, pachymetry, refractive magnitude, residual stromal bed, and anterior topographic evidence.":"Yaş, pakimetri, refraktif büyüklük, rezidüel stromal yatak ve anterior topografik bulguları değerlendirir.",
    "Component scoring remains visible.":"Bileşen puanlaması görünür kalır.",
    "Topography evidence remains source-tracked.":"Topografi bulgularının kaynağı izlenebilir kalır.",
    "ERSS stays independent from tomography systems.":"ERSS tomografi sistemlerinden bağımsız kalır.",
    "Independent tomographic signal":"Bağımsız tomografik sinyal",
    "Final BAD-D is interpreted as its own Pentacam-derived risk channel.":"Final BAD-D, Pentacam kaynaklı bağımsız bir risk kanalı olarak yorumlanır.",
    "Final value and class are displayed directly.":"Final değer ve sınıf doğrudan gösterilir.",
    "Subcomponents remain supporting context.":"Alt bileşenler destekleyici bağlam olarak tutulur.",
    "Abnormality can independently change disposition.":"Anormallik nihai kararı bağımsız olarak değiştirebilir.",
    "Structured tomography pathway":"Yapılandırılmış tomografi yolu",
    "NICE is evaluated independently using required tomographic inputs and a component audit.":"NICE, gerekli tomografik girdiler ve bileşen denetimi kullanılarak bağımsız şekilde değerlendirilir.",
    "Each component and source is retained.":"Her bileşen ve kaynağı korunur.",
    "Missing information is identified.":"Eksik bilgiler belirlenir.",
    "No mathematical blending with ERSS or BAD-D.":"ERSS veya BAD-D ile matematiksel birleştirme yapılmaz.",
    "Procedure-aware risk channel":"Prosedüre duyarlı risk kanalı",
    "PS3 adds independent review of selected corneal, refractive, tomographic, and inter-eye findings.":"PS3 seçilmiş korneal, refraktif, tomografik ve gözler arası bulguların bağımsız değerlendirmesini ekler.",
    "Moderate and High criteria are shown individually.":"Orta ve Yüksek kriterler ayrı ayrı gösterilir.",
    "Triggered factors are documented.":"Tetiklenen faktörler belgelenir.",
    "LASIK, PRK, and SMILE consequences remain explicit.":"LASIK, PRK ve SMILE sonuçları açık şekilde gösterilir.",
    "Separate from ectasia scoring:":"Ektazi puanlamasından ayrı olarak:",
    "CER-AI also evaluates tissue and procedural safety. A reassuring ectasia score does not override a separate safety stop.":"CER-AI ayrıca doku ve prosedür güvenliğini değerlendirir. Güven verici bir ektazi puanı ayrı bir güvenlik durdurma kriterini geçersiz kılmaz.",
    "Clinical architecture":"Klinik mimari",
    "How CER-AI Works":"CER-AI Nasıl Çalışır",
    "The platform separates risk assessment, data integrity, and procedure safety so that the final recommendation remains auditable.":"Platform risk değerlendirmesini, veri bütünlüğünü ve prosedür güvenliğini birbirinden ayırarak nihai önerinin denetlenebilir kalmasını sağlar.",
    "Independent Risk Pathways":"Bağımsız Risk Yolları",
    "ERSS, Final BAD-D, NICE, and PS3 remain independently interpretable.":"ERSS, Final BAD-D, NICE ve PS3 bağımsız olarak yorumlanabilir kalır.",
    "Pentacam-Based Structure":"Pentacam Tabanlı Yapı",
    "Important measurements are linked to defined Pentacam source fields.":"Önemli ölçümler tanımlanmış Pentacam kaynak alanlarına bağlanır.",
    "Safety Calculations":"Güvenlik Hesaplamaları",
    "Tissue and procedure-specific constraints are evaluated separately.":"Doku ve prosedüre özgü kısıtlamalar ayrı değerlendirilir.",
    "Transparent Reporting":"Şeffaf Raporlama",
    "Missing, conflicting, and surgeon-confirmed information remains visible.":"Eksik, çelişkili ve cerrah tarafından doğrulanmış bilgiler görünür kalır.",
    "Using CER-AI":"CER-AI Kullanımı",
    "A practical workflow for qualified ophthalmic professionals using the clinical application.":"Klinik uygulamayı kullanan yetkin göz hekimleri için pratik bir iş akışı.",
    "Enter the clinical application":"Klinik uygulamaya girin",
    "Select Access CER-AI and enter the authorized doctor name in the current supervised trial login flow.":"CER-AI'ye Eriş seçeneğini seçin ve mevcut kontrollü deneme girişinde yetkili doktor adını girin.",
    "Complete case information":"Vaka bilgilerini tamamlayın",
    "Enter patient identification, age, planned procedure, refraction, treatment parameters, and clinical modifiers.":"Hasta kimliği, yaş, planlanan prosedür, refraksiyon, tedavi parametreleri ve klinik değiştiricileri girin.",
    "Upload Pentacam material":"Pentacam materyalini yükleyin",
    "Upload required Pentacam screenshots or source images. CER-AI retains source provenance.":"Gerekli Pentacam ekran görüntülerini veya kaynak görselleri yükleyin. CER-AI kaynak bilgisini korur.",
    "Resolve unread or conflicting fields":"Okunamayan veya çelişkili alanları çözün",
    "Decision-critical missing or conflicting data are completed or surgeon-confirmed rather than silently estimated.":"Kararı etkileyen eksik veya çelişkili veriler sessizce tahmin edilmek yerine tamamlanır veya cerrah tarafından doğrulanır.",
    "Review independent risk systems":"Bağımsız risk sistemlerini inceleyin",
    "Review ERSS, Final BAD-D, NICE, PS3, and procedure safety separately.":"ERSS, Final BAD-D, NICE, PS3 ve prosedür güvenliğini ayrı ayrı inceleyin.",
    "Review and save the report":"Raporu inceleyin ve kaydedin",
    "Confirm disposition, procedure implications, warnings, and planning information before export or archive.":"Dışa aktarma veya arşivleme öncesinde nihai kararı, prosedür sonuçlarını, uyarıları ve planlama bilgilerini doğrulayın.",
    "Clinical use:":"Klinik kullanım:",
    "CER-AI is a decision-support system and does not replace examination, image-quality review, clinical judgment, or surgeon responsibility.":"CER-AI bir karar destek sistemidir; muayenenin, görüntü kalitesi değerlendirmesinin, klinik muhakemenin veya cerrah sorumluluğunun yerini almaz.",
    "Open Clinical Application":"Klinik Uygulamayı Aç",
    "About CER-AI":"CER-AI Hakkında",
    "One auditable clinical decision-support platform":"Denetlenebilir tek klinik karar destek platformu",
    "CER-AI integrates independent risk systems, canonical Pentacam data, tissue calculations, surgical eligibility, reporting, and planning support.":"CER-AI bağımsız risk sistemlerini, kanonik Pentacam verilerini, doku hesaplamalarını, cerrahi uygunluğu, raporlamayı ve planlama desteğini birleştirir.",
    "Developer and Clinical Lead":"Geliştirici ve Klinik Lider",
    "Ophthalmic Surgeon · Developer of CER-AI":"Göz Cerrahı · CER-AI Geliştiricisi",
    "Approximately 30 years of clinical and surgical ophthalmology experience":"Yaklaşık 30 yıllık klinik ve cerrahi oftalmoloji deneyimi",
    "Refractive · Cataract · Vitreoretinal Surgery":"Refraktif · Katarakt · Vitreoretinal Cerrahi",
    "Founder, Vision Eye Hospital":"Kurucu, Vision Eye Hospital",
    "Founder’s Note":"Kurucunun Notu",
    "After more than thirty years of surgical and administrative experience, I wanted to find a way to pass some of that accumulated knowledge on to the generations that follow.":"Otuz yılı aşkın cerrahi ve idari deneyimden sonra, biriktirdiğim bilgi ve deneyimin bir bölümünü benden sonraki kuşaklara aktarabilmenin bir yolunu bulmak istedim.",
    "As a refractive surgeon, one of the complications we fear most is corneal ectasia. My aim was to develop a system that could help identify ectasia susceptibility more reliably before surgery and, ultimately, help protect patients from an avoidable complication. With the rapid development of artificial intelligence, I decided to combine established clinical evidence, modern imaging data, and my own surgical experience into a structured clinical decision-support platform.":"Bir refraktif cerrah olarak en çok çekindiğimiz komplikasyonlardan biri korneal ektazidir. Amacım, cerrahi öncesinde ektazi yatkınlığını daha güvenilir biçimde belirlemeye yardımcı olabilecek ve sonuçta hastaları önlenebilir bir komplikasyondan korumaya katkı sağlayabilecek bir sistem geliştirmekti. Yapay zekânın hızlı gelişimiyle birlikte, yerleşik klinik kanıtları, modern görüntüleme verilerini ve kendi cerrahi deneyimimi yapılandırılmış bir klinik karar destek platformunda birleştirmeye karar verdim.",
    "CER-AI — Corneal Ectasia Risk Assessment Intelligence — is the single current product name used throughout the platform.":"CER-AI — Corneal Ectasia Risk Assessment Intelligence, platform genelinde kullanılan tek güncel ürün adıdır.",
    "The software developed progressively through versions 0.1, 0.2, 0.3 and subsequent iterations, reaching version":"Yazılım 0.1, 0.2, 0.3 sürümleri ve sonraki geliştirmelerle aşamalı olarak ilerledi; bu metnin yazıldığı sırada",
    "at the time of writing. It is under continuous development, so by the time you read this, a newer version may already be in use.":"sürümüne ulaştı. Geliştirme sürekli devam ettiği için siz bunu okurken daha yeni bir sürüm kullanımda olabilir.",
    "During its development, I conducted an extensive review of the medical literature related to corneal ectasia, keratoconus susceptibility, refractive-surgery screening, corneal tomography, topography, biomechanics, and tissue safety. I combined this evidence with practical surgical experience to bring several different ectasia-risk assessment systems together within a single framework.":"Geliştirme sürecinde korneal ektazi, keratokonus yatkınlığı, refraktif cerrahi taraması, kornea tomografisi, topografi, biyomekanik ve doku güvenliğiyle ilgili tıbbi literatürü kapsamlı biçimde gözden geçirdim. Bu kanıtları pratik cerrahi deneyimle birleştirerek farklı ektazi risk değerlendirme sistemlerini tek bir çerçeve içinde bir araya getirdim.",
    "A central principle of CER-AI is that these systems remain":"CER-AI'nin temel ilkelerinden biri, bu sistemlerin",
    "independent from one another":"birbirinden bağımsız kalmasıdır",
    "Rather than blending them into a single opaque score, each pathway evaluates the case separately so that the surgeon can see where agreement or disagreement exists between different risk-assessment approaches.":"Bunları tek ve şeffaf olmayan bir puanda birleştirmek yerine, her değerlendirme yolu vakayı ayrı olarak inceler; böylece cerrah farklı risk değerlendirme yaklaşımlarının nerede uyumlu, nerede farklı sonuç verdiğini görebilir.",
    "The primary purpose of CER-AI is not to make the surgical decision on behalf of the physician. It is designed to":"CER-AI'nin temel amacı hekimin yerine cerrahi karar vermek değildir. Sistem;",
    "support the physician’s decision-making":"hekimin karar verme sürecini desteklemek",
    "to organize complex preoperative information, and most importantly, to help identify a finding that may otherwise have been overlooked.":"karmaşık preoperatif bilgiyi düzenlemek ve en önemlisi gözden kaçabilecek bir bulgunun fark edilmesine yardımcı olmak üzere tasarlanmıştır.",
    "To younger colleagues in particular, I would like to emphasize a principle that has guided me throughout my surgical career:":"Özellikle genç meslektaşlarıma, cerrahi kariyerim boyunca bana yol gösteren şu ilkeyi vurgulamak isterim:",
    "Whatever the procedure, our first responsibility is to avoid harming the patient.":"Hangi işlemi yaparsak yapalım, ilk sorumluluğumuz hastaya zarar vermemektir.",
    "Technology, imaging, scoring systems, and artificial intelligence can assist us, but they should always serve that fundamental clinical responsibility.":"Teknoloji, görüntüleme, puanlama sistemleri ve yapay zekâ bize yardımcı olabilir; ancak bunların tümü her zaman bu temel klinik sorumluluğa hizmet etmelidir.",
    "Clinical philosophy":"Klinik yaklaşım",
    "Artificial intelligence should support clinical judgment, not replace it.":"Yapay zekâ klinik muhakemeyi desteklemeli, onun yerini almamalıdır.",
    "CER-AI organizes and cross-checks clinical information, applies predefined safety rules, and documents the reasoning behind an assessment. The final surgical decision always remains with the surgeon.":"CER-AI klinik bilgileri düzenler ve çapraz kontrol eder, önceden tanımlanmış güvenlik kurallarını uygular ve değerlendirmenin gerekçesini belgeler. Nihai cerrahi karar her zaman cerraha aittir.",
    "For ophthalmic surgeons":"Göz cerrahları için",
    "Open the secure clinical application to begin a CER-AI assessment.":"CER-AI değerlendirmesine başlamak için güvenli klinik uygulamayı açın.",
    "Developed by Hüseyin Cengiz, M.D.":"Hüseyin Cengiz, M.D. tarafından geliştirilmiştir.",
    "All rights reserved.":"Tüm hakları saklıdır.",
    "Final responsibility always belongs to the surgeon.":"Nihai sorumluluk her zaman cerraha aittir.",
    "Scientific foundation":"Bilimsel temel",
    "Medical References":"Tıbbi Kaynaklar",
    "Review the consolidated medical literature discussed and used across CER-AI development, including ERSS, NICE, PS3, BAD-D, Pentacam tomography, PRFI, PTA, RTA, SCORE, biomechanical safety and postoperative ectasia literature.":"CER-AI geliştirme sürecinde tartışılan ve kullanılan ERSS, NICE, PS3, BAD-D, Pentacam tomografisi, PRFI, PTA, RTA, SCORE, biyomekanik güvenlik ve postoperatif ektazi literatürü dahil olmak üzere birleştirilmiş tıbbi literatürü inceleyin.",
    "View the CER-AI reference registry":"CER-AI kaynak kayıtlarını görüntüleyin",
    "The registry is searchable by author, title, journal, DOI and clinical topic.":"Kayıtlar yazar, başlık, dergi, DOI ve klinik konuya göre aranabilir.",
    "Open References":"Kaynakları Aç",
    "Professional clinical decision support":"Profesyonel klinik karar desteği",
    "Corneal Ectasia Risk Assessment Software for Refractive Surgeons | CER-AI":"Refraktif Cerrahlar İçin Korneal Ektazi Risk Değerlendirme Yazılımı | CER-AI",
    "Corneal ectasia risk assessment software for refractive surgeons":"Refraktif cerrahlar için korneal ektazi risk değerlendirme yazılımı",
    "CER-AI is a web-based clinical decision-support platform that structures preoperative corneal ectasia risk assessment before procedures such as LASIK and PRK.":"CER-AI, LASIK ve PRK gibi işlemler öncesinde preoperatif korneal ektazi risk değerlendirmesini yapılandıran web tabanlı bir klinik karar destek platformudur.",
    "Corneal ectasia risk assessment before refractive surgery":"Refraktif cerrahi öncesi korneal ektazi risk değerlendirmesi",
    "CER-AI is a web-based clinical decision-support platform designed to structure preoperative assessment of corneal ectasia risk before procedures such as LASIK and PRK.":"CER-AI, LASIK ve PRK gibi işlemler öncesinde korneal ektazi riskinin preoperatif değerlendirmesini yapılandırmak için tasarlanmış web tabanlı bir klinik karar destek platformudur.",
    "What CER-AI is:":"CER-AI nedir:",
    "a structured, auditable assessment environment that keeps major ectasia-risk pathways independently interpretable while also checking procedure-specific tissue safety. It is not an autonomous diagnostic system and does not replace surgeon judgment.":"Temel ektazi risk yollarını bağımsız olarak yorumlanabilir tutarken prosedüre özgü doku güvenliğini de kontrol eden yapılandırılmış ve denetlenebilir bir değerlendirme ortamıdır. Otonom bir tanı sistemi değildir ve cerrahın klinik değerlendirmesinin yerini almaz.",
    "Clinical problem addressed":"Ele alınan klinik sorun",
    "Postoperative corneal ectasia is a major safety concern in corneal refractive surgery. Preoperative screening therefore examines multiple domains rather than relying on a single measurement. These domains can include anterior corneal topography, corneal tomography, pachymetry, refractive magnitude, age, residual stromal bed and other procedure-specific factors.":"Postoperatif korneal ektazi, korneal refraktif cerrahide önemli bir güvenlik sorunudur. Bu nedenle preoperatif tarama tek bir ölçüme dayanmak yerine birden fazla alanı değerlendirir. Bunlar anterior kornea topografisi, kornea tomografisi, pakimetri, refraktif büyüklük, yaş, rezidüel stromal yatak ve prosedüre özgü diğer faktörleri içerebilir.",
    "Risk pathways represented in CER-AI":"CER-AI'de yer alan risk yolları",
    "The Randleman Ectasia Risk Score System is represented as an independent clinical risk pathway using its defined component structure and anterior-topography evidence.":"Randleman Ektazi Risk Skor Sistemi, tanımlı bileşen yapısı ve anterior topografi bulguları kullanılarak bağımsız bir klinik risk yolu olarak değerlendirilir.",
    "Pentacam Belin/Ambrosio Final BAD-D is treated as an independent tomographic signal rather than being mathematically blended into ERSS.":"Pentacam Belin/Ambrosio Final BAD-D, ERSS ile matematiksel olarak birleştirilmek yerine bağımsız bir tomografik sinyal olarak değerlendirilir.",
    "The NICE pathway is evaluated separately using the required corneal tomography inputs and an auditable component assessment.":"NICE yolu gerekli kornea tomografi girdileri ve denetlenebilir bileşen değerlendirmesi kullanılarak ayrı değerlendirilir.",
    "PS3 adds another independently visible risk pathway with procedure-aware interpretation of selected corneal, refractive and inter-eye findings.":"PS3 seçilmiş korneal, refraktif ve gözler arası bulguların prosedüre duyarlı yorumunu içeren ayrı ve görünür bir risk yolu ekler.",
    "Pentacam and corneal imaging concepts":"Pentacam ve kornea görüntüleme kavramları",
    "CER-AI is designed around structured interpretation of Pentacam-derived corneal information. Relevant search concepts include corneal topography, corneal tomography, keratoconus screening, ectasia susceptibility, Belin/Ambrosio Enhanced Ectasia Display, Final BAD-D, pachymetry, topometric indices, anterior and posterior elevation, and inter-eye asymmetry.":"CER-AI, Pentacam kaynaklı korneal bilgilerin yapılandırılmış yorumlanması üzerine tasarlanmıştır. İlgili kavramlar kornea topografisi, kornea tomografisi, keratokonus taraması, ektazi yatkınlığı, Belin/Ambrosio Enhanced Ectasia Display, Final BAD-D, pakimetri, topometrik indeksler, anterior ve posterior elevasyon ve gözler arası asimetriyi içerir.",
    "Tissue-safety assessment remains separate":"Doku güvenliği değerlendirmesi ayrı kalır",
    "A reassuring ectasia-risk pathway does not automatically establish procedural safety. CER-AI separately evaluates treatment-related tissue constraints, including pachymetry, anticipated ablation, residual stromal bed or residual stromal tissue, planned refractive correction and postoperative keratometric safety.":"Güven verici bir ektazi risk yolu prosedür güvenliğini otomatik olarak kanıtlamaz. CER-AI pakimetri, beklenen ablasyon, rezidüel stromal yatak veya rezidüel stromal doku, planlanan refraktif düzeltme ve postoperatif keratometrik güvenlik dahil tedaviye bağlı doku kısıtlamalarını ayrıca değerlendirir.",
    "Why the pathways remain independent":"Risk yolları neden bağımsız kalır",
    "Independent presentation makes disagreement between risk systems visible. It also allows the clinician to identify which observation or missing input is responsible for a caution or stop decision instead of receiving only a single opaque composite score.":"Bağımsız sunum, risk sistemleri arasındaki uyumsuzluğu görünür kılar. Ayrıca klinisyenin yalnızca tek ve şeffaf olmayan birleşik bir puan almak yerine hangi bulgunun veya eksik girdinin dikkat ya da durdurma kararına yol açtığını belirlemesini sağlar.",
    "Frequently asked questions about CER-AI":"CER-AI hakkında sık sorulan sorular",
    "Is CER-AI a single corneal ectasia score?":"CER-AI tek bir korneal ektazi skoru mudur?",
    "No. CER-AI keeps ERSS, BAD-D, NICE and PS3 independently visible and separately interpretable. Tissue and procedure-safety calculations are also presented separately rather than being hidden inside one proprietary score.":"Hayır. CER-AI; ERSS, BAD-D, NICE ve PS3'ü bağımsız olarak görünür ve ayrı ayrı yorumlanabilir tutar. Doku ve prosedür güvenliği hesaplamaları da tek bir özel skor içinde gizlenmek yerine ayrı olarak sunulur.",
    "Which Pentacam images does a CER-AI assessment require?":"Bir CER-AI değerlendirmesi hangi Pentacam görüntülerini gerektirir?",
    "The current bilateral workflow requires five Pentacam sources: 4 Maps Refractive for OD and OS, Belin/Ambrósio BAD Display for OD and OS, and one Show 2 Exams Topometric comparison. A treatment card is optional; when it is absent or unreadable, the surgeon supplies the required manifest and intended refraction.":"Mevcut bilateral iş akışı beş Pentacam kaynağı gerektirir: OD ve OS için 4 Maps Refractive, OD ve OS için Belin/Ambrósio BAD Display ve bir Show 2 Exams Topometric karşılaştırması. Tedavi kartı isteğe bağlıdır; kart yoksa veya okunamıyorsa gerekli manifest ve hedef refraksiyon değerlerini cerrah girer.",
    "Who is CER-AI designed for?":"CER-AI kimler için tasarlanmıştır?",
    "CER-AI is intended for qualified ophthalmologists and refractive surgeons performing structured preoperative screening. It is not a patient self-assessment tool.":"CER-AI, yapılandırılmış preoperatif tarama yapan yetkin göz hekimleri ve refraktif cerrahlar için tasarlanmıştır. Hastaların kendi kendine değerlendirme yapacağı bir araç değildir.",
    "How does CER-AI handle missing or unreadable information?":"CER-AI eksik veya okunamayan bilgileri nasıl ele alır?",
    "Decision-critical values remain linked to defined source fields. When a required value cannot be obtained reliably, the workflow identifies the missing field for surgeon completion instead of silently inventing a value.":"Kararı etkileyen değerler tanımlanmış kaynak alanlarıyla bağlantılı kalır. Gerekli bir değer güvenilir biçimde elde edilemezse iş akışı sessizce değer üretmek yerine cerrahın tamamlaması gereken eksik alanı belirtir.",
    "Does CER-AI decide whether surgery should be performed?":"CER-AI ameliyat yapılıp yapılmayacağına karar verir mi?",
    "No. CER-AI organizes evidence, applies predefined assessment and safety rules, and documents the reasoning. The final clinical and surgical decision remains the surgeon's responsibility.":"Hayır. CER-AI kanıtları düzenler, önceden tanımlanmış değerlendirme ve güvenlik kurallarını uygular ve gerekçeyi belgeler. Nihai klinik ve cerrahi karar cerrahın sorumluluğunda kalır.",
    "Has the complete CER-AI software been externally validated?":"CER-AI yazılımının tamamı dışarıdan doğrulanmış mıdır?",
    "The public evidence pages identify literature supporting individual clinical concepts and risk pathways. Those publications do not constitute external validation of CER-AI as a complete software product. CER-AI does not claim validated diagnostic sensitivity, specificity or superiority unless supporting CER-AI-specific evidence is explicitly published.":"Kamuya açık kanıt sayfaları, ayrı klinik kavramları ve risk yollarını destekleyen literatürü belirtir. Bu yayınlar, CER-AI'nin eksiksiz bir yazılım ürünü olarak dış doğrulaması anlamına gelmez. CER-AI'ye özgü destekleyici kanıt açıkça yayımlanmadıkça doğrulanmış tanısal duyarlılık, özgüllük veya üstünlük iddiasında bulunulmaz.",
    "Review the":"İnceleyin:",
    "clinical evidence mapped to CER-AI":"CER-AI ile eşleştirilmiş klinik kanıtlar",
    "and the":"ve",
    "complete medical reference registry":"eksiksiz tıbbi kaynak kaydı",
    "Clinical author and reviewer:":"Klinik yazar ve gözden geçiren:",
    "Ophthalmic Surgeon and Developer of CER-AI":"Göz Cerrahı ve CER-AI Geliştiricisi",
    "Last reviewed:":"Son gözden geçirme:",
    "September 8, 2026":"8 Eylül 2026",
    "Software version:":"Yazılım sürümü:",
    "Search terminology associated with CER-AI":"CER-AI ile ilişkili arama terimleri",
    "Clinical-use notice:":"Klinik kullanım uyarısı:",
    "CER-AI provides decision support for qualified ophthalmic professionals. Public website content is educational and descriptive; it is not patient-specific medical advice and should not be interpreted as a claim of validated diagnostic performance unless the relevant evidence is explicitly cited.":"CER-AI yetkin göz hekimleri için karar desteği sağlar. Kamuya açık web sitesi içeriği eğitsel ve açıklayıcıdır; hastaya özel tıbbi öneri değildir ve ilgili kanıt açıkça belirtilmedikçe doğrulanmış tanısal performans iddiası olarak yorumlanmamalıdır.",
    "Return to CER-AI home":"CER-AI ana sayfasına dön"
  };

  const originals = new WeakMap();
  const attrOriginals = new WeakMap();

  function translateText(text) {
    const trimmed = text.trim();
    if (!trimmed) return text;
    const translated = TR[trimmed];
    if (!translated) return text;
    const left = text.slice(0, text.indexOf(trimmed));
    const right = text.slice(text.indexOf(trimmed) + trimmed.length);
    return left + translated + right;
  }

  function applyToNode(root) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        const parent = node.parentElement;
        if (!parent || ["SCRIPT", "STYLE", "NOSCRIPT"].includes(parent.tagName)) return NodeFilter.FILTER_REJECT;
        return node.nodeValue.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      }
    });
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    for (const node of nodes) {
      if (!originals.has(node)) originals.set(node, node.nodeValue);
      node.nodeValue = locale === "tr" ? translateText(originals.get(node)) : originals.get(node);
    }

    root.querySelectorAll?.("[title],[aria-label],[placeholder]").forEach(el => {
      if (!attrOriginals.has(el)) {
        attrOriginals.set(el, {
          title: el.getAttribute("title"),
          ariaLabel: el.getAttribute("aria-label"),
          placeholder: el.getAttribute("placeholder")
        });
      }
      const orig = attrOriginals.get(el);
      for (const [attr, key] of [["title","title"],["aria-label","ariaLabel"],["placeholder","placeholder"]]) {
        const value = orig[key];
        if (value !== null) el.setAttribute(attr, locale === "tr" ? (TR[value] || value) : value);
      }
    });

    document.documentElement.lang = locale;
    const titleEn = document.documentElement.dataset.titleEn || document.title;
    document.documentElement.dataset.titleEn = titleEn;
    if (locale === "tr") {
      document.title = TR[titleEn] || titleEn
        .replace("Corneal Ectasia Risk Assessment", "Kornea Ektazi Risk Değerlendirmesi")
        .replace("Clinical Evidence", "Klinik Kanıtlar")
        .replace("References", "Kaynaklar");
    } else document.title = titleEn;
  }

  function renderSwitcher() {
    if (document.getElementById("cerai-public-language")) return;
    const box = document.createElement("div");
    box.id = "cerai-public-language";
    box.setAttribute("aria-label", "Language");
    box.innerHTML = '<button type="button" data-lang="en">EN</button><span>|</span><button type="button" data-lang="tr">TR</button>';
    Object.assign(box.style, {
      position:"fixed", top:"12px", right:"14px", zIndex:"9999", display:"flex", gap:"7px", alignItems:"center",
      padding:"6px 9px", borderRadius:"8px", background:"rgba(5,9,13,.92)", color:"#d7e2eb", border:"1px solid #40515f",
      font:"700 12px Arial,Helvetica,sans-serif", boxShadow:"0 3px 14px rgba(0,0,0,.16)"
    });
    box.querySelectorAll("button").forEach(btn => {
      Object.assign(btn.style, {border:"0", background:"transparent", color:"inherit", cursor:"pointer", font:"inherit", padding:"2px"});
      btn.addEventListener("click", () => setLocale(btn.dataset.lang));
    });
    document.body.appendChild(box);
    updateSwitcher();
  }

  function updateSwitcher() {
    document.querySelectorAll("#cerai-public-language button").forEach(btn => {
      btn.style.textDecoration = btn.dataset.lang === locale ? "underline" : "none";
      btn.style.color = btn.dataset.lang === locale ? "#ffffff" : "#9fb0bd";
      btn.setAttribute("aria-pressed", btn.dataset.lang === locale ? "true" : "false");
    });
  }

  function routeLearningCenterLinks() {
    document.querySelectorAll('a[href="/learning-center"],a[href="/tr/learning-center"]').forEach(link => {
      const label = (link.textContent || "").trim();
      if (label === "Learning Center" || label === "Eğitim Merkezi") {
        link.setAttribute("href", locale === "tr" ? "/tr/learning-center" : "/learning-center");
      }
    });
  }

  function setLocale(next) {
    locale = next === "tr" ? "tr" : "en";
    localStorage.setItem(STORAGE_KEY, locale);
    applyToNode(document.body);
    routeLearningCenterLinks();
    updateSwitcher();
  }

  function init() {
    renderSwitcher();
    applyToNode(document.body);
    routeLearningCenterLinks();
    const observer = new MutationObserver(mutations => {
      for (const mutation of mutations) {
        mutation.addedNodes.forEach(node => {
          if (node.nodeType === Node.ELEMENT_NODE) applyToNode(node);
        });
      }
    });
    observer.observe(document.body, {childList:true, subtree:true});
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, {once:true});
  else init();
})();
