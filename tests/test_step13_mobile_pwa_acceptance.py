"""Stage 13 acceptance for the mobile and PWA clinical workflow."""
import json
from pathlib import Path
import shutil
import struct
import subprocess
import time
from types import SimpleNamespace
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

import analysis_job_service
import named_user_ui
import operational_security
import public_site
import user_access


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", data[16:24])


def test_manifest_opens_the_clinical_app_and_declares_the_image_share_target():
    manifest = json.loads((STATIC / "manifest.webmanifest").read_text(encoding="utf-8"))
    assert manifest["name"] == "CER-AI — Cornea Ectasia Risk Assessment Intelligence"
    assert manifest["short_name"] == "CER-AI"
    assert manifest["start_url"] == "/app"
    assert manifest["scope"] == "/"
    assert manifest["display"] == "standalone"
    target = manifest["share_target"]
    assert target == {
        "action": "/share-target",
        "method": "POST",
        "enctype": "multipart/form-data",
        "params": {"files": [{"name": "images", "accept": ["image/*"]}]},
    }
    expected_icons = {
        "icon-192.png": (192, 192),
        "icon-512.png": (512, 512),
        "icon-maskable-512.png": (512, 512),
        "apple-touch-icon.png": (180, 180),
    }
    for filename, size in expected_icons.items():
        assert _png_size(STATIC / "icons" / filename) == size


def test_share_worker_redirects_to_the_clinical_app_and_enforces_upload_limits():
    source = (STATIC / "sw.js").read_text(encoding="utf-8")
    assert "new URL(`/app?${parameters}`, self.location.origin).href" in source
    assert "MAX_SHARED_IMAGES = 6" in source
    assert "MAX_SHARED_IMAGE_BYTES = 20 * 1024 * 1024" in source
    assert "MAX_SHARED_TOTAL_BYTES = 80 * 1024 * 1024" in source
    assert 'clinicalRedirect(`share_token=${encodeURIComponent(token)}`)' in source
    assert 'Response.redirect(`/?share_token=' not in source
    assert 'Response.redirect("/?share_error=' not in source


def test_share_worker_behavior_uses_absolute_app_redirects():
    if not shutil.which("node"):
        pytest.skip("Node is not available")
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const listeners={};
class SharedFile extends Blob{constructor(parts,name,options={}){super(parts,options);this.name=name;this.lastModified=1;}}
const entries=new Map();
const cache={keys:async()=>[],delete:async()=>true,put:async(key,value)=>entries.set(String(key),value),match:async key=>entries.get(String(key))};
const context={self:{location:{origin:'https://cer-ai.test'},crypto:{randomUUID:()=> 'share-uuid'},addEventListener:(name,fn)=>listeners[name]=fn,skipWaiting(){},clients:{claim(){}}},File:SharedFile,Blob,Response,Request,URL,Date,Math,caches:{open:async()=>cache},console};
vm.createContext(context);vm.runInContext(fs.readFileSync('static/sw.js','utf8'),context);
(async()=>{
  const empty=await vm.runInContext('receiveSharedImages',context)({formData:async()=>({getAll:()=>[]})});
  assert.equal(empty.status,303);assert.equal(empty.headers.get('location'),'https://cer-ai.test/app?share_error=no_images');
  const file=new SharedFile(['image'],'OD.png',{type:'image/png'});
  const success=await vm.runInContext('receiveSharedImages',context)({formData:async()=>({getAll:()=>[file]})});
  assert.equal(success.status,303);assert.equal(success.headers.get('location'),'https://cer-ai.test/app?share_token=share-uuid');
  assert(entries.has('/__hc_share__/share-uuid/meta'));
})().catch(error=>{console.error(error);process.exit(1)});
'''
    subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)


def _job_client(monkeypatch):
    app = FastAPI()
    calls = []

    async def analyze(**kwargs):
        calls.append(kwargs)
        return {"workflow_status": "READY"}

    core = SimpleNamespace(app=app, analyze=analyze)
    monkeypatch.setattr(analysis_job_service, "_jobs", {})
    analysis_job_service.install(core)
    return TestClient(app), calls


def test_first_mobile_analysis_attempt_uses_a_canonical_uuid_and_retry_is_idempotent(monkeypatch):
    client, calls = _job_client(monkeypatch)
    data = {"age": "30", "assessment_request_id": "mobile-browser-request"}

    with client:
        first = client.post(
            "/analysis/jobs",
            files=[("images", ("OD.png", b"image", "image/png"))],
            data=data,
        )
        retry = client.post(
            "/analysis/jobs",
            files=[("images", ("OD.png", b"image", "image/png"))],
            data=data,
        )
        assert first.status_code == retry.status_code == 202
        job_id = first.json()["job_id"]
        assert UUID(job_id).version == 5
        assert retry.json()["job_id"] == job_id

        deadline = time.time() + 2
        while True:
            status = client.get(f"/analysis/jobs/{job_id}")
            if status.status_code != 202:
                break
            assert time.time() < deadline
            time.sleep(0.01)

    assert status.status_code == 200
    assert len(calls) == 1
    assert calls[0]["assessment_request_id"] == job_id


def _named_user_client():
    app = FastAPI()
    core = SimpleNamespace(
        app=app,
        _cerai_named_users_enabled=True,
        _cerai_authenticate_request=lambda _request: None,
        _cerai_bind_principal=user_access.bind_current_principal,
        _cerai_reset_principal=user_access.reset_current_principal,
        _cerai_case_archive_runtime=SimpleNamespace(enabled=False),
        _cerai_audit_log_installed=False,
        _cerai_historical_report_installed=False,
        _cerai_research_export_enabled=False,
    )
    operational_security.install(core)
    named_user_ui.install(core)
    return TestClient(app, base_url="https://testserver", follow_redirects=False)


def test_login_gate_preserves_only_valid_share_handoffs():
    with _named_user_client() as client:
        valid = client.get("/app?share_token=share-123")
        error = client.get("/app?share_error=image_too_large")
        invalid = client.get("/app?share_token=bad%20token&next=https://evil.test")
    assert valid.headers["location"] == "/auth/login-page?next=/app%3Fshare_token%3Dshare-123"
    assert error.headers["location"] == "/auth/login-page?next=/app%3Fshare_error%3Dimage_too_large"
    assert invalid.headers["location"] == "/auth/login-page?next=/app"


def test_login_pages_allow_the_validated_share_handoff_without_open_redirects():
    for filename in ("login.html", "trial-login.html"):
        source = (STATIC / filename).read_text(encoding="utf-8")
        assert "safeSharedApp" in source
        assert "[A-Za-z0-9-]{1,128}" in source
        assert "allowedNext.has(requested) || safeSharedApp" in source
        assert 'const next = requested' not in source


def test_shared_files_join_the_normal_source_retention_path():
    readiness = (STATIC / "assessment-readiness.js").read_text(encoding="utf-8")
    app = (STATIC / "index.html").read_text(encoding="utf-8")
    assert "adopt:files=>setFiles([...files])" in readiness
    assert 'typeof retention?.adopt==="function"' in app
    assert "retention.adopt(files)" in app
    assert "renderSelectedFiles(imageInput.files)" in app
    assert "sharedImages=[]" in app


def test_mobile_report_and_archive_actions_are_touch_and_popup_safe():
    app = (STATIC / "index.html").read_text(encoding="utf-8")
    archive = (STATIC / "archive.html").read_text(encoding="utf-8")
    assert 'window.open("about:blank","_blank")' in app
    assert "preview.location.replace(url)" in app
    assert "setTimeout(()=>URL.revokeObjectURL(url),60000)" in app
    assert "Open / Download PDF" in app
    assert ".report-toolbar button{flex:1 1 145px;min-height:44px}" in app
    assert ".links a,.source-button,.case-button{font-size:12px;min-height:40px" in archive
    assert ".source-close{min-height:44px}" in archive
    assert "input,select,button{font-size:16px}" in archive


def test_public_renderer_directly_owns_mobile_install_content_without_wrapper():
    assert not (ROOT / "mobile_install_section.py").exists()
    runtime = (ROOT / "runtime_composition.py").read_text(encoding="utf-8")
    assert "mobile_install_section" not in runtime

    app = FastAPI()
    public_site.install(SimpleNamespace(app=app))
    with TestClient(app) as client:
        page = client.get("/")
    assert page.status_code == 200
    assert page.text.count('id="mobile-install"') == 1
    assert "Install CER-AI on your phone" in page.text
    assert '/static/manifest.webmanifest?v=11' in page.text


def test_mobile_ui_uses_one_server_workflow_from_upload_through_archive():
    app = (STATIC / "index.html").read_text(encoding="utf-8")
    job_client = (STATIC / "analysis-jobs-client.js").read_text(encoding="utf-8")
    archive = (STATIC / "archive.html").read_text(encoding="utf-8")
    access_ui = (ROOT / "named_user_ui.py").read_text(encoding="utf-8")
    assert "'/analysis/jobs'" in job_client
    assert "`/analysis/jobs/${encodeURIComponent(jobId)}`" in job_client
    assert "ceraiFetch('/assessment/complete'" in app
    assert "ceraiFetch(`/report/${kind}`" in app
    assert 'href="/archive-ui"' in access_ui
    assert 'request("/archive/search"' in archive
