/* Input completion only. Clinical completeness and scores are owned by the server. */
window.HCReadiness = class {
  constructor(panel) { this.panel=panel; this.reset(); }
  reset() { this.token=null; this.overrides={}; this.panel.hidden=true; this.panel.replaceChildren(); }
  collect() {
    for(const input of this.panel.querySelectorAll('[data-measurement]')) {
      if(!input.value.trim()) continue;
      let value=input.value;
      if(input.tagName!=='SELECT') {
        const raw=value.trim().replace(/\s+/g,'').replace(/[−–—﹣－]/g,'-').replace(/[＋﹢]/g,'+').replace(',','.');
        if(!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(raw)||!Number.isFinite(Number(raw)))
          throw new Error((window.CERAI_I18N?.locale==='tr'?'Geçerli bir sayı girin':'Enter a valid number for')+` ${input.dataset.eye} ${input.dataset.measurement}.`);
        value=Number(raw);
      }
      (this.overrides[input.dataset.eye]??={})[input.dataset.measurement]=value;
    }
    return this.overrides;
  }
  show(response) {
    this.token=response.assessment_token;
    this.panel.replaceChildren();
    this.panel.hidden=response.workflow_status!=='NEEDS_INPUT';
    if(this.panel.hidden)return false;
    const tr=value=>window.CERAI_I18N?.translate(value)??value;
    const heading=document.createElement('h3'); heading.textContent=tr('Required information — no report has been generated');
    this.panel.append(heading);
    const note=document.createElement('p');note.textContent=tr('Complete all items below, then continue. Existing inputs and image readings are retained. No calculation is required from the surgeon.');this.panel.append(note);
    const seen=new Set();
    for(const item of response.input_requests||[]) {
      const identity=[item.eye,item.form_id||item.key,item.kind].join(':');
      if(seen.has(identity))continue;seen.add(identity);
      const row=document.createElement('div');row.className='row';
      const label=document.createElement('label');label.textContent=`${item.eye}: ${tr(item.label)}`;row.append(label);
      let input;
      if(item.kind==='form') {
        const original=document.getElementById(item.form_id);
        if(original){
          input=original.cloneNode(true);input.removeAttribute('id');input.removeAttribute('name');input.removeAttribute('required');
          input.readOnly=false;input.value=original.value;
          input.addEventListener('input',()=>{original.value=input.value;original.setCustomValidity('');original.dispatchEvent(new Event('input',{bubbles:true}));});
          input.addEventListener('change',()=>{original.value=input.value;original.dispatchEvent(new Event('change',{bubbles:true}));});
        }
      }else if(item.kind==='number'||item.kind==='select') {
        input=document.createElement(item.kind==='select'?'select':'input');
        if(item.kind==='select')for(const value of ['',...(item.options||[])]){const option=document.createElement('option');option.value=value;option.textContent=tr(value||'Select');input.append(option);}
        else {input.type='text';input.inputMode='decimal';input.autocomplete='off';}
        input.dataset.measurement=item.key;input.dataset.eye=item.eye;
        input.value=this.overrides[item.eye]?.[item.key]??'';
      }
      if(input){input.id=`completion_${seen.size}`;label.htmlFor=input.id;row.append(input);}
      else {const help=document.createElement('span');help.textContent=tr(item.help);row.append(help);}
      this.panel.append(row);
    }
    this.panel.scrollIntoView({behavior:'smooth',block:'start'});
    return true;
  }
};
