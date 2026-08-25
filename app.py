
import os, json, base64, mimetypes
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI

app = FastAPI(title="HC Ectasia App v0.3")
app.mount("/static", StaticFiles(directory="static"), name="static")
client = OpenAI()
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-terra")

SCHEMA = {
  "type": "object",
  "additionalProperties": False,
  "properties": {
    "eyes": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
          "eye": {"type": "string", "enum": ["OD","OS","UNKNOWN"]},
          "screen_types": {"type": "array", "items": {"type":"string"}},
          "quality": {"type":"string", "enum":["ADEQUATE","LIMITED","INADEQUATE"]},
          "missing_or_unreadable": {"type":"array","items":{"type":"string"}},
          "K1_D":{"type":["number","null"]},"K2_D":{"type":["number","null"]},
          "Kmax_D":{"type":["number","null"]},"pachy_thinnest_um":{"type":["number","null"]},
          "BAD_D":{"type":["number","null"]},"Df":{"type":["number","null"]},
          "Db":{"type":["number","null"]},"Dp":{"type":["number","null"]},
          "Dt":{"type":["number","null"]},"Da":{"type":["number","null"]},
          "PPI_avg":{"type":["number","null"]},"PPI_max":{"type":["number","null"]},
          "ARTmax_um":{"type":["number","null"]},"ISV":{"type":["number","null"]},
          "IVA":{"type":["number","null"]},"KI":{"type":["number","null"]},
          "CKI":{"type":["number","null"]},"IHD":{"type":["number","null"]},
          "I_S":{"type":["number","null"]},"KISA":{"type":["number","null"]},
          "asymmetric_bow_tie":{"type":"string","enum":["YES","NO","UNCERTAIN"]},
          "srax":{"type":"string","enum":["YES","NO","UNCERTAIN"]},
          "srax_deg":{"type":["number","null"]},
          "posterior_pattern":{"type":"string","enum":["REASSURING","BORDERLINE","ABNORMAL","UNREADABLE"]}
        },
        "required":["eye","screen_types","quality","missing_or_unreadable","K1_D","K2_D","Kmax_D",
          "pachy_thinnest_um","BAD_D","Df","Db","Dp","Dt","Da","PPI_avg","PPI_max","ARTmax_um",
          "ISV","IVA","KI","CKI","IHD","I_S","KISA","asymmetric_bow_tie","srax","srax_deg","posterior_pattern"]
      }
    },
    "global_warnings":{"type":"array","items":{"type":"string"}}
  },
  "required":["eyes","global_warnings"]
}

PROMPT = """You are a data-extraction component for Pentacam corneal tomography photographs.
Extract only values visibly supported by the supplied images. Never guess an unreadable or absent number.
Identify OD/OS and screen types. Return null for unreadable/absent numeric values and list them in
missing_or_unreadable. Assess asymmetric bow-tie and SRAX only when the map is sufficiently visible;
otherwise UNCERTAIN. Do not make a surgical recommendation. Do not infer BAD-D from other values.
Treat this as transcription/structured image interpretation, not autonomous diagnosis."""

def data_url(raw: bytes, filename: str) -> str:
    mime = mimetypes.guess_type(filename)[0] or "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(raw).decode()

def limiting(eyes, key, mode):
    vals=[e.get(key) for e in eyes if isinstance(e.get(key),(int,float))]
    if not vals: return None
    return min(vals) if mode=="min" else max(vals)

def hc_engine(extracted, prior, age, procedure, sphere, cylinder, ablation, flap, stable):
    eyes=extracted.get("eyes",[])
    warnings=list(extracted.get("global_warnings",[]))
    missing=[]
    if prior not in ("no","yes","unknown"): missing.append("prior surgery status")
    if procedure not in ("PRK","LASIK"): missing.append("procedure")
    if sphere is None: missing.append("intended sphere")
    if cylinder is None: missing.append("cylinder")
    if stable not in ("yes","no"): missing.append("refractive stability")

    pachy=limiting(eyes,"pachy_thinnest_um","min")
    bad=limiting(eyes,"BAD_D","max")
    art=limiting(eyes,"ARTmax_um","min")
    ppi=limiting(eyes,"PPI_max","max")
    if pachy is None: missing.append("thinnest pachymetry")

    suspicious_morph=any(e.get("asymmetric_bow_tie")=="YES" or e.get("srax")=="YES" for e in eyes)
    ectatic_like=any(
        (isinstance(e.get("BAD_D"),(int,float)) and e["BAD_D"]>=2.6 and
         isinstance(e.get("ARTmax_um"),(int,float)) and e["ARTmax_um"]<300)
        for e in eyes
    )

    if ablation is None and sphere is not None and cylinder is not None:
        ablation=(abs(sphere)+abs(cylinder))*12.0
        warnings.append("Maximum ablation estimated with HC 12 µm/D convention; actual laser plan preferred.")

    rst = pachy-50-ablation if pachy is not None and ablation is not None else None
    rsb = pachy-flap-ablation if pachy is not None and ablation is not None else None
    pta = (flap+ablation)/pachy*100 if pachy is not None and ablation is not None else None

    status="PASS"
    reasons=[]
    if prior=="yes":
        status="POST-REFRACTIVE PATHWAY REQUIRED"; reasons.append("Prior corneal refractive surgery.")
    elif prior=="unknown":
        status="DATA INSUFFICIENT"; reasons.append("Prior surgery status unresolved.")
    elif pachy is not None and pachy < 480:
        status="DO NOT PROCEED"; reasons.append("HC hard stop: thinnest preoperative cornea <480 µm.")
    elif sphere is not None and sphere < -10:
        status="DO NOT PROCEED"; reasons.append("HC myopic treatment cutoff exceeded.")
    elif sphere is not None and sphere > 6:
        status="DO NOT PROCEED"; reasons.append("HC hyperopic treatment cutoff exceeded.")
    elif stable=="no":
        status="CAUTION — STOP/DEFER"; reasons.append("Refraction not stable.")
    elif procedure=="PRK" and rst is not None and rst < 310:
        status="DO NOT PROCEED"; reasons.append("HC PRK RST hard stop <310 µm.")
    elif procedure=="LASIK" and rsb is not None and rsb < 300:
        status="DO NOT PROCEED"; reasons.append("HC LASIK RSB hard stop <300 µm.")
    elif suspicious_morph and bad is None:
        status="BORDERLINE — TOMOGRAPHIC CHARACTERIZATION REQUIRED"
        reasons.append("Suspicious anterior morphology with BAD-D unavailable.")
    elif missing:
        status="DATA INSUFFICIENT"; reasons.append("Decision-critical data missing.")
    elif ectatic_like or (bad is not None and bad >= 1.6) or (art is not None and art < 370):
        status="BORDERLINE — FURTHER ASSESSMENT"
        reasons.append("One or more HC susceptibility signals require further assessment.")
    else:
        reasons.append("All currently implemented required HC parameters are within acceptable limits.")

    return {
      "status":status, "reasons":reasons, "warnings":warnings, "missing":sorted(set(missing)),
      "limiting_values":{"pachy_thinnest_um":pachy,"BAD_D":bad,"ARTmax_um":art,"PPI_max":ppi},
      "structural":{"max_ablation_um":ablation,"PRK_RST_um":rst,"LASIK_RSB_um":rsb,"LASIK_PTA_percent":pta}
    }

@app.get("/")
def index():
    return FileResponse("static/index.html")

@app.post("/analyze")
async def analyze(
    images: List[UploadFile] = File(...),
    prior: str = Form(...),
    age: int | None = Form(None),
    procedure: str = Form(...),
    sphere: float | None = Form(None),
    cylinder: float | None = Form(None),
    ablation: float | None = Form(None),
    flap: float = Form(100),
    stable: str = Form(...)
):
    if not images:
        raise HTTPException(400, "No images supplied.")
    content=[{"type":"input_text","text":PROMPT}]
    for img in images:
        raw=await img.read()
        if not raw: continue
        content.append({"type":"input_image","image_url":data_url(raw,img.filename),"detail":"original"})

    response=client.responses.create(
        model=MODEL,
        store=False,
        reasoning={"effort":"low"},
        input=[{"role":"user","content":content}],
        text={"format":{
          "type":"json_schema","name":"pentacam_extraction","strict":True,"schema":SCHEMA
        }}
    )
    extracted=json.loads(response.output_text)
    decision=hc_engine(extracted,prior,age,procedure,sphere,cylinder,ablation,flap,stable)
    return {"extracted":extracted,"decision":decision}
