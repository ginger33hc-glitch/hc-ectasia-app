"""Patch professional PDF/DOCX exports: remove raw morphology rows and add reference tables."""
import reports

# Remove morphology from both the clinical metrics and extracted-tomography table.
_orig_eye_metrics=reports._eye_metrics
_orig_tomo_rows=reports._tomography_rows

def _eye_metrics_no_morphology(eye):
    return [(k,v) for k,v in _orig_eye_metrics(eye) if k.strip().lower()!="morphology category"]

def _tomography_rows_no_morphology(extracted,eye_id):
    return [(k,v) for k,v in _orig_tomo_rows(extracted,eye_id) if k.strip().lower()!="morphology"]

reports._eye_metrics=_eye_metrics_no_morphology
reports._tomography_rows=_tomography_rows_no_morphology

# Add reference appendices immediately before Interpretation note in both export builders by wrapping
# the document-generation primitives. This is deliberately export-side; browser DOM patches do not
# affect downloaded PDF/DOCX files.
from reportlab.platypus import Paragraph,Table,TableStyle,Spacer
from reportlab.lib import colors
from docx.shared import Pt

PDF_BAD=[["Final BAD-D","HC interpretation / action"],["<=1.6","NORMAL"],[">1.6 to <3.0","SUSPICIOUS - REVIEW / NOT CLEARED"],[">=3.0","ABNORMAL CORNEA - DO NOT PROCEED"]]
ERSS=[["Variable","Finding","Points"],["Anterior topography","Normal / symmetrical","0"],["Anterior topography","Asymmetric bow-tie","1"],["Anterior topography","Inferior steepening / significant SRA-SRAX","3"],["Anterior topography","Abnormal ectatic pattern","4"],["Residual stromal bed",">=300 um","0"],["Residual stromal bed","280-299 um","1"],["Residual stromal bed","260-279 um","2"],["Residual stromal bed","240-259 um","3"],["Residual stromal bed","<240 um","4"],["Age","18-21","3"],["Age","22-25","2"],["Age","26-29","1"],["Age",">=30","0"],["MRSE","<=8 D myopia","0"],["MRSE",">8-10 D","1"],["MRSE",">10-12 D","2"],["MRSE",">12-14 D","3"],["MRSE",">14 D","4"]]

# Monkey-patch Paragraph construction used by reports module. When the builder reaches its unique
# Interpretation-note heading, insert appendices into the same story/document first.
_orig_pdf=reports.build_pdf
_orig_docx=reports.build_docx

def build_pdf(payload):
    # Reimplement insertion by temporarily intercepting SimpleDocTemplate.build and splice before note.
    orig_build=reports.SimpleDocTemplate.build
    def patched_build(doc,story,*a,**kw):
        idx=next((i for i,x in enumerate(story) if isinstance(x,Paragraph) and getattr(x,'text','')=='Interpretation note'),len(story))
        styles=reports.getSampleStyleSheet()
        sec=reports.ParagraphStyle('HCRefSection',parent=styles['Heading2'],fontName='Helvetica-Bold',fontSize=10.5,leading=13,textColor=reports._rl(reports.NAVY),spaceBefore=10,spaceAfter=5)
        tiny=reports.ParagraphStyle('HCRefTiny',parent=styles['BodyText'],fontName='Helvetica',fontSize=7.2,leading=9,textColor=reports._rl(reports.GRAY))
        bad=Table(PDF_BAD,colWidths=[1.7*reports.inch,4.45*reports.inch],repeatRows=1)
        bad.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),reports._rl(reports.NAVY)),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),7.5),('GRID',(0,0),(-1,-1),.35,reports._rl(reports.LINE)),('BACKGROUND',(1,1),(1,1),reports._rl(reports.GREEN_FILL)),('BACKGROUND',(1,2),(1,2),reports._rl(reports.AMBER_FILL)),('BACKGROUND',(1,3),(1,3),reports._rl(reports.RED_FILL))]))
        erss=Table(ERSS,colWidths=[1.55*reports.inch,3.85*reports.inch,.75*reports.inch],repeatRows=1)
        erss.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),reports._rl(reports.NAVY)),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),7.1),('GRID',(0,0),(-1,-1),.35,reports._rl(reports.LINE))]))
        appendix=[Paragraph('HC BAD-D reference points',sec),bad,Paragraph('BAD-D is read from the Pentacam BAD display and is independent of Randleman/ERSS anterior-topography scoring.',tiny),Paragraph('Randleman / ERSS scoring points',sec),erss,Paragraph('Randleman anterior-topography points are derived only from a qualifying anterior curvature/topography image. On Pentacam 4 Maps Refractive this is the upper-left Axial/Sagittal Curvature (Front) panel; elevation, pachymetry and BAD displays cannot generate this score. ERSS total: 0-2 low, 3 moderate, >=4 high.',tiny),Spacer(1,8)]
        story[idx:idx]=appendix
        return orig_build(doc,story,*a,**kw)
    reports.SimpleDocTemplate.build=patched_build
    try:return _orig_pdf(payload)
    finally:reports.SimpleDocTemplate.build=orig_build

def build_docx(payload):
    # Intercept heading creation; insert native Word tables immediately before Interpretation note.
    orig_heading=reports._add_heading
    def patched_heading(document,text,level=1):
        if text=='Interpretation note':
            orig_heading(document,'HC BAD-D reference points',1)
            t=document.add_table(rows=1,cols=2);t.style='Table Grid';t.rows[0].cells[0].text='Final BAD-D';t.rows[0].cells[1].text='HC interpretation / action'
            for row in PDF_BAD[1:]:
                c=t.add_row().cells;c[0].text=row[0];c[1].text=row[1]
            reports._style_doc_table(t,[1.6,4.25],header=True)
            p=document.add_paragraph('BAD-D is read from the Pentacam BAD display and is independent of Randleman/ERSS anterior-topography scoring.');p.runs[0].font.size=Pt(8)
            orig_heading(document,'Randleman / ERSS scoring points',1)
            e=document.add_table(rows=1,cols=3);e.style='Table Grid'
            for j,x in enumerate(ERSS[0]):e.rows[0].cells[j].text=x
            for row in ERSS[1:]:
                c=e.add_row().cells
                for j,x in enumerate(row):c[j].text=x
            reports._style_doc_table(e,[1.5,3.65,.7],header=True)
            p=document.add_paragraph('Randleman anterior-topography points are derived only from the anterior curvature/topography image; on Pentacam 4 Maps Refractive this is the upper-left Axial/Sagittal Curvature (Front) panel. ERSS total: 0-2 low, 3 moderate, >=4 high.');p.runs[0].font.size=Pt(8)
        return orig_heading(document,text,level)
    reports._add_heading=patched_heading
    try:return _orig_docx(payload)
    finally:reports._add_heading=orig_heading

reports.build_pdf=build_pdf
reports.build_docx=build_docx
