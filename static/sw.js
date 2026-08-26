const SHARE_CACHE = "hc-ectasia-shared-images-v1";
const SHARE_PATH = "/share-target";

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", event => {
  event.waitUntil(self.clients.claim());
});

function shareToken(){
  if(self.crypto && typeof self.crypto.randomUUID === "function")return self.crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

async function receiveSharedImages(request){
  const formData=await request.formData();
  const files=formData.getAll("images").filter(item=>item instanceof File && item.type.startsWith("image/") && item.size>0);
  if(!files.length)return Response.redirect("/?share_error=no_images",303);

  const cache=await caches.open(SHARE_CACHE), token=shareToken(), metadata=[];
  for(let index=0;index<files.length;index+=1){
    const file=files[index], url=`/__hc_share__/${token}/${index}`;
    await cache.put(url,new Response(file,{headers:{"Content-Type":file.type||"application/octet-stream"}}));
    metadata.push({url,name:file.name||`shared-image-${index+1}.jpg`,type:file.type,lastModified:file.lastModified});
  }
  await cache.put(
    `/__hc_share__/${token}/meta`,
    new Response(JSON.stringify({files:metadata}),{headers:{"Content-Type":"application/json","Cache-Control":"no-store"}})
  );
  return Response.redirect(`/?share_token=${encodeURIComponent(token)}`,303);
}

self.addEventListener("fetch",event=>{
  const url=new URL(event.request.url);
  if(event.request.method==="POST" && url.origin===self.location.origin && url.pathname===SHARE_PATH){
    event.respondWith(receiveSharedImages(event.request));
  }
});
