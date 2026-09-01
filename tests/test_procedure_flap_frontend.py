"""Procedure-specific flap UI checks without a browser or patient data."""
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_prk_clears_and_disables_flap_then_lasik_restores_default():
    if not shutil.which("node"):
        pytest.skip("Node is not available")
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync('static/index.html','utf8');
class Field{
  constructor(value=''){this.value=value;this.disabled=false;this.listeners={};this.options=[{textContent:'Select'}];}
  addEventListener(type,fn){(this.listeners[type]??=[]).push(fn);}
  dispatchEvent(event){for(const fn of this.listeners[event.type]||[])fn(event);}
}
const fields={
  od_procedure:new Field(''),od_flap:new Field('100'),
  os_procedure:new Field(''),os_flap:new Field('100'),
};
const context={document:{getElementById:id=>fields[id]},i18n:{translate:value=>value}};
vm.createContext(context);
const start=html.indexOf('function syncProcedureSpecificInputs(');
const end=html.indexOf('// Manifest is the surgeon',start);
vm.runInContext(html.slice(start,end),context);
fields.od_procedure.value='PRK';
fields.od_procedure.dispatchEvent({type:'change'});
assert.equal(fields.od_flap.value,'');
assert.equal(fields.od_flap.disabled,true);
assert.equal(fields.od_flap.options[0].textContent,'None');
fields.od_procedure.value='LASIK';
fields.od_procedure.dispatchEvent({type:'change'});
assert.equal(fields.od_flap.value,'100');
assert.equal(fields.od_flap.disabled,false);
assert.equal(fields.od_flap.options[0].textContent,'Select');
'''
    subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
