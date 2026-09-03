/* Input completion only. Clinical completeness and scores are owned by the server. */
(function installSourceImageRetention(){
  if(typeof window==='undefined'||typeof document==='undefined')return;
  const imageInput=document.getElementById('imageInput');
  if(!imageInput||typeof DataTransfer==='undefined')return;
  const MAX_IMAGES=6;
  let retained=[];
  let replaying=false;

  const sameFile=(a,b)=>a&&b&&a.name===b.name&&a.size===b.size&&a.lastModified===b.lastModified;
  const setFiles=files=>{
    const transfer=new DataTransfer();
    files.slice(0,MAX_IMAGES).forEach(file=>transfer.items.add(file));
    imageInput.files=transfer.files;
    retained=[...imageInput.files];
  };
  const ageSnapshot=()=>{
    const input=document.getElementById('age');
    const row=document.getElementById('manualAgeRow');
    if(!input)return null;
    return {value:input.value,readOnly:input.readOnly,required:input.required,rowHidden:row?row.hidden:null};
  };
  const restoreAge=snapshot=>{
    if(!snapshot)return;
    queueMicrotask(()=>{
      const input=document.getElementById('age');
      const row=document.getElementById('manualAgeRow');
      if(!input)return;
      input.value=snapshot.value;input.readOnly=snapshot.readOnly;input.required=snapshot.required;
      if(row&&snapshot.rowHidden!==null)row.hidden=snapshot.rowHidden;
    });
  };
  const chooseReplacementIndex=files=>{
    const list=files.map((file,index)=>`${index+1}. ${file.name}`).join('\n');
    const locale=window.CERAI_I18N?.locale;
    const promptText=locale==='tr'
      ?`Altı görüntü zaten yüklü. Değiştirilecek görüntünün numarasını girin:\n${list}`
      :`Six images are already loaded. Enter the number of the image to replace:\n${list}`;
    const value=window.prompt(promptText,'');
    if(value===null)return null;
    const index=Number.parseInt(value,10)-1;
    return Number.isInteger(index)&&index>=0&&index<files.length?index:null;
  };
  const sharedFilesFromRenderedLinks=async()=>{
    if(!window.caches)return [];
    const links=[...document.querySelectorAll('#selectedFiles a.selected-file')]
      .map(link=>({url:link.getAttribute('href')||'',name:(link.textContent||'shared-image.jpg').trim()}))
      .filter(item=>item.url.includes('/__hc_share__/'));
    if(!links.length)return [];
    const cache=await caches.open('hc-ectasia-shared-images-v1');
    const files=[];
    for(const item of links){
      const response=await cache.match(item.url);
      if(!response)continue;
      const blob=await response.blob();
      files.push(new File([blob],item.name,{type:blob.type||'image/jpeg',lastModified:Date.now()}));
    }
    return files;
  };
  const mergeFiles=(base,selected)=>{
    const next=[...base];
    for(const file of selected){
      const exact=next.findIndex(existing=>sameFile(existing,file));
      if(exact>=0){next[exact]=file;continue;}
      const sameName=next.findIndex(existing=>existing.name===file.name);
      if(sameName>=0){next[sameName]=file;continue;}
      if(next.length<MAX_IMAGES){next.push(file);continue;}
      const replaceIndex=chooseReplacementIndex(next);
      if(replaceIndex===null)return null;
      next[replaceIndex]=file;
    }
    return next;
  };

  imageInput.addEventListener('change',event=>{
    if(replaying)return;
    const selected=[...imageInput.files];
    if(!selected.length)return;
    if(!retained.length){
      const sharedLinks=document.querySelectorAll('#selectedFiles a.selected-file[href*="/__hc_share__/"]');
      if(sharedLinks.length){
        event.stopImmediatePropagation();
        const snapshot=ageSnapshot();
        sharedFilesFromRenderedLinks().then(shared=>{
          const merged=mergeFiles(shared,selected);
          if(!merged){setFiles(shared);restoreAge(snapshot);return;}
          setFiles(merged);replaying=true;imageInput.dispatchEvent(new Event('change',{bubbles:true}));replaying=false;restoreAge(snapshot);
        }).catch(()=>{
          setFiles(selected);replaying=true;imageInput.dispatchEvent(new Event('change',{bubbles:true}));replaying=false;restoreAge(snapshot);
        });
        return;
      }
      retained=[...selected];
      return;
    }
    const snapshot=ageSnapshot();
    const merged=selected.length>=5?selected.slice(0,MAX_IMAGES):mergeFiles(retained,selected);
    if(!merged){event.stopImmediatePropagation();setFiles(retained);restoreAge(snapshot);return;}
    setFiles(merged);restoreAge(snapshot);
  },true);

  const wrapper=imageInput.closest('.file-picker-wrap')||imageInput.parentElement;
  if(wrapper&&!document.getElementById('source-image-retention-note')){
    const note=document.createElement('p');note.id='source-image-retention-note';note.className='note';
    note.textContent=window.CERAI_I18N?.locale==='tr'
      ?'Eksik veya okunamayan bir kaynak görüntü istenirse yalnızca yeni görüntüyü seçin. Mevcut hasta bilgileri ve seçilmiş görüntüler korunur.'
      :'If a source image is missing or unreadable, select only the new/replacement image. Existing patient information and selected images are retained.';
    wrapper.append(note);
  }
  window.CER_AI_SourceImageRetention={openPicker:()=>imageInput.click(),files:()=>[...retained]};
})();

window.HCReadiness = class {
  constructor(panel) { this.panel=panel; this.regionUrls=[]; this.reset(); }
  reset() {
    for(const url of this.regionUrls||[])URL.revokeObjectURL(url);
    this.regionUrls=[];this.token=null;this.overrides={};this.hasCompletableInputs=false;this.panel.hidden=true;this.panel.replaceChildren();
  }
  async loadSourceRegion(container,item,index=0) {
    const tr=value=>window.CERAI_I18N?.translate(value)??value;
    const status=document.createElement('span');status.textContent=tr('Loading unread Pentacam/topography region...');container.append(status);
    try{
      const request=window.ceraiFetch||window.fetch.bind(window);
      const response=await request('/assessment/source-region',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({assessment_token:this.token,eye:item.eye,key:item.key,index})
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
    this.hasCompletableInputs=false;
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
        row.append(region);
        const count=Math.max(1,Number(item.source_region_count)||1);
        for(let index=0;index<count;index++)this.loadSourceRegion(region,item,index);
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
      if(input){this.hasCompletableInputs=true;input.id=`completion_${seen.size}`;label.htmlFor=input.id;row.append(input);}
      else {
        row.classList.add('completion-blocker');
        const help=document.createElement('span');help.textContent=tr(item.help);row.append(help);
        const replace=document.createElement('button');replace.type='button';replace.className='secondary';
        replace.textContent=window.CERAI_I18N?.locale==='tr'?'Kaynak görüntü ekle/değiştir':'Add/replace source image';
        replace.addEventListener('click',()=>window.CER_AI_SourceImageRetention?.openPicker());
        row.append(replace);
      }
      this.panel.append(row);
    }
    this.panel.scrollIntoView({behavior:'smooth',block:'start'});
    return true;
  }
};
