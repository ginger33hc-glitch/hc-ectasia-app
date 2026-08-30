"""Professional PDF/DOCX export guard: reference appendices, concise identity notice, and safe serialization."""
from io import BytesIO
import re
from threading import RLock
import reports

_orig_eye_metrics=reports._eye_metrics
_orig_tomo_rows=reports._tomography_rows

def _eye_metrics_no_morphology(eye):
    return [(k,v) for k,v in _orig_eye_metrics(eye) if k.strip().lower()!="morphology category"]

def _tomography_rows_no_morphology(extracted,eye_id):
    return [(k,v) for k,v in _orig_tomo_rows(extracted,eye_id) if k.strip().lower()!="morphology"]

reports._eye_metrics=_eye_metrics_no_morphology
reports._tomography_rows=_tomography_rows_no_morphology

from reportlab.platypus import Paragraph,Table,TableStyle,Spacer
from reportlab.lib import colors
from docx import Document
from docx.shared import Pt

IDENTITY_HEADING="PATIENT IDENTITY NOT VERIFIED - SURGEON CONFIRMATION REQUIRED"
PDF_BAD=[["Final BAD-D","CERAI interpretation / action"],["<=1.6","NORMAL"],[">1.6 to <3.0","SUSPICIOUS - REVIEW / NOT CLEARED"],[">=3.0","ABNORMAL CORNEA - DO NOT PROCEED"]]
ERSS=[
 ["Variable","Finding","Points"],
 ["Anterior topography","Normal / symmetrical","0"],["Anterior topography","Asymmetric bow-tie","1"],["Anterior topography","Inferior steepening / significant SRA-SRAX","3"],["Anterior topography","Abnormal ectatic pattern","4"],
 ["Residual stromal bed",">=300 um","0"],["Residual stromal bed","280-299 um","1"],["Residual stromal bed","260-279 um","2"],["Residual stromal bed","240-259 um","3"],["Residual stromal bed","<240 um","4"],
 ["Age","18-21","3"],["Age","22-25","2"],["Age","26-29","1"],["Age",">=30","0"],
 ["Preop corneal thickness","<450 um","4"],["Preop corneal thickness","451-480 um","3"],["Preop corneal thickness","481-510 um","2"],["Preop corneal thickness",">=510 um","0"],
 ["MRSE","<=8 D myopia","0"],["MRSE",">8-10 D","1"],["MRSE",">10-12 D","2"],["MRSE",">12-14 D","3"],["MRSE",">14 D","4"]
]
HC_NOTE="Published Randleman/ERSS table shown for reference. The CERAI engine intentionally uses CERAI-modified age and pachymetry rules; the displayed patient score must therefore be read from the CERAI score breakdown, not reconstructed from the published reference table."

_orig_pdf=reports.build_pdf
_orig_docx=reports.build_docx
_EXPORT_LOCK=RLock()

def _current_version():
    return str(getattr(reports,"APP_VERSION","unknown"))

def _sync_pdf_version(story):
    version=_current_version()
    for i,item in enumerate(story):
        if isinstance(item,Paragraph) and "Software v" in getattr(item,"text",""):
            text=re.sub(r"Software v[^ <]+",f"Software v{version}",item.text)
            story[i]=Paragraph(text,item.style)

def _sync_docx_version(data):
    version=_current_version()
    document=Document(BytesIO(data))
    changed=False
    for paragraph in document.paragraphs:
        if "Software v" in paragraph.text:
            for run in paragraph.runs:
                if "Software v" in run.text:
                    run.text=re.sub(r"Software v\S+",f"Software v{version}",run.text)
                    changed=True
            if not changed:
                paragraph.text=re.sub(r"Software v\S+",f"Software v{version}",paragraph.text)
                changed=True
    if not changed:return data
    output=BytesIO();document.save(output);return output.getvalue()

def _remove_pdf_identity_details(story):
    """Keep the identity-verification heading but suppress verbose source-by-source bullets."""
    start=next((i for i,x in enumerate(story) if isinstance(x,Paragraph) and getattr(x,'text','')==IDENTITY_HEADING),None)
    if start is None:return
    end=start+1
    while end < len(story):
        item=story[end]
        if isinstance(item,Paragraph) and getattr(getattr(item,'style',None),'name','')=='Section':break
        end+=1
    del story[start+1:end]

def build_pdf(payload):
    # The legacy report builder requires a temporary ReportLab build hook. Serialize the
    # complete hook lifetime so concurrent web requests cannot observe each other's patch.
    with _EXPORT_LOCK:
        orig_build=reports.SimpleDocTemplate.build
        def patched_build(doc,story,*a,**kw):
            _sync_pdf_version(story)
            _remove_pdf_identity_details(story)
            idx=next((i for i,x in enumerate(story) if isinstance(x,Paragraph) and getattr(x,'text','')=='Interpretation note'),len(story))
            styles=reports.getSampleStyleSheet()
            sec=reports.ParagraphStyle('HCRefSection',parent=styles['Heading2'],fontName='Helvetica-Bold',fontSize=10.5,leading=13,textColor=reports._rl(reports.NAVY),spaceBefore=10,spaceAfter=5)
            tiny=reports.ParagraphStyle('HCRefTiny',parent=styles['BodyText'],fontName='Helvetica',fontSize=7.2,leading=9,textColor=reports._rl(reports.GRAY))
            bad=Table(PDF_BAD,colWidths=[1.7*reports.inch,4.45*reports.inch],repeatRows=1)
            bad.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),reports._rl(reports.NAVY)),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),7.5),('GRID',(0,0),(-1,-1),.35,reports._rl(reports.LINE)),('BACKGROUND',(1,1),(1,1),reports._rl(reports.GREEN_FILL)),('BACKGROUND',(1,2),(1,2),reports._rl(reports.AMBER_FILL)),('BACKGROUND',(1,3),(1,3),reports._rl(reports.RED_FILL))]))
            erss=Table(ERSS,colWidths=[1.55*reports.inch,3.85*reports.inch,.75*reports.inch],repeatRows=1)
            erss.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),reports._rl(reports.NAVY)),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),7.1),('GRID',(0,0),(-1,-1),.35,reports._rl(reports.LINE))]))
            appendix=[Paragraph('CERAI BAD-D reference points',sec),bad,Paragraph('BAD-D is read from the Pentacam BAD display and is independent of Randleman/ERSS anterior-topography scoring.',tiny),Paragraph('Published Randleman / ERSS scoring points',sec),erss,Paragraph('Randleman anterior-topography points come only from a qualifying anterior curvature/topography image. On Pentacam 4 Maps Refractive this is the upper-left Axial/Sagittal Curvature (Front) panel. ERSS total: 0-2 low, 3 moderate, >=4 high.',tiny),Paragraph(HC_NOTE,tiny),Spacer(1,8)]
            story[idx:idx]=appendix
            return orig_build(doc,story,*a,**kw)
        reports.SimpleDocTemplate.build=patched_build
        try:return _orig_pdf(payload)
        finally:reports.SimpleDocTemplate.build=orig_build

def build_docx(payload):
    # Same serialization rule for the temporary helper hooks used by the legacy DOCX builder.
    with _EXPORT_LOCK:
        orig_heading=reports._add_heading
        orig_bullet=reports._add_bullet
        state={"suppress_identity":False}
        def patched_bullet(document,text):
            if state["suppress_identity"]:return None
            return orig_bullet(document,text)
        def patched_heading(document,text,level=1):
            if text==IDENTITY_HEADING:
                state["suppress_identity"]=True
                return orig_heading(document,text,level)
            state["suppress_identity"]=False
            if text=='Interpretation note':
                orig_heading(document,'CERAI BAD-D reference points',1)
                t=document.add_table(rows=1,cols=2);t.style='Table Grid';t.rows[0].cells[0].text='Final BAD-D';t.rows[0].cells[1].text='CERAI interpretation / action'
                for row in PDF_BAD[1:]:
                    c=t.add_row().cells;c[0].text=row[0];c[1].text=row[1]
                reports._style_doc_table(t,[1.6,4.25],header=True)
                p=document.add_paragraph('BAD-D is read from the Pentacam BAD display and is independent of Randleman/ERSS anterior-topography scoring.');p.runs[0].font.size=Pt(8)
                orig_heading(document,'Published Randleman / ERSS scoring points',1)
                e=document.add_table(rows=1,cols=3);e.style='Table Grid'
                for j,x in enumerate(ERSS[0]):e.rows[0].cells[j].text=x
                for row in ERSS[1:]:
                    c=e.add_row().cells
                    for j,x in enumerate(row):c[j].text=x
                reports._style_doc_table(e,[1.5,3.65,.7],header=True)
                for note in ('Randleman anterior-topography points come only from the anterior curvature/topography image; on Pentacam 4 Maps Refractive this is the upper-left Axial/Sagittal Curvature (Front) panel. ERSS total: 0-2 low, 3 moderate, >=4 high.',HC_NOTE):
                    p=document.add_paragraph(note);p.runs[0].font.size=Pt(8)
            return orig_heading(document,text,level)
        reports._add_heading=patched_heading
        reports._add_bullet=patched_bullet
        try:data=_orig_docx(payload)
        finally:
            reports._add_heading=orig_heading
            reports._add_bullet=orig_bullet
        return _sync_docx_version(data)

reports.build_pdf=build_pdf
reports.build_docx=build_docx