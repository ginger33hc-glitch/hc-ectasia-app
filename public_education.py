"""Presentation-only content for the public CER-AI Learning Center.

This module contains no patient inputs, clinical scoring, extraction, safety,
planning, report, authentication, or archive behavior.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from html import escape


@dataclass(frozen=True)
class Topic:
    slug: str
    title: str
    description: str
    eyebrow: str
    sections: tuple[tuple[str, str], ...]
    references: tuple[tuple[str, str], ...]


TOPICS = (
    Topic(
        "corneal-ectasia-basics",
        "Corneal ectasia: clinical foundations",
        "A surgeon-focused introduction to corneal ectasia, susceptibility, postoperative ectasia, and the role of preoperative screening.",
        "Foundation module",
        (
            ("What corneal ectasia means", "Corneal ectasia describes progressive loss of corneal shape and optical regularity associated with structural weakening. Clinical findings can include localized steepening, thinning, irregular astigmatism, and reduced corrected visual quality. Keratoconus is a primary ectatic disorder; postoperative ectasia is a distinct clinical context that may become evident after corneal refractive surgery."),
            ("Susceptibility is not the same as diagnosis", "Preoperative screening asks whether available history, examination, topography, tomography, and procedure-related factors suggest vulnerability. A susceptibility signal is not automatically a diagnosis of keratoconus, and a normal-looking single metric cannot exclude all risk. The evidence must be interpreted as a pattern and in clinical context."),
            ("Why multimodal screening matters", "Published postoperative cases show that no single variable captures every pathway to ectasia. Anterior curvature patterns, pachymetric distribution, posterior-surface information, age, refractive magnitude, and planned tissue alteration answer different questions. Discordance between these channels is itself information that deserves review."),
            ("What this module does not do", "This page teaches terminology and reasoning. It does not diagnose an individual eye, calculate a patient-specific probability, or determine surgical eligibility. Longitudinal change, image quality, contact-lens history, ocular examination, and surgeon judgment remain essential."),
        ),
        (
            ("Randleman et al., Ophthalmology 2008", "https://pubmed.ncbi.nlm.nih.gov/17624434/"),
            ("Moshirfar et al., Ophthalmology and Therapy 2021", "https://doi.org/10.1007/s40123-021-00383-w"),
            ("Rabinowitz, Survey of Ophthalmology 1998", "https://doi.org/10.1016/S0039-6257(97)00119-7"),
        ),
    ),
    Topic(
        "pentacam-education",
        "Pentacam education for ectasia screening",
        "How refractive surgeons can organize Pentacam curvature, elevation, pachymetry, and quality information without interchanging sources.",
        "Imaging module",
        (
            ("A tomographic examination, not one number", "Scheimpflug tomography reconstructs anterior-segment geometry from multiple images. The resulting displays include anterior and posterior corneal surfaces, pachymetry, curvature-derived maps, and composite indices. These outputs are related, but they are not interchangeable."),
            ("Read the named display and field", "A value should be interpreted from its labeled source display, eye, examination, and surface. K1, K2, Km, Kmax, thinnest pachymetry, posterior elevation, and composite indices describe different properties. Copying a visually similar number from another panel can create a clinically important source error."),
            ("How CER-AI reads Pentacam images", "CER-AI first identifies the complete five-image source set and laterality. Its image-extraction layer transcribes only explicitly labeled values from each field's registered display region. It does not sample map colors, estimate an unreadable number, or calculate one locked field from another. Each accepted value carries its source identifier into reconciliation, assessment, and reporting."),
            ("What happens when a value is uncertain", "An absent, obscured, wrong-screen, or conflicting locked value remains null. CER-AI may perform a field-specific targeted reread; if the canonical box still cannot be resolved, it requests surgeon entry or confirmation when that workflow permits. It does not choose the first, average, minimum, maximum, or most concerning value to hide disagreement."),
            ("Quality precedes interpretation", "Acquisition quality, fixation, blinking, tear-film disturbance, decentration, and contact-lens effects can alter measurements. A quality warning does not automatically define the clinical result; it signals that the examination and the affected values require review or repeat acquisition when appropriate."),
            ("Compare patterns across channels", "Curvature describes optical shape, elevation describes surface position relative to a reference surface, and pachymetric progression describes spatial thickness behavior. Concordant abnormal findings are different from an isolated borderline value. Bilateral comparison and prior examinations can add context but do not replace inspection of each eye."),
        ),
        (
            ("OCULUS Pentacam Interpretation Guide 2024", "https://www.pentacam.com/fileadmin/user_upload/pentacam.de/downloads/interpretations-leitfaden/Pentacam_Interpretation_Guide_Ophth_EN_0624.pdf"),
            ("Ambrósio et al., JCRS 2006", "https://doi.org/10.1016/j.jcrs.2006.06.025"),
            ("Toprak et al., Turkish Journal of Ophthalmology 2023", "https://doi.org/10.4274/tjo.galenos.2023.68188"),
        ),
    ),
    Topic(
        "bad-d-component-indices",
        "BAD-D and component indices",
        "An evidence-bounded guide to the Belin/Ambrósio Enhanced Ectasia Display, Final BAD-D, and its component deviation indices.",
        "Tomography module",
        (
            ("What Final BAD-D represents", "The Belin/Ambrósio Enhanced Ectasia Display combines deviation information from several tomographic domains into a final multivariate index. It is designed to highlight ectatic-pattern deviation relative to the device reference database. Final BAD-D is therefore a composite signal, not a direct measurement such as micrometers or diopters."),
            ("The component family", "Commonly displayed components include deviation measures related to anterior elevation (Df), posterior elevation (Db), pachymetric progression (Dp), thinnest pachymetry (Dt), and relational thickness or ARTmax (Da). Software labeling and reference data should be checked against the installed Pentacam version and manufacturer documentation."),
            ("Interpret the final value with its components", "Two examinations can have a similar Final BAD-D for different component reasons. Reviewing which domains contribute helps the surgeon distinguish an elevation-driven, thickness-driven, or mixed pattern. The composite should be considered with raw maps, examination quality, and the rest of the clinical evaluation."),
            ("Important evidence boundary", "Published sensitivity and specificity estimates depend on the population, case definition, comparator, software version, and chosen threshold. They should not be transferred automatically to every refractive-surgery population or used as proof that a separate software product has been validated."),
        ),
        (
            ("Belin, Acta Ophthalmologica 2025", "https://doi.org/10.1111/aos.16814"),
            ("Bamdad et al., Journal of Ophthalmology 2020", "https://doi.org/10.1155/2020/7625659"),
            ("OCULUS Pentacam manufacturer documentation", "https://www.oculus.de/en/documents/"),
        ),
    ),
    Topic(
        "topometric-indices",
        "Pentacam topometric indices",
        "A practical guide to ISV, IVA, KI, CKI, IHA, IHD, and Rmin as pattern descriptors rather than stand-alone diagnoses.",
        "Topometry module",
        (
            ("What topometric indices summarize", "Topometric indices compress aspects of anterior corneal curvature into numeric descriptors. Common labels include the index of surface variance (ISV), index of vertical asymmetry (IVA), keratoconus index (KI), central keratoconus index (CKI), index of height asymmetry (IHA), index of height decentration (IHD), and minimum sagittal curvature radius (Rmin)."),
            ("Why the source matters", "Topometric values should be read from the named topometric examination and assigned to the correct eye. A similarly named or positioned value on another Pentacam display is not a substitute. Device software versions and reference databases may affect displayed classifications."),
            ("Pattern before label", "An index can indicate variance, vertical asymmetry, decentration, or localized curvature behavior, but it does not explain the complete corneal phenotype. Map morphology, bilateral symmetry, elevation, pachymetric progression, quality, and clinical history determine whether the numeric signal is coherent."),
            ("Use thresholds cautiously", "Published or device-displayed reference bands are population- and platform-dependent. Borderline values should not be treated as universal hard stops, and a normal value should not erase a concerning pattern elsewhere in the examination."),
        ),
        (
            ("OCULUS Pentacam manufacturer documentation", "https://www.oculus.de/en/documents/"),
            ("Toprak et al., Turkish Journal of Ophthalmology 2023", "https://doi.org/10.4274/tjo.galenos.2023.68188"),
            ("Maraghechi et al., Journal of Medicine and Life 2020", "https://doi.org/10.25122/jml-2020-0057"),
        ),
    ),
    Topic(
        "randleman-erss",
        "Randleman Ectasia Risk Score System (ERSS)",
        "The variables, evidence base, scope, and limitations of the Randleman ERSS in preoperative LASIK screening.",
        "Risk-system module",
        (
            ("The five-domain framework", "The original ERSS organizes five preoperative or planned-procedure domains: anterior topographic pattern, predicted residual stromal bed, age, preoperative corneal thickness, and manifest refractive spherical equivalent. The components are weighted rather than treated as equivalent observations."),
            ("Development and validation context", "The system was derived from retrospective post-refractive-surgery ectasia cases and controls and was subsequently evaluated in a separate LASIK screening study. The original publications should be consulted for cohort definitions, scoring tables, operating characteristics, and exclusions."),
            ("What ERSS contributes", "ERSS makes established clinical risk factors explicit and auditable. It also illustrates why a planned procedure cannot be assessed from corneal shape alone: tissue removal and flap-related geometry contribute information not contained in a preoperative topography map."),
            ("What ERSS cannot establish", "ERSS is not a universal lifetime probability calculator. Its reported performance belongs to the studied cohorts and methodology. Modern tomography and biomechanics can reveal information that the original anterior-topography-era framework did not directly encode."),
        ),
        (
            ("Randleman et al., Ophthalmology 2008", "https://pubmed.ncbi.nlm.nih.gov/17624434/"),
            ("Randleman et al., American Journal of Ophthalmology 2008", "https://pubmed.ncbi.nlm.nih.gov/18328998/"),
            ("Chan et al., Clinical & Experimental Ophthalmology 2010", "https://doi.org/10.1111/j.1442-9071.2010.02251.x"),
        ),
    ),
    Topic(
        "nice-risk-assessment",
        "NICE ectasia-risk assessment",
        "A careful introduction to the NICE cumulative risk concept, its elevation-tomography basis, and CER-AI's explicit implementation boundary.",
        "Risk-system module",
        (
            ("Origin of the concept", "NICE was proposed as a cumulative ectasia-risk index based on elevation-tomography variables for preoperative LASIK screening. The original academic work and later published clarification should be read together when evaluating its definitions and clinical scope."),
            ("Why implementation details matter", "A named risk system is reproducible only when its input definitions, source displays, units, cut points, point assignments, and missing-data behavior are explicit. Substituting a different elevation location or a similarly named Pentacam field changes the implemented method."),
            ("Independent interpretation", "NICE and ERSS examine overlapping clinical concerns through different variable structures. Agreement may reinforce concern; disagreement should prompt source and pattern review. Their scores should not be added together unless a separately validated method explicitly defines such a combination."),
            ("CER-AI methodology boundary", "CER-AI labels its implementation as CER-AI-adapted NICE and displays the component audit separately. This educational page explains the source literature; it does not publish or alter the application's current clinical rules."),
        ),
        (
            ("Navarro Naranjo, Universidad del Rosario 2016", "https://doi.org/10.48713/10336_12505"),
            ("Navarro-Naranjo et al., Clinical Ophthalmology 2024", "https://doi.org/10.2147/OPTH.S464217"),
        ),
    ),
    Topic(
        "ps3-risk-assessment",
        "PS3 practical subjective scoring",
        "A factor-by-factor guide to the Practical Subjective Scoring System and the procedure-specific way CER-AI evaluates its automated findings.",
        "Risk-system module",
        (
            ("What PS3 contributes", "PS3 organizes selected corneal, elevation, pachymetric, SRAX, and inter-eye findings as Normal, Moderate, or High factors. CER-AI keeps this pathway independent from ERSS, Final BAD-D, and NICE so the origin and consequence of every finding remain visible."),
            ("Automated factor set", "The current CER-AI implementation evaluates anterior Km, thinnest pachymetry, front and back elevation at the thinnest point, PPI Average, bilateral asymmetry, and SRAX. Corneal Thickness Map, Relative Thickness Map, and PTI/CTSP morphology remain explicit surgeon-review items and are not silently counted by automation."),
            ("Procedure-specific consequence", "One Moderate factor defers LASIK while allowing PRK and SMILE when the automated set is otherwise complete. Two or more Moderate factors, or any High factor, defer all three procedures. Missing decision-critical factors make the pathway incomplete; an already established defer finding is retained."),
            ("Do not add unlike quantities", "Moderate and High are categorical findings, not interchangeable numeric points. CER-AI counts factors only within PS3, converts the selected procedure's PS3 result to an independent pathway disposition, and does not add PS3 counts to ERSS or NICE totals."),
            ("Evidence and implementation boundary", "The public module documents the current CER-AI operational implementation and its source literature. It does not claim that every operational threshold has been prospectively validated for every device, population, or procedure."),
        ),
        (
            ("Elhusseiny et al., Benha Medical Journal 2021", "https://doi.org/10.21608/bmfj.2021.100688.1503"),
            ("Sinjab, Step by Step: Reading Pentacam Topography, 3rd ed.", "https://books.google.com/books?id=RPUbEAAAQBAJ"),
            ("CER-AI Clinical Evidence", "/clinical-evidence"),
        ),
    ),
    Topic(
        "topography-tomography-patterns",
        "Corneal topography and tomography patterns",
        "How to describe asymmetric bow-tie, inferior or superior steepening, skewed axes, elevation, and pachymetric patterns without overcalling a diagnosis.",
        "Pattern-recognition module",
        (
            ("Describe before classifying", "A disciplined review begins with what is visible: symmetry, axis orientation, superior-inferior distribution, localization, magnitude, and inter-eye relationship. Descriptive language reduces the risk of forcing every atypical map into a diagnostic label."),
            ("Curvature patterns", "Anterior curvature maps may show symmetric or asymmetric bow-tie configurations, inferior or superior steepening, skewed radial axes, or other localized patterns. Map scale, color step, centration, and display type can change visual appearance, so numerical and geometric confirmation matters."),
            ("Tomographic corroboration", "Posterior elevation and pachymetric distribution can provide information not present in anterior curvature alone. A coherent ectatic pattern may involve spatially related abnormalities across curvature, elevation, and thickness progression; isolated discordant findings require quality and source review."),
            ("Laterality and time", "Bilateral asymmetry can be informative, but one eye should not be used as a normalizing substitute for the other. Serial examinations can help distinguish stable anatomy from change only when acquisition conditions and image quality are sufficiently comparable."),
        ),
        (
            ("Abad et al., Ophthalmology 2007", "https://doi.org/10.1016/j.ophtha.2006.10.022"),
            ("Ambrósio et al., JCRS 2006", "https://doi.org/10.1016/j.jcrs.2006.06.025"),
            ("Quisling et al., Ophthalmology 2006", "https://doi.org/10.1016/j.ophtha.2006.03.046"),
        ),
    ),
    Topic(
        "surgical-safety-concepts",
        "Surgical tissue-safety concepts",
        "Educational review of residual stromal bed, percent tissue altered, ablation depth, flap thickness, and why safety checks remain separate from ectasia scores.",
        "Procedure-safety module",
        (
            ("Risk screening and tissue safety are different", "A cornea can have reassuring screening indices while a proposed treatment removes an unfavorable amount of tissue. Conversely, conservative tissue geometry does not neutralize a suspicious preoperative corneal pattern. These questions should remain separately visible."),
            ("Residual stromal bed", "For LASIK, predicted residual stromal bed depends on preoperative thickness, flap thickness, and ablation depth. Each input carries measurement or prediction uncertainty. A calculated value is therefore a planning estimate, not a direct postoperative measurement."),
            ("Percent tissue altered", "PTA relates flap thickness and ablation depth to preoperative central corneal thickness. Published associations are clinically important, but a single cutoff should not be generalized beyond the population and definitions studied or interpreted independently of topography and tomography."),
            ("Procedure-specific reasoning", "Surface ablation and flap-based procedures alter tissue differently. Optical zone, transition zone, refractive magnitude, platform-specific ablation behavior, retreatment history, and expected postoperative curvature all affect planning. Educational reference values are not a substitute for device data or surgeon verification."),
        ),
        (
            ("Santhiago et al., American Journal of Ophthalmology 2014", "https://pubmed.ncbi.nlm.nih.gov/24727263/"),
            ("Schmack et al., Journal of Refractive Surgery 2005", "https://doi.org/10.3928/1081-597X-20050901-04"),
            ("Dupps and Wilson, Experimental Eye Research 2006", "https://doi.org/10.1016/j.exer.2006.03.015"),
        ),
    ),
    Topic(
        "clinical-cases",
        "Clinical reasoning cases",
        "De-identified teaching archetypes showing how surgeons can reconcile concordant, discordant, incomplete, and procedure-dependent ectasia-risk evidence.",
        "Case-learning module",
        (
            ("Case A: concordant concern", "Anterior curvature asymmetry, corresponding posterior-elevation deviation, and abnormal pachymetric progression point toward the same region. The learning task is to verify acquisition quality and source identity, then explain why multiple independent channels are concordant rather than merely counting abnormal labels."),
            ("Case B: isolated composite alert", "Final BAD-D is outside the device reference band while the anterior curvature map appears regular. The learning task is to inspect the component deviations, raw elevation and pachymetry displays, quality status, and fellow eye before deciding whether the composite is coherent or isolated."),
            ("Case C: reassuring shape, unfavorable plan", "Topography and tomography appear reassuring, but planned flap and ablation geometry leave limited predicted stromal reserve. The learning task is to keep tissue safety independent from ectasia-pattern screening and reconsider the proposed procedure rather than allowing normal maps to override the plan."),
            ("Case D: missing decision-critical source", "A required display is absent or unreadable. The learning task is not to infer a favorable result from missingness. Identify the exact field and source needed, obtain a repeat examination or surgeon-confirmed value when appropriate, and preserve the uncertainty in documentation."),
        ),
        (
            ("Randleman et al., Ophthalmology 2008", "https://pubmed.ncbi.nlm.nih.gov/17624434/"),
            ("Chan et al., JCRS 2018", "https://doi.org/10.1016/j.jcrs.2018.05.013"),
            ("Moshirfar et al., Ophthalmology and Therapy 2021", "https://doi.org/10.1007/s40123-021-00383-w"),
        ),
    ),
    Topic(
        "cer-ai-methodology",
        "CER-AI methodology and evidence boundaries",
        "How CER-AI separates educational content, structured assessment, source provenance, independent risk pathways, and procedural safety.",
        "Methodology module",
        (
            ("Education and assessment are separate", "The Learning Center explains published concepts and clinical reasoning. The protected CER-AI application performs structured, patient-specific assessment. Reading an educational page never calculates, changes, or substitutes for a clinical result."),
            ("Independent pathways", "CER-AI keeps ERSS, Final BAD-D, CER-AI-adapted NICE, and PS3 visible as distinct assessment channels. It does not present them as one externally validated proprietary probability. Agreement and disagreement remain available for surgeon review."),
            ("Source provenance and uncertainty", "Decision-critical extracted values remain tied to defined source fields. Missing, unreadable, conflicting, and surgeon-completed data are not intended to disappear inside a final label. This supports auditability and reduces silent source interchange."),
            ("Validation language", "Publications cited by CER-AI support specific variables, systems, or background concepts. They do not automatically validate CER-AI as a complete product. CER-AI-specific diagnostic performance, clinical outcome, superiority, or regulatory claims require their own supporting evidence."),
        ),
        (
            ("CER-AI Clinical Evidence", "/clinical-evidence"),
            ("CER-AI Medical Reference Registry", "/references"),
            ("Corneal ectasia risk assessment overview", "/corneal-ectasia-risk-assessment"),
        ),
    ),
    Topic(
        "surgeon-learning-modules",
        "Surgeon learning pathway",
        "A structured sequence for learning corneal ectasia screening, Pentacam interpretation, risk systems, and procedure-specific safety.",
        "Curriculum",
        (
            ("Module 1: establish the vocabulary", "Begin with corneal ectasia basics and the distinction between diagnosis, susceptibility, and postoperative risk. The objective is to describe what each evidence channel can and cannot establish."),
            ("Module 2: read the examination by source", "Continue with Pentacam education, BAD-D components, topometric indices, and map patterns. The objective is to identify the correct display, eye, surface, unit, and quality status before interpretation."),
            ("Module 3: compare risk systems", "Study ERSS and NICE as independently defined methods, then use the evidence library to examine derivation populations and limitations. The objective is not memorization alone; it is knowing when a score is being applied outside its evidence base."),
            ("Module 4: integrate without blending", "Work through the teaching cases and surgical safety concepts. The objective is to reconcile concordant and discordant evidence while preserving independent safety constraints and surgeon responsibility."),
        ),
        (
            ("Start: corneal ectasia basics", "/learning/corneal-ectasia-basics"),
            ("Continue: Pentacam education", "/learning/pentacam-education"),
            ("Apply: clinical reasoning cases", "/learning/clinical-cases"),
        ),
    ),
)

TOPIC_BY_SLUG = {topic.slug: topic for topic in TOPICS}


TR_TOPICS = (
    Topic(
        "corneal-ectasia-basics",
        "Korneal ektazi: klinik temeller",
        "Korneal ektazi, yatkınlık, cerrahi sonrası ektazi ve preoperatif taramanın rolüne yönelik cerrah odaklı bir giriş.",
        "Temel modül",
        (
            ("Korneal ektazi neyi ifade eder?", "Korneal ektazi, korneanın yapısal olarak zayıflamasıyla ilişkili biçim ve optik düzen kaybının ilerleyici olmasıdır. Klinik bulgular lokalize dikleşme, incelme, düzensiz astigmatizma ve düzeltilmiş görme kalitesinde azalmayı içerebilir. Keratokonus primer bir ektatik hastalıktır; refraktif cerrahi sonrası ektazi ise farklı bir klinik bağlamdır."),
            ("Yatkınlık tanı ile aynı değildir", "Preoperatif tarama; öykü, muayene, topografi, tomografi ve planlanan işleme ilişkin faktörlerin kırılganlığa işaret edip etmediğini sorgular. Bir yatkınlık sinyali tek başına keratokonus tanısı değildir; tek bir normal ölçüm de tüm risk yollarını dışlamaz. Kanıtlar örüntü olarak ve klinik bağlam içinde yorumlanmalıdır."),
            ("Çoklu veri kanalı neden önemlidir?", "Cerrahi sonrası olgular, tek bir değişkenin ektaziye giden bütün yolları kapsamadığını göstermektedir. Ön yüz eğrilik örüntüsü, pakimetrik dağılım, arka yüz bilgisi, yaş, refraksiyon büyüklüğü ve planlanan doku değişikliği farklı soruları yanıtlar. Bu kanallar arasındaki uyumsuzluk da ayrıca incelenmesi gereken bir bilgidir."),
            ("Biyomekanik çerçeve", "Kornea doğrusal olmayan, anizotropik ve zamana bağlı bir yük taşıyan dokudur. Klinik haritalar biyomekanik dayanımı doğrudan ölçmez; geometri ve optik yüzeyler üzerinden dolaylı fenotip bilgisi sağlar. Bu nedenle şekil, kalınlık dağılımı ve cerrahi doku yükü birlikte değerlendirilir, ancak birbirinin yerine kullanılmaz."),
            ("Bu modül ne yapmaz?", "Bu sayfa terminoloji ve klinik akıl yürütmeyi öğretir. Tek bir göze tanı koymaz, hastaya özgü olasılık hesaplamaz veya cerrahi uygunluğu belirlemez. Boylamsal değişim, görüntü kalitesi, kontakt lens öyküsü, oküler muayene ve cerrah kararı temel olmaya devam eder."),
        ),
        (
            ("Randleman ve ark., Ophthalmology 2008", "https://pubmed.ncbi.nlm.nih.gov/17624434/"),
            ("Moshirfar ve ark., Ophthalmology and Therapy 2021", "https://doi.org/10.1007/s40123-021-00383-w"),
            ("Rabinowitz, Survey of Ophthalmology 1998", "https://doi.org/10.1016/S0039-6257(97)00119-7"),
        ),
    ),
    Topic(
        "pentacam-education",
        "Ektazi taramasında Pentacam eğitimi",
        "Refraktif cerrahlar için Pentacam eğrilik, elevasyon, pakimetri ve kalite bilgilerinin kaynakları karıştırılmadan düzenlenmesi.",
        "Görüntüleme modülü",
        (
            ("Tek sayı değil, tomografik inceleme", "Dönen Scheimpflug kamera, farklı meridyenlerden optik kesitler alarak ön segment geometrisini üç boyutlu olarak yeniden oluşturur. Elde edilen ekranlar ön ve arka korneal yüzeyleri, pakimetriyi, eğrilik haritalarını ve bileşik indeksleri içerir. Bu çıktılar ilişkili olsa da birbirinin yerine geçmez."),
            ("Adlandırılmış ekranı ve alanı okuyun", "Bir değer, etiketlenmiş kaynak ekranından; doğru göz, çekim ve yüzey ile birlikte yorumlanmalıdır. K1, K2, Km, Kmax, en ince pakimetri, arka elevasyon ve bileşik indeksler farklı özellikleri tanımlar. Görsel olarak benzer bir sayının başka panelden kopyalanması klinik açıdan önemli kaynak hatası oluşturabilir."),
            ("CER-AI Pentacam görüntülerini nasıl okur?", "CER-AI önce beş görüntüden oluşan zorunlu kaynak kümesini ve göz tarafını tanımlar. Görüntü çıkarım katmanı, her alanın kayıtlı ekran bölgesindeki yalnız açıkça etiketlenmiş değeri yazıya aktarır. Harita renginden sayı örneklemez, okunamayan değeri tahmin etmez veya kaynağı kilitli bir alanı başka alandan hesaplamaz. Kabul edilen her değer kaynak kimliğini uzlaştırma, değerlendirme ve rapora taşır."),
            ("Değer belirsiz olduğunda ne olur?", "Bulunmayan, kapalı, yanlış ekrandan gelen veya çelişkili kaynağı kilitli değer null olarak kalır. CER-AI alana özgü hedefli yeniden okuma yapabilir; kanonik kutu yine çözülemezse iş akışının izin verdiği durumda cerrah girişi ya da doğrulaması ister. Çelişkiyi gizlemek için ilk, ortalama, minimum, maksimum veya en kaygı verici değeri seçmez."),
            ("Elevasyonun referans yüzeye bağımlılığı", "Elevasyon mutlak bir anatomik yükseklik değildir; seçilen en uygun küre, elipsoid veya geliştirilmiş referans yüzeye göre hesaplanan farktır. Analiz çapı, merkezleme, hariç tutulan bölge ve yazılım algoritması değişirse aynı kornea için gösterilen elevasyon değeri de değişebilir."),
            ("Yorumdan önce kalite", "Fiksasyon, göz kırpma, gözyaşı filmi bozukluğu, desantralizasyon ve kontakt lens etkileri ölçümleri değiştirebilir. Kalite uyarısı klinik sonucu otomatik olarak tanımlamaz; çekimin ve etkilenen değerlerin incelenmesini, uygun olduğunda tekrar ölçüm alınmasını gerektirir."),
            ("Kanallar arasında örüntü karşılaştırması", "Eğrilik optik şekli, elevasyon referans yüzeye göre konumu, pakimetrik progresyon ise kalınlığın uzaysal davranışını tanımlar. Birbiriyle uyumlu anormal bulgular, izole sınırda bir değerden farklıdır. İki göz ve önceki çekimler ek bağlam sağlar; her gözün ayrı incelenmesinin yerini tutmaz."),
        ),
        (
            ("OCULUS Pentacam Yorumlama Rehberi 2024", "https://www.pentacam.com/fileadmin/user_upload/pentacam.de/downloads/interpretations-leitfaden/Pentacam_Interpretation_Guide_Ophth_EN_0624.pdf"),
            ("Ambrósio ve ark., JCRS 2006", "https://doi.org/10.1016/j.jcrs.2006.06.025"),
            ("Toprak ve ark., Turkish Journal of Ophthalmology 2023", "https://doi.org/10.4274/tjo.galenos.2023.68188"),
        ),
    ),
    Topic(
        "bad-d-component-indices",
        "BAD-D ve bileşen indeksleri",
        "Belin/Ambrósio Geliştirilmiş Ektazi Ekranı, Final BAD-D ve bileşen sapma indeksleri için kanıt sınırları belirlenmiş rehber.",
        "Tomografi modülü",
        (
            ("Final BAD-D neyi temsil eder?", "Belin/Ambrósio Geliştirilmiş Ektazi Ekranı, birden fazla tomografik alandaki sapma bilgisini çok değişkenli nihai bir indekste birleştirir. Amaç, cihazın referans veritabanına göre ektatik örüntü sapmasını belirginleştirmektir. Final BAD-D mikrometre veya diyoptri gibi doğrudan bir ölçüm değil, bileşik bir sinyaldir."),
            ("Bileşen ailesi", "Sıklıkla gösterilen bileşenler; ön elevasyon (Df), arka elevasyon (Db), pakimetrik progresyon (Dp), en ince pakimetri (Dt) ve göreli kalınlık/ARTmax (Da) ile ilişkili standardize sapmaları içerir. Etiketler ve referans verileri kullanılan Pentacam yazılım sürümü ve üretici dokümantasyonu ile doğrulanmalıdır."),
            ("Sapma değerinin anlamı", "D ile başlayan bileşenler ham mikrometre ya da diyoptri değildir; ilgili ölçümün normatif dağılımdan uzaklığını özetleyen boyutsuz sapma değerleridir. Bu ayrım, örneğin Db ile arka elevasyonun ham mikrometre değerinin birbirine karıştırılmasını önler."),
            ("Nihai değeri bileşenleriyle yorumlayın", "İki inceleme farklı bileşen katkılarıyla benzer Final BAD-D değerine ulaşabilir. Katkıda bulunan alanların incelenmesi elevasyon ağırlıklı, kalınlık ağırlıklı veya karma örüntünün ayırt edilmesine yardım eder. Bileşik değer ham haritalar, çekim kalitesi ve klinik değerlendirme ile birlikte ele alınmalıdır."),
            ("Kanıt sınırı", "Yayımlanmış duyarlılık ve özgüllük tahminleri popülasyona, olgu tanımına, karşılaştırıcıya, yazılım sürümüne ve seçilen eşiğe bağlıdır. Bu sonuçlar her refraktif cerrahi popülasyonuna otomatik aktarılmamalı ve ayrı bir yazılım ürününün doğrulandığının kanıtı olarak sunulmamalıdır."),
        ),
        (
            ("Belin, Acta Ophthalmologica 2025", "https://doi.org/10.1111/aos.16814"),
            ("Bamdad ve ark., Journal of Ophthalmology 2020", "https://doi.org/10.1155/2020/7625659"),
            ("OCULUS Pentacam üretici dokümantasyonu", "https://www.oculus.de/en/documents/"),
        ),
    ),
    Topic(
        "topometric-indices",
        "Pentacam topometrik indeksleri",
        "ISV, IVA, KI, CKI, IHA, IHD ve Rmin'in tek başına tanı değil, örüntü tanımlayıcıları olarak kullanımı.",
        "Topometri modülü",
        (
            ("Topometrik indeksler neyi özetler?", "Topometrik indeksler ön korneal eğriliğin belirli özelliklerini sayısal tanımlayıcılara sıkıştırır. Yaygın etiketler yüzey varyansı indeksi (ISV), vertikal asimetri indeksi (IVA), keratokonus indeksi (KI), santral keratokonus indeksi (CKI), yükseklik asimetrisi indeksi (IHA), yükseklik desantralizasyonu indeksi (IHD) ve minimum sagittal eğrilik yarıçapını (Rmin) içerir."),
            ("Her indeks farklı geometriyi vurgular", "ISV genel yüzey düzensizliğine, IVA vertikal eğrilik asimetrisine, KI ve CKI bölgesel eğrilik ilişkilerine, IHA ve IHD yükseklik verisinin asimetri ve desantralizasyonuna duyarlıdır. Rmin, en dik bölgeyle ilişkili en küçük sagittal yarıçaptır; yarıçap küçüldükçe eğrilik artar."),
            ("Kaynak neden önemlidir?", "Topometrik değerler adlandırılmış topometri incelemesinden okunmalı ve doğru göze atanmalıdır. Başka bir Pentacam ekranındaki benzer isimli veya benzer konumlu değer yerine kullanılamaz. Yazılım sürümü ve referans veritabanı gösterilen sınıflamayı etkileyebilir."),
            ("Etiketten önce örüntü", "Bir indeks varyans, vertikal asimetri, desantralizasyon veya lokalize eğrilik davranışına işaret edebilir; ancak korneal fenotipin tamamını açıklamaz. Harita morfolojisi, iki göz arasındaki ilişki, elevasyon, pakimetrik progresyon, kalite ve klinik öykü sayısal sinyalin tutarlı olup olmadığını belirler."),
            ("Eşikleri dikkatle kullanın", "Yayımlanmış veya cihazda gösterilen referans bantları popülasyona ve platforma bağlıdır. Sınırda değerler evrensel mutlak dışlama ölçütü sayılmamalı; normal bir değer başka kanaldaki kaygı verici örüntüyü silmemelidir."),
        ),
        (
            ("OCULUS Pentacam üretici dokümantasyonu", "https://www.oculus.de/en/documents/"),
            ("Toprak ve ark., Turkish Journal of Ophthalmology 2023", "https://doi.org/10.4274/tjo.galenos.2023.68188"),
            ("Maraghechi ve ark., Journal of Medicine and Life 2020", "https://doi.org/10.25122/jml-2020-0057"),
        ),
    ),
    Topic(
        "randleman-erss",
        "Randleman Ektazi Risk Skor Sistemi (ERSS)",
        "Preoperatif LASIK taramasında Randleman ERSS değişkenleri, kanıt tabanı, kapsamı ve sınırlılıkları.",
        "Risk sistemi modülü",
        (
            ("Beş alanlı çerçeve", "Orijinal ERSS beş preoperatif veya planlama alanını düzenler: ön topografik örüntü, öngörülen rezidüel stromal yatak, yaş, preoperatif kornea kalınlığı ve manifest refraktif sferik eşdeğer. Bileşenler eşdeğer gözlemler olarak değil, farklı ağırlıklarla puanlanır."),
            ("Geliştirme ve doğrulama bağlamı", "Sistem, refraktif cerrahi sonrası ektazi olguları ile kontrollerin retrospektif karşılaştırılmasından geliştirilmiş, daha sonra ayrı bir LASIK tarama çalışmasında değerlendirilmiştir. Kohort tanımları, puanlama tabloları, çalışma karakteristikleri ve dışlamalar için orijinal yayınlara başvurulmalıdır."),
            ("ERSS ne sağlar?", "ERSS yerleşik klinik risk faktörlerini açık ve denetlenebilir hale getirir. Ayrıca planlanan işlemin yalnızca kornea şeklinden değerlendirilemeyeceğini gösterir: doku çıkarımı ve flep geometrisi, preoperatif topografi haritasında bulunmayan bilgiler taşır."),
            ("Matematiksel yapı", "ERSS bir regresyon olasılığı değil, kategorilere ayrılmış beş değişkenden gelen puanların toplamıdır. Bu nedenle toplam puandaki bir birimlik değişimin biyolojik riskte sabit veya doğrusal bir artış anlamına geldiği varsayılamaz."),
            ("ERSS neyi gösteremez?", "ERSS evrensel bir yaşam boyu olasılık hesaplayıcısı değildir. Bildirilen performans çalışılan kohortlara ve yönteme aittir. Güncel tomografi ve biyomekanik ölçümler, ön topografi döneminde geliştirilen çerçevenin doğrudan kodlamadığı bilgiler sağlayabilir."),
        ),
        (
            ("Randleman ve ark., Ophthalmology 2008", "https://pubmed.ncbi.nlm.nih.gov/17624434/"),
            ("Randleman ve ark., American Journal of Ophthalmology 2008", "https://pubmed.ncbi.nlm.nih.gov/18328998/"),
            ("Chan ve ark., Clinical & Experimental Ophthalmology 2010", "https://doi.org/10.1111/j.1442-9071.2010.02251.x"),
        ),
    ),
    Topic(
        "nice-risk-assessment",
        "NICE ektazi risk değerlendirmesi",
        "NICE kümülatif risk kavramı, elevasyon tomografisi temeli ve CER-AI uygulama sınırı için dikkatli bir giriş.",
        "Risk sistemi modülü",
        (
            ("Kavramın kökeni", "NICE, preoperatif LASIK taraması için elevasyon tomografisi değişkenlerine dayanan kümülatif bir ektazi risk indeksi olarak önerilmiştir. Tanımlar ve klinik kapsam değerlendirilirken orijinal akademik çalışma ile daha sonraki yayımlanmış açıklama birlikte okunmalıdır."),
            ("Uygulama ayrıntıları neden önemlidir?", "Adlandırılmış bir risk sistemi ancak girdi tanımları, kaynak ekranları, birimler, kesim noktaları, puan atamaları ve eksik veri davranışı açık olduğunda yeniden üretilebilir. Farklı bir elevasyon konumunun veya benzer adlı Pentacam alanının kullanılması, uygulanan yöntemi değiştirir."),
            ("Bağımsız yorum", "NICE ve ERSS birbiriyle kesişen klinik kaygıları farklı değişken yapılarıyla inceler. Uyum kaygıyı güçlendirebilir; uyumsuzluk kaynak ve örüntü incelemesini gerektirir. Ayrı olarak doğrulanmış bir yöntem tanımlamadıkça skorları birbirine eklenmemelidir."),
            ("Aktarılabilirlik sınırı", "Bir indeksin belirli bir kohorttaki sınıflandırma başarısı, farklı prevalans, cihaz sürümü veya cerrahi aday popülasyonunda aynı pozitif ve negatif öngörü değerlerini garanti etmez. Kesim noktası, örneklem ve sonuç tanımı birlikte raporlanmalıdır."),
            ("CER-AI metodoloji sınırı", "CER-AI uygulamasını CER-AI-uyarlanmış NICE olarak etiketler ve bileşen denetimini ayrı gösterir. Bu eğitim sayfası kaynak literatürü açıklar; uygulamanın güncel klinik kurallarını yayımlamaz veya değiştirmez."),
        ),
        (
            ("Navarro Naranjo, Universidad del Rosario 2016", "https://doi.org/10.48713/10336_12505"),
            ("Navarro-Naranjo ve ark., Clinical Ophthalmology 2024", "https://doi.org/10.2147/OPTH.S464217"),
        ),
    ),
    Topic(
        "ps3-risk-assessment",
        "PS3 pratik subjektif skorlama",
        "Practical Subjective Scoring System'ın faktör bazında açıklaması ve CER-AI'ın otomatik bulguları işleme özgü nasıl değerlendirdiği.",
        "Risk sistemi modülü",
        (
            ("PS3 ne sağlar?", "PS3 seçilmiş korneal, elevasyon, pakimetrik, SRAX ve iki göz arası bulguları Normal, Orta veya Yüksek faktörler olarak düzenler. CER-AI her bulgunun kökeni ve sonucu görünür kalsın diye bu yolu ERSS, Final BAD-D ve NICE'tan bağımsız tutar."),
            ("Otomatik faktör kümesi", "Güncel CER-AI uygulaması ön Km, en ince pakimetri, en ince noktadaki ön ve arka elevasyon, PPI Average, iki göz arası asimetri ve SRAX'ı değerlendirir. Corneal Thickness Map, Relative Thickness Map ve PTI/CTSP morfolojisi açık cerrah inceleme maddeleri olarak kalır; otomasyon tarafından sessizce sayılmaz."),
            ("İşleme özgü sonuç", "Tek bir Orta faktör, otomatik küme başka yönden tam ise LASIK'i ertelerken PRK ve SMILE'a izin verir. İki veya daha fazla Orta faktör ya da herhangi bir Yüksek faktör üç işlemi de erteler. Karar için kritik faktörlerin eksikliği yolu tamamlanmamış yapar; daha önce oluşmuş erteleme bulgusu korunur."),
            ("Benzer olmayan nicelikleri toplamayın", "Orta ve Yüksek kategorik bulgulardır; birbirinin yerine geçen sayısal puanlar değildir. CER-AI faktörleri yalnız PS3 içinde sayar, seçilen işlemin PS3 sonucunu bağımsız yol kararına dönüştürür ve PS3 sayılarını ERSS veya NICE toplamına eklemez."),
            ("Kanıt ve uygulama sınırı", "Kamusal modül güncel CER-AI operasyonel uygulamasını ve kaynak literatürü belgeler. Her operasyonel eşiğin her cihaz, popülasyon veya işlem için prospektif olarak doğrulandığını iddia etmez."),
        ),
        (
            ("Elhusseiny ve ark., Benha Medical Journal 2021", "https://doi.org/10.21608/bmfj.2021.100688.1503"),
            ("Sinjab, Step by Step: Reading Pentacam Topography, 3. baskı", "https://books.google.com/books?id=RPUbEAAAQBAJ"),
            ("CER-AI Klinik Kanıt", "/clinical-evidence"),
        ),
    ),
    Topic(
        "topography-tomography-patterns",
        "Korneal topografi ve tomografi örüntüleri",
        "Asimetrik papyon, inferior veya superior dikleşme, çarpık eksenler, elevasyon ve pakimetrik örüntülerin tanıyı aşırı yorumlamadan tanımlanması.",
        "Örüntü tanıma modülü",
        (
            ("Sınıflamadan önce tanımlayın", "Disiplinli inceleme görünür özelliklerle başlar: simetri, eksen yönü, superior-inferior dağılım, lokalizasyon, büyüklük ve iki göz arasındaki ilişki. Tanımlayıcı dil, her atipik haritayı zorla tanısal etikete dönüştürme riskini azaltır."),
            ("Eğrilik örüntüleri", "Ön eğrilik haritaları simetrik veya asimetrik papyon, inferior veya superior dikleşme, çarpık radyal eksenler ya da başka lokal örüntüler gösterebilir. Harita ölçeği, renk basamağı, merkezleme ve ekran tipi görsel görünümü değiştirebildiği için sayısal ve geometrik doğrulama gerekir."),
            ("SRAX'ın teknik anlamı", "Skewed radial axes (SRAX), papyonun üst ve alt dik hemimeridyenleri arasındaki açısal uyumsuzluğu tanımlar. Ölçüm; kullanılan eksen konvansiyonu, haritanın uygun papyon morfolojisine sahip olması ve doğru meridyen seçimine bağlıdır; yalnızca renk örüntüsünden güvenilir biçimde tahmin edilmemelidir."),
            ("Tomografik doğrulama", "Arka elevasyon ve pakimetrik dağılım ön eğrilikte bulunmayan bilgi sağlayabilir. Uyumlu ektatik örüntü, eğrilik, elevasyon ve kalınlık progresyonunda uzaysal olarak ilişkili anormallikler içerebilir; izole uyumsuz bulgular kalite ve kaynak incelemesi gerektirir."),
            ("Taraf ve zaman", "İki göz arasındaki asimetri bilgi sağlayabilir, ancak bir göz diğerini normalleştiren ikame olarak kullanılmamalıdır. Seri incelemeler, yalnızca çekim koşulları ve görüntü kalitesi yeterince karşılaştırılabilir olduğunda stabil anatomi ile değişimi ayırt etmeye yardım eder."),
        ),
        (
            ("Abad ve ark., Ophthalmology 2007", "https://doi.org/10.1016/j.ophtha.2006.10.022"),
            ("Ambrósio ve ark., JCRS 2006", "https://doi.org/10.1016/j.jcrs.2006.06.025"),
            ("Quisling ve ark., Ophthalmology 2006", "https://doi.org/10.1016/j.ophtha.2006.03.046"),
        ),
    ),
    Topic(
        "surgical-safety-concepts",
        "Cerrahi doku güvenliği kavramları",
        "Rezidüel stromal yatak, yüzde doku değişimi, ablasyon derinliği ve flep kalınlığının; güvenlik kontrolleri ektazi skorlarından ayrı tutularak incelenmesi.",
        "İşlem güvenliği modülü",
        (
            ("Risk taraması ve doku güvenliği farklıdır", "Bir korneada tarama indeksleri güven verici olduğu halde önerilen tedavi elverişsiz miktarda doku çıkarabilir. Tersine, konservatif doku geometrisi şüpheli preoperatif korneal örüntüyü etkisizleştirmez. Bu sorular ayrı görünür kalmalıdır."),
            ("Rezidüel stromal yatak", "LASIK için öngörülen rezidüel stromal yatak yaklaşık olarak RSB = CCT − FT − AD bağıntısıyla ifade edilir; burada CCT preoperatif santral kornea kalınlığı, FT flep kalınlığı ve AD ablasyon derinliğidir. Her girdi ölçüm veya tahmin belirsizliği taşır; sonuç doğrudan postoperatif ölçüm değil planlama tahminidir."),
            ("Yüzde doku değişimi", "PTA = (FT + AD) / CCT × 100 olarak tanımlanır. Yayımlanmış ilişkiler klinik olarak önemlidir; ancak tek bir eşik çalışılan popülasyon ve tanımların dışına genellenmemeli, topografi ve tomografiden bağımsız yorumlanmamalıdır."),
            ("Belirsizlik yayılımı", "Flep kalınlığı için nominal yerine gerçekleşen değer, ablasyon için platform tahmini yerine gerçek doku etkisi farklı olabilir. Bu değişkenlerdeki hata RSB ve PTA hesaplarına doğrudan taşınır; cerrahi planlamada kaynak ve varsayımların belgelenmesi gerekir."),
            ("İşleme özgü akıl yürütme", "Yüzey ablasyonu ve flepli işlemler dokuyu farklı biçimde değiştirir. Optik zon, geçiş zonu, refraksiyon büyüklüğü, platforma özgü ablasyon davranışı, yeniden tedavi öyküsü ve beklenen postoperatif eğrilik planlamayı etkiler. Eğitim amaçlı referans değerler cihaz verisi veya cerrah doğrulamasının yerini tutmaz."),
        ),
        (
            ("Santhiago ve ark., American Journal of Ophthalmology 2014", "https://pubmed.ncbi.nlm.nih.gov/24727263/"),
            ("Schmack ve ark., Journal of Refractive Surgery 2005", "https://doi.org/10.3928/1081-597X-20050901-04"),
            ("Dupps ve Wilson, Experimental Eye Research 2006", "https://doi.org/10.1016/j.exer.2006.03.015"),
        ),
    ),
    Topic(
        "clinical-cases",
        "Klinik akıl yürütme olguları",
        "Uyumlu, uyumsuz, eksik ve işleme bağımlı ektazi risk kanıtlarının uzlaştırılmasını gösteren kimliksiz eğitim arketipleri.",
        "Olgu öğrenme modülü",
        (
            ("Olgu A: uyumlu kaygı", "Ön eğrilik asimetrisi, aynı bölgeye karşılık gelen arka elevasyon sapması ve anormal pakimetrik progresyon aynı yöne işaret eder. Öğrenme görevi; çekim kalitesini ve kaynak kimliğini doğrulamak, ardından yalnızca anormal etiketleri saymak yerine bağımsız kanalların neden uyumlu olduğunu açıklamaktır."),
            ("Olgu B: izole bileşik uyarı", "Final BAD-D cihaz referans bandının dışındayken ön eğrilik haritası düzenli görünür. Öğrenme görevi; bileşen sapmalarını, ham elevasyon ve pakimetri ekranlarını, kalite durumunu ve diğer gözü inceleyerek bileşik sinyalin tutarlı mı izole mi olduğunu belirlemektir."),
            ("Olgu C: güven verici şekil, elverişsiz plan", "Topografi ve tomografi güven verici görünür, ancak planlanan flep ve ablasyon geometrisi sınırlı stromal rezerv bırakır. Öğrenme görevi; doku güvenliğini ektazi örüntü taramasından bağımsız tutmak ve normal haritaların planı geçersiz biçimde onaylamasına izin vermemektir."),
            ("Olgu D: karar için kritik kaynak eksik", "Gerekli bir ekran yoktur veya okunamıyordur. Öğrenme görevi eksikliği olumlu sonuç olarak varsaymamak; gerekli alanı ve kaynağı açıkça tanımlamak, uygun olduğunda tekrar inceleme veya cerrahça doğrulanmış değer almak ve belirsizliği kayıtta korumaktır."),
            ("Bayesçi uyarı", "Bir testin son-test olasılığı yalnızca duyarlılık ve özgüllüğe değil, değerlendirilen popülasyondaki ön-test olasılığına da bağlıdır. Bu nedenle doğrulanmış olsa bile tek bir indeksin sonuçları, seçilmiş cerrahi adaylar ile hastalık kliniğine başvuranlarda aynı anlamı taşımaz."),
        ),
        (
            ("Randleman ve ark., Ophthalmology 2008", "https://pubmed.ncbi.nlm.nih.gov/17624434/"),
            ("Chan ve ark., JCRS 2018", "https://doi.org/10.1016/j.jcrs.2018.05.013"),
            ("Moshirfar ve ark., Ophthalmology and Therapy 2021", "https://doi.org/10.1007/s40123-021-00383-w"),
        ),
    ),
    Topic(
        "cer-ai-methodology",
        "CER-AI metodolojisi ve kanıt sınırları",
        "CER-AI'ın eğitim içeriğini, yapılandırılmış değerlendirmeyi, kaynak kökenini, bağımsız risk yollarını ve işlem güvenliğini nasıl ayırdığı.",
        "Metodoloji modülü",
        (
            ("Eğitim ve değerlendirme ayrıdır", "Öğrenme Merkezi yayımlanmış kavramları ve klinik akıl yürütmeyi açıklar. Korunan CER-AI uygulaması yapılandırılmış, hastaya özgü değerlendirmeyi gerçekleştirir. Bir eğitim sayfasını okumak klinik sonucu hesaplamaz, değiştirmez veya onun yerine geçmez."),
            ("Bağımsız yollar", "CER-AI; ERSS, Final BAD-D, CER-AI-uyarlanmış NICE ve PS3'ü ayrı değerlendirme kanalları olarak görünür tutar. Bunları dışarıdan doğrulanmış tek bir özel olasılık olarak sunmaz. Uyum ve uyumsuzluk cerrah incelemesine açık kalır."),
            ("Kaynak kökeni ve belirsizlik", "Karar için kritik çıkarılmış değerler tanımlı kaynak alanlarına bağlı kalır. Eksik, okunamayan, çelişkili ve cerrah tarafından tamamlanan verilerin nihai etiket içinde kaybolmaması amaçlanır. Bu yaklaşım denetlenebilirliği destekler ve sessiz kaynak değişimini azaltır."),
            ("Doğrulama dili", "CER-AI'ın atıf yaptığı yayınlar belirli değişkenleri, sistemleri veya arka plan kavramlarını destekler. CER-AI'ı eksiksiz ürün olarak otomatik biçimde doğrulamaz. CER-AI'a özgü tanısal performans, klinik sonuç, üstünlük veya düzenleyici iddialar kendi destekleyici kanıtını gerektirir."),
            ("Sürüm ve yönetişim sınırı", "Eğitim içeriğindeki bir tanım, klinik motordaki kanonik puanlama kuralı değildir. Klinik kurallar ayrı sürümlenir, test edilir ve denetlenir; kamusal metin değişikliği değerlendirme motorunu değiştiremez."),
        ),
        (
            ("CER-AI Klinik Kanıt", "/clinical-evidence"),
            ("CER-AI Tıbbi Kaynak Kayıt Sistemi", "/references"),
            ("Korneal ektazi risk değerlendirmesine genel bakış", "/corneal-ectasia-risk-assessment"),
        ),
    ),
    Topic(
        "surgeon-learning-modules",
        "Cerrah öğrenme yolu",
        "Korneal ektazi taraması, Pentacam yorumlama, risk sistemleri ve işleme özgü güvenlik için yapılandırılmış eğitim sırası.",
        "Müfredat",
        (
            ("Modül 1: terminolojiyi kurun", "Korneal ektazinin temelleri ile tanı, yatkınlık ve cerrahi sonrası risk ayrımıyla başlayın. Amaç her kanıt kanalının neyi gösterebileceğini ve neyi gösteremeyeceğini tanımlamaktır."),
            ("Modül 2: incelemeyi kaynağına göre okuyun", "Pentacam eğitimi, BAD-D bileşenleri, topometrik indeksler ve harita örüntüleriyle devam edin. Amaç yorumdan önce doğru ekranı, gözü, yüzeyi, birimi ve kalite durumunu belirlemektir."),
            ("Modül 3: risk sistemlerini karşılaştırın", "ERSS ve NICE'ı bağımsız tanımlanmış yöntemler olarak inceleyin; ardından türetme popülasyonlarını ve sınırlılıkları değerlendirmek için kanıt kütüphanesini kullanın. Amaç yalnızca ezber değil, bir skorun kanıt tabanı dışında ne zaman uygulandığını bilmektir."),
            ("Modül 4: birleştirmeden bütünleştirin", "Öğretici olgular ve cerrahi güvenlik kavramları üzerinde çalışın. Amaç bağımsız güvenlik kısıtlarını ve cerrah sorumluluğunu koruyarak uyumlu ve uyumsuz kanıtları uzlaştırmaktır."),
            ("Teknik yeterlilik hedefi", "Öğrenen kişi her kritik veriyi göz, çekim, ekran, yüzey ve birimiyle ifade edebilmeli; ham ölçüm ile standardize sapmayı ayırabilmeli; RSB ve PTA formüllerindeki varsayımları belirtebilmeli ve kanıtı hasta-özel kararla karıştırmamalıdır."),
        ),
        (
            ("Başlangıç: korneal ektazi temelleri", "/tr/learning/corneal-ectasia-basics"),
            ("Devam: Pentacam eğitimi", "/tr/learning/pentacam-education"),
            ("Uygulama: klinik akıl yürütme olguları", "/tr/learning/clinical-cases"),
        ),
    ),
)

TR_TOPIC_BY_SLUG = {topic.slug: topic for topic in TR_TOPICS}


FAQS = (
    ("Does the Learning Center perform a CER-AI assessment?", "No. Public education pages explain science and terminology. Patient-specific structured assessment occurs only in the protected clinical application."),
    ("Is Final BAD-D the same as an ectasia diagnosis?", "No. Final BAD-D is a composite tomographic deviation index. It must be interpreted with its components, raw maps, examination quality, and clinical context."),
    ("Can a normal ERSS exclude ectasia susceptibility?", "No screening system excludes every pathway to susceptibility. ERSS should be interpreted within its original evidence base and alongside contemporary tomography and clinical findings."),
    ("Are topography and tomography interchangeable?", "No. Curvature, elevation, and spatial pachymetry describe related but different corneal properties. Their source displays and units should remain explicit."),
    ("Does a cited study validate CER-AI?", "Not unless the study specifically evaluates CER-AI as a complete product. Most references support individual concepts, variables, or named risk systems."),
    ("Will the educational assistant give patient-specific advice?", "No. The planned assistant is restricted to the cited public knowledge base and educational navigation. It will not accept patient data, calculate a clinical disposition, or replace the clinical application or surgeon judgment."),
)

TR_FAQS = (
    ("Öğrenme Merkezi CER-AI değerlendirmesi yapar mı?", "Hayır. Kamusal eğitim sayfaları bilimi ve terminolojiyi açıklar. Hastaya özgü yapılandırılmış değerlendirme yalnızca korunan klinik uygulamada yapılır."),
    ("Final BAD-D ektazi tanısıyla aynı mıdır?", "Hayır. Final BAD-D bileşik bir tomografik sapma indeksidir. Bileşenleri, ham haritalar, çekim kalitesi ve klinik bağlamla birlikte yorumlanmalıdır."),
    ("Normal ERSS ektazi yatkınlığını dışlar mı?", "Hayır. Hiçbir tarama sistemi yatkınlığa giden bütün yolları dışlamaz. ERSS özgün kanıt tabanı içinde, güncel tomografi ve klinik bulgularla birlikte yorumlanmalıdır."),
    ("Topografi ve tomografi birbirinin yerine kullanılabilir mi?", "Hayır. Eğrilik, elevasyon ve uzaysal pakimetri ilişkili fakat farklı korneal özellikleri tanımlar. Kaynak ekranları ve birimleri açık kalmalıdır."),
    ("Atıf yapılan bir çalışma CER-AI'ı doğrular mı?", "Çalışma CER-AI'ı eksiksiz ürün olarak özellikle değerlendirmedikçe hayır. Kaynakların çoğu ayrı kavramları, değişkenleri veya adlandırılmış risk sistemlerini destekler."),
    ("Eğitim asistanı hastaya özgü öneri verecek mi?", "Hayır. Planlanan asistan atıf yapılmış kamusal bilgi tabanı ve eğitim yönlendirmesiyle sınırlıdır. Hasta verisi kabul etmeyecek, klinik karar hesaplamayacak ve klinik uygulamanın ya da cerrah kararının yerini almayacaktır."),
)


# Public documentation of the current canonical v0.7.71 behavior. These tables
# are presentation data only; the clinical engine remains the sole rule owner.
TECHNICAL_TABLES = {
    "en": {
        "pentacam-education": (
            ("Surgeon upload and source confirmation", ("Required image", "Surgeon must define/confirm", "Image acquisition requirement"), (
                ("1. 4 Maps Refractive — OD", "Right eye; 4 Maps Refractive", "Full display, captured directly from the front"),
                ("2. 4 Maps Refractive — OS", "Left eye; 4 Maps Refractive", "Full display, captured directly from the front"),
                ("3. Belin/Ambrósio BAD Display — OD", "Right eye; BAD Display", "Full display with bottom D strip and labeled boxes visible"),
                ("4. Belin/Ambrósio BAD Display — OS", "Left eye; BAD Display", "Full display with bottom D strip and labeled boxes visible"),
                ("5. Show 2 Exams Topometric", "Bilateral comparison; OD and OS panels identified", "Full display with Cornea Front, Cornea Back, and center indices readable"),
            ), "The surgeon must upload and confirm all five Pentacam source images. Use a clear screenshot or a photograph taken perpendicular to the screen—not from an angle. Avoid blur, glare, perspective distortion, compression, cropping, shadows, and covered labels. Poor image quality can make a field unreadable or inconsistent; CER-AI must request a clearer source rather than infer a value. Clear acquisition supports consistency but does not guarantee clinical correctness."),
            ("Standard 4 Maps Refractive quadrant localization", ("Screen location", "Required printed map type", "CER-AI use and conflict rule"), (
                ("Upper left", "Axial/Sagittal Curvature (Front)", "Only this anterior/front curvature map is used by the deterministic SRAX geometry layer."),
                ("Upper right", "Elevation (Front)", "Anterior elevation pattern review; it does not substitute for the BAD Display F.Ele.Th labeled value."),
                ("Lower left", "Corneal Thickness / Pachymetry", "Spatial thickness-pattern review; decision fields still come from their explicitly labeled Pupil Center and Thinnest Location values."),
                ("Lower right", "Elevation (Back)", "Posterior elevation pattern review; it does not substitute for BAD Display B.Ele.Th or Show 2 Cornea Back values."),
            ), "CER-AI requires the standard full 4 Maps Refractive layout and verifies the printed map label as well as its quadrant. Do not upload a custom/rearranged four-map layout or place an anterior sagittal-curvature map in a right-hand quadrant. A label–position mismatch, front/back substitution, rotation, or crop is a source conflict and must be corrected with a standard export or clear front-on image."),
            ("Required Pentacam source set", ("Source image", "Required set", "CER-AI extraction role"), (
                ("4 Maps Refractive", "One OD and one OS", "Pupil Center pachymetry, circle-marked Thinnest Location, K Max (Front), HWTW, acquisition/identity evidence; the Axial/Sagittal Curvature (Front) map supplies deterministic SRAX geometry."),
                ("Belin/Ambrósio BAD Display", "One OD and one OS", "Signed F.Ele.Th and B.Ele.Th; PPI Min/Avg/Max and ARTmax; Df/Db/Dp/Dt/Da and Final D; specific upper-middle K1/K2/Axis fields for their limited planning or validation roles."),
                ("Show 2 Exams Topometric", "One bilateral comparison page", "For each eye: Cornea Front K1/K2/axes/Km/Astig; Cornea Back Km and Rmin; center 8-mm indices including ISV, IVA, KI, CKI, IHA, IHD, RMin, TKC, KISA, and signed I-S."),
                ("Excimer treatment card", "Optional sixth image", "Only the labeled Düzeltme Miktarı row may supply treatment correction. If absent, the surgeon provides complete manifest and intended refraction for both eyes."),
            ), "All five Pentacam pages must be identified before targeted rereading, geometric SRAX analysis, clinical scoring, or report generation. A duplicate page never substitutes for a missing source family."),
            ("Source-locked field map", ("Registered region", "Accepted fields", "Prohibited substitution"), (
                ("Show 2 → Cornea Front", "K1, K1 axis, K2, K2 axis, printed Km, Astig and steep axis", "No Cornea Back, Kmax, True Net Power, map spot, or calculated mean"),
                ("Show 2 → Cornea Back", "Printed posterior Km and posterior Rmin", "No Cornea Front Rmin or center topometric RMin"),
                ("Show 2 → center Indices (8 mm)", "ISV, IVA, KI, CKI, IHA, IHD, topometric RMin, TKC, KISA, signed I-S", "No index may substitute for I-S; preserve the printed sign"),
                ("4 Maps → lower-left labeled box", "Pupil Center pachymetry, Thinnest Location pachymetry, K Max (Front), HWTW", "No Pachy Vertex, map color/spot, or neighboring number"),
                ("BAD → elevation row", "Signed F.Ele.Th and B.Ele.Th in µm", "No elevation-map spot, K field, or unlabeled value"),
                ("BAD → Progression Index", "PPI Min/Avg/Max and ARTmax", "No back-calculation of Dp or Da"),
                ("BAD → bottom D strip", "Df, Db, Dp, Dt, Da, Final D", "No reconstruction of any component or Final D"),
            ), "The registry distinguishes fields that look similar. In particular, posterior Rmin and center topometric RMin are separate measurements, and BAD upper-middle K1/K2 are reserved for the ML7 planning role rather than general scoring keratometry."),
            ("From image to auditable report", ("Stage", "What CER-AI does", "Safety behavior"), (
                ("1. Page identity", "Confirms screen family, OD/OS laterality, patient/exam identity, and the five-source set", "Assessment does not start when a mandatory source is missing or unidentified"),
                ("2. Primary transcription", "Reads labeled numeric boxes and records exact canonical source IDs", "Wrong-screen or inferred values are rejected"),
                ("3. Reconciliation", "Merges readings only when field, eye, and source agree", "Same-source disagreement clears the field; it is never averaged"),
                ("4. Targeted reread", "Re-examines the exact missing or unreadable box", "The prompt remains field- and source-specific"),
                ("5. Surgeon completion", "Accepts an explicit surgeon-entered or confirmed value where permitted", "Surgeon input is authoritative and labeled SURGEON_CONFIRMED"),
                ("6. Clinical adapter/report", "Maps resolved values into ERSS, BAD-D, NICE, PS3, safety, then copies computed results and provenance into the report", "The PDF/Word renderer does not rescore the case"),
            ), "The image model transcribes dates and printed values; deterministic code calculates age, refraction normalization, SRAX geometry, scores, safety formulas, and final disposition."),
        ),
        "topometric-indices": (
            ("What each 8-mm topometric index describes", ("Index", "Technical meaning", "CER-AI role"), (
                ("ISV", "Standard deviation of individual sagittal radii from mean curvature; a global surface-irregularity descriptor", "Reported context; not an independent CER-AI disposition gate"),
                ("IVA", "Mean superior–inferior curvature difference relative to the horizontal meridian", "Reported context; not substituted for signed I-S"),
                ("KI", "Ratio of mean radius values in the superior and inferior corneal halves", "Reported context"),
                ("CKI", "Ratio of peripheral-ring to central-ring mean radius; emphasizes central steepening", "Reported context"),
                ("IHA", "Mean superior–inferior difference in corneal elevation along the horizontal meridian", "Reported context"),
                ("IHD", "Vertical decentration of elevation data derived by Fourier analysis on a 3-mm-radius ring", "Reported context"),
                ("RMin", "Smallest axial/sagittal curvature radius across the measurement area", "Center topometric index; distinct from posterior Cornea Back Rmin"),
                ("TKC", "Pentacam anterior-surface topographic keratoconus classification", "Reported device classification; not an autonomous CER-AI diagnosis"),
                ("KISA%", "Composite of central K, I-S, corneal astigmatism, and SRAX", "Reported device index; CER-AI does not reverse-engineer its inputs from KISA"),
                ("Signed I-S", "Printed inferior–superior dioptric asymmetry with sign preserved", "Direct numeric input to CER-AI ERSS topography and NICE; never replaced by ISV/IVA/IHD/IHA/KISA"),
            ), "Definitions follow the OCULUS Pentacam Interpretation Guide. Device colors and thresholds describe the Pentacam reference framework; CER-AI preserves these indices as source-linked context unless a separate canonical pathway explicitly names the field."),
        ),
        "randleman-erss": (
            ("CER-AI ERSS component scoring", ("Component", "Current operational rule", "Points"), (
                ("Topography", "Normal/symmetric; asymmetric bow-tie; inferior steepening/SRAX; abnormal/ectatic", "0; 1; 3; 4"),
                ("LASIK RSB or PRK RST", ">=300; 280 to <300; 260 to <280; 240 to <260; <240 µm", "0; 1; 2; 3; 4"),
                ("Age", ">=21; 19 to <21; 18 to <19 years", "0; 2; 3"),
                ("Thinnest pachymetry", ">=510; 500 to <510; 480 to <500 µm", "0; 1; 2"),
                ("Manifest MRSE", ">=-8; <-8 to >=-10; <-10 to >=-12; <-12 to >=-14; <-14 D", "0; 1; 2; 3; 4"),
            ), "Age <18 is incomplete. Pachymetry <480 µm is not assigned an ERSS row score because it is an independent CER-AI STOP-DEFER. PRK uses RST for the tissue row; its independent RST hard stop is <310 µm."),
            ("From ERSS total to CER-AI pathway result", ("ERSS total", "CER-AI result", "Report behavior"), (
                ("0–2", "PASS", "Five rows, total, topography category, and disposition are reported."),
                ("3", "CAUTION", "Requires explicit surgeon review; does not alone impose the global final result."),
                (">=4", "STOP-DEFER", "Becomes a stop driver in the final report."),
                ("Critical input missing", "ASSESSMENT INCOMPLETE", "A complete report token is not issued until the required field is resolved."),
            ), "CER-AI does not convert the ordinal total into an individual lifetime probability."),
        ),
        "bad-d-component-indices": (
            ("Final BAD-D disposition", ("Final D", "Classification", "CER-AI pathway result"), (
                ("<=1.60", "Normal", "PASS"),
                (">1.60 and <2.60", "Suspicious", "CAUTION"),
                (">=2.60", "Abnormal", "STOP-DEFER"),
                ("Unavailable", "Unavailable", "ASSESSMENT INCOMPLETE"),
            ), "Final D is read from the BAD Display bottom strip. CER-AI never reconstructs it from Df, Db, Dp, Dt, or Da."),
            ("Context carried into the report", ("Field", "Meaning", "Decision role"), (
                ("Df / Db", "Anterior / posterior elevation deviation", "Context only"),
                ("Dp / Dt / Da", "Pachymetric progression, thinnest thickness, and ARTmax-related deviations", "Context only"),
                ("PPI min/avg/max; ARTmax", "Pachymetric progression and relational thickness", "Display/QC context; PPI Average has a separate PS3 rule"),
            ), "Component colors and contextual bands never add a second BAD-D caution or stop."),
        ),
        "nice-risk-assessment": (
            ("CER-AI-adapted NICE component scoring", ("Input", "1 point", "2 points", "3 points"), (
                ("K2", "<45 D", "45–47 D", ">47 D"),
                ("Central pachymetry", ">520 µm", "500–520 µm", "<500 µm"),
                ("B.Ele.Th", "<=15.5 µm", ">15.5 to <18 µm", ">=18 µm"),
                ("Signed I-S", "<1.00 D", "1.00–1.40 D", ">1.40 D"),
            ), "All four source-locked numeric inputs are required. Out-of-range or missing data make NICE incomplete rather than favorable."),
            ("From NICE total to CER-AI pathway result", ("Total", "Category", "CER-AI result"), (
                ("4", "No NICE escalation", "PASS"),
                ("5–8", "Caution", "CAUTION"),
                (">=9", "Hard stop", "STOP-DEFER"),
            ), "NICE remains independent; its points are never added to ERSS or PS3."),
        ),
        "ps3-risk-assessment": (
            ("Automated PS3 factors in CER-AI", ("Factor", "Moderate", "High"), (
                ("Anterior Km", "48–50 D", ">50 D"),
                ("Thinnest pachymetry", "470–500 µm", "<470 µm"),
                ("Elevation at thinnest", "—", "F.Ele.Th >12 µm or B.Ele.Th >15 µm"),
                ("PPI Average", ">1.20", "—"),
                ("Inter-eye asymmetry", "4 of 5 differences reach threshold", "5 of 5 differences reach threshold"),
                ("SRAX", "—", ">20° with nonnegative signed I-S and required surgeon confirmation"),
            ), "Inter-eye thresholds are anterior Km 0.3 D, posterior Km 0.1 D, thinnest pachymetry 12 µm, front elevation 2 µm, and back elevation 5 µm; equality counts as exceeded."),
            ("PS3 procedure disposition", ("Factor pattern", "LASIK", "PRK / SMILE"), (
                ("No Moderate or High; complete", "Allowed", "Allowed"),
                ("One Moderate; complete", "Defer", "Allowed"),
                (">=2 Moderate or >=1 High", "Defer", "Defer"),
                ("Required factor missing", "Incomplete unless already deferred", "Incomplete unless already deferred"),
            ), "Manual map-morphology review items remain visible but are not counted as automated factors."),
        ),
        "cer-ai-methodology": (
            ("How independent pathways become the final result", ("Condition", "Final disposition", "Priority"), (
                ("Any STOP-DEFER driver", "STOP-DEFER", "Overrides all other results"),
                ("No stop, but critical data incomplete", "ASSESSMENT INCOMPLETE", "Missingness is never converted to PASS"),
                ("Four systems complete; 0 or 1 CAUTION", "PASS", "Individual caution remains visible in its section"),
                ("Four systems complete; 2 CAUTION", "PASS WITH CAUTION", "Both drivers are listed"),
                ("Four systems complete; 3 or 4 CAUTION", "CAUTION", "All drivers are listed"),
                ("Independent non-system caution", "CAUTION", "Retains its own authority"),
            ), "The four counted systems are ERSS, Final BAD-D, NICE, and PS3. Tissue and clinical-eligibility stops remain independent; bilateral aggregation preserves the worse eye and does not add caution counts across eyes."),
            ("What the structured report carries", ("Report block", "Content", "Why it matters"), (
                ("ERSS", "Five component rows, points, total, topography category, disposition", "Auditable weighted score"),
                ("NICE", "Four inputs, points, total, category, disposition", "Auditable cumulative score"),
                ("PS3", "Every factor, exact finding, Moderate/High counts, procedure disposition", "Shows why a procedure is allowed, deferred, or incomplete"),
                ("BAD-D", "Final D, classification, status, component/PPI/ART context", "Separates the decision signal from context"),
                ("Safety and provenance", "RSB/RST, PTA, final-K checks, source fields, confirmations, versions", "Preserves independent constraints and traceability"),
            ), "PDF and Word reports consume the same already-computed canonical report payload; report rendering does not recalculate clinical rules."),
        ),
    },
    "tr": {
        "pentacam-education": (
            ("Cerrah yüklemesi ve kaynak doğrulaması", ("Zorunlu görüntü", "Cerrahın tanımlaması/doğrulaması", "Görüntü alma gerekliliği"), (
                ("1. 4 Maps Refractive — OD", "Sağ göz; 4 Maps Refractive", "Tam ekran, doğrudan karşıdan alınmış"),
                ("2. 4 Maps Refractive — OS", "Sol göz; 4 Maps Refractive", "Tam ekran, doğrudan karşıdan alınmış"),
                ("3. Belin/Ambrósio BAD Display — OD", "Sağ göz; BAD Display", "Alt D şeridi ve etiketli kutular görünür tam ekran"),
                ("4. Belin/Ambrósio BAD Display — OS", "Sol göz; BAD Display", "Alt D şeridi ve etiketli kutular görünür tam ekran"),
                ("5. Show 2 Exams Topometric", "Bilateral karşılaştırma; OD ve OS panelleri tanımlı", "Cornea Front, Cornea Back ve orta indeksler okunur tam ekran"),
            ), "Cerrah beş Pentacam kaynak görüntüsünün tamamını yüklemeli ve doğrulamalıdır. Net ekran görüntüsü veya ekrana dik, doğrudan karşıdan çekilmiş fotoğraf kullanın; açılı çekim kullanmayın. Bulanıklık, parlama, perspektif bozulması, sıkıştırma, kırpma, gölge ve kapalı etiketlerden kaçının. Düşük görüntü kalitesi alanı okunamaz veya tutarsız yapabilir; CER-AI değer tahmin etmek yerine daha net kaynak istemelidir. Net görüntü alma tutarlılığı destekler ancak klinik doğruluğu garanti etmez."),
            ("Standart 4 Maps Refractive kadran yerleşimi", ("Ekran konumu", "Zorunlu yazılı harita tipi", "CER-AI kullanımı ve çelişki kuralı"), (
                ("Sol üst", "Axial/Sagittal Curvature (Front)", "Deterministik SRAX geometri katmanı yalnız bu anterior/ön eğrilik haritasını kullanır."),
                ("Sağ üst", "Elevation (Front)", "Ön elevasyon örüntüsü incelemesi; BAD Display'deki etiketli F.Ele.Th değerinin yerine geçmez."),
                ("Sol alt", "Corneal Thickness / Pachymetry", "Uzaysal kalınlık örüntüsü incelemesi; karar alanları yine etiketli Pupil Center ve Thinnest Location değerlerinden gelir."),
                ("Sağ alt", "Elevation (Back)", "Arka elevasyon örüntüsü incelemesi; BAD Display B.Ele.Th veya Show 2 Cornea Back değerlerinin yerine geçmez."),
            ), "CER-AI standart ve tam 4 Maps Refractive yerleşimini ister; yazılı harita etiketini ve kadran konumunu birlikte doğrular. Özel/yeniden düzenlenmiş dört-harita yerleşimi yüklemeyin ve anterior sagittal eğrilik haritasını sağ taraftaki bir kadrana yerleştirmeyin. Etiket–konum uyumsuzluğu, ön/arka ikamesi, döndürme veya kırpma kaynak çelişkisidir; standart dışa aktarım ya da net karşıdan çekimle düzeltilmelidir."),
            ("Zorunlu Pentacam kaynak kümesi", ("Kaynak görüntü", "Zorunlu küme", "CER-AI çıkarım rolü"), (
                ("4 Maps Refractive", "Bir OD ve bir OS", "Pupil Center pakimetrisi, daireyle işaretli Thinnest Location, K Max (Front), HWTW ve çekim/kimlik kanıtı; Axial/Sagittal Curvature (Front) haritası deterministik SRAX geometrisini sağlar."),
                ("Belin/Ambrósio BAD Display", "Bir OD ve bir OS", "İşaretli F.Ele.Th ve B.Ele.Th; PPI Min/Avg/Max ve ARTmax; Df/Db/Dp/Dt/Da ve Final D; sınırlı planlama veya doğrulama rolleri için belirli üst-orta K1/K2/Axis alanları."),
                ("Show 2 Exams Topometric", "Bir bilateral karşılaştırma sayfası", "Her göz için: Cornea Front K1/K2/eksenler/Km/Astig; Cornea Back Km ve Rmin; ISV, IVA, KI, CKI, IHA, IHD, RMin, TKC, KISA ve işaretli I-S dahil orta 8 mm indeksleri."),
                ("Eksimer tedavi kartı", "İsteğe bağlı altıncı görüntü", "Yalnız etiketli Düzeltme Miktarı satırı tedavi düzeltmesini sağlayabilir. Kart yoksa cerrah iki göz için tam manifest ve hedeflenen refraksiyonu girer."),
            ), "Hedefli yeniden okuma, geometrik SRAX analizi, klinik skorlama veya rapor üretiminden önce beş Pentacam sayfasının tamamı tanımlanmalıdır. Yinelenen sayfa eksik kaynak ailesinin yerine geçmez."),
            ("Kaynağı kilitli alan haritası", ("Kayıtlı bölge", "Kabul edilen alanlar", "Yasak ikame"), (
                ("Show 2 → Cornea Front", "K1, K1 ekseni, K2, K2 ekseni, yazılı Km, Astig ve dik eksen", "Cornea Back, Kmax, True Net Power, harita noktası veya hesaplanmış ortalama yok"),
                ("Show 2 → Cornea Back", "Yazılı posterior Km ve posterior Rmin", "Cornea Front Rmin veya orta topometrik RMin yok"),
                ("Show 2 → orta Indices (8 mm)", "ISV, IVA, KI, CKI, IHA, IHD, topometrik RMin, TKC, KISA, işaretli I-S", "Hiçbir indeks I-S yerine geçmez; yazılı işaret korunur"),
                ("4 Maps → sol-alt etiketli kutu", "Pupil Center pakimetrisi, Thinnest Location pakimetrisi, K Max (Front), HWTW", "Pachy Vertex, harita rengi/noktası veya komşu sayı yok"),
                ("BAD → elevasyon satırı", "µm cinsinden işaretli F.Ele.Th ve B.Ele.Th", "Elevasyon haritası noktası, K alanı veya etiketsiz değer yok"),
                ("BAD → Progression Index", "PPI Min/Avg/Max ve ARTmax", "Dp veya Da geriye doğru hesaplanmaz"),
                ("BAD → alt D şeridi", "Df, Db, Dp, Dt, Da, Final D", "Hiçbir bileşen veya Final D yeniden oluşturulmaz"),
            ), "Kayıt sistemi benzer görünen alanları ayırır. Posterior Rmin ile orta topometrik RMin ayrı ölçümlerdir; BAD üst-orta K1/K2 ise genel skorlama keratometrisi değil, ML7 planlama rolüne ayrılmıştır."),
            ("Görüntüden denetlenebilir rapora", ("Aşama", "CER-AI ne yapar?", "Güvenlik davranışı"), (
                ("1. Sayfa kimliği", "Ekran ailesi, OD/OS tarafı, hasta/inceleme kimliği ve beş kaynaklı kümeyi doğrular", "Zorunlu kaynak eksik veya tanımsızsa değerlendirme başlamaz"),
                ("2. Birincil yazıya aktarma", "Etiketli sayısal kutuları okur ve kesin kanonik kaynak kimliklerini kaydeder", "Yanlış ekran veya çıkarıma dayalı değer reddedilir"),
                ("3. Uzlaştırma", "Okumaları yalnız alan, göz ve kaynak uyuştuğunda birleştirir", "Aynı kaynak çelişkisi alanı temizler; ortalama alınmaz"),
                ("4. Hedefli yeniden okuma", "Tam eksik veya okunamayan kutuyu yeniden inceler", "İstem alan ve kaynağa özgü kalır"),
                ("5. Cerrah tamamlaması", "İzin verilen durumda açık cerrah girişi veya doğrulamasını kabul eder", "Cerrah girdisi yetkilidir ve SURGEON_CONFIRMED olarak etiketlenir"),
                ("6. Klinik adaptör/rapor", "Çözülmüş değerleri ERSS, BAD-D, NICE, PS3 ve güvenliğe eşler; hesaplanmış sonuçlar ile kökeni rapora kopyalar", "PDF/Word oluşturucu olguyu yeniden skorlamaz"),
            ), "Görüntü modeli tarihleri ve yazılı değerleri aktarır; deterministik kod yaş, refraksiyon normalizasyonu, SRAX geometrisi, skorlar, güvenlik formülleri ve nihai kararı hesaplar."),
        ),
        "topometric-indices": (
            ("Her 8 mm topometrik indeks neyi tanımlar?", ("İndeks", "Teknik anlam", "CER-AI rolü"), (
                ("ISV", "Tek tek sagittal yarıçapların ortalama eğrilikten standart sapması; global yüzey düzensizliği tanımlayıcısı", "Raporlanan bağlam; bağımsız CER-AI karar kapısı değildir"),
                ("IVA", "Horizontal meridyene göre ortalama superior–inferior eğrilik farkı", "Raporlanan bağlam; işaretli I-S yerine kullanılmaz"),
                ("KI", "Korneanın üst ve alt yarısındaki ortalama yarıçap değerlerinin oranı", "Raporlanan bağlam"),
                ("CKI", "Periferik halka ile santral halka ortalama yarıçap oranı; santral dikleşmeyi vurgular", "Raporlanan bağlam"),
                ("IHA", "Horizontal meridyen boyunca superior–inferior korneal elevasyonun ortalama farkı", "Raporlanan bağlam"),
                ("IHD", "3 mm yarıçaplı halkada Fourier analiziyle hesaplanan elevasyon verisinin vertikal desantralizasyonu", "Raporlanan bağlam"),
                ("RMin", "Tüm ölçüm alanındaki en küçük aksiyel/sagittal eğrilik yarıçapı", "Orta topometrik indeks; posterior Cornea Back Rmin'den farklıdır"),
                ("TKC", "Pentacam ön yüz topografik keratokonus sınıflaması", "Raporlanan cihaz sınıflaması; otonom CER-AI tanısı değildir"),
                ("KISA%", "Santral K, I-S, korneal astigmatizma ve SRAX'ın bileşik indeksi", "Raporlanan cihaz indeksi; CER-AI girdileri KISA'dan geriye doğru üretmez"),
                ("İşaretli I-S", "İşareti korunmuş yazılı inferior–superior diyoptrik asimetri", "CER-AI ERSS topografisi ve NICE için doğrudan sayısal girdi; ISV/IVA/IHD/IHA/KISA ile değiştirilmez"),
            ), "Tanımlar OCULUS Pentacam Yorumlama Rehberi'ni izler. Cihaz renkleri ve eşikleri Pentacam referans çerçevesini tanımlar; ayrı bir kanonik yol alanı açıkça adlandırmadıkça CER-AI bu indeksleri kaynağa bağlı bağlam olarak korur."),
        ),
        "randleman-erss": (
            ("CER-AI ERSS bileşen puanlaması", ("Bileşen", "Güncel operasyonel kural", "Puan"), (
                ("Topografi", "Normal/simetrik; asimetrik papyon; inferior dikleşme/SRAX; anormal/ektatik", "0; 1; 3; 4"),
                ("LASIK RSB veya PRK RST", ">=300; 280–<300; 260–<280; 240–<260; <240 µm", "0; 1; 2; 3; 4"),
                ("Yaş", ">=21; 19–<21; 18–<19 yıl", "0; 2; 3"),
                ("En ince pakimetri", ">=510; 500–<510; 480–<500 µm", "0; 1; 2"),
                ("Manifest MRSE", ">=-8; <-8–>=-10; <-10–>=-12; <-12–>=-14; <-14 D", "0; 1; 2; 3; 4"),
            ), "18 yaş altı tamamlanmamıştır. <480 µm pakimetri, bağımsız CER-AI STOP-DEFER olduğu için ERSS satır puanı almaz. PRK doku satırında RST kullanır; bağımsız PRK RST durdurma sınırı <310 µm'dir."),
            ("ERSS toplamından CER-AI yol sonucuna", ("ERSS toplamı", "CER-AI sonucu", "Rapor davranışı"), (
                ("0–2", "PASS", "Beş satır, toplam, topografi kategorisi ve karar raporlanır."),
                ("3", "CAUTION", "Açık cerrah incelemesi ister; tek başına genel nihai sonucu dayatmaz."),
                (">=4", "STOP-DEFER", "Nihai raporda durdurma nedeni olur."),
                ("Kritik girdi eksik", "ASSESSMENT INCOMPLETE", "Alan çözülene kadar tam rapor belirteci üretilmez."),
            ), "CER-AI ordinal toplamı kişisel yaşam boyu olasılığa dönüştürmez."),
        ),
        "bad-d-component-indices": (
            ("Final BAD-D kararı", ("Final D", "Sınıflama", "CER-AI yol sonucu"), (
                ("<=1.60", "Normal", "PASS"),
                (">1.60 ve <2.60", "Şüpheli", "CAUTION"),
                (">=2.60", "Anormal", "STOP-DEFER"),
                ("Yok", "Kullanılamıyor", "ASSESSMENT INCOMPLETE"),
            ), "Final D, BAD Display alt şeridinden okunur. CER-AI bunu Df, Db, Dp, Dt veya Da'dan yeniden hesaplamaz."),
            ("Rapora taşınan bağlam", ("Alan", "Anlam", "Karar rolü"), (
                ("Df / Db", "Ön / arka elevasyon sapması", "Yalnız bağlam"),
                ("Dp / Dt / Da", "Pakimetrik progresyon, en ince kalınlık ve ARTmax ilişkili sapmalar", "Yalnız bağlam"),
                ("PPI min/avg/max; ARTmax", "Pakimetrik progresyon ve göreli kalınlık", "Ekran/KG bağlamı; PPI Average için ayrı PS3 kuralı vardır"),
            ), "Bileşen renkleri ve bağlamsal bantlar ikinci bir BAD-D uyarısı veya durdurması eklemez."),
        ),
        "nice-risk-assessment": (
            ("CER-AI-uyarlanmış NICE bileşen puanlaması", ("Girdi", "1 puan", "2 puan", "3 puan"), (
                ("K2", "<45 D", "45–47 D", ">47 D"),
                ("Santral pakimetri", ">520 µm", "500–520 µm", "<500 µm"),
                ("B.Ele.Th", "<=15.5 µm", ">15.5–<18 µm", ">=18 µm"),
                ("İşaretli I-S", "<1.00 D", "1.00–1.40 D", ">1.40 D"),
            ), "Kaynağı kilitli dört sayısal girdinin tamamı gerekir. Eksik veya geçersiz aralıktaki veri NICE'ı olumlu değil, tamamlanmamış yapar."),
            ("NICE toplamından CER-AI yol sonucuna", ("Toplam", "Kategori", "CER-AI sonucu"), (
                ("4", "NICE yükseltmesi yok", "PASS"),
                ("5–8", "Uyarı", "CAUTION"),
                (">=9", "Kesin durdurma", "STOP-DEFER"),
            ), "NICE bağımsız kalır; puanları ERSS veya PS3'e eklenmez."),
        ),
        "ps3-risk-assessment": (
            ("CER-AI'daki otomatik PS3 faktörleri", ("Faktör", "Orta", "Yüksek"), (
                ("Ön Km", "48–50 D", ">50 D"),
                ("En ince pakimetri", "470–500 µm", "<470 µm"),
                ("En ince noktada elevasyon", "—", "F.Ele.Th >12 µm veya B.Ele.Th >15 µm"),
                ("PPI Average", ">1.20", "—"),
                ("İki göz arası asimetri", "5 farktan 4'ü eşiğe ulaşır", "5 farktan 5'i eşiğe ulaşır"),
                ("SRAX", "—", "İşaretli I-S negatif değilken >20° ve gerekli cerrah doğrulaması"),
            ), "İki göz arası eşikler: ön Km 0.3 D, arka Km 0.1 D, en ince pakimetri 12 µm, ön elevasyon 2 µm ve arka elevasyon 5 µm; eşitlik aşım olarak sayılır."),
            ("PS3 işlem kararı", ("Faktör örüntüsü", "LASIK", "PRK / SMILE"), (
                ("Orta/Yüksek yok; tam", "Uygun", "Uygun"),
                ("Bir Orta; tam", "Ertele", "Uygun"),
                (">=2 Orta veya >=1 Yüksek", "Ertele", "Ertele"),
                ("Gerekli faktör eksik", "Önceden erteleme yoksa tamamlanmamış", "Önceden erteleme yoksa tamamlanmamış"),
            ), "Manuel harita morfolojisi maddeleri görünür kalır ancak otomatik faktör olarak sayılmaz."),
        ),
        "cer-ai-methodology": (
            ("Bağımsız yollar nihai sonuca nasıl dönüşür?", ("Koşul", "Nihai karar", "Öncelik"), (
                ("Herhangi bir STOP-DEFER nedeni", "STOP-DEFER", "Diğer bütün sonuçlara üstün gelir"),
                ("Durdurma yok, kritik veri eksik", "ASSESSMENT INCOMPLETE", "Eksiklik hiçbir zaman PASS'a çevrilmez"),
                ("Dört sistem tam; 0 veya 1 CAUTION", "PASS", "Tekil uyarı kendi bölümünde görünür kalır"),
                ("Dört sistem tam; 2 CAUTION", "PASS WITH CAUTION", "İki neden de listelenir"),
                ("Dört sistem tam; 3 veya 4 CAUTION", "CAUTION", "Bütün nedenler listelenir"),
                ("Sistem dışı bağımsız uyarı", "CAUTION", "Kendi karar yetkisini korur"),
            ), "Sayılan dört sistem ERSS, Final BAD-D, NICE ve PS3'tür. Doku ve klinik uygunluk durdurmaları bağımsız kalır; iki gözün birleşiminde daha olumsuz göz korunur, gözler arasında uyarı sayısı toplanmaz."),
            ("Yapılandırılmış rapor ne taşır?", ("Rapor bloğu", "İçerik", "Neden önemli?"), (
                ("ERSS", "Beş bileşen satırı, puanlar, toplam, topografi kategorisi, karar", "Denetlenebilir ağırlıklı skor"),
                ("NICE", "Dört girdi, puanlar, toplam, kategori, karar", "Denetlenebilir kümülatif skor"),
                ("PS3", "Her faktör, kesin bulgu, Orta/Yüksek sayısı, işlem kararı", "İşlemin neden uygun, ertelenmiş veya eksik olduğunu gösterir"),
                ("BAD-D", "Final D, sınıflama, durum, bileşen/PPI/ART bağlamı", "Karar sinyalini bağlamdan ayırır"),
                ("Güvenlik ve köken", "RSB/RST, PTA, final-K kontrolleri, kaynak alanları, doğrulamalar, sürümler", "Bağımsız kısıtları ve izlenebilirliği korur"),
            ), "PDF ve Word raporları önceden hesaplanmış aynı kanonik rapor yükünü kullanır; rapor oluşturma klinik kuralları yeniden hesaplamaz."),
        ),
    },
}


@dataclass(frozen=True)
class SampleCase:
    slug: str
    title: str
    summary: str
    inputs: tuple[tuple[str, str], ...]
    pathways: tuple[tuple[str, str, str], ...]
    final_result: str
    report_text: str
    learning_points: tuple[str, ...]


SAMPLE_CASES = (
    SampleCase("concordant-low-risk-lasik", "Case 1: concordant low-risk LASIK screen", "Synthetic example in which all four risk pathways and independent tissue-safety checks are complete.", (("Procedure", "LASIK"), ("Age / thinnest", "30 years / 540 µm"), ("I-S / SRAX", "-0.20 D / 10°"), ("Manifest MRSE", "-4.00 D"), ("Flap / ablation / RSB / PTA", "110 / 60 / 370 µm / 31.5%"), ("Final BAD-D", "1.20")), (("ERSS", "0", "PASS"), ("BAD-D", "1.20 normal", "PASS"), ("NICE", "4", "PASS"), ("PS3", "No Moderate/High factors", "PASS"), ("Tissue safety", "RSB 370 µm; PTA 31.5%", "PASS")), "PASS", "The report shows each pathway separately, preserves the source measurements, and states that PASS is decision support—not a guarantee of zero ectasia risk or autonomous surgical clearance.", ("Concordance strengthens interpretability but does not prove future stability.", "A negative signed I-S represents superior rather than inferior asymmetry; SRAX does not create an inferior-risk factor.", "All source identity, quality, eligibility, and surgeon-review requirements still apply.")),
    SampleCase("two-caution-pathways", "Case 2: two independent caution pathways", "Synthetic LASIK example showing why CER-AI does not hide discordance inside one average score.", (("Procedure", "LASIK"), ("Age / thinnest", "25 years / 505 µm"), ("I-S / SRAX", "+0.80 D / 15°"), ("Manifest MRSE", "-5.00 D"), ("Flap / ablation / RSB", "110 / 70 / 325 µm"), ("Final BAD-D", "2.00"), ("NICE inputs", "K2 46 D; central 505 µm; B.Ele.Th 16 µm; I-S 0.80 D")), (("ERSS", "Topography 1 + pachymetry 1 = 2", "PASS"), ("BAD-D", "2.00 suspicious", "CAUTION"), ("NICE", "2 + 2 + 2 + 1 = 7", "CAUTION"), ("PS3", "Complete; no Moderate/High", "PASS"), ("Tissue safety", "Independent checks complete", "PASS")), "PASS WITH CAUTION", "The report lists BAD-D and NICE as separate caution drivers. Because exactly two of the four completed scoring systems are CAUTION and no stop is present, the combined result is PASS WITH CAUTION.", ("NICE points are not added to ERSS points.", "BAD-D component context does not create extra caution counts.", "The surgeon sees which pathways disagree and reviews the underlying maps.")),
    SampleCase("srax-ps3-stop", "Case 3: SRAX-driven defer", "Synthetic case demonstrating one geometric finding entering ERSS and PS3 under different internal rules without being double-counted across systems.", (("Procedure", "LASIK"), ("Age / thinnest", "28 years / 530 µm"), ("Signed I-S", "+0.20 D"), ("Measured SRAX", "25°; surgeon confirms >20°"), ("Final BAD-D / NICE", "1.20 / 4")), (("ERSS", "Topography category escalates to inferior steepening = 3", "CAUTION"), ("BAD-D", "Normal", "PASS"), ("NICE", "4", "PASS"), ("PS3", "SRAX High factor", "STOP-DEFER"), ("Tissue safety", "No independent stop in this example", "PASS")), "STOP-DEFER", "The report preserves the ERSS caution and the exact PS3 High finding. PS3's procedure disposition becomes a stop driver, and STOP-DEFER overrides all reassuring or caution results.", ("The same source observation may inform two named systems, but their internal arithmetic is never blended.", "Exactly 20.0° is negative; >20° is positive only under the signed-I-S and confirmation policy.", "A confirmed stop remains visible even when other pathways pass.")),
    SampleCase("incomplete-source", "Case 4: decision-critical source missing", "Synthetic example showing why missing tomography is not interpreted as normal.", (("Procedure", "PRK"), ("B.Ele.Th", "Unreadable / unavailable"), ("Other measurements", "Available but insufficient for complete NICE and PS3")), (("ERSS", "Complete", "PASS"), ("BAD-D", "Complete", "PASS"), ("NICE", "B.Ele.Th missing", "ASSESSMENT INCOMPLETE"), ("PS3", "Elevation factor not evaluated", "ASSESSMENT INCOMPLETE"), ("Report gate", "Decision-critical dependency unresolved", "No complete report token")), "ASSESSMENT INCOMPLETE", "CER-AI requests the exact missing BAD Display field or surgeon-confirmed value. It does not infer zero elevation, reuse a similarly named field, or issue a reassuring completed report.", ("Missingness is a workflow state, not a low-risk observation.", "Source-specific rereading protects against field interchange.", "The report becomes available only after completeness and integrity gates are satisfied.")),
)

TR_SAMPLE_CASES = (
    SampleCase("concordant-low-risk-lasik", "Olgu 1: uyumlu düşük riskli LASIK taraması", "Dört risk yolunun ve bağımsız doku güvenliği kontrollerinin tamamlandığı sentetik örnek.", (("İşlem", "LASIK"), ("Yaş / en ince", "30 yıl / 540 µm"), ("I-S / SRAX", "-0.20 D / 10°"), ("Manifest MRSE", "-4.00 D"), ("Flep / ablasyon / RSB / PTA", "110 / 60 / 370 µm / %31.5"), ("Final BAD-D", "1.20")), (("ERSS", "0", "PASS"), ("BAD-D", "1.20 normal", "PASS"), ("NICE", "4", "PASS"), ("PS3", "Orta/Yüksek faktör yok", "PASS"), ("Doku güvenliği", "RSB 370 µm; PTA %31.5", "PASS")), "PASS", "Rapor her yolu ayrı gösterir, kaynak ölçümlerini korur ve PASS'ın sıfır ektazi riskini garanti etmediğini ve otonom cerrahi onay olmadığını belirtir.", ("Uyum yorumlanabilirliği güçlendirir ancak gelecekteki stabiliteyi kanıtlamaz.", "Negatif işaretli I-S superior asimetriyi gösterir; SRAX inferior risk faktörü oluşturmaz.", "Kaynak kimliği, kalite, uygunluk ve cerrah inceleme gereklilikleri devam eder.")),
    SampleCase("two-caution-pathways", "Olgu 2: iki bağımsız uyarı yolu", "CER-AI'ın uyumsuzluğu tek ortalama skor içinde neden gizlemediğini gösteren sentetik LASIK örneği.", (("İşlem", "LASIK"), ("Yaş / en ince", "25 yıl / 505 µm"), ("I-S / SRAX", "+0.80 D / 15°"), ("Manifest MRSE", "-5.00 D"), ("Flep / ablasyon / RSB", "110 / 70 / 325 µm"), ("Final BAD-D", "2.00"), ("NICE girdileri", "K2 46 D; santral 505 µm; B.Ele.Th 16 µm; I-S 0.80 D")), (("ERSS", "Topografi 1 + pakimetri 1 = 2", "PASS"), ("BAD-D", "2.00 şüpheli", "CAUTION"), ("NICE", "2 + 2 + 2 + 1 = 7", "CAUTION"), ("PS3", "Tam; Orta/Yüksek yok", "PASS"), ("Doku güvenliği", "Bağımsız kontroller tam", "PASS")), "PASS WITH CAUTION", "Rapor BAD-D ve NICE'ı ayrı uyarı nedenleri olarak listeler. Dört tamamlanmış skorlama sisteminin tam ikisi CAUTION olduğundan ve durdurma bulunmadığından birleşik sonuç PASS WITH CAUTION olur.", ("NICE puanları ERSS puanlarına eklenmez.", "BAD-D bileşen bağlamı ek uyarı sayısı oluşturmaz.", "Cerrah hangi yolların uyumsuz olduğunu görür ve alttaki haritaları inceler.")),
    SampleCase("srax-ps3-stop", "Olgu 3: SRAX kaynaklı erteleme", "Tek geometrik bulgunun sistemler arası çift sayım yapılmadan ERSS ve PS3'e farklı iç kurallarla girmesini gösteren sentetik olgu.", (("İşlem", "LASIK"), ("Yaş / en ince", "28 yıl / 530 µm"), ("İşaretli I-S", "+0.20 D"), ("Ölçülen SRAX", "25°; cerrah >20° olduğunu doğrular"), ("Final BAD-D / NICE", "1.20 / 4")), (("ERSS", "Topografi inferior dikleşmeye yükselir = 3", "CAUTION"), ("BAD-D", "Normal", "PASS"), ("NICE", "4", "PASS"), ("PS3", "SRAX Yüksek faktör", "STOP-DEFER"), ("Doku güvenliği", "Bu örnekte bağımsız durdurma yok", "PASS")), "STOP-DEFER", "Rapor ERSS uyarısını ve kesin PS3 Yüksek bulgusunu korur. PS3 işlem kararı durdurma nedeni olur ve STOP-DEFER bütün olumlu veya uyarılı sonuçlara üstün gelir.", ("Aynı kaynak gözlem iki adlandırılmış sistemi bilgilendirebilir; iç aritmetikleri birleştirilmez.", "Tam 20.0° negatiftir; yalnızca >20° işaretli I-S ve doğrulama politikasında pozitiftir.", "Doğrulanmış durdurma diğer yollar geçse bile görünür kalır.")),
    SampleCase("incomplete-source", "Olgu 4: karar için kritik kaynak eksik", "Eksik tomografinin neden normal olarak yorumlanmadığını gösteren sentetik örnek.", (("İşlem", "PRK"), ("B.Ele.Th", "Okunamıyor / yok"), ("Diğer ölçümler", "Var; ancak NICE ve PS3'ü tamamlamak için yetersiz")), (("ERSS", "Tam", "PASS"), ("BAD-D", "Tam", "PASS"), ("NICE", "B.Ele.Th eksik", "ASSESSMENT INCOMPLETE"), ("PS3", "Elevasyon faktörü değerlendirilmedi", "ASSESSMENT INCOMPLETE"), ("Rapor kapısı", "Karar-kritik bağımlılık çözülmedi", "Tam rapor belirteci yok")), "ASSESSMENT INCOMPLETE", "CER-AI tam eksik BAD Display alanını veya cerrahça doğrulanmış değeri ister. Elevasyonu sıfır varsaymaz, benzer adlı alanı kullanmaz ve güven verici tamamlanmış rapor üretmez.", ("Eksiklik düşük risk gözlemi değil, iş akışı durumudur.", "Kaynağa özgü yeniden okuma alan değişimini önler.", "Rapor yalnız tamlık ve bütünlük kapıları karşılandıktan sonra kullanılabilir.")),
)


def _head(base: str, canonical_path: str, title: str, description: str, robots: str, schema: dict, locale: str) -> str:
    canonical = f"{base}{canonical_path}"
    english_path = canonical_path[3:] if canonical_path.startswith("/tr/") else canonical_path
    turkish_path = f"/tr{english_path}"
    return f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} | CER-AI Learning Center</title>
<meta name="description" content="{escape(description, quote=True)}">
<meta name="robots" content="{escape(robots, quote=True)}">
<meta name="author" content="Hüseyin Cengiz, M.D.">
<meta name="copyright" content="© 2026 Hüseyin Cengiz, M.D. CER-AI. All rights reserved.">
<link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="en" href="{base}{english_path}">
<link rel="alternate" hreflang="tr" href="{base}{turkish_path}">
<link rel="alternate" hreflang="x-default" href="{base}{english_path}">
<link rel="describedby" type="text/markdown" href="{base}/llms.txt">
<link rel="stylesheet" href="/static/technical-public.css?v=4">
<link rel="icon" type="image/png" sizes="32x32" href="/static/icons/favicon-32.png?v=8">
<meta name="theme-color" content="#05090d">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False, separators=(",", ":"))}</script>"""


def _path(locale: str, path: str) -> str:
    return f"/tr{path}" if locale == "tr" else path


def _nav(locale: str, current_path: str) -> str:
    if locale == "tr":
        switch_path = current_path[3:] if current_path.startswith("/tr/") else "/learning-center"
        labels = ("Öğrenme Merkezi", "Kanıt", "Kaynaklar", "Klinik Uygulama", "English")
        aria = "Öğrenme Merkezi menüsü"
    else:
        switch_path = f"/tr{current_path}"
        labels = ("Learning Center", "Evidence", "References", "Clinical Application", "Türkçe")
        aria = "Learning Center navigation"
    return f"""<header class="learning-header"><div class="learning-wrap learning-nav"><a class="learning-brand" href="/">CER-AI</a><nav aria-label="{aria}"><a href="{_path(locale, '/learning-center')}">{labels[0]}</a><a href="/clinical-evidence">{labels[1]}</a><a href="/references">{labels[2]}</a><a class="language-link" hreflang="{'en' if locale == 'tr' else 'tr'}" lang="{'en' if locale == 'tr' else 'tr'}" href="{switch_path}">{labels[4]}</a><a class="learning-app-link" href="/app">{labels[3]}</a></nav></div></header>"""


def _footer(locale: str) -> str:
    if locale == "tr":
        principle = "Eğitim bilimi açıklar; yapılandırılmış değerlendirmeyi CER-AI uygulaması yapar. Eğitim içeriği muayene, görüntü kalitesi incelemesi, klinik karar veya cerrah sorumluluğunun yerini tutmaz."
        rights = "CER-AI'ın sahibi ve geliştiricisi Hüseyin Cengiz, M.D.'dir. © 2026 Tüm hakları saklıdır."
    else:
        principle = "Education explains the science; the CER-AI application performs the structured assessment. Educational content does not replace examination, image-quality review, clinical judgment, or surgeon responsibility."
        rights = "CER-AI is owned and developed by Hüseyin Cengiz, M.D. © 2026 All rights reserved."
    return f"""<footer class="learning-footer"><div class="learning-wrap"><strong>CER-AI Learning Center</strong><p>{principle}</p><p class="learning-rights">{rights}</p></div></footer>"""


def _breadcrumb(items: tuple[tuple[str, str], ...]) -> str:
    return '<nav class="breadcrumbs" aria-label="Breadcrumb">' + "<span aria-hidden=\"true\">›</span>".join(
        f'<a href="{escape(url, quote=True)}">{escape(label)}</a>' if url else f'<span aria-current="page">{escape(label)}</span>'
        for label, url in items
    ) + "</nav>"


def _technical_tables(locale: str, slug: str) -> str:
    specs = TECHNICAL_TABLES.get(locale, {}).get(slug, ())
    if not specs:
        return ""
    blocks = []
    for title, headers, rows, note in specs:
        head = "".join(f"<th scope=\"col\">{escape(item)}</th>" for item in headers)
        body = "".join("<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in row) + "</tr>" for row in rows)
        blocks.append(f'<section class="technical-table-section"><h2>{escape(title)}</h2><div class="table-scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div><p class="table-note">{escape(note)}</p></section>')
    return "".join(blocks)


def _case_cards(locale: str) -> str:
    cases = TR_SAMPLE_CASES if locale == "tr" else SAMPLE_CASES
    label = "Olguya git" if locale == "tr" else "Open worked case"
    return "".join(f'<article class="learning-card case-card"><span>{"Sentetik eğitim olgusu" if locale == "tr" else "Synthetic teaching case"}</span><h3><a href="{_path(locale, f"/learning/cases/{case.slug}")}">{escape(case.title)}</a></h3><p>{escape(case.summary)}</p><a class="text-link" href="{_path(locale, f"/learning/cases/{case.slug}")}">{label} <span aria-hidden="true">→</span></a></article>' for case in cases)


def render_hub(base: str, robots: str, locale: str = "en") -> str:
    path = _path(locale, "/learning-center")
    topics = TR_TOPICS if locale == "tr" else TOPICS
    if locale == "tr":
        description = "Korneal ektazi, Pentacam, BAD-D, topometrik indeksler, ERSS, NICE, PS3, doku güvenliği, olgular ve CER-AI metodolojisi için cerrah eğitimi."
        title = "Cerrah Eğitimi"
        breadcrumb = (("Ana Sayfa", "/"), ("Öğrenme Merkezi", ""))
        hero = ("Cerrah eğitimi", "CER-AI Öğrenme Merkezi", "Oftalmologlar ve refraktif cerrahlar için korneal ektazi taramasına yönelik yapılandırılmış, kanıt bağlantılı ve teknik rehber.")
        curriculum = ("Müfredat", "Klinik soruya göre öğrenin", "Her modül kanıt sınırlarını belirtir; birincil literatüre veya üretici dokümantasyonuna bağlanır. Hiçbir eğitim sayfası hastaya özgü sonuç hesaplamaz.", "Modülü aç")
    else:
        description = "CER-AI surgeon education on corneal ectasia, Pentacam, BAD-D, topometric indices, ERSS, NICE, PS3, map patterns, tissue safety, cases, and methodology."
        title = "Surgeon Education"
        breadcrumb = (("Home", "/"), ("Learning Center", ""))
        hero = ("Surgeon education", "CER-AI Learning Center", "A structured, evidence-linked technical guide to corneal ectasia screening for ophthalmologists and refractive surgeons.")
        curriculum = ("Curriculum", "Learn by clinical question", "Each module names its evidence limits and links to primary literature or manufacturer documentation. No educational page calculates a patient result.", "Open module")
    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "@id": f"{base}{path}#page",
        "url": f"{base}{path}",
        "name": hero[1],
        "description": description,
        "audience": {"@type": "MedicalAudience", "audienceType": "Ophthalmologists and refractive surgeons"},
        "hasPart": [{"@type": "MedicalWebPage", "name": t.title, "url": f"{base}{_path(locale, f'/learning/{t.slug}')}"} for t in topics],
        "isPartOf": {"@id": f"{base}/#website"},
        "inLanguage": locale,
        "copyrightHolder": {"@type": "Person", "name": "Hüseyin Cengiz, M.D."},
        "copyrightYear": 2026,
    }
    cards = "".join(
        f'<article class="learning-card"><span>{escape(t.eyebrow)}</span><h2><a href="{_path(locale, f"/learning/{t.slug}")}">{escape(t.title)}</a></h2><p>{escape(t.description)}</p><a class="text-link" href="{_path(locale, f"/learning/{t.slug}")}">{curriculum[3]} <span aria-hidden="true">→</span></a></article>'
        for t in topics
    )
    if locale == "tr":
        boundary = ("Temel sınır", "Eğitim bilimi açıklar; yapılandırılmış değerlendirmeyi CER-AI uygulaması yapar.")
        case_head = ("Çalışılmış örnekler", "Sentetik olgular ve rapor akışı", "Girdilerin ayrı risk yollarına, güvenlik kontrollerine ve yapılandırılmış rapora nasıl dönüştüğünü adım adım izleyin.")
        resources = '<div><p class="learning-kicker">Kanıt kütüphanesi</p><h2>İfadeleri kaynaklarına kadar izleyin</h2><p>Yol düzeyinde yorum için klinik kanıt haritasını, eksiksiz bibliyografya için aranabilir kayıt sistemini kullanın.</p><div class="learning-actions"><a class="learning-button" href="/clinical-evidence">Klinik kanıt</a><a class="learning-button secondary" href="/references">Kaynak kayıt sistemi</a></div></div><div><p class="learning-kicker">Sorular</p><h2>SSS ve eğitim asistanı sınırı</h2><p>Kısa yanıtları okuyun ve planlanan asistanın hastaya özgü klinik değerlendirmeden nasıl ayrı kalacağını görün.</p><div class="learning-actions"><a class="learning-button" href="/tr/learning/faq">SSS\'yi aç</a></div></div>'
    else:
        boundary = ("Core boundary", "Education explains the science; the CER-AI application performs the structured assessment.")
        case_head = ("Worked examples", "Synthetic cases and report flow", "Follow how source inputs become independent risk pathways, safety checks, and a structured report.")
        resources = '<div><p class="learning-kicker">Evidence library</p><h2>Trace statements to their sources</h2><p>Use the clinical evidence map for pathway-level interpretation and the searchable registry for the complete bibliography.</p><div class="learning-actions"><a class="learning-button" href="/clinical-evidence">Clinical evidence</a><a class="learning-button secondary" href="/references">Reference registry</a></div></div><div><p class="learning-kicker">Questions</p><h2>FAQ and educational assistant boundary</h2><p>Read concise answers and see how the planned assistant remains separated from patient-specific assessment.</p><div class="learning-actions"><a class="learning-button" href="/learning/faq">Open FAQ</a></div></div>'
    return f"""<!doctype html><html lang="{locale}"><head>{_head(base, path, title, description, robots, schema, locale)}</head><body>{_nav(locale, path)}<main>
<section class="learning-hero"><div class="learning-wrap">{_breadcrumb(breadcrumb)}<p class="learning-kicker">{hero[0]}</p><h1>{hero[1]}</h1><p class="learning-lead">{hero[2]}</p><div class="learning-principle"><strong>{boundary[0]}</strong><span>{boundary[1]}</span></div></div></section>
<section class="learning-section"><div class="learning-wrap"><div class="learning-section-head"><p class="learning-kicker">{curriculum[0]}</p><h2>{curriculum[1]}</h2><p>{curriculum[2]}</p></div><div class="learning-grid">{cards}</div></div></section>
<section class="learning-section learning-alt"><div class="learning-wrap"><div class="learning-section-head"><p class="learning-kicker">{case_head[0]}</p><h2>{case_head[1]}</h2><p>{case_head[2]}</p></div><div class="learning-grid case-grid">{_case_cards(locale)}</div></div></section>
<section class="learning-section"><div class="learning-wrap learning-resource-grid">{resources}</div></section>
</main>{_footer(locale)}</body></html>"""


def render_topic(base: str, robots: str, topic: Topic, locale: str = "en") -> str:
    path = _path(locale, f"/learning/{topic.slug}")
    topics = TR_TOPICS if locale == "tr" else TOPICS
    schema = {
        "@context": "https://schema.org",
        "@type": "MedicalWebPage",
        "@id": f"{base}{path}#page",
        "url": f"{base}{path}",
        "name": topic.title,
        "description": topic.description,
        "about": {"@type": "MedicalCondition", "name": "Corneal ectasia"},
        "audience": {"@type": "MedicalAudience", "audienceType": "Ophthalmologists and refractive surgeons"},
        "citation": [url for _, url in topic.references if url.startswith("http")],
        "isPartOf": {"@id": f"{base}{_path(locale, '/learning-center')}#page"},
        "inLanguage": locale,
        "copyrightHolder": {"@type": "Person", "name": "Hüseyin Cengiz, M.D."},
        "copyrightYear": 2026,
    }
    sections = "".join(f"<section><h2>{escape(title)}</h2><p>{escape(body)}</p></section>" for title, body in topic.sections)
    references = "".join(f'<li><a href="{escape(url, quote=True)}">{escape(label)}</a></li>' for label, url in topic.references)
    related = [candidate for candidate in topics if candidate.slug != topic.slug][:3]
    related_cards = "".join(f'<a class="related-card" href="{_path(locale, f"/learning/{t.slug}")}"><span>{escape(t.eyebrow)}</span><strong>{escape(t.title)}</strong></a>' for t in related)
    if locale == "tr":
        crumbs = (("Ana Sayfa", "/"), ("Öğrenme Merkezi", "/tr/learning-center"), (topic.title, ""))
        scope = ("Eğitim kapsamı", "Bu modül güncel CER-AI uygulamasını açıklar. CER-AI klinik değerlendirmesi yapmaz veya klinik motoru değiştirmez.")
        sources = ("Seçilmiş kaynaklar", 'Daha geniş bağlam için <a href="/references">eksiksiz CER-AI tıbbi kaynak kayıt sistemine</a> bakın.')
        continue_label = "Öğrenmeye devam"
        evidence = ("Kanıt sınırı", "Klinik kanıt haritası")
    else:
        crumbs = (("Home", "/"), ("Learning Center", "/learning-center"), (topic.title, ""))
        scope = ("Educational scope", "This module explains concepts. It does not perform or change a CER-AI clinical assessment. Where stated, it documents the current CER-AI v0.7.71 implementation for transparent surgeon education.")
        sources = ("Selected sources", 'See the <a href="/references">complete CER-AI medical reference registry</a> for broader context.')
        continue_label = "Continue learning"
        evidence = ("Evidence boundary", "Clinical evidence map")
    cases = ""
    if topic.slug == "clinical-cases":
        cases = f'<section><h2>{"Çalışılmış sentetik olgular" if locale == "tr" else "Worked synthetic cases"}</h2><div class="learning-grid case-grid">{_case_cards(locale)}</div></section>'
    return f"""<!doctype html><html lang="{locale}"><head>{_head(base, path, topic.title, topic.description, robots, schema, locale)}</head><body>{_nav(locale, path)}<main>
<article><header class="learning-hero article-hero"><div class="learning-wrap">{_breadcrumb(crumbs)}<p class="learning-kicker">{escape(topic.eyebrow)}</p><h1>{escape(topic.title)}</h1><p class="learning-lead">{escape(topic.description)}</p><div class="learning-principle"><strong>{scope[0]}</strong><span>{scope[1]}</span></div></div></header>
<div class="learning-wrap article-layout"><div class="article-body">{sections}{_technical_tables(locale, topic.slug)}{cases}<section class="article-references"><h2>{sources[0]}</h2><ol>{references}</ol><p>{sources[1]}</p></section></div><aside class="article-aside"><p class="learning-kicker">{continue_label}</p>{related_cards}<a class="related-card evidence" href="/clinical-evidence"><span>{evidence[0]}</span><strong>{evidence[1]}</strong></a></aside></div></article>
</main>{_footer(locale)}</body></html>"""


def render_faq(base: str, robots: str, locale: str = "en") -> str:
    path = _path(locale, "/learning/faq")
    faqs = TR_FAQS if locale == "tr" else FAQS
    description = "CER-AI eğitimi, ektazi taraması, kanıt sınırları ve planlanan eğitim asistanı hakkında cerrah soruları." if locale == "tr" else "Frequently asked surgeon questions about CER-AI education, ectasia screening concepts, evidence boundaries, and the planned educational assistant."
    name = "CER-AI Öğrenme Merkezi SSS" if locale == "tr" else "CER-AI Learning Center FAQ"
    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "@id": f"{base}{path}#page",
        "url": f"{base}{path}",
        "name": name,
        "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs],
        "isPartOf": {"@id": f"{base}{_path(locale, '/learning-center')}#page"},
        "inLanguage": locale,
        "copyrightHolder": {"@type": "Person", "name": "Hüseyin Cengiz, M.D."},
        "copyrightYear": 2026,
    }
    items = "".join(f"<details><summary>{escape(q)}</summary><p>{escape(a)}</p></details>" for q, a in faqs)
    if locale == "tr":
        crumbs = (("Ana Sayfa", "/"), ("Öğrenme Merkezi", "/tr/learning-center"), ("SSS", ""))
        hero = ("Eğitim soruları", "SSS ve eğitim asistanı sınırı", "Kamusal öğrenme kaynaklarını kullanan cerrahlar için kısa ve kanıt sınırları belirlenmiş yanıtlar.")
        assistant = '<p class="learning-kicker">Planlanan asistan</p><h2>Yalnız kamusal eğitim</h2><p>Gelecekteki eğitim asistanı, atıf yapılmış kamusal bilgi tabanından yanıt verecek ve cerrahları ilgili modüllere yönlendirecektir.</p><ul><li>Hasta verisi yok</li><li>Klinik puanlama yok</li><li>Cerrahi karar yok</li><li>CER-AI motorunda değişiklik yok</li></ul><p>Kanıta bağlı erişim katmanı uygulanıp test edilene kadar CER-AI kamusal bir sohbet botunu klinik otorite olarak sunmaz.</p>'
        page_title = "SSS ve Eğitim Asistanı"
    else:
        crumbs = (("Home", "/"), ("Learning Center", "/learning-center"), ("FAQ", ""))
        hero = ("Educational questions", "FAQ and educational assistant boundary", "Concise, evidence-bounded answers for surgeons using the public learning resources.")
        assistant = '<p class="learning-kicker">Planned assistant</p><h2>Public education only</h2><p>The future educational assistant will answer from the cited public knowledge base and guide surgeons to relevant modules.</p><ul><li>No patient data</li><li>No clinical scoring</li><li>No surgical disposition</li><li>No modification of the CER-AI engine</li></ul><p>Until that evidence-linked retrieval layer is implemented and tested, CER-AI does not present a public chatbot as clinically authoritative.</p>'
        page_title = "FAQ and Educational Assistant"
    return f"""<!doctype html><html lang="{locale}"><head>{_head(base, path, page_title, description, robots, schema, locale)}</head><body>{_nav(locale, path)}<main>
<section class="learning-hero article-hero"><div class="learning-wrap">{_breadcrumb(crumbs)}<p class="learning-kicker">{hero[0]}</p><h1>{hero[1]}</h1><p class="learning-lead">{hero[2]}</p></div></section>
<section class="learning-section"><div class="learning-wrap faq-layout"><div>{items}</div><aside class="assistant-boundary">{assistant}</aside></div></section>
</main>{_footer(locale)}</body></html>"""


def render_case(base: str, robots: str, case: SampleCase, locale: str = "en") -> str:
    path = _path(locale, f"/learning/cases/{case.slug}")
    description = case.summary
    schema = {"@context": "https://schema.org", "@type": "MedicalWebPage", "@id": f"{base}{path}#page", "url": f"{base}{path}", "name": case.title, "description": description, "audience": {"@type": "MedicalAudience", "audienceType": "Ophthalmologists and refractive surgeons"}, "isPartOf": {"@id": f"{base}{_path(locale, '/learning/clinical-cases')}#page"}, "inLanguage": locale, "copyrightHolder": {"@type": "Person", "name": "Hüseyin Cengiz, M.D."}, "copyrightYear": 2026}
    input_rows = "".join(f"<tr><th scope=\"row\">{escape(label)}</th><td>{escape(value)}</td></tr>" for label, value in case.inputs)
    pathway_rows = "".join(f"<tr><th scope=\"row\">{escape(name)}</th><td>{escape(calculation)}</td><td><strong>{escape(status)}</strong></td></tr>" for name, calculation, status in case.pathways)
    points = "".join(f"<li>{escape(point)}</li>" for point in case.learning_points)
    if locale == "tr":
        crumbs = (("Ana Sayfa", "/"), ("Öğrenme Merkezi", "/tr/learning-center"), ("Klinik olgular", "/tr/learning/clinical-cases"), (case.title, ""))
        labels = ("Sentetik eğitim olgusu", "Gerçek hasta verisi değildir", "Bu çalışılmış örnek, güncel CER-AI v0.7.71 kurallarını öğretmek için oluşturulmuştur. Klinik karar değildir.", "Kaynak girdiler", "Alan", "Değer", "Yol değerlendirmesi", "Sistem", "Hesaplama / bulgu", "Sonuç", "Nihai CER-AI sonucu", "Rapor özeti", "Öğrenme noktaları")
        page_title = f"{case.title} — CER-AI eğitim olgusu"
    else:
        crumbs = (("Home", "/"), ("Learning Center", "/learning-center"), ("Clinical cases", "/learning/clinical-cases"), (case.title, ""))
        labels = ("Synthetic teaching case", "Not real patient data", "This worked example was created to teach the current CER-AI v0.7.71 rules. It is not a clinical decision.", "Source inputs", "Field", "Value", "Pathway evaluation", "System", "Calculation / finding", "Result", "Final CER-AI result", "Report summary", "Learning points")
        page_title = f"{case.title} — CER-AI teaching case"
    return f"""<!doctype html><html lang="{locale}"><head>{_head(base, path, page_title, description, robots, schema, locale)}</head><body>{_nav(locale, path)}<main><article><header class="learning-hero article-hero"><div class="learning-wrap">{_breadcrumb(crumbs)}<p class="learning-kicker">{labels[0]}</p><h1>{escape(case.title)}</h1><p class="learning-lead">{escape(case.summary)}</p><div class="learning-principle"><strong>{labels[1]}</strong><span>{labels[2]}</span></div></div></header><div class="learning-wrap case-detail"><section><h2>{labels[3]}</h2><div class="table-scroll"><table><thead><tr><th>{labels[4]}</th><th>{labels[5]}</th></tr></thead><tbody>{input_rows}</tbody></table></div></section><section><h2>{labels[6]}</h2><div class="table-scroll"><table><thead><tr><th>{labels[7]}</th><th>{labels[8]}</th><th>{labels[9]}</th></tr></thead><tbody>{pathway_rows}</tbody></table></div></section><section class="case-result"><p class="learning-kicker">{labels[10]}</p><h2>{escape(case.final_result)}</h2></section><section><h2>{labels[11]}</h2><p>{escape(case.report_text)}</p></section><section><h2>{labels[12]}</h2><ul>{points}</ul></section></div></article></main>{_footer(locale)}</body></html>"""


SAMPLE_CASE_BY_SLUG = {case.slug: case for case in SAMPLE_CASES}
TR_SAMPLE_CASE_BY_SLUG = {case.slug: case for case in TR_SAMPLE_CASES}
