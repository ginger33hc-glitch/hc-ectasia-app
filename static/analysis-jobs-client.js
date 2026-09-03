/* CER-AI mobile transport shim: upload once, then poll a server-side job. */
(function(){
  const nativeFetch=window.fetch.bind(window);
  const ACTIVE_JOB_KEY='cerai_active_analysis_job_v1';
  const POLL_MS=1800;
  const RETRY_MS=3000;
  const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
  const urlPath=input=>{
    try{return new URL(typeof input==='string'?input:input.url,window.location.href).pathname;}
    catch{return String(input||'');}
  };
  const cloneHeaders=source=>new Headers(source||{});
  const jsonResponse=(payload,status=200)=>new Response(JSON.stringify(payload),{
    status,headers:{'Content-Type':'application/json'}
  });

  async function pollJob(jobId,headers){
    for(;;){
      try{
        const response=await nativeFetch(`/analysis/jobs/${encodeURIComponent(jobId)}`,{
          method:'GET',headers:cloneHeaders(headers),cache:'no-store',credentials:'same-origin'
        });
        const text=await response.text();
        let payload;try{payload=JSON.parse(text)}catch{payload={detail:text||'Invalid job response'};}
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

  window.fetch=async function(input,init={}){
    const path=urlPath(input);
    const method=String(init.method||'GET').toUpperCase();
    if(path!=='/analyze'||method!=='POST')return nativeFetch(input,init);

    // The original application still builds the canonical multipart FormData.
    // Only transport changes: upload it to a short-lived job endpoint first.
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
    return pollJob(payload.job_id,init.headers);
  };

  window.CER_AI_AnalysisJobs={
    activeJob:()=>localStorage.getItem(ACTIVE_JOB_KEY),
    clear:()=>localStorage.removeItem(ACTIVE_JOB_KEY)
  };
})();
