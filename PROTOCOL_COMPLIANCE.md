# HC Ectasia App v0.5 — Source Compliance Audit

Audit date: 25 August 2026  
Protocol: HC Preoperative Ectasia Risk Assessment for Corneal Refractive Surgery  
Evidence set: the 10 supplied source/review files dated through 24 August 2026, plus binding HC operational amendments.

## Compliance matrix

| Domain | Source/protocol requirement | Earlier finding | v0.5 implementation |
|---|---|---|---|
| Eye handling | Score each eye separately; never average discordant eyes | Used the most limiting value across all eyes in one decision | Separate OD/OS plans, scores, structural calculations, missing-data lists, and dispositions; overall status is only the least-favorable summary |
| Override gate | Definite KC/FFKC/PMD/unequivocal ectatic morphology overrides tissue metrics and score | No complete morphology category or override | Explicit morphology extraction; `ABNORMAL_ECTATIC` is a hard override and cannot be canceled by score/RSB/RST/PTA |
| LASIK | Use the published five-component ERSS and published categories | ERSS was not calculated | Topography, RSB, age, pachymetry, and MRSE points; 0–2 low, 3 moderate, ≥4 high |
| Placido definitions | Use visible morphology plus published `I-S ≥1.4 D` abnormal-pattern and `SRA/SRAX ≥20°` category definitions | Numeric I-S/SRAX data were extracted but unused | Deterministic scoring-category support is applied; a single numeric index is not relabeled as a definite keratoconus diagnosis/override |
| LASIK boundaries | Do not silently invent categories at the printed 450/510 µm ambiguity | Not addressed | Exactly 450 or 510 µm is left unscored and requires documented adjudication; `<480 µm` HC hard stop still applies independently |
| PRK | Do not transfer LASIK ERSS unchanged; use the provisional morphology/pachymetry/age hierarchy with limitations | No PRK-EWSS score | PRK-EWSS v1.0 with 0/2/5 morphology, 0/2/3/4 pachymetry, 0/1/2/3 age weights; instrument always labeled unvalidated |
| Pachymetry policy | HC hard stop `<480 µm`; exactly 480 does not trigger the cutoff | Implemented | Preserved and boundary-tested; all hard stops are accumulated even when other data are missing |
| PRK structure | Use 50 µm epithelium; PRK RST `<310 µm` hard stop | RST formula present | Preserved, with exact 310 allowed by that rule and tested |
| LASIK structure | RSB `<300 µm` hard stop | Present | Preserved, with exact 300 allowed by that rule and tested |
| PTA | LASIK `(flap + ablation)/CCT`; PRK `(50 + ablation)/CCT` | Returned one flap-based PTA irrespective of procedure | Separate procedure-correct PTA values |
| Ablation estimate | HC conventions: Alcon EX500 `12 µm/D` at a 6.0-mm optical zone and `15 µm/D` at a 6.5-mm optical zone; actual plan is preferred | Applied one estimate to every platform/zone | A zone-specific estimate runs only when EX500 and either 6.0 or 6.5 mm are explicitly documented; otherwise actual maximum ablation is required. The 6.5-mm coefficient is a binding HC operational convention supplied for this implementation and is not independently validated by the supplied source set |
| Treatment-card input | Treatment intent must be traceable to the documented plan and must not be inferred from unrelated refraction rows | Manual entry only | Excimer Laser Takip Kartı values are extracted only from `Düzeltme Miktarı`, separately for SAĞ/OD and SOL/OS. Confident minus-cylinder values may fill only wholly empty correction fields; manual entries prevail, partial manual/extracted pairs are never mixed, and uncertainty/conflict/plus-cylinder notation blocks automatic transfer. The card never supplies or implies procedure, platform, optical zone, or ablation depth |
| PRK direct cohort | 310 µm is the cohort minimum, not a validated universal safe cutoff; PTA range to 35.28% is an evidence envelope | Not documented | HC 310 hard stop is explicitly labeled operational policy; `PRK PTA >35.28%` is labeled an evidence-gap flag, not proof of harm |
| BAD display | Components: `<1.6` normal, `1.6–<2.6` suspicious, `≥2.6` abnormal; final D `≤1.6` normal, `>1.6–<3.0` suspicious, `≥3.0` abnormal | Used `BAD-D ≥1.6` as a generic borderline rule and an unsupported composite with ARTmax | Boundary-specific display classification; no diagnostic or probability claim |
| ARTmax/TP/Dt/Da | Use as adjunctive cross-sectional concern flags, not validated post-refractive predictors | Unsupported `ARTmax <370` decision threshold | Removed `<370`; reports supplied cutoffs (`ARTmax ≤424`, TP `≤544`, Dt `≥−0.165`, Da `≥0.585`) only as adjunctive flags |
| Tomography flag disposition | A positive cross-sectional threshold is a review signal; do not present the tomography layer as reassuring | Flags were calculated but could coexist with `REASSURING` and `PASS` | Any supplied ARTmax/TP/Dt/Da concern flag changes the tomography layer to `CONCERN FLAGS` and requires `REVIEW — NOT CLEARED`; no ectasia diagnosis or probability is inferred |
| Multi-image conflicts | Conflicting extracted values must be surfaced and must not be silently treated as resolved | Some conflicts retained the first value and could still allow PASS | Every value conflict is recorded per eye, the more concerning value is retained for supported directional fields, and any unresolved conflict prohibits PASS |
| Image quality | Missing or unreliable imaging prohibits clearance | `LIMITED` quality could still allow PASS | Both `LIMITED` and `INADEQUATE` quality prohibit PASS |
| Anterior/posterior phenotype | Review both elevation maps, thickness distribution, and visibly available adjunctive parameters | Only a qualitative posterior pattern was required | Both anterior and posterior patterns are required; visibly printed elevation-at-TP, thinnest-point location, PPI-min/avg/max, topometric, volume, and HOA/coma fields are transcribed and reported without invented cutoffs |
| PRK direct-cohort PTA envelope | `>35.28%` is an evidence gap, not a validated harm cutoff; it cannot be called reassuring | The flag could coexist with PASS | The plan is labeled outside the supplied 2-year envelope and receives `REVIEW — NOT CLEARED`, not an ectasia diagnosis or hard stop |
| Treatment-range rules | Do not introduce source-untraceable hard stops | Sphere `<−10 D` and `>+6 D` were coded as hard stops without support in the supplied protocol/source set | Removed; hyperopic or mixed-meridian LASIK/PRK remains outside the predominantly myopic supplied scoring evidence and requires review; the linear HC ablation estimate is not used for such plans |
| Clinical modifiers | Record stability/progression, CDVA, eye rubbing, family history, and inter-eye asymmetry | Only binary stability was collected | Explicit yes/no/unknown collection; instability/progression defers, unexplained low CDVA/inter-eye asymmetry prevents clearance, other modifiers are reported without invented point weights |
| Missing data | Missing/unreliable topography, tomography, pachymetry, age, or plan inputs are unscorable; never issue PASS | Some missing fields were ignored; age was collected but unused | Required-data inventory per eye; no PASS when any critical input is missing/unreadable; no surgeon-confirmation checkbox |
| Caution | CAUTION is STOP/DEFER; repeat/re-evaluate after ≥6 months | Several non-protocol borderline labels without the binding action | One explicit `CAUTION — STOP/DEFER` status and action wording |
| Merge behavior | Use visibly supported values and identify conflicts | Missing flags persisted after later images supplied the value; worst image quality was retained | Resolved missing flags are cleared; best readable image quality is retained; conflicts generate warnings and specified conservative handling |

## Evidence versus HC policy

The software intentionally distinguishes two layers:

1. **Published evidence/instruments.** LASIK ERSS is a validated retrospective case-control score. PRK-EWSS is provisional and has no validated sensitivity, specificity, calibration, or risk probability. BAD and other Pentacam thresholds in the supplied studies are diagnostic/review signals, not prospective post-refractive ectasia predictors.
2. **Binding HC operational safety policy.** The `<480 µm` preoperative pachymetry, `<300 µm` LASIK RSB, and `<310 µm` PRK RST rules are enforced as hard stops. The supplied Li et al. appraisal does not independently validate 310 µm as a universal safe PRK cutoff; this limitation is displayed in every eye record.

## Source set checked

1. Randleman JB, Trattler WB, Stulting RD. *Validation of the Ectasia Risk Score System for Preoperative LASIK Screening* (2008).
2. Sorkin N et al. *Risk Assessment for Corneal Ectasia following PRK* (2017).
3. Moshirfar M et al. *Ectasia After Corneal Refractive Surgery: A Systematic Review* (2021).
4. Dupps WJ Jr, Wilson SE. *Biomechanics and Wound Healing in the Cornea* (2006).
5. Shams SS et al. *Effect of BAD-D on 2-year refractive outcomes of PRK* (2024).
6. Bamdad S et al. *Sensitivity and Specificity of BAD in Early Diagnosis of Keratoconus* (2020).
7. Maraghechi G et al. *Pentacam Indices in PRK Surgery* (2020).
8. Toprak I et al. *Revisiting Pentacam Parameters in Subclinical and Mild Keratoconus* (2023).
9. Focused appraisal of Li H et al. (2023) for the 310–348 µm PRK RST cohort envelope.
10. HC evidence reviews and the master protocol supplied on 25 August 2026.

## Remaining validation limit

Code-rule compliance does not establish clinical validity. Before production clinical reliance, v0.5 still requires prospective locked-rule validation against a labeled case set, image-extraction accuracy testing by screen type/device, and deployment testing with real de-identified cases. The software must not be described as a validated ectasia probability calculator or as autonomous surgical clearance.
