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
            ("Quality precedes interpretation", "Acquisition quality, fixation, blinking, tear-film disturbance, decentration, and contact-lens effects can alter measurements. A quality warning does not automatically define the clinical result; it signals that the examination and the affected values require review or repeat acquisition when appropriate."),
            ("Compare patterns across channels", "Curvature describes optical shape, elevation describes surface position relative to a reference surface, and pachymetric progression describes spatial thickness behavior. Concordant abnormal findings are different from an isolated borderline value. Bilateral comparison and prior examinations can add context but do not replace inspection of each eye."),
        ),
        (
            ("OCULUS Pentacam manufacturer documentation", "https://www.oculus.de/en/documents/"),
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


FAQS = (
    ("Does the Learning Center perform a CER-AI assessment?", "No. Public education pages explain science and terminology. Patient-specific structured assessment occurs only in the protected clinical application."),
    ("Is Final BAD-D the same as an ectasia diagnosis?", "No. Final BAD-D is a composite tomographic deviation index. It must be interpreted with its components, raw maps, examination quality, and clinical context."),
    ("Can a normal ERSS exclude ectasia susceptibility?", "No screening system excludes every pathway to susceptibility. ERSS should be interpreted within its original evidence base and alongside contemporary tomography and clinical findings."),
    ("Are topography and tomography interchangeable?", "No. Curvature, elevation, and spatial pachymetry describe related but different corneal properties. Their source displays and units should remain explicit."),
    ("Does a cited study validate CER-AI?", "Not unless the study specifically evaluates CER-AI as a complete product. Most references support individual concepts, variables, or named risk systems."),
    ("Will the educational assistant give patient-specific advice?", "No. The planned assistant is restricted to the cited public knowledge base and educational navigation. It will not accept patient data, calculate a clinical disposition, or replace the clinical application or surgeon judgment."),
)


def _head(base: str, canonical_path: str, title: str, description: str, robots: str, schema: dict) -> str:
    canonical = f"{base}{canonical_path}"
    return f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} | CER-AI Learning Center</title>
<meta name="description" content="{escape(description, quote=True)}">
<meta name="robots" content="{escape(robots, quote=True)}">
<link rel="canonical" href="{canonical}">
<link rel="describedby" type="text/markdown" href="{base}/llms.txt">
<link rel="stylesheet" href="{base}/static/technical-public.css?v=2">
<link rel="icon" type="image/png" sizes="32x32" href="{base}/static/icons/favicon-32.png?v=8">
<meta name="theme-color" content="#05090d">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False, separators=(",", ":"))}</script>"""


def _nav() -> str:
    return """<header class="learning-header"><div class="learning-wrap learning-nav"><a class="learning-brand" href="/">CER-AI</a><nav aria-label="Learning Center navigation"><a href="/learning-center">Learning Center</a><a href="/clinical-evidence">Evidence</a><a href="/references">References</a><a class="learning-app-link" href="/app">Clinical Application</a></nav></div></header>"""


def _footer() -> str:
    return """<footer class="learning-footer"><div class="learning-wrap"><strong>CER-AI Learning Center</strong><p>Education explains the science; the CER-AI application performs the structured assessment. Educational content does not replace examination, image-quality review, clinical judgment, or surgeon responsibility.</p></div></footer>"""


def _breadcrumb(items: tuple[tuple[str, str], ...]) -> str:
    return '<nav class="breadcrumbs" aria-label="Breadcrumb">' + "<span aria-hidden=\"true\">›</span>".join(
        f'<a href="{escape(url, quote=True)}">{escape(label)}</a>' if url else f'<span aria-current="page">{escape(label)}</span>'
        for label, url in items
    ) + "</nav>"


def render_hub(base: str, robots: str) -> str:
    path = "/learning-center"
    description = "CER-AI surgeon education on corneal ectasia, Pentacam, BAD-D, topometric indices, ERSS, NICE, map patterns, tissue safety, cases, and methodology."
    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "@id": f"{base}{path}#page",
        "url": f"{base}{path}",
        "name": "CER-AI Learning Center",
        "description": description,
        "audience": {"@type": "MedicalAudience", "audienceType": "Ophthalmologists and refractive surgeons"},
        "hasPart": [{"@type": "MedicalWebPage", "name": t.title, "url": f"{base}/learning/{t.slug}"} for t in TOPICS],
        "isPartOf": {"@id": f"{base}/#website"},
        "inLanguage": "en",
    }
    cards = "".join(
        f'<article class="learning-card"><span>{escape(t.eyebrow)}</span><h2><a href="/learning/{t.slug}">{escape(t.title)}</a></h2><p>{escape(t.description)}</p><a class="text-link" href="/learning/{t.slug}">Open module <span aria-hidden="true">→</span></a></article>'
        for t in TOPICS
    )
    return f"""<!doctype html><html lang="en"><head>{_head(base, path, "Surgeon Education", description, robots, schema)}</head><body>{_nav()}<main>
<section class="learning-hero"><div class="learning-wrap">{_breadcrumb((("Home", "/"), ("Learning Center", "")))}<p class="learning-kicker">Surgeon education</p><h1>CER-AI Learning Center</h1><p class="learning-lead">A structured, evidence-linked guide to corneal ectasia screening for ophthalmologists and refractive surgeons.</p><div class="learning-principle"><strong>Core boundary</strong><span>Education explains the science; the CER-AI application performs the structured assessment.</span></div></div></section>
<section class="learning-section"><div class="learning-wrap"><div class="learning-section-head"><p class="learning-kicker">Curriculum</p><h2>Learn by clinical question</h2><p>Each module names its evidence limits and links to primary literature or manufacturer documentation. No educational page calculates a patient result.</p></div><div class="learning-grid">{cards}</div></div></section>
<section class="learning-section learning-alt"><div class="learning-wrap learning-resource-grid"><div><p class="learning-kicker">Evidence library</p><h2>Trace statements to their sources</h2><p>Use the clinical evidence map for pathway-level interpretation and the searchable registry for the complete bibliography.</p><div class="learning-actions"><a class="learning-button" href="/clinical-evidence">Clinical evidence</a><a class="learning-button secondary" href="/references">Reference registry</a></div></div><div><p class="learning-kicker">Questions</p><h2>FAQ and educational assistant boundary</h2><p>Read concise answers now and see how the planned educational assistant will remain separated from patient-specific clinical assessment.</p><div class="learning-actions"><a class="learning-button" href="/learning/faq">Open FAQ</a></div></div></div></section>
</main>{_footer()}</body></html>"""


def render_topic(base: str, robots: str, topic: Topic) -> str:
    path = f"/learning/{topic.slug}"
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
        "isPartOf": {"@id": f"{base}/learning-center#page"},
        "inLanguage": "en",
    }
    sections = "".join(f"<section><h2>{escape(title)}</h2><p>{escape(body)}</p></section>" for title, body in topic.sections)
    references = "".join(f'<li><a href="{escape(url, quote=True)}">{escape(label)}</a></li>' for label, url in topic.references)
    related = [candidate for candidate in TOPICS if candidate.slug != topic.slug][:3]
    related_cards = "".join(f'<a class="related-card" href="/learning/{t.slug}"><span>{escape(t.eyebrow)}</span><strong>{escape(t.title)}</strong></a>' for t in related)
    return f"""<!doctype html><html lang="en"><head>{_head(base, path, topic.title, topic.description, robots, schema)}</head><body>{_nav()}<main>
<article><header class="learning-hero article-hero"><div class="learning-wrap">{_breadcrumb((("Home", "/"), ("Learning Center", "/learning-center"), (topic.title, "")))}<p class="learning-kicker">{escape(topic.eyebrow)}</p><h1>{escape(topic.title)}</h1><p class="learning-lead">{escape(topic.description)}</p><div class="learning-principle"><strong>Educational scope</strong><span>This module explains concepts. It does not perform or change a CER-AI clinical assessment.</span></div></div></header>
<div class="learning-wrap article-layout"><div class="article-body">{sections}<section class="article-references"><h2>Selected sources</h2><ol>{references}</ol><p>See the <a href="/references">complete CER-AI medical reference registry</a> for broader context.</p></section></div><aside class="article-aside"><p class="learning-kicker">Continue learning</p>{related_cards}<a class="related-card evidence" href="/clinical-evidence"><span>Evidence boundary</span><strong>Clinical evidence map</strong></a></aside></div></article>
</main>{_footer()}</body></html>"""


def render_faq(base: str, robots: str) -> str:
    path = "/learning/faq"
    description = "Frequently asked surgeon questions about CER-AI education, ectasia screening concepts, evidence boundaries, and the planned educational assistant."
    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "@id": f"{base}{path}#page",
        "url": f"{base}{path}",
        "name": "CER-AI Learning Center FAQ",
        "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQS],
        "isPartOf": {"@id": f"{base}/learning-center#page"},
        "inLanguage": "en",
    }
    items = "".join(f"<details><summary>{escape(q)}</summary><p>{escape(a)}</p></details>" for q, a in FAQS)
    return f"""<!doctype html><html lang="en"><head>{_head(base, path, "FAQ and Educational Assistant", description, robots, schema)}</head><body>{_nav()}<main>
<section class="learning-hero article-hero"><div class="learning-wrap">{_breadcrumb((("Home", "/"), ("Learning Center", "/learning-center"), ("FAQ", "")))}<p class="learning-kicker">Educational questions</p><h1>FAQ and educational assistant boundary</h1><p class="learning-lead">Concise, evidence-bounded answers for surgeons using the public learning resources.</p></div></section>
<section class="learning-section"><div class="learning-wrap faq-layout"><div>{items}</div><aside class="assistant-boundary"><p class="learning-kicker">Planned assistant</p><h2>Public education only</h2><p>The future educational assistant will answer from the cited public knowledge base and guide surgeons to relevant modules.</p><ul><li>No patient data</li><li>No clinical scoring</li><li>No surgical disposition</li><li>No modification of the CER-AI engine</li></ul><p>Until that evidence-linked retrieval layer is implemented and tested, CER-AI does not present a public chatbot as clinically authoritative.</p></aside></div></section>
</main>{_footer()}</body></html>"""
