/* CER-AI mobile transport: upload once, report server progress, then poll the job. */
(function(){
  const nativeFetch=window.fetch.bind(window);
  const ACTIVE_JOB_KEY='cerai_active_analysis_job_v1';
  const POLL_MS=1800;
  const RETRY_MS=3000;
  let assessmentActive=false;
  let wakeLock=null;
  let wakeRequested=false;
  let interruptWait=null;
  let progressTimer=null;
  let lastProgress=null;
  let elapsedAnchorMs=0;
  let elapsedAnchorAt=0;

  const urlPath=input=>{
    try{return new URL(typeof input==='string'?input:input.url,window.location.href).pathname;}
    catch{return String(input||'');}
  };
  const cloneHeaders=source=>new Headers(source||{});
  const jsonResponse=(payload,status=200)=>new Response(JSON.stringify(payload),{
    status,headers:{'Content-Type':'application/json'}
  });
  const isTurkish=()=>String(window.CERAI_I18N?.locale||'en').toLowerCase().startsWith('tr');
  const fieldLabel=field=>({
    I_S:'I-S',exam_date:isTurkish()?'muayene tarihi':'examination date',
    patient_age_years:isTurkish()?'hasta yaşı':'patient age',pentacam_qs:'Pentacam QS'
  })[field]||String(field).replaceAll('_',' ');
  const seconds=milliseconds=>Math.max(0,Math.floor(Number(milliseconds||0)/1000));

  function progressMessage(progress){
    const item=progress||{};
    const done=Number(item.completed_images||0);
    const total=Number(item.total_images||0);
    const fields=Array.isArray(item.fields)?item.fields.map(fieldLabel):[];
    if(isTurkish()){
      if(item.code==='UPLOADING')return `${total||''} Pentacam görüntüsü hazırlanıyor ve yükleniyor…`.trim();
      if(item.code==='IMAGES_RECEIVED')return 'Görüntüler sunucu tarafından alındı.';
      if(item.code==='ANALYZING_IMAGES')return `Pentacam görüntüleri analiz ediliyor — ${done}/${total} tamamlandı`;
      if(item.code==='VERIFYING_REQUIRED_VALUES')return fields.length
        ?`Okunamayan zorunlu değerler doğrulanıyor: ${fields.join(', ')}`
        :'Zorunlu değerler doğrulanıyor.';
      if(item.code==='CALCULATING_ASSESSMENT')return 'Klinik değerlendirme hesaplanıyor.';
      if(item.code==='COMPLETED')return 'Değerlendirme tamamlandı — rapor gösteriliyor.';
      return 'Değerlendirme sunucuda devam ediyor.';
    }
    if(item.code==='UPLOADING')return `Preparing and uploading ${total||''} Pentacam images…`.replace('  ',' ');
    if(item.code==='IMAGES_RECEIVED')return 'Images received by the server.';
    if(item.code==='ANALYZING_IMAGES')return `Analyzing Pentacam images — ${done} of ${total} completed`;
    if(item.code==='VERIFYING_REQUIRED_VALUES')return fields.length
      ?`Verifying unread required values: ${fields.join(', ')}`
      :'Verifying required values.';
    if(item.code==='CALCULATING_ASSESSMENT')return 'Calculating the clinical assessment.';
    if(item.code==='COMPLETED')return 'Assessment complete — displaying report.';
    return 'Assessment continues on the server.';
  }

  function renderProgress(progress,elapsedMs){
    if(progress)lastProgress=progress;
    if(Number.isFinite(Number(elapsedMs))){
      elapsedAnchorMs=Number(elapsedMs);
      elapsedAnchorAt=Date.now();
    }
    const target=document.getElementById('assessmentProgress');
    if(!target||!lastProgress)return;
    const elapsed=elapsedAnchorMs+(elapsedAnchorAt?Date.now()-elapsedAnchorAt:0);
    const elapsedText=isTurkish()?`Geçen süre: ${seconds(elapsed)} sn`:`Elapsed: ${seconds(elapsed)}s`;
    target.textContent=`${progressMessage(lastProgress)} ${elapsedText}`;
    target.hidden=false;
  }

  function startProgress(progress,elapsedMs=0){
    lastProgress=progress;
    elapsedAnchorMs=Number(elapsedMs)||0;
    elapsedAnchorAt=Date.now();
    renderProgress(progress,elapsedAnchorMs);
    clearInterval(progressTimer);
    progressTimer=setInterval(()=>renderProgress(),1000);
  }

  function stopProgress(){
    clearInterval(progressTimer);
    progressTimer=null;
  }

  function wait(ms){
    return new Promise(resolve=>{
      let finished=false;
      const finish=()=>{
        if(finished)return;
        finished=true;
        clearTimeout(timer);
        if(interruptWait===finish)interruptWait=null;
        resolve();
      };
      const timer=setTimeout(finish,ms);
      interruptWait=finish;
    });
  }

  function refreshNow(){
    if(assessmentActive&&interruptWait)interruptWait();
  }

  async function acquireWakeLock(){
    if(!assessmentActive||document.hidden||wakeLock||wakeRequested||!navigator.wakeLock)return;
    wakeRequested=true;
    try{
      wakeLock=await navigator.wakeLock.request('screen');
      wakeLock.addEventListener('release',()=>{wakeLock=null;},{once:true});
    }catch(error){
      // Wake lock is optional; server-side processing and polling still continue.
    }finally{wakeRequested=false;}
  }

  async function releaseWakeLock(){
    const held=wakeLock;
    wakeLock=null;
    if(held){try{await held.release();}catch(error){}}
  }

  function beginAssessment(progress){
    assessmentActive=true;
    startProgress(progress,0);
    acquireWakeLock();
  }

  function endAssessment(){
    assessmentActive=false;
    stopProgress();
    releaseWakeLock();
  }

  async function pollJob(jobId,headers){
    for(;;){
      try{
        const response=await nativeFetch(`/analysis/jobs/${encodeURIComponent(jobId)}`,{
          method:'GET',headers:cloneHeaders(headers),cache:'no-store',credentials:'same-origin'
        });
        const text=await response.text();
        let payload;try{payload=JSON.parse(text)}catch{payload={detail:text||'Invalid job response'};}
        if(payload.progress)renderProgress(payload.progress,payload.elapsed_ms);
        if(response.status===202){await wait(POLL_MS);continue;}
        if(response.ok&&payload.status==='COMPLETED'){
          localStorage.removeItem(ACTIVE_JOB_KEY);
          return jsonResponse(payload.result,200);
        }
        if(response.status===410)localStorage.removeItem(ACTIVE_JOB_KEY);
        return jsonResponse({detail:payload.detail||'Assessment job failed.'},response.status||500);
      }catch(error){
        // The phone may sleep, switch networks, or temporarily lose service.
        // The server job continues; resume short polling when connectivity returns.
        await wait(RETRY_MS);
      }
    }
  }

  document.addEventListener('visibilitychange',()=>{
    if(!document.hidden&&assessmentActive){acquireWakeLock();refreshNow();}
  });
  window.addEventListener('pageshow',refreshNow);
  window.addEventListener('online',refreshNow);

  window.fetch=async function(input,init={}){
    const path=urlPath(input);
    const method=String(init.method||'GET').toUpperCase();
    if(path!=='/analyze'||method!=='POST')return nativeFetch(input,init);

    const imageCount=init.body instanceof FormData?init.body.getAll('images').length:0;
    beginAssessment({code:'UPLOADING',total_images:imageCount});
    try{
      let started;
      try{
        started=await nativeFetch('/analysis/jobs',{
          ...init,
          method:'POST',
          credentials:'same-origin'
        });
      }catch(error){
        // Upload itself was not confirmed by the server. Preserve the original
        // network error so the existing UI can tell the surgeon to retry.
        throw error;
      }
      const text=await started.text();
      let payload;try{payload=JSON.parse(text)}catch{payload={detail:text||'Invalid upload response'};}
      if(!started.ok||!payload.job_id){
        return jsonResponse({detail:payload.detail||'Image upload could not be started.'},started.status||500);
      }
      localStorage.setItem(ACTIVE_JOB_KEY,payload.job_id);
      if(payload.progress)renderProgress(payload.progress,0);
      return await pollJob(payload.job_id,init.headers);
    }finally{
      endAssessment();
    }
  };

  window.CER_AI_AnalysisJobs={
    activeJob:()=>localStorage.getItem(ACTIVE_JOB_KEY),
    clear:()=>localStorage.removeItem(ACTIVE_JOB_KEY),
    refresh:refreshNow
  };
})();
