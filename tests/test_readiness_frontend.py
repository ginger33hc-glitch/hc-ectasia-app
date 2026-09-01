"""Pure JavaScript unit checks; no browser, network, or patient data."""
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_frontend_js_syntax_and_manual_role_preservation():
    if not shutil.which('node'):
        pytest.skip('Node is not available')
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync('static/index.html','utf8');
for(const match of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g))new vm.Script(match[1]);
new vm.Script(fs.readFileSync('static/assessment-readiness.js','utf8'));
const fields={};
for(const eye of ['od','os'])for(const suffix of ['manifest_sphere','manifest_cylinder','sphere','cylinder','axis'])fields['#'+eye+'_'+suffix]={value:''};
fields['#od_manifest_sphere'].value='−7,50';fields['#od_manifest_cylinder'].value='-1.50';fields['#od_axis'].value='8';
fields['#os_manifest_sphere'].value='-4';
const context={document:{querySelector:key=>fields[key]},value:key=>String(fields['#'+key].value),cardTransferNote:{},correctionText:()=>''};
vm.createContext(context);
vm.runInContext(html.slice(html.indexOf('function applyEffectivePlans('),html.indexOf('function listBlock(')),context);
context.applyEffectivePlans({OD:{correction_source:'card',manifest_sphere_D:-6,manifest_cylinder_magnitude_D:2,intended_sphere_D:-6,intended_cylinder_magnitude_D:2,correction_axis_deg:90},OS:{correction_source:'card',manifest_sphere_D:-6,manifest_cylinder_magnitude_D:2}});
assert.equal(fields['#od_manifest_sphere'].value,'−7,50');assert.equal(fields['#od_manifest_cylinder'].value,'-1.50');assert.equal(fields['#od_axis'].value,'8');
assert.equal(fields['#od_sphere'].value,-6);assert.equal(fields['#od_cylinder'].value,-2);
assert.equal(fields['#os_manifest_cylinder'].value,'');
const ctx={window:{}};vm.createContext(ctx);vm.runInContext(fs.readFileSync('static/assessment-readiness.js','utf8'),ctx);
const panel={hidden:false,replaceChildren(){},querySelectorAll(){return this.inputs||[];}};
const readiness=new ctx.window.HCReadiness(panel);
panel.inputs=[{value:'−0,61',tagName:'INPUT',dataset:{eye:'OD',measurement:'I_S'}}];
assert.equal(readiness.collect().OD.I_S,-.61);
panel.inputs[0].value='wrong';assert.throws(()=>readiness.collect());
readiness.reset();assert.equal(readiness.token,null);assert.equal(panel.hidden,true);
'''
    subprocess.run(['node', '-e', script], cwd=ROOT, check=True, capture_output=True, text=True)


def test_hidden_reports_stay_hidden_when_printing_and_after_edits():
    html = (ROOT / 'static/index.html').read_text()
    assert '.report-card[hidden]{display:none!important}' in html
    assert "if(lastReport&&!reportCard.hidden)window.print()" in html
    assert "f.addEventListener('input',()=>{reportCard.hidden=true;lastReport=null;})" in html
    assert "f.addEventListener('change',()=>{reportCard.hidden=true;lastReport=null;})" in html


def test_patient_age_completion_uses_one_shared_field():
    workflow = (ROOT / 'assessment_workflow.py').read_text()
    readiness = (ROOT / 'static/assessment-readiness.js').read_text()
    assert 'items.append(("PATIENT", "age"))' in workflow
    assert 'item.form_id===\'age\'' in readiness
    assert 'originalRow.hidden=true' in readiness
    assert 'original.required=false;input.required=true' in readiness
