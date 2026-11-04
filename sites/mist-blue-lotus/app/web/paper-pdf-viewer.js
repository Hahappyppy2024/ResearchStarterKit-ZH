import * as pdfjs from './vendor/pdfjs/build/pdf.mjs';
pdfjs.GlobalWorkerOptions.workerSrc=new URL('./vendor/pdfjs/build/pdf.worker.mjs',import.meta.url).href;
let current=null,observer=null,version=0,zoom=1;
export async function mountPdf(url,host){
 current=await pdfjs.getDocument({url,isEvalSupported:false}).promise;
 document.getElementById('pdf-controls').hidden=false;
 document.getElementById('pdf-page-count').textContent='全文 '+current.numPages+' 页';
 const draw=async()=>{
  const stamp=++version;observer?.disconnect();host.replaceChildren();
  const first=await current.getPage(1),base=first.getViewport({scale:1});
  const scale=Math.max(.2,(host.clientWidth-34)/base.width)*zoom;
  document.getElementById('pdf-zoom-label').textContent=zoom===1?'适合宽度':Math.round(zoom*100)+'%';
  const drawPage=async box=>{if(box.dataset.rendered)return;box.dataset.rendered='true';const page=await current.getPage(Number(box.dataset.page));if(stamp!==version)return;const viewport=page.getViewport({scale}),ratio=Math.min(window.devicePixelRatio||1,2),canvas=document.createElement('canvas');canvas.width=Math.round(viewport.width*ratio);canvas.height=Math.round(viewport.height*ratio);canvas.setAttribute('aria-label','论文第 '+box.dataset.page+' 页');box.append(canvas);await page.render({canvasContext:canvas.getContext('2d'),viewport,transform:ratio===1?null:[ratio,0,0,ratio,0,0]}).promise;box.classList.add('rendered');};
  observer=new IntersectionObserver(entries=>{for(const entry of entries)if(entry.isIntersecting){observer.unobserve(entry.target);drawPage(entry.target).catch(()=>{entry.target.querySelector('.pdf-page-label').textContent='该页加载失败，请重试原文';});}},{root:host,rootMargin:'600px'});
  for(let i=1;i<=current.numPages;i++){const box=document.createElement('div');box.className='pdf-page';box.dataset.page=i;box.style.width=base.width*scale+'px';box.style.height=base.height*scale+'px';const label=document.createElement('span');label.className='pdf-page-label';label.textContent='第 '+i+' 页';box.append(label);host.append(box);observer.observe(box);}
  await drawPage(host.firstElementChild);
 };
 document.getElementById('pdf-zoom-in').onclick=()=>{zoom=Math.min(2.5,zoom+.15);draw();};
 document.getElementById('pdf-zoom-out').onclick=()=>{zoom=Math.max(.4,zoom-.15);draw();};
 document.getElementById('pdf-fit').onclick=()=>{zoom=1;draw();};
 let timer;new ResizeObserver(()=>{clearTimeout(timer);timer=setTimeout(draw,150);}).observe(host);
 await draw();
}
