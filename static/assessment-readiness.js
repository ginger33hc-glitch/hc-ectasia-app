/* Input completion only. Clinical completeness and scores are owned by the server. */
window.HCReadiness = class {
  constructor(panel) { this.panel=panel; this.regionUrls=[]; this.reset(); }
  reset() {
    for(const url of this.regionUrls||[])URL.revokeObjectURL(url);
    this.regionUrls=[];this.token=null;this.overrides={};this.panel.hidden=true;this.panel.replaceChildren();
  }
  async loadSourceRegion(container,item) {
    const tr=value=>window.CERAI_I18N?.translate(value)??value;
    const status=document.createElement('span');status.textContent=tr('Loading unread Pentacam/topography region...');container.append(status);
    try{
      const request=window.ceraiFetch||window.fetch.bind(window);
      const response=await request('/assessment/source-region',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({assessment_token:this.token,eye:item.eye,key:item.key})
      });
      if(!response.ok)throw new Error('source region unavailable');
      const url=URL.createObjectURL(await response.blob());this.regionUrls.push(url);
      const image=document.createElement('img');image.src=url;image.alt=tr('Pentacam/topography region the application could not read');
      image.addEventListener('load',()=>status.remove());container.prepend(image);
    }catch(error){status.textContent=tr('The unread source region could not be displayed. Enter the value from the original Pentacam/topography image.');}
  }
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
    for(const url of this.regionUrls||[])URL.revokeObjectURL(url);
    this.regionUrls=[];
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
      const label=document.createElement('label');label.textContent=`${tr(item.eye)}: ${tr(item.label)}`;row.append(label);
      if(item.source_region){
        row.classList.add('completion-with-source');
        const region=document.createElement('div');region.className='completion-source-region';
        row.append(region);this.loadSourceRegion(region,item);
      }
      let input;
      if(item.kind==='form') {
        const original=document.getElementById(item.form_id);
        if(original){
          input=original.cloneNode(true);input.removeAttribute('id');input.removeAttribute('name');input.removeAttribute('required');
          input.readOnly=false;input.value=original.value;
          if(item.form_id==='age'){
            const originalRow=original.closest('.row');if(originalRow)originalRow.hidden=true;
            original.required=false;input.required=true;
          }
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
