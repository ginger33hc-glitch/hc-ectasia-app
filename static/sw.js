const SHARE_CACHE = "hc-ectasia-shared-images-v1";
const SHARE_PATH = "/share-target";
const SHARE_STORAGE_PATH = "/__hc_share__/";
const PUBLIC_HELPER_PATH = "/static/public-tr-home-overrides.js";
const MAX_SHARED_IMAGES = 6;
const MAX_SHARED_IMAGE_BYTES = 20 * 1024 * 1024;
const MAX_SHARED_TOTAL_BYTES = 80 * 1024 * 1024;

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", event => {
  event.waitUntil(self.clients.claim());
});

function shareToken(){
  if(self.crypto && typeof self.crypto.randomUUID === "function")return self.crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function clinicalRedirect(parameters){
  return Response.redirect(new URL(`/app?${parameters}`, self.location.origin).href, 303);
}

async function receiveSharedImages(request){
  const formData=await request.formData();
  const files=formData.getAll("images").filter(item=>item instanceof File && item.type.startsWith("image/") && item.size>0);
  if(!files.length)return clinicalRedirect("share_error=no_images");
  if(files.length>MAX_SHARED_IMAGES)return clinicalRedirect("share_error=too_many_images");
  if(files.some(file=>file.size>MAX_SHARED_IMAGE_BYTES))return clinicalRedirect("share_error=image_too_large");
  if(files.reduce((total,file)=>total+file.size,0)>MAX_SHARED_TOTAL_BYTES)return clinicalRedirect("share_error=images_too_large");

  const cache=await caches.open(SHARE_CACHE), token=shareToken(), metadata=[];
  // Only one shared assessment is active at a time. Removing an older set here
  // prevents abandoned Android shares from consuming persistent browser storage.
  for(const cachedRequest of await cache.keys())await cache.delete(cachedRequest);
  for(let index=0;index<files.length;index+=1){
    const file=files[index], url=`/__hc_share__/${token}/${index}`;
    await cache.put(url,new Response(file,{headers:{"Content-Type":file.type||"application/octet-stream"}}));
    metadata.push({url,name:file.name||`shared-image-${index+1}.jpg`,type:file.type,size:file.size,lastModified:file.lastModified});
  }
  await cache.put(
    `/__hc_share__/${token}/meta`,
    new Response(JSON.stringify({files:metadata}),{headers:{"Content-Type":"application/json","Cache-Control":"no-store"}})
  );
  return clinicalRedirect(`share_token=${encodeURIComponent(token)}`);
}

self.addEventListener("fetch",event=>{
  const url=new URL(event.request.url);
  if(event.request.method==="POST" && url.origin===self.location.origin && url.pathname===SHARE_PATH){
    event.respondWith(receiveSharedImages(event.request));
  }else if(event.request.method==="GET" && url.origin===self.location.origin && url.pathname===PUBLIC_HELPER_PATH){
    // The public homepage historically referenced this helper with a fixed ?v=1 URL.
    // Force a revalidated network request so mobile navigation/PWA presentation updates
    // are not hidden behind an older browser cache entry.
    event.respondWith(fetch(new Request(event.request,{cache:"reload"})));
  }else if(event.request.method==="GET" && url.origin===self.location.origin && url.pathname.startsWith(SHARE_STORAGE_PATH)){
    // Permit an explicit surgeon preview without copying every shared image
    // into page memory during initial load.
    event.respondWith(caches.open(SHARE_CACHE).then(cache=>cache.match(event.request)).then(response=>response||new Response("Not found",{status:404})));
  }
});
